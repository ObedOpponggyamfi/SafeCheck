"""Findings service — raise a finding for every failed checklist item."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from safecheck.core import models
from safecheck.core.enums import AnswerType, FindingStatus

# The order findings move through during remediation.
STATUS_FLOW = [
    FindingStatus.OPEN.value,
    FindingStatus.IN_PROGRESS.value,
    FindingStatus.PENDING_VERIFICATION.value,
    FindingStatus.CLOSED.value,
]


def create_findings_for_inspection(session: Session, inspection: models.Inspection) -> int:
    """Create an Open finding for each "No" response on *inspection*.

    Existing findings (by question) are skipped so re-submitting never creates
    duplicates. Returns the number of new findings created.
    """
    already = {
        f.question_id
        for f in session.scalars(
            select(models.Finding).where(models.Finding.inspection_id == inspection.id)
        )
    }

    created = 0
    for response in inspection.responses:
        if response.answer != AnswerType.NO.value:
            continue
        if response.question_id in already:
            continue

        question = response.question
        photo = session.scalars(
            select(models.InspectionPhoto).where(
                models.InspectionPhoto.response_id == response.id
            )
        ).first()

        session.add(models.Finding(
            inspection_id=inspection.id,
            question_id=question.id,
            checklist_name=inspection.template.name if inspection.template else None,
            failed_question_text=question.text,
            comment=response.comment,
            photo_path=photo.file_path if photo else None,
            asset_id=inspection.asset_id,
            department_text=inspection.department_text or inspection.host_department,
            contractor_text=inspection.contractor_text or inspection.contractor_company,
            inspector_id=inspection.inspector_id,
            is_no_go=question.is_no_go,
            status=FindingStatus.OPEN.value,
        ))
        created += 1

    return created


def count_open_findings(session: Session, inspector_id: int | None = None) -> int:
    """Count findings still in the Open state, optionally for one inspector."""
    stmt = select(models.Finding).where(models.Finding.status == FindingStatus.OPEN.value)
    if inspector_id is not None:
        stmt = stmt.where(models.Finding.inspector_id == inspector_id)
    return len(session.scalars(stmt).all())


# ---------------------------------------------------------------------------
# Findings workflow (Phase Two)
# ---------------------------------------------------------------------------
def list_findings(
    session: Session,
    inspector_id: int | None = None,
    status: str | None = None,
    limit: int | None = 200,
) -> list[models.Finding]:
    """List findings newest first, optionally filtered by inspector and status."""
    stmt = select(models.Finding).order_by(models.Finding.finding_date.desc())
    if inspector_id is not None:
        stmt = stmt.where(models.Finding.inspector_id == inspector_id)
    if status:
        stmt = stmt.where(models.Finding.status == status)
    if limit:
        stmt = stmt.limit(limit)
    return list(session.scalars(stmt).all())


def get_finding(session: Session, finding_id: int) -> models.Finding | None:
    return session.get(models.Finding, finding_id)


def set_finding_status(session: Session, finding: models.Finding, status: str) -> None:
    """Update a finding's status (Open / In Progress / Pending Verification / Closed)."""
    finding.status = status
    session.commit()


def add_corrective_action(
    session: Session,
    finding: models.Finding,
    description: str,
    responsible_person: str | None = None,
    due_date: datetime | None = None,
) -> models.CorrectiveAction:
    """Attach a corrective action to a finding."""
    action = models.CorrectiveAction(
        finding_id=finding.id,
        description=description,
        responsible_person=responsible_person,
        due_date=due_date,
        status=FindingStatus.OPEN.value,
    )
    session.add(action)
    session.commit()
    return action


def list_corrective_actions(session: Session, finding_id: int) -> list[models.CorrectiveAction]:
    return list(session.scalars(
        select(models.CorrectiveAction)
        .where(models.CorrectiveAction.finding_id == finding_id)
        .order_by(models.CorrectiveAction.created_at)
    ).all())


def status_counts(session: Session, inspector_id: int | None = None) -> dict[str, int]:
    """Count findings grouped by status (for filters and dashboards)."""
    counts: dict[str, int] = {}
    for status in STATUS_FLOW:
        stmt = select(func.count(models.Finding.id)).where(models.Finding.status == status)
        if inspector_id is not None:
            stmt = stmt.where(models.Finding.inspector_id == inspector_id)
        counts[status] = session.scalar(stmt) or 0
    return counts
