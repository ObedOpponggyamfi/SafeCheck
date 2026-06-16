"""Application controller — holds session state and switches screens.

Flet 0.85 removed the ``page.views`` stack, so navigation here is explicit:
each ``show_*`` method clears the page and adds the freshly built screen (plus a
bottom navigation bar on the main screens).
"""
from __future__ import annotations

import flet as ft

from safecheck.config import APP_NAME, DATA_DIR
from safecheck.ui import theme
from safecheck.ui.views.dashboard import build_dashboard
from safecheck.ui.views.findings import build_finding_detail, build_findings
from safecheck.ui.views.history import build_history
from safecheck.ui.views.home import build_home
from safecheck.ui.views.inspection import InspectionScreen
from safecheck.ui.views.login import build_login
from safecheck.ui.views.pending_sync import build_pending_sync
from safecheck.ui.views.profile import build_profile
from safecheck.ui.views.review import build_review
from safecheck.ui.views.success import build_success

# Stores the last username when "Remember me" is ticked.
REMEMBER_FILE = DATA_DIR / "last_user.txt"


class SafeCheckApp:
    """Owns the Flet page, the logged-in user and all navigation."""

    def __init__(self, page: ft.Page):
        self.page = page

        # Logged-in user state (set on successful login).
        self.user_id: int | None = None
        self.user_name: str = ""
        self.user_role: str = ""
        self.username: str = ""
        self.site_id: int | None = None
        self.site_name: str = "—"

        # A single file picker service shared by the inspection screen.
        self.file_picker = ft.FilePicker()
        try:
            page.services.append(self.file_picker)
        except Exception:  # noqa: BLE001 — services list always exists in 0.85
            pass

        self._configure_page()

    def _configure_page(self) -> None:
        self.page.title = APP_NAME
        self.page.padding = 0
        self.page.bgcolor = theme.BG
        # Phone-like window on desktop; harmless if the attribute differs.
        try:
            self.page.window.width = 430
            self.page.window.height = 860
        except Exception:  # noqa: BLE001
            pass

    def start(self) -> None:
        self.show_login()

    # -- Remember-me persistence ------------------------------------------
    def get_remembered_username(self) -> str:
        try:
            return REMEMBER_FILE.read_text(encoding="utf-8").strip()
        except Exception:  # noqa: BLE001 — no remembered user yet
            return ""

    def _remember(self, username: str, remember: bool) -> None:
        try:
            if remember:
                REMEMBER_FILE.write_text(username, encoding="utf-8")
            elif REMEMBER_FILE.exists():
                REMEMBER_FILE.unlink()
        except Exception:  # noqa: BLE001
            pass

    # -- Session state -----------------------------------------------------
    def set_user(self, *, user_id, full_name, role, site_id, site_name, remember, username) -> None:
        self.user_id = user_id
        self.user_name = full_name
        self.user_role = role
        self.site_id = site_id
        self.site_name = site_name
        self.username = username
        self._remember(username, remember)

    def logout(self) -> None:
        self.user_id = None
        self.user_name = ""
        self.show_login()

    # -- Navigation --------------------------------------------------------
    def _render(self, content: ft.Control, active: str | None = None) -> None:
        self.page.clean()
        children = [content]
        if active:
            children.append(self._bottom_nav(active))
        self.page.add(ft.Column(children, expand=True, spacing=0))
        self.page.update()

    def show_login(self) -> None:
        self._render(build_login(self))

    def show_home(self, message=None) -> None:
        self._render(build_home(self, message), active="home")

    def show_pending_sync(self, message=None) -> None:
        self._render(build_pending_sync(self, message), active="pending")

    def show_history(self, message=None) -> None:
        self._render(build_history(self, message), active="history")

    def show_dashboard(self, message=None) -> None:
        self._render(build_dashboard(self, message), active="home")

    def show_findings(self, message=None, status=None) -> None:
        self._render(build_findings(self, message, status), active="findings")

    def show_finding_detail(self, finding_id: int, message=None) -> None:
        self._render(build_finding_detail(self, finding_id, message), active="findings")

    def show_profile(self, message=None) -> None:
        self._render(build_profile(self, message), active="profile")

    def show_inspection(self, template_id: int | None = None, inspection_id: int | None = None) -> None:
        screen = InspectionScreen(self, template_id=template_id, inspection_id=inspection_id)
        self._render(screen.build())

    def show_review(self, inspection_id: int, message=None) -> None:
        self._render(build_review(self, inspection_id, message))

    def show_success(self, inspection_id: int) -> None:
        self._render(build_success(self, inspection_id))

    # -- Bottom navigation bar --------------------------------------------
    def _bottom_nav(self, active: str) -> ft.Control:
        items = [
            ("home", "Home", ft.Icons.HOME, self.show_home),
            ("pending", "Pending", ft.Icons.SYNC, self.show_pending_sync),
            ("history", "History", ft.Icons.HISTORY, self.show_history),
            ("findings", "Findings", ft.Icons.WARNING_AMBER, self.show_findings),
            ("profile", "Profile", ft.Icons.PERSON, self.show_profile),
        ]
        cells = []
        for key, label, icon, handler in items:
            selected = key == active
            color = theme.PRIMARY if selected else theme.MUTED
            cells.append(ft.Container(
                content=ft.Column(
                    [
                        ft.Icon(icon, color=color, size=24),
                        ft.Text(label, size=11, color=color,
                                weight=ft.FontWeight.BOLD if selected else None),
                    ],
                    spacing=2, horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                on_click=(lambda fn: lambda e: fn())(handler),
                ink=True, expand=True,
                padding=ft.Padding.symmetric(vertical=8, horizontal=0),
                alignment=ft.Alignment.CENTER,
                bgcolor=theme.GOLD_TINT if selected else None,
                border=ft.Border(top=ft.BorderSide(3, theme.GOLD)) if selected else None,
            ))
        return ft.Container(
            content=ft.Row(cells, spacing=0),
            bgcolor=theme.CARD,
            border=ft.Border.all(1, theme.BORDER),
        )
