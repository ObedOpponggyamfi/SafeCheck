"""Inspection service — the heart of the application.

Responsibilities:
* start / load inspections and their checklist questions
* record Yes / No / N/A answers with immediate auto-save
* compute the automatic result
* validate and submit, raising findings and queuing for sync
* provide the counts and lists the Home, History and Pending Sync screens need
"""
from __future__ import annotations

from datetime import date, datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from safecheck.core import models
from safecheck.core.enums import AnswerType, InspectionResult, ResultMode, SyncStatus
from safecheck.services import finding_service, sync_service


class InspectionValidationError(ValueError):
    """Raised when an inspection cannot be submitted. Carries the error list."""

    def __init__(self, errors: list[str]):
        self.errors = errors
        super().__init__("; ".join(errors))


# ---------------------------------------------------------------------------
# Templates and assets
# ---------------------------------------------------------------------------
def list_templates(session: Session) -> list[models.ChecklistTemplate]:
    """All active checklist templates."""
    return list(session.scalars(
        select(models.ChecklistTemplate)
        .where(models.ChecklistTemplate.is_active.is_(True))
        .order_by(models.ChecklistTemplate.name)
    ).all())


def get_template(session: Session, template_id: int) -> models.ChecklistTemplate | None:
    return session.get(models.ChecklistTemplate, template_id)


def list_assets_for_template(session: Session, template: models.ChecklistTemplate) -> list[models.Asset]:
    """Active assets whose category matches the template's category."""
    stmt = select(models.Asset).where(models.Asset.is_active.is_(True))
    if template.category_id is not None:
        stmt = stmt.where(models.Asset.category_id == template.category_id)
    return list(session.scalars(stmt.order_by(models.Asset.asset_number)).all())


def active_questions(session: Session, template_id: int) -> list[models.ChecklistQuestion]:
    """Ordered, active questions for a template."""
    return list(session.scalars(
        select(models.ChecklistQuestion)
        .where(
            models.ChecklistQuestion.template_id == template_id,
            models.ChecklistQuestion.is_active.is_(True),
        )
        .order_by(models.ChecklistQuestion.display_order)
    ).all())


# ---------------------------------------------------------------------------
# Inspection lifecycle
# ---------------------------------------------------------------------------
def start_inspection(
    session: Session,
    template_id: int,
    inspector_id: int,
    site_id: int | None = None,
) -> models.Inspection:
    """Create a new draft inspection and persist it immediately."""
    inspection = models.Inspection(
        template_id=template_id,
        inspector_id=inspector_id,
        site_id=site_id,
        sync_status=SyncStatus.DRAFT.value,
        start_time=datetime.now(timezone.utc),
    )
    session.add(inspection)
    session.commit()
    return inspection


def get_inspection(session: Session, inspection_id: int) -> models.Inspection | None:
    return session.get(models.Inspection, inspection_id)


def set_asset(session: Session, inspection: models.Inspection, asset: models.Asset | None) -> None:
    """Attach an asset and copy its number/registration onto the inspection."""
    inspection.asset_id = asset.id if asset else None
    if asset:
        inspection.asset_number_text = asset.asset_number
        inspection.registration_text = asset.registration_number
        inspection.vehicle_number = asset.registration_number or asset.asset_number
        if asset.department and not inspection.department_text:
            inspection.department_text = asset.department.name
        if asset.contractor and not inspection.contractor_text:
            inspection.contractor_text = asset.contractor.name
    session.commit()


def update_header(session: Session, inspection: models.Inspection, **fields) -> None:
    """Set arbitrary header attributes (driver, location, meter reading, …)."""
    for key, value in fields.items():
        if hasattr(inspection, key):
            setattr(inspection, key, value)
    session.commit()


def record_response(
    session: Session,
    inspection: models.Inspection,
    question_id: int,
    answer: str,
    comment: str | None = None,
) -> models.InspectionResponse:
    """Upsert a single answer and save immediately (crash-safe auto-save)."""
    response = session.scalars(
        select(models.InspectionResponse).where(
            models.InspectionResponse.inspection_id == inspection.id,
            models.InspectionResponse.question_id == question_id,
        )
    ).first()

    if response is None:
        response = models.InspectionResponse(
            inspection_id=inspection.id,
            question_id=question_id,
        )
        session.add(response)

    response.answer = answer
    if comment is not None:
        response.comment = comment
    session.commit()
    return response


def set_comment(
    session: Session,
    inspection: models.Inspection,
    question_id: int,
    comment: str,
) -> None:
    """Persist the failure comment for a question (auto-save)."""
    response = session.scalars(
        select(models.InspectionResponse).where(
            models.InspectionResponse.inspection_id == inspection.id,
            models.InspectionResponse.question_id == question_id,
        )
    ).first()
    if response is not None:
        response.comment = comment
        session.commit()


def responses_map(session: Session, inspection: models.Inspection) -> dict[int, models.InspectionResponse]:
    """Map of question_id -> response for quick UI lookups."""
    return {r.question_id: r for r in inspection.responses}


