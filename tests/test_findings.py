"""Tests for the findings workflow service (Phase Two)."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from safecheck.core import models
from safecheck.core.database import Base
from safecheck.core.enums import AnswerType, FindingStatus
from safecheck.data.seed import seed_all
from safecheck.services import auth_service, finding_service, inspection_service


def _session_with_findings():
    """Seed a DB and submit one inspection that fails two items (2 findings)."""
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine, expire_on_commit=False, future=True)()
    seed_all(session)

    user = auth_service.authenticate(session, "officer1", "safecheck")
    template = session.scalars(
        select(models.ChecklistTemplate).where(
            models.ChecklistTemplate.name == "Light Vehicle Inspection")
    ).first()
    asset = inspection_service.list_assets_for_template(session, template)[0]
    insp = inspection_service.start_inspection(session, template.id, user.id)
    inspection_service.set_asset(session, insp, asset)
    questions = inspection_service.active_questions(session, template.id)
    for q in questions:
        inspection_service.record_response(session, insp, q.id, AnswerType.YES.value)
    no_go = next(q for q in questions if q.is_no_go)
    normal = next(q for q in questions if not q.is_no_go)
    inspection_service.record_response(session, insp, no_go.id, AnswerType.NO.value, "Expired")
    inspection_service.record_response(session, insp, normal.id, AnswerType.NO.value, "Minor")
    inspection_service.submit_inspection(session, insp)
    return session, user


def test_findings_listed_and_counted():
    session, user = _session_with_findings()
    findings = finding_service.list_findings(session, inspector_id=user.id)
    assert len(findings) == 2
    counts = finding_service.status_counts(session, inspector_id=user.id)
    assert counts[FindingStatus.OPEN.value] == 2
    # Filter by status.
    assert len(finding_service.list_findings(session, status=FindingStatus.CLOSED.value)) == 0


def test_status_transition_and_corrective_action():
    session, user = _session_with_findings()
    finding = finding_service.list_findings(session, inspector_id=user.id)[0]

    finding_service.set_finding_status(session, finding, FindingStatus.IN_PROGRESS.value)
    counts = finding_service.status_counts(session, inspector_id=user.id)
    assert counts[FindingStatus.IN_PROGRESS.value] == 1
    assert counts[FindingStatus.OPEN.value] == 1

    finding_service.add_corrective_action(
        session, finding, "Replace licence", responsible_person="Supervisor")
    actions = finding_service.list_corrective_actions(session, finding.id)
    assert len(actions) == 1 and actions[0].description == "Replace licence"


def _run_all():
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for test in tests:
        test()
        print(f"  PASS  {test.__name__}")
    print(f"\n{len(tests)}/{len(tests)} tests passed.")


if __name__ == "__main__":
    _run_all()
