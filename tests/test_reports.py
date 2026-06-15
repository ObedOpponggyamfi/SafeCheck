"""Tests for report generation (PDF + Excel)."""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from safecheck.core import models
from safecheck.core.database import Base
from safecheck.core.enums import AnswerType
from safecheck.data.seed import seed_all
from safecheck.services import auth_service, inspection_service, report_service


def _seed_with_inspection():
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
    inspection_service.record_response(session, insp, no_go.id, AnswerType.NO.value, "Expired")
    inspection_service.submit_inspection(session, insp)
    return session, insp


def test_all_reports_generate_non_empty_files():
    session, insp = _seed_with_inspection()
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        pdf = report_service.inspection_pdf(session, insp.id, out_path=tmp / "report.pdf")
        register = report_service.inspection_register_xlsx(session, out_path=tmp / "register.xlsx")
        failed = report_service.failed_items_xlsx(session, out_path=tmp / "failed.xlsx")
        no_go = report_service.no_go_xlsx(session, out_path=tmp / "nogo.xlsx")
        history = report_service.asset_history_xlsx(session, out_path=tmp / "history.xlsx")

        for path in (pdf, register, failed, no_go, history):
            p = Path(path)
            assert p.exists() and p.stat().st_size > 100, path

        # The PDF should start with the PDF magic header.
        assert Path(pdf).read_bytes().startswith(b"%PDF")


def _run_all():
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for test in tests:
        test()
        print(f"  PASS  {test.__name__}")
    print(f"\n{len(tests)}/{len(tests)} tests passed.")


if __name__ == "__main__":
    _run_all()