def progress(session: Session, inspection: models.Inspection) -> tuple[int, int]:
    """Return ``(answered, total)`` for the inspection's mandatory questions."""
    questions = active_questions(session, inspection.template_id)
    answered_ids = {
        r.question_id for r in inspection.responses
        if r.answer in (AnswerType.YES.value, AnswerType.NO.value, AnswerType.NA.value)
    }
    answered = sum(1 for q in questions if q.id in answered_ids)
    return answered, len(questions)


# ---------------------------------------------------------------------------
# Result calculation
# ---------------------------------------------------------------------------
def compute_result(session: Session, inspection: models.Inspection) -> str:
    """Derive the automatic inspection result from the recorded answers."""
    questions = {q.id: q for q in active_questions(session, inspection.template_id)}

    any_no_go_fail = False
    any_normal_fail = False
    for response in inspection.responses:
        question = questions.get(response.question_id)
        if question is None or response.answer != AnswerType.NO.value:
            continue
        if question.is_no_go:
            any_no_go_fail = True
        else:
            any_normal_fail = True

    visitor = inspection.template and inspection.template.result_mode == ResultMode.VISITOR.value
    if visitor:
        return (InspectionResult.ENTRY_DENIED.value if any_no_go_fail
                else InspectionResult.ENTRY_APPROVED.value)

    if any_no_go_fail:
        return InspectionResult.NO_GO.value
    if any_normal_fail:
        return InspectionResult.REQUIRES_ATTENTION.value
    return InspectionResult.FIT_FOR_USE.value


# ---------------------------------------------------------------------------
# Validation, draft and submission
# ---------------------------------------------------------------------------
def validate_submission(session: Session, inspection: models.Inspection) -> list[str]:
    """Return a list of reasons the inspection cannot yet be submitted."""
    errors: list[str] = []
    questions = active_questions(session, inspection.template_id)
    answers = responses_map(session, inspection)

    if inspection.asset_id is None:
        errors.append("Select the vehicle or machine before submitting.")

    unanswered = [
        q for q in questions
        if q.is_mandatory and (
            q.id not in answers
            or answers[q.id].answer not in (
                AnswerType.YES.value, AnswerType.NO.value, AnswerType.NA.value
            )
        )
    ]
    if unanswered:
        errors.append(f"Answer all questions ({len(unanswered)} still unanswered).")

    missing_comment = [
        q for q in questions
        if q.is_no_go
        and q.id in answers
        and answers[q.id].answer == AnswerType.NO.value
        and not (answers[q.id].comment or "").strip()
    ]
    if missing_comment:
        errors.append("Add a comment for every failed No-Go item.")

    return errors


def save_draft(session: Session, inspection: models.Inspection) -> None:
    """Keep the inspection as a draft (answers are already auto-saved)."""
    inspection.sync_status = SyncStatus.DRAFT.value
    session.commit()


def submit_inspection(session: Session, inspection: models.Inspection) -> models.Inspection:
    """Validate, finalise, raise findings and queue the inspection for sync."""
    errors = validate_submission(session, inspection)
    if errors:
        raise InspectionValidationError(errors)

    inspection.completion_time = datetime.now(timezone.utc)
    inspection.result = compute_result(session, inspection)
    finding_service.create_findings_for_inspection(session, inspection)
    sync_service.enqueue(session, inspection)  # sets status to Pending Sync
    session.commit()
    return inspection


# ---------------------------------------------------------------------------
# Dashboard counts and listings
# ---------------------------------------------------------------------------
def summary_counts(session: Session, inspector_id: int) -> dict[str, int]:
    """Counts for the Home summary cards, scoped to one inspector."""
    mine = select(models.Inspection).where(models.Inspection.inspector_id == inspector_id)

    def _count(stmt) -> int:
        return len(session.scalars(stmt).all())

    today = date.today()
    completed_today = sum(
        1 for insp in session.scalars(mine).all()
        if insp.completion_time and insp.completion_time.date() == today
    )
    drafts = _count(mine.where(models.Inspection.sync_status == SyncStatus.DRAFT.value))
    pending = _count(mine.where(models.Inspection.sync_status.in_(sync_service.PENDING_STATUSES)))
    no_go = _count(mine.where(models.Inspection.result.in_(
        [InspectionResult.NO_GO.value, InspectionResult.ENTRY_DENIED.value]
    )))
    open_findings = finding_service.count_open_findings(session, inspector_id)

    return {
        "completed_today": completed_today,
        "drafts": drafts,
        "pending": pending,
        "no_go": no_go,
        "open_findings": open_findings,
    }


def list_inspections(
    session: Session,
    inspector_id: int | None = None,
    statuses: list[str] | None = None,
    limit: int | None = None,
) -> list[models.Inspection]:
    """List inspections, newest first, optionally filtered by inspector/status."""
    stmt = select(models.Inspection)
    if inspector_id is not None:
        stmt = stmt.where(models.Inspection.inspector_id == inspector_id)
    if statuses:
        stmt = stmt.where(models.Inspection.sync_status.in_(statuses))
    stmt = stmt.order_by(models.Inspection.created_at.desc())
    if limit:
        stmt = stmt.limit(limit)
    return list(session.scalars(stmt).all())
