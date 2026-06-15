"""Pending Sync screen — queued inspections with retry / sync-all."""
from __future__ import annotations

import flet as ft

from safecheck.core.database import SessionLocal
from safecheck.services import inspection_service, sync_service
from safecheck.ui import theme

# Colour the status label by sync state.
STATUS_COLORS = {
    "Pending Sync": theme.AMBER,
    "Uploading": theme.PRIMARY,
    "Sync Failed": theme.RED,
    "Synced": theme.GREEN,
    "Draft": theme.MUTED,
}


def build_pending_sync(app, message=None) -> ft.Control:
    """Return the Pending Sync screen content."""
    with SessionLocal() as session:
        pending = sync_service.list_pending(session)
        rows = [
            {
                "id": insp.id,
                "ref": insp.uuid[:8].upper(),
                "checklist": insp.template.name if insp.template else "—",
                "asset": insp.asset_number_text or "—",
                "date": theme.fmt_dt(insp.updated_at),
                "status": insp.sync_status,
            }
            for insp in pending
        ]

    def _retry(inspection_id):
        with SessionLocal() as session:
            insp = inspection_service.get_inspection(session, inspection_id)
            ok, msg = sync_service.attempt_sync(session, insp)
        app.show_pending_sync(message=("success" if ok else "error", msg))

    def _sync_all(_event):
        with SessionLocal() as session:
            ok, fail = sync_service.sync_all(session)
        app.show_pending_sync(message=("info", f"{ok} synced, {fail} still pending."))

    sync_all_btn = ft.Container(
        content=ft.Icon(ft.Icons.SYNC, color=theme.WHITE, size=22),
        on_click=_sync_all, ink=True, border_radius=20, padding=ft.Padding.all(6),
    )

    cards = []
    for row in rows:
        cards.append(theme.card(ft.Row(
            [
                ft.Column(
                    [
                        ft.Row(
                            [
                                ft.Text(row["checklist"], size=15, weight=ft.FontWeight.BOLD, color=theme.TEXT),
                                ft.Container(
                                    content=ft.Text(row["status"], color=theme.WHITE, size=11, weight=ft.FontWeight.BOLD),
                                    bgcolor=STATUS_COLORS.get(row["status"], theme.MUTED),
                                    border_radius=8, padding=ft.Padding.symmetric(horizontal=8, vertical=3),
                                ),
                            ],
                            spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                        ft.Text(f"Ref {row['ref']}  •  Asset {row['asset']}", size=12, color=theme.MUTED),
                        ft.Text(f"Submitted {row['date']}", size=12, color=theme.MUTED),
                    ],
                    spacing=4, expand=True,
                ),
                theme.outline_button(
                    "Retry", (lambda iid: lambda e: _retry(iid))(row["id"]),
                    height=42,
                ),
            ],
            vertical_alignment=ft.CrossAxisAlignment.CENTER, spacing=10,
        )))

    if not cards:
        cards = [ft.Container(
            content=ft.Column(
                [
                    ft.Icon(ft.Icons.CLOUD_DONE, color=theme.GREEN, size=46),
                    ft.Text("Nothing waiting to sync", size=15, weight=ft.FontWeight.BOLD, color=theme.TEXT),
                    ft.Text("Submitted inspections will appear here until they reach the server.",
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
            theme.top_bar("Pending Sync", action=sync_all_btn),
            ft.Container(content=body, expand=True, padding=ft.Padding.all(16)),
        ],
        expand=True, spacing=0,
    )
