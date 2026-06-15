"""Tests for the Phase Two machinery checklists and idempotent seeding."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker

from safecheck.core import models
from safecheck.core.database import Base
from safecheck.core.enums import AnswerType, InspectionResult
from safecheck.data.machinery_checklists import MACHINERY_TEMPLATES
from safecheck.data.seed import ALL_TEMPLATES, seed_all
from safecheck.services import auth_service, inspection_service


def _fresh_session():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine, expire_on_commit=False, future=True)()
    seed_all(session)
    return session


def _template(session, name):
    return session.scalars(
        select(models.ChecklistTemplate).where(models.ChecklistTemplate.name == name)
    ).first()


def test_all_templates_seeded():
    session = _fresh_session()
    templates = inspection_service.list_templates(session)
    assert len(templates) == len(ALL_TEMPLATES) == 11  # 2 Phase One + 9 machinery


def test_every_machinery_template_has_questions_and_an_asset():
    session = _fresh_session()
    for spec in MACHINERY_TEMPLATES:
        template = _template(session, spec["name"])
        assert template is not None, spec["name"]
        questions = inspection_service.active_questions(session, template.id)
        assert len(questions) == len(spec["questions"]) > 0
        assets = inspection_service.list_assets_for_template(session, template)
        assert assets, f"no demo asset for {spec['name']}"


def test_excavator_inspection_flow():
    session = _fresh_session()
    user = auth_service.authenticate(session, "officer1", "safecheck")
    template = _template(session, "Excavator Inspection")
    asset = inspection_service.list_assets_for_template(session, template)[0]

    insp = inspection_service.start_inspection(session, template.id, user.id)
    inspection_service.set_asset(session, insp, asset)
    for q in inspection_service.active_questions(session, template.id):
        inspection_service.record_response(session, insp, q.id, AnswerType.YES.value)
    inspection_service.submit_inspection(session, insp)
    assert insp.result == InspectionResult.FIT_FOR_USE.value


def test_seed_is_idempotent():
    session = _fresh_session()
    seed_all(session)  # run a second time
    seed_all(session)  # and a third
    assert session.scalar(select(func.count(models.ChecklistTemplate.id))) == 11
    # One demo asset per category in ASSETS — no duplicates after repeats.
    assert session.scalar(select(func.count(models.Asset.id))) == 14


def _run_all():
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for test in tests:
        test()
        print(f"  PASS  {test.__name__}")
    print(f"\n{len(tests)}/{len(tests)} tests passed.")


if __name__ == "__main__":
    _run_all()
