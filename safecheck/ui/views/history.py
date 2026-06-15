"""Inspection History screen — a list of completed and draft inspections."""
from __future__ import annotations

import flet as ft

from safecheck.core.database import SessionLocal
from safecheck.services import inspection_service
from safecheck.ui import theme


def build_history(app, message=None) -> ft.Control:
    """Return the Inspection History screen content."""
    with SessionLocal() as session:
        inspections = inspection_service.list_inspections(session, inspector_id=app.user_id, limit=100)
        rows = [
            {
                "ref": insp.uuid[:8].upper(),
                "checklist": insp.template.name if insp.template else "—",
                "asset": insp.asset_number_text or "—",
                "date": theme.fmt_dt(insp.completion_time or insp.created_at),
                "result": insp.result,
                "sync": insp.sync_status,
            }
            for insp in inspections
        ]

    cards = []
    for row in rows:
        cards.append(theme.card(ft.Column(
            [
                ft.Row(
                    [
                        ft.Text(row["checklist"], size=15, weight=ft.FontWeight.BOLD, color=theme.TEXT, expand=True),
                        theme.result_chip(row["result"]),
                    ],
                    vertical_alignment=ft.CrossAxisAlignment.CENTER, spacing=8,
                ),
                ft.Text(f"Ref {row['ref']}  •  Asset {row['asset']}", size=12, color=theme.MUTED),
                ft.Text(f"{row['date']}  •  {row['sync']}", size=12, color=theme.MUTED),
            ],
            spacing=4,
        )))

    if not cards:
        cards = [ft.Container(
            content=ft.Column(
                [
                    ft.Icon(ft.Icons.HISTORY, color=theme.MUTED, size=46),
                    ft.Text("No inspections yet", size=15, weight=ft.FontWeight.BOLD, color=theme.TEXT),
                    ft.Text("Completed and draft inspections will be listed here.",
                            size=12, color=theme.MUTED, text_align=ft.TextAlign.CENTER),
                ],
                spacing=8, horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            padding=ft.Padding.all(30), alignment=ft.Alignment.CENTER,
        )]

    body_controls = []
    if message:
        body_controls.append(theme.banner(message[1], message[0]))
    body_controls += cards
    body = ft.Column(body_controls, spacing=12, scroll=ft.ScrollMode.AUTO, expand=True)

    return ft.Column(
        [
            theme.top_bar("Inspection History"),
            ft.Container(content=body, expand=True, padding=ft.Padding.all(16)),
        ],
        expand=True, spacing=0,
    )
