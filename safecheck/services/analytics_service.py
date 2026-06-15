"""Analytics service — aggregate counts for the dashboard screen."""
from __future__ import annotations

from collections import Counter
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from safecheck.core import models
from safecheck.core.enums import InspectionResult, SyncStatus
from safecheck.services import finding_service

# Display order for the result and sync breakdowns.
RESULT_ORDER = [
    InspectionResult.FIT_FOR_USE.value,
    InspectionResult.REQUIRES_ATTENTION.value,
    InspectionResult.NO_GO.value,
    InspectionResult.ENTRY_APPROVED.value,
    InspectionResult.ENTRY_DENIED.value,
]
SYNC_ORDER = [
    SyncStatus.DRAFT.value,
    SyncStatus.PENDING_SYNC.value,
    SyncStatus.UPLOADING.value,
    SyncStatus.SYNCED.value,
    SyncStatus.SYNC_FAILED.value,
]
_NO_GO_RESULTS = {InspectionResult.NO_GO.value, InspectionResult.ENTRY_DENIED.value}


def dashboard_data(session: Session, inspector_id: int | None = None) -> dict:
    """Return all aggregate figures the dashboard needs, scoped to one inspector."""
    stmt = select(models.Inspection)
    if inspector_id is not None:
        stmt = stmt.where(models.Inspection.inspector_id == inspector_id)
    inspections = list(session.scalars(stmt).all())

    result_counts = Counter(i.result for i in inspections if i.result)
    sync_counts = Counter(i.sync_status for i in inspections)
    by_checklist = Counter(i.template.name for i in inspections if i.template)

    today = date.today()
    week_start = today - timedelta(days=today.weekday())
    completed_today = sum(1 for i in inspections
                          if i.completion_time and i.completion_time.date() == today)
    this_week = sum(1 for i in inspections
                    if i.completion_time and i.completion_time.date() >= week_start)
    no_go = sum(1 for i in inspections if i.result in _NO_GO_RESULTS)

    return {
        "totals": {
            "inspections": len(inspections),
            "today": completed_today,
            "this_week": this_week,
            "no_go": no_go,
            "open_findings": finding_service.count_open_findings(session, inspector_id),
        },
        # Ordered (label, count) pairs, only including non-empty result/sync states.
        "results": [(r, result_counts.get(r, 0)) for r in RESULT_ORDER if result_counts.get(r, 0)],
        "sync": [(s, sync_counts.get(s, 0)) for s in SYNC_ORDER if sync_counts.get(s, 0)],
        "findings_by_status": finding_service.status_counts(session, inspector_id),
        "by_checklist": by_checklist.most_common(8),
    }
