"""Tests for the dashboard analytics service (Phase Two)."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from safecheck.core import models
from safecheck.core.database import Base
from safecheck.core.enums import AnswerType, InspectionResult
from safecheck.data.seed import seed_all
from safecheck.services import analytics_service, auth_service, inspection_service


def _seed():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine, expire_on_commit=False, future=True)()
    seed_all(session)
    return session


def _submit(session, user, template, fail_no_go=False):
    asset = inspection_service.list_assets_for_template(session, template)[0]
    insp = inspection_service.start_inspection(session, template.id, user.id)
    inspection_service.set_asset(session, insp, asset)
    questions = inspection_service.active_questions(session, template.id)
    for q in questions:
        inspection_service.record_response(session, insp, q.id, AnswerType.YES.value)
    if fail_no_go:
        no_go = next(q for q in questions if q.is_no_go)
        inspection_service.record_response(session, insp, no_go.id, AnswerType.NO.value, "bad")
    inspection_service.submit_inspection(session, insp)
    return insp


def test_dashboard_aggregates():
    session = _seed()
    user = auth_service.authenticate(session, "officer1", "safecheck")
    template = session.scalars(
        select(models.ChecklistTemplate).where(
            models.ChecklistTemplate.name == "Light Vehicle Inspection")
    ).first()
    _submit(session, user, template, fail_no_go=False)  # Fit for Use
    _submit(session, user, template, fail_no_go=True)   # No Go

    data = analytics_service.dashboard_data(session, inspector_id=user.id)
    assert data["totals"]["inspections"] == 2
    assert data["totals"]["no_go"] == 1
    results = dict(data["results"])
    assert results.get(InspectionResult.FIT_FOR_USE.value) == 1
    assert results.get(InspectionResult.NO_GO.value) == 1
    assert dict(data["sync"]).get("Pending Sync") == 2
    assert data["findings_by_status"]["Open"] >= 1
    assert ("Light Vehicle Inspection", 2) in data["by_checklist"]


def _run_all():
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for test in tests:
        test()
        print(f"  PASS  {test.__name__}")
    print(f"\n{len(tests)}/{len(tests)} tests passed.")


if __name__ == "__main__":
    _run_all()
