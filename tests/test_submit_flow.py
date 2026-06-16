"""End-to-end tests for the submission flow and draft lifecycle.

Covers the scenarios that must hold before the Submit feature is trusted:
start/restore a draft, every answer type, normal vs No-Go failures, missing
asset/response, duplicate submit, offline pending-sync, audit logging, atomic
rollback on failure, and resuming a draft after an app "restart".
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker

from safecheck.core import models
from safecheck.core.database import Base
from safecheck.core.enums import AnswerType, InspectionResult, SyncStatus
from safecheck.data.seed import seed_all
from safecheck.services import auth_service, finding_service, inspection_service


def _make_db():
    """A shared in-memory engine + session factory (multiple sessions allowed)."""
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    Maker = sessionmaker(bind=engine, expire_on_commit=False, future=True)
    seed_all(Maker())
    return Maker


def _ctx(Maker, template_name="Light Vehicle Inspection"):
    session = Maker()
    user = auth_service.authenticate(session, "officer1", "safecheck")
    template = session.scalars(
        select(models.ChecklistTemplate).where(models.ChecklistTemplate.name == template_name)
    ).first()
    asset = inspection_service.list_assets_for_template(session, template)[0]
    return session, user, template, asset


def _answer_all(session, insp, answer=AnswerType.YES.value):
    for q in inspection_service.active_questions(session, insp.template_id):
        inspection_service.record_response(session, insp, q.id, answer)


def test_start_and_restore_draft():
    Maker = _make_db()
    session, user, template, asset = _ctx(Maker)
    insp = inspection_service.start_inspection(session, template.id, user.id)
    inspection_service.set_asset(session, insp, asset)
    q0 = inspection_service.active_questions(session, template.id)[0]
    inspection_service.record_response(session, insp, q0.id, AnswerType.YES.value)
    assert insp.sync_status == SyncStatus.DRAFT.value
    # Restore from the database (fresh map) — the answer survives.
    restored = inspection_service.get_inspection(session, insp.id)
    answers = inspection_service.responses_map(session, restored)
    assert answers[q0.id].answer == AnswerType.YES.value


def test_each_answer_type_records():
    Maker = _make_db()
    session, user, template, asset = _ctx(Maker)
    insp = inspection_service.start_inspection(session, template.id, user.id)
    qs = inspection_service.active_questions(session, template.id)
    inspection_service.record_response(session, insp, qs[0].id, AnswerType.YES.value)
    inspection_service.record_response(session, insp, qs[1].id, AnswerType.NA.value)
    inspection_service.record_response(session, insp, qs[2].id, AnswerType.NO.value, "comment")
    amap = inspection_service.responses_map(session, insp)
    assert {amap[qs[0].id].answer, amap[qs[1].id].answer, amap[qs[2].id].answer} == {
        AnswerType.YES.value, AnswerType.NA.value, AnswerType.NO.value}


def test_missing_asset_and_missing_response_block():
    Maker = _make_db()
    session, user, template, asset = _ctx(Maker)
    insp = inspection_service.start_inspection(session, template.id, user.id)
    _answer_all(session, insp)
    assert any("vehicle or machine" in e.lower() for e in
               inspection_service.validate_submission(session, insp))
    # With asset but one response cleared -> unanswered error.
    inspection_service.set_asset(session, insp, asset)
    qs = inspection_service.active_questions(session, template.id)
    resp = inspection_service.responses_map(session, insp)[qs[0].id]
    resp.answer = None
    session.commit()
    session.expire(insp, ["responses"])
    assert any("answer all questions" in e.lower() for e in
               inspection_service.validate_submission(session, insp))


def test_no_go_requires_comment_then_submits():
    Maker = _make_db()
    session, user, template, asset = _ctx(Maker)
    insp = inspection_service.start_inspection(session, template.id, user.id)
    inspection_service.set_asset(session, insp, asset)
    _answer_all(session, insp)
    no_go = next(q for q in inspection_service.active_questions(session, template.id) if q.is_no_go)
    inspection_service.record_response(session, insp, no_go.id, AnswerType.NO.value)
    assert any("comment" in e.lower() for e in
               inspection_service.validate_submission(session, insp))
    inspection_service.set_comment(session, insp, no_go.id, "Licence expired")
    inspection_service.submit_inspection(session, insp)
    assert insp.result == InspectionResult.NO_GO.value


def test_offline_submit_creates_pending_sync_audit_and_findings():
    Maker = _make_db()
    session, user, template, asset = _ctx(Maker)
    insp = inspection_service.start_inspection(session, template.id, user.id)
    inspection_service.set_asset(session, insp, asset)
    _answer_all(session, insp)
    normal = next(q for q in inspection_service.active_questions(session, template.id)
                  if not q.is_no_go)
    inspection_service.record_response(session, insp, normal.id, AnswerType.NO.value, "minor")
    inspection_service.submit_inspection(session, insp)

    assert insp.sync_status == SyncStatus.PENDING_SYNC.value
    assert insp.result == InspectionResult.REQUIRES_ATTENTION.value
    assert session.scalar(select(func.count(models.SyncQueue.id))
                          .where(models.SyncQueue.inspection_id == insp.id)) == 1
    assert session.scalar(select(func.count(models.AuditLog.id))
                          .where(models.AuditLog.action == "SUBMIT_INSPECTION")) == 1
    assert session.scalar(select(func.count(models.Finding.id))
                          .where(models.Finding.inspection_id == insp.id)) == 1


def test_duplicate_submit_is_idempotent():
    Maker = _make_db()
    session, user, template, asset = _ctx(Maker)
    insp = inspection_service.start_inspection(session, template.id, user.id)
    inspection_service.set_asset(session, insp, asset)
    _answer_all(session, insp)
    inspection_service.submit_inspection(session, insp)
    inspection_service.submit_inspection(session, insp)  # second click
    inspection_service.submit_inspection(session, insp)  # third click
    assert session.scalar(select(func.count(models.AuditLog.id))
                          .where(models.AuditLog.action == "SUBMIT_INSPECTION")) == 1
    assert session.scalar(select(func.count(models.SyncQueue.id))
                          .where(models.SyncQueue.inspection_id == insp.id)) == 1


def test_submit_rolls_back_on_failure_and_preserves_draft():
    Maker = _make_db()
    session, user, template, asset = _ctx(Maker)
    insp = inspection_service.start_inspection(session, template.id, user.id)
    inspection_service.set_asset(session, insp, asset)
    _answer_all(session, insp)

    # Force a failure midway through the submit transaction.
    original = finding_service.create_findings_for_inspection

    def _boom(*_a, **_k):
        raise RuntimeError("simulated failure")

    finding_service.create_findings_for_inspection = _boom
    try:
        raised = False
        try:
            inspection_service.submit_inspection(session, insp)
        except RuntimeError:
            raised = True
        assert raised
    finally:
        finding_service.create_findings_for_inspection = original

    # Everything rolled back: still a draft, no result, no audit/sync rows.
    session.expire_all()
    reloaded = inspection_service.get_inspection(session, insp.id)
    assert reloaded.sync_status == SyncStatus.DRAFT.value
    assert reloaded.result is None and reloaded.completion_time is None
    assert session.scalar(select(func.count(models.AuditLog.id))
                          .where(models.AuditLog.action == "SUBMIT_INSPECTION")) == 0
    assert session.scalar(select(func.count(models.SyncQueue.id))
                          .where(models.SyncQueue.inspection_id == insp.id)) == 0


def test_resume_draft_after_restart():
    Maker = _make_db()
    # "First run": create a draft and answer everything, then close the session.
    session1, user, template, asset = _ctx(Maker)
    insp = inspection_service.start_inspection(session1, template.id, user.id)
    inspection_service.set_asset(session1, insp, asset)
    _answer_all(session1, insp)
    insp_id = insp.id
    session1.close()

    # "After restart": a brand-new session loads the draft and submits it.
    session2 = Maker()
    resumed = inspection_service.get_inspection(session2, insp_id)
    assert resumed.sync_status == SyncStatus.DRAFT.value
    answered, total = inspection_service.progress(session2, resumed)
    assert answered == total
    inspection_service.submit_inspection(session2, resumed)
    assert resumed.result == InspectionResult.FIT_FOR_USE.value


def _run_all():
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for test in tests:
        test()
        print(f"  PASS  {test.__name__}")
    print(f"\n{len(tests)}/{len(tests)} tests passed.")


if __name__ == "__main__":
    _run_all()
