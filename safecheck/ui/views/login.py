"""Login screen — simple username/email + password with a Remember option."""
from __future__ import annotations

import flet as ft
from sqlalchemy import select

from safecheck.config import APP_NAME, DEMO_PASSWORD
from safecheck.core.database import SessionLocal
from safecheck.core import models
from safecheck.services import auth_service
from safecheck.ui import theme


def build_login(app) -> ft.Control:
    """Return the login screen content."""
    username = ft.TextField(
        label="Username or email",
        value=app.get_remembered_username(),
        autofocus=True,
        border_color=theme.BORDER,
    )
    password = ft.TextField(
        label="Password",
        password=True,
        can_reveal_password=True,
        border_color=theme.BORDER,
        on_submit=lambda e: _do_login(),
    )
    remember = ft.Checkbox(label="Remember me on this device", value=bool(username.value))
    error = ft.Text("", color=theme.RED, size=13, visible=False)

    def _do_login():
        error.visible = False
        with SessionLocal() as session:
            user = auth_service.authenticate(session, username.value, password.value)
            if user is None:
                error.value = "Invalid username/email or password."
                error.visible = True
                app.page.update()
                return
            site = session.scalars(select(models.Site)).first()
            app.set_user(
                user_id=user.id,
                full_name=user.full_name,
                role=user.role.name if user.role else "",
                site_id=site.id if site else None,
                site_name=site.name if site else "—",
                remember=remember.value,
                username=user.username,
            )
        app.show_home(message=("success", f"Welcome back, {app.user_name}."))

    login_btn = theme.big_button("Login", lambda e: _do_login(), expand=True, height=54)

    card = ft.Container(
        content=ft.Column(
            [
                ft.Icon(ft.Icons.VERIFIED_USER, color=theme.PRIMARY, size=48),
                ft.Text(APP_NAME, size=26, weight=ft.FontWeight.BOLD, color=theme.PRIMARY),
                ft.Text("Offline safety inspections", size=13, color=theme.MUTED),
                ft.Container(height=8),
                username,
                password,
                remember,
                error,
                ft.Container(height=4),
                login_btn,
                ft.Container(height=4),
                ft.Text(f"Demo accounts: admin, officer1, driver …  •  password: {DEMO_PASSWORD}",
                        size=11, color=theme.MUTED, text_align=ft.TextAlign.CENTER),
            ],
            spacing=12,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        bgcolor=theme.CARD,
        border_radius=18,
        padding=ft.Padding.all(28),
        border=ft.Border.all(1, theme.BORDER),
        width=420,
    )

    return ft.Container(
        content=card,
        alignment=ft.Alignment.CENTER,
        bgcolor=theme.BG,
        expand=True,
        padding=ft.Padding.all(20),
    )
