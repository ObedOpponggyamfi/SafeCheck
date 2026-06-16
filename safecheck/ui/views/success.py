"""Submission success screen — clear confirmation after a successful submit."""
from __future__ import annotations

import flet as ft
from sqlalchemy import func, select

from safecheck.core import models
from safecheck.core.database import SessionLocal
from safecheck.core.enums import AnswerType, SyncStatus
from safecheck.services import inspection_service
from safecheck.ui import theme


def build_success(app, inspection_id: int) -> ft.Control:
    """Return the success screen for a just-submitted inspection."""
    with SessionLocal() as session:
        inspection = inspection_service.get_inspection(session, inspection_id)
        if inspection is None:
            return ft.Column(
                [theme.top_bar("Submitted"),
                 ft.Container(content=theme.banner("Inspection not found.", "error"),
                              padding=ft.Padding.all(16))],
                expand=True, spacing=0)
        failed = session.scalar(
            select(func.count(models.InspectionResponse.id)).where(
                models.InspectionResponse.inspection_id == inspection.id,
                models.InspectionResponse.answer == AnswerType.NO.value)) or 0
        data = {
            "ref": inspection.uuid[:8].upper(),
            "checklist": inspection.template.name if inspection.template else "—",
            "asset": inspection.asset_number_text or "—",
            "result": inspection.result,
            "failed": failed,
            "sync": inspection.sync_status,
            "time": theme.fmt_dt(inspection.completion_time),
        }

    synced = data["sync"] == SyncStatus.SYNCED.value
    details = theme.card(ft.Column(
        [
            _row("Reference", data["ref"]),
            _row("Checklist", data["checklist"]),
            _row("Asset", data["asset"]),
            ft.Row([ft.Text("Result", size=13, color=theme.MUTED, width=110),
                    theme.result_chip(data["result"])],
                   vertical_alignment=ft.CrossAxisAlignment.CENTER),
            _row("Failed items", str(data["failed"])),
            _row("Sync status", data["sync"]),
            _row("Submitted", data["time"]),
        ],
        spacing=10,
    ))

    sync_message = (
        "Inspection synchronised to the server."
        if synced else
        "Inspection saved securely on this device. It will synchronize automatically "
        "when internet access becomes available."
    )

    hero = ft.Container(
        content=ft.Column(
            [
                ft.Container(
                    content=ft.Icon(ft.Icons.CHECK_CIRCLE, color=theme.WHITE, size=56),
                    bgcolor=theme.GREEN, border_radius=50, padding=ft.Padding.all(16),
                ),
                ft.Text("Inspection submitted", size=22, weight=ft.FontWeight.BOLD, color=theme.TEXT),
                ft.Text(f"Result: {data['result']}", size=14, color=theme.MUTED),
            ],
            spacing=10, horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        alignment=ft.Alignment.CENTER, padding=ft.Padding.symmetric(horizontal=0, vertical=8),
    )

    buttons = ft.Column(
        [
            theme.big_button("Return Home", lambda e: app.show_home(), expand=True, icon=ft.Icons.HOME),
            ft.Row(
                [theme.outline_button("Start Another", lambda e: app.show_home(), expand=True),
                 theme.outline_button("View in History", lambda e: app.show_history(), expand=True)],
                spacing=12,
            ),
        ],
        spacing=12,
    )

    body = ft.Column(
        [hero, details, theme.banner(sync_message, "success" if synced else "info"),
         ft.Container(height=4), buttons, ft.Container(height=8)],
        spacing=14, scroll=ft.ScrollMode.AUTO, expand=True,
    )
    return ft.Column(
        [theme.top_bar("Submission Complete"),
         ft.Container(content=body, expand=True, padding=ft.Padding.all(16))],
        expand=True, spacing=0,
    )


def _row(label: str, value: str) -> ft.Row:
    return ft.Row(
        [ft.Text(label, size=13, color=theme.MUTED, width=110),
         ft.Text(value, size=14, weight=ft.FontWeight.BOLD, color=theme.TEXT, expand=True)],
        spacing=8,
    )
