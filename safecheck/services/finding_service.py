"""Findings service — raise a finding for every failed checklist item."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from safecheck.core import models
from safecheck.core.enums import AnswerType, FindingStatus


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
