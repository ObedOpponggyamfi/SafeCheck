"""Unit tests for the core inspection logic.

These tests run against an isolated in-memory SQLite database, so they never
touch the field application's real data file. Run with ``pytest`` or directly
with ``python tests/test_inspection_logic.py``.
"""
from __future__ import annotations

import sys
from pathlib import Path

# Allow running this file directly (python tests/test_inspection_logic.py).
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from safecheck.core import models
from safecheck.core.database import Base
from safecheck.core.enums import AnswerType, InspectionResult, SyncStatus
from safecheck.data.seed import seed_all
from safecheck.services import auth_service, inspection_service


def _fresh_session():
    """Build an isolated in-memory database seeded with demo data."""
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine, expire_on_commit=False, future=True)()
    seed_all(session)
    return session


def _template(session, name):
    return session.scalars(
        select(models.ChecklistTemplate).where(models.ChecklistTemplate.name == name)
    ).first()


def _answer_all(session, inspection, answer, comment=None):
    for q in inspection_service.active_questions(session, inspection.template_id):
        inspection_service.record_response(session, inspection, q.id, answer, comment)


def test_seed_creates_templates_and_users():
    session = _fresh_session()
    assert _template(session, "Light Vehicle Inspection") is not None
    assert _template(session, "Visitor Vehicle Inspection") is not None
    # Two safety officers among the demo users.
    officers = [u for u in session.scalars(select(models.User)).all()
                if u.role and u.role.name == "Safety Officer"]
    assert len(officers) == 2


def test_authentication():
    session = _fresh_session()
    assert auth_service.authenticate(session, "officer1", "safecheck") is not None
    assert auth_service.authenticate(session, "officer1", "wrong") is None
    assert auth_service.authenticate(session, "nobody", "safecheck") is None


def test_all_yes_is_fit_for_use():
    session = _fresh_session()
    user = auth_service.authenticate(session, "officer1", "safecheck")
    template = _template(session, "Light Vehicle Inspection")
    asset = inspection_service.list_assets_for_template(session, template)[0]

    insp = inspection_service.start_inspection(session, template.id, user.id)
    inspection_service.set_asset(session, insp, asset)
    _answer_all(session, insp, AnswerType.YES.value)

    assert inspection_service.validate_submission(session, insp) == []
    inspection_service.submit_inspection(session, insp)
    assert insp.result == InspectionResult.FIT_FOR_USE.value
    assert insp.sync_status == SyncStatus.PENDING_SYNC.value


def test_no_go_failure_requires_comment_and_blocks_until_present():
    session = _fresh_session()
    user = auth_service.authenticate(session, "officer1", "safecheck")
    template = _template(session, "Light Vehicle Inspection")
    asset = inspection_service.list_assets_for_template(session, template)[0]

    insp = inspection_service.start_inspection(session, template.id, user.id)
    inspection_service.set_asset(session, insp, asset)
    _answer_all(session, insp, AnswerType.YES.value)

    # Fail a No-Go question (Valid driver's licence) without a comment.
    no_go_q = next(q for q in inspection_service.active_questions(session, insp.template_id)
                   if q.is_no_go)
    inspection_service.record_response(session, insp, no_go_q.id, AnswerType.NO.value)

    errors = inspection_service.validate_submission(session, insp)
    assert any("comment" in e.lower() for e in errors)

    # Add the comment and it should submit as a No Go with a finding.
    inspection_service.set_comment(session, insp, no_go_q.id, "Licence expired")
    inspection_service.submit_inspection(session, insp)
    assert insp.result == InspectionResult.NO_GO.value
    findings = session.scalars(select(models.Finding)).all()
    assert len(findings) == 1 and findings[0].is_no_go is True


def test_normal_failure_is_requires_attention():
    session = _fresh_session()
    user = auth_service.authenticate(session, "officer1", "safecheck")
    template = _template(session, "Light Vehicle Inspection")
    asset = inspection_service.list_assets_for_template(session, template)[0]

    insp = inspection_service.start_inspection(session, template.id, user.id)
    inspection_service.set_asset(session, insp, asset)
    _answer_all(session, insp, AnswerType.YES.value)

    normal_q = next(q for q in inspection_service.active_questions(session, insp.template_id)
                    if not q.is_no_go)
    inspection_service.record_response(session, insp, normal_q.id, AnswerType.NO.value, "Minor")
    inspection_service.submit_inspection(session, insp)
    assert insp.result == InspectionResult.REQUIRES_ATTENTION.value


def test_visitor_entry_denied_on_no_go():
    session = _fresh_session()
    user = auth_service.authenticate(session, "officer1", "safecheck")
    template = _template(session, "Visitor Vehicle Inspection")
    asset = inspection_service.list_assets_for_template(session, template)[0]

    insp = inspection_service.start_inspection(session, template.id, user.id)
    inspection_service.set_asset(session, insp, asset)
    _answer_all(session, insp, AnswerType.YES.value)
    assert inspection_service.compute_result(session, insp) == InspectionResult.ENTRY_APPROVED.value

    no_go_q = next(q for q in inspection_service.active_questions(session, insp.template_id)
                   if q.is_no_go)
    inspection_service.record_response(session, insp, no_go_q.id, AnswerType.NO.value, "No licence")
    inspection_service.submit_inspection(session, insp)
    assert insp.result == InspectionResult.ENTRY_DENIED.value


def test_cannot_submit_without_asset():
    session = _fresh_session()
    user = auth_service.authenticate(session, "officer1", "safecheck")
    template = _template(session, "Light Vehicle Inspection")
    insp = inspection_service.start_inspection(session, template.id, user.id)
    _answer_all(session, insp, AnswerType.YES.value)
    errors = inspection_service.validate_submission(session, insp)
    assert any("vehicle or machine" in e.lower() for e in errors)


def _run_all():
    """Tiny runner so the file works without pytest installed."""
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    passed = 0
    for test in tests:
        test()
        print(f"  PASS  {test.__name__}")
        passed += 1
    print(f"\n{passed}/{len(tests)} tests passed.")


if __name__ == "__main__":
    _run_all()
