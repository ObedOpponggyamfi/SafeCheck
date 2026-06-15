"""Construction smoke test for the Flet UI.

Builds every screen against the seeded database using a stub page, so we catch
Flet 0.85 API mistakes without opening a desktop window. Run directly:

    python tests/ui_smoke.py
"""
from __future__ import annotations

import sys
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import flet as ft
from sqlalchemy import select

from safecheck.core import models
from safecheck.core.database import SessionLocal, init_db
from safecheck.data.seed import seed_all
from safecheck.services import auth_service
from safecheck.ui.app import SafeCheckApp
from safecheck.ui.views.inspection import InspectionScreen


class StubPage:
    """A minimal stand-in for ft.Page (no rendering, no event loop)."""

    def __init__(self):
        self.services = []
        self.controls = []
        self.title = None
        self.padding = None
        self.bgcolor = None

    def clean(self):
        self.controls = []

    def add(self, *controls):
        self.controls.extend(controls)

    def update(self):
        pass


def main() -> int:
    init_db()
    seed_all()

    page = StubPage()
    app = SafeCheckApp(page)

    with SessionLocal() as session:
        user = auth_service.authenticate(session, "officer1", "safecheck")
        site = session.scalars(select(models.Site)).first()
        lv = session.scalars(
            select(models.ChecklistTemplate).where(
                models.ChecklistTemplate.name == "Light Vehicle Inspection"
            )
        ).first()
        visitor = session.scalars(
            select(models.ChecklistTemplate).where(
                models.ChecklistTemplate.name == "Visitor Vehicle Inspection"
            )
        ).first()
        app.set_user(user_id=user.id, full_name=user.full_name, role="Safety Officer",
                     site_id=site.id, site_name=site.name, remember=False, username="officer1")
        lv_id, visitor_id = lv.id, visitor.id

    checks = [
        ("login", app.show_login),
        ("home", app.show_home),
        ("pending_sync", app.show_pending_sync),
        ("history", app.show_history),
        ("profile", app.show_profile),
    ]

    failures = 0
    for name, fn in checks:
        try:
            fn()
            assert page.controls, f"{name} produced no controls"
            print(f"  PASS  build {name}")
        except Exception:  # noqa: BLE001
            failures += 1
            print(f"  FAIL  build {name}")
            traceback.print_exc()

    # Inspection screens (both result modes), built and closed cleanly.
    for name, tid in [("light_vehicle", lv_id), ("visitor_vehicle", visitor_id)]:
        try:
            screen = InspectionScreen(app, tid)
            screen.build()
            # Exercise a couple of interactions that don't need a live page.
            first_q = screen.questions[0]
            screen._on_answer(first_q.id, "No")          # opens failure panel
            screen._save_comment(first_q.id, "Test note")  # auto-save comment
            screen._close()
            print(f"  PASS  build inspection:{name}")
        except Exception:  # noqa: BLE001
            failures += 1
            print(f"  FAIL  build inspection:{name}")
            traceback.print_exc()

    print(f"\n{'ALL UI SCREENS BUILD' if not failures else f'{failures} FAILURE(S)'}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
