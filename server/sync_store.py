"""Server-side storage of uploaded inspections (idempotent by UUID)."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from safecheck.core import models
from safecheck.core.enums import AnswerType, FindingStatus, SyncStatus
from server.schemas import InspectionUpload


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def _get_or_create(session: Session, model, defaults: dict | None = None, **filters):
    instance = session.scalars(select(model).filter_by(**filters)).first()
    if instance:
        return instance
    instance = model(**{**filters, **(defaults or {})})
    session.add(instance)
    session.flush()
    return instance


def store_inspection(session: Session, payload: InspectionUpload) -> tuple[str, models.Inspection, int]:
    """Persist an uploaded inspection. Returns ``(status, inspection, findings_created)``.

    De-duplication is by inspection UUID: a repeat upload returns the existing
    record with status ``"duplicate"`` and creates nothing new.
    """
    existing = session.scalars(
        select(models.Inspection).where(models.Inspection.uuid == payload.uuid)
    ).first()
    if existing is not None:
        return "duplicate", existing, 0

    template = _get_or_create(
        session, models.ChecklistTemplate, name=payload.template_name,
        defaults={"result_mode": payload.result_mode},
    )
    inspector = None
    if payload.inspector_username:
        inspector = session.scalars(
            select(models.User).where(models.User.username == payload.inspector_username)
        ).first()
    asset = None
    if payload.asset_number:
        asset = _get_or_create(
            session, models.Asset, asset_number=payload.asset_number,
            defaults={"registration_number": payload.registration, "category_id": template.category_id},
        )

    inspection = models.Inspection(
        uuid=payload.uuid,
        template_id=template.id,
        asset_id=asset.id if asset else None,
        inspector_id=inspector.id if inspector else None,
        asset_number_text=payload.asset_number,
        registration_text=payload.registration,
        department_text=payload.department,
        contractor_text=payload.contractor,
        general_comment=payload.general_comment,
        start_time=_parse_dt(payload.start_time) or datetime.utcnow(),
        completion_time=_parse_dt(payload.completion_time),
        result=payload.result,
        sync_status=SyncStatus.SYNCED.value,
    )
    session.add(inspection)
    session.flush()

    findings_created = 0
    for item in payload.responses:
        question = _get_or_create(
            session, models.ChecklistQuestion,
            template_id=template.id, text=item.question_text,
            defaults={"is_no_go": item.is_no_go, "comment_required_on_fail": item.is_no_go},
        )
        session.add(models.InspectionResponse(
            inspection_id=inspection.id, question_id=question.id,
            answer=item.answer, comment=item.comment,
        ))
        if item.answer == AnswerType.NO.value:
            session.add(models.Finding(
                inspection_id=inspection.id, question_id=question.id,
                checklist_name=template.name, failed_question_text=item.question_text,
                comment=item.comment, asset_id=asset.id if asset else None,
                department_text=payload.department, contractor_text=payload.contractor,
                inspector_id=inspector.id if inspector else None,
                is_no_go=item.is_no_go, status=FindingStatus.OPEN.value,
            ))
            findings_created += 1

    # Mirror into the sync queue so the server has a record of receipt.
    session.add(models.SyncQueue(
        inspection_id=inspection.id, inspection_uuid=inspection.uuid,
        status=SyncStatus.SYNCED.value,
    ))
    session.commit()
    return "created", inspection, findings_created
