"""Synchronisation service — local-first queue with safe retry.

In Phase One there is usually no server running, so inspections simply wait in
the queue with a "Pending Sync" status. The actual upload to the FastAPI server
is exercised in Phase Two; the queue, retry and de-duplication logic already
lives here so the field experience is complete.
"""
from __future__ import annotations

from datetime import datetime, timezone

import httpx
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from safecheck.config import SYNC_SERVER_URL, SYNC_TIMEOUT_SECONDS
from safecheck.core import models
from safecheck.core.enums import SyncStatus

# Statuses that still need to reach the server.
PENDING_STATUSES = (
    SyncStatus.PENDING_SYNC.value,
    SyncStatus.UPLOADING.value,
    SyncStatus.SYNC_FAILED.value,
)


def enqueue(session: Session, inspection: models.Inspection) -> models.SyncQueue:
    """Add (or refresh) the inspection's entry in the synchronisation queue.

    De-duplication is by inspection UUID so an inspection is never queued twice.
    """
    entry = session.scalars(
        select(models.SyncQueue).where(
            models.SyncQueue.inspection_uuid == inspection.uuid
        )
    ).first()
    if entry is None:
        entry = models.SyncQueue(
            inspection_id=inspection.id,
            inspection_uuid=inspection.uuid,
            status=SyncStatus.PENDING_SYNC.value,
        )
        session.add(entry)
    else:
        entry.status = SyncStatus.PENDING_SYNC.value
    inspection.sync_status = SyncStatus.PENDING_SYNC.value
    return entry


def list_pending(session: Session) -> list[models.Inspection]:
    """Inspections that have been submitted but not yet confirmed by the server."""
    return list(session.scalars(
        select(models.Inspection)
        .where(models.Inspection.sync_status.in_(PENDING_STATUSES))
        .order_by(models.Inspection.updated_at.desc())
    ).all())


def _build_payload(inspection: models.Inspection) -> dict:
    """Serialise an inspection for upload to the sync server.

    The payload is self-describing (question text, inspector, asset, etc.) so the
    central server can store a complete record even though its primary-key ids
    differ from the field device's.
    """
    template = inspection.template
    return {
        "uuid": inspection.uuid,
        "template_name": template.name if template else "",
        "result_mode": template.result_mode if template else "standard",
        "inspector_username": inspection.inspector.username if inspection.inspector else None,
        "inspector_name": inspection.inspector.full_name if inspection.inspector else None,
        "site_name": inspection.site.name if inspection.site else None,
        "asset_number": inspection.asset_number_text,
        "registration": inspection.registration_text,
        "department": inspection.department_text or inspection.host_department,
        "contractor": inspection.contractor_text or inspection.contractor_company,
        "general_comment": inspection.general_comment,
        "start_time": inspection.start_time.isoformat() if inspection.start_time else None,
        "completion_time": inspection.completion_time.isoformat()
        if inspection.completion_time else None,
        "result": inspection.result,
        "responses": [
            {
                "question_text": r.question.text if r.question else "",
                "answer": r.answer,
                "comment": r.comment,
                "is_no_go": r.question.is_no_go if r.question else False,
            }
            for r in inspection.responses
        ],
    }


def attempt_sync(session: Session, inspection: models.Inspection) -> tuple[bool, str]:
    """Try to upload one inspection. Returns ``(success, message)``.

    The local record is always retained; on failure the status becomes
    "Sync Failed" so the user can retry manually.
    """
    entry = enqueue(session, inspection)
    entry.attempts += 1
    entry.last_attempt_at = datetime.now(timezone.utc)
    inspection.sync_status = SyncStatus.UPLOADING.value
    entry.status = SyncStatus.UPLOADING.value

    try:
        response = httpx.post(
            f"{SYNC_SERVER_URL}/api/inspections",
            json=_build_payload(inspection),
            timeout=SYNC_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
    except (httpx.HTTPError, OSError) as exc:
        inspection.sync_status = SyncStatus.SYNC_FAILED.value
        entry.status = SyncStatus.SYNC_FAILED.value
        entry.last_error = str(exc)[:250]
        session.commit()
        return False, "Server unreachable — inspection will sync when online."

    inspection.sync_status = SyncStatus.SYNCED.value
    entry.status = SyncStatus.SYNCED.value
    entry.last_error = None
    session.commit()
    return True, "Inspection synchronised successfully."


def sync_all(session: Session) -> tuple[int, int]:
    """Attempt to sync every pending inspection. Returns ``(succeeded, failed)``."""
    succeeded = failed = 0
    for inspection in list_pending(session):
        ok, _ = attempt_sync(session, inspection)
        if ok:
            succeeded += 1
        else:
            failed += 1
    return succeeded, failed


def server_reachable(timeout: float = 1.5) -> bool:
    """Quick health probe of the sync server (used for the online/offline badge)."""
    try:
        return httpx.get(f"{SYNC_SERVER_URL}/health", timeout=timeout).status_code == 200
    except Exception:  # noqa: BLE001 — any failure means "offline"
        return False


def last_sync_time(session: Session):
    """Most recent successful synchronisation timestamp, or ``None``."""
    return session.scalar(
        select(func.max(models.SyncQueue.last_attempt_at))
        .where(models.SyncQueue.status == SyncStatus.SYNCED.value)
    )
