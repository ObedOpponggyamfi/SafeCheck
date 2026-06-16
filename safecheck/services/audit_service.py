"""Audit logging — records significant user/system actions to ``audit_logs``."""
from __future__ import annotations

from sqlalchemy.orm import Session

from safecheck.core import models


def record(
    session: Session,
    user_id: int | None,
    action: str,
    entity_type: str | None = None,
    entity_id: str | int | None = None,
    detail: str | None = None,
    commit: bool = False,
) -> models.AuditLog:
    """Append an audit-log entry.

    Pass ``commit=False`` (the default) to enrol the entry in the caller's
    transaction so it commits or rolls back atomically with the related changes.
    """
    entry = models.AuditLog(
        user_id=user_id,
        action=action,
        entity_type=entity_type,
        entity_id=str(entity_id) if entity_id is not None else None,
        detail=detail,
    )
    session.add(entry)
    if commit:
        session.commit()
    return entry
