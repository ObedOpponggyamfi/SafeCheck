"""Profile screen — current user details and logout."""
from __future__ import annotations

import flet as ft

from safecheck.config import APP_NAME, APP_VERSION
from safecheck.ui import theme


def _row(label: str, value: str) -> ft.Row:
    return ft.Row(
        [
            ft.Text(label, size=13, color=theme.MUTED, width=90),
            ft.Text(value, size=14, weight=ft.FontWeight.BOLD, color=theme.TEXT, expand=True),
        ],
        spacing=8,
    )


def build_profile(app, message=None) -> ft.Control:
    """Return the Profile screen content."""
    details = theme.card(ft.Column(
        [
            ft.Row(
                [
                    ft.Container(
                        content=ft.Icon(ft.Icons.PERSON, color=theme.ON_GOLD, size=34),
                        bgcolor=theme.GOLD, border_radius=30, padding=ft.Padding.all(14),
                    ),
                    ft.Column(
                        [
                            ft.Text(app.user_name, size=18, weight=ft.FontWeight.BOLD, color=theme.TEXT),
                            ft.Text(app.user_role, size=13, color=theme.MUTED),
                        ],
                        spacing=2,
                    ),
                ],
                spacing=14, vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            ft.Divider(height=20, color=theme.BORDER),
            _row("Username", app.username or "—"),
            _row("Role", app.user_role or "—"),
            _row("Site", app.site_name or "—"),
        ],
        spacing=12,
    ))

    about = theme.card(ft.Column(
        [
            ft.Text("About", size=14, weight=ft.FontWeight.BOLD, color=theme.TEXT),
            ft.Text(f"{APP_NAME}  •  version {APP_VERSION}", size=12, color=theme.MUTED),
            ft.Text("Offline-first safety inspections. Data stays on this device until "
                    "it syncs to the server.", size=12, color=theme.MUTED),
        ],
        spacing=6,
    ))

    body_controls = []
    if message:
        body_controls.append(theme.banner(message[1], message[0]))
    body_controls += [
        details,
        about,
        ft.Container(height=4),
        theme.big_button("Log out", lambda e: app.logout(), bgcolor=theme.RED, expand=True, icon=ft.Icons.LOGOUT),
    ]
    body = ft.Column(body_controls, spacing=14, scroll=ft.ScrollMode.AUTO, expand=True)

    return ft.Column(
        [
            theme.top_bar("Profile"),
            ft.Container(content=body, expand=True, padding=ft.Padding.all(16)),
        ],
        expand=True, spacing=0,
    )
