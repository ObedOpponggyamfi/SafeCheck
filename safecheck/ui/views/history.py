"""Inspection History screen — list of inspections with report exports."""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import flet as ft

from safecheck.core.database import SessionLocal
from safecheck.services import inspection_service, report_service
from safecheck.ui import theme


def _open_file(path: str) -> None:
    """Open a generated report in the OS default application (best effort)."""
    try:
        if sys.platform.startswith("win"):
            os.startfile(path)  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            subprocess.run(["open", path], check=False)
        else:
            subprocess.run(["xdg-open", path], check=False)
    except Exception:  # noqa: BLE001 — opening is a convenience, never fatal
        pass


def build_history(app, message=None) -> ft.Control:
    """Return the Inspection History screen content."""
    with SessionLocal() as session:
        inspections = inspection_service.list_inspections(session, inspector_id=app.user_id, limit=100)
        rows = [
            {
                "id": insp.id,
                "ref": insp.uuid[:8].upper(),
                "checklist": insp.template.name if insp.template else "—",
                "asset": insp.asset_number_text or "—",
                "date": theme.fmt_dt(insp.completion_time or insp.created_at),
                "result": insp.result,
                "sync": insp.sync_status,
            }
            for insp in inspections
        ]

    # --- Report handlers --------------------------------------------------
    def _export(generator, label):
        with SessionLocal() as session:
            path = generator(session)
        _open_file(path)
        app.show_history(message=("success", f"{label} saved to {Path(path).name} (opened)."))

    def _pdf(inspection_id):
        with SessionLocal() as session:
            path = report_service.inspection_pdf(session, inspection_id)
        _open_file(path)
        app.show_history(message=("success", f"PDF saved to {Path(path).name} (opened)."))

    reports_card = theme.card(ft.Column(
        [
            ft.Text("Reports", size=14, weight=ft.FontWeight.BOLD, color=theme.TEXT),
            ft.Row(
                [
                    theme.outline_button("Register (Excel)",
                                         lambda e: _export(report_service.inspection_register_xlsx, "Register"),
                                         height=42),
                    theme.outline_button("No Go (Excel)",
                                         lambda e: _export(report_service.no_go_xlsx, "No Go report"),
                                         height=42),
                    theme.outline_button("Failed items (Excel)",
                                         lambda e: _export(report_service.failed_items_xlsx, "Failed items"),
                                         height=42),
                    theme.outline_button("Asset history (Excel)",
                                         lambda e: _export(report_service.asset_history_xlsx, "Asset history"),
                                         height=42),
                ],
                wrap=True, spacing=8, run_spacing=8,
            ),
        ],
        spacing=10,
    ))

    cards = []
    for row in rows:
        cards.append(theme.card(ft.Row(
            [
                ft.Column(
                    [
                        ft.Row([ft.Text(row["checklist"], size=15, weight=ft.FontWeight.BOLD,
                                        color=theme.TEXT, expand=True),
                                theme.result_chip(row["result"])],
                               vertical_alignment=ft.CrossAxisAlignment.CENTER, spacing=8),
                        ft.Text(f"Ref {row['ref']}  •  Asset {row['asset']}", size=12, color=theme.MUTED),
                        ft.Text(f"{row['date']}  •  {row['sync']}", size=12, color=theme.MUTED),
                    ],
                    spacing=4, expand=True,
                ),
                (theme.outline_button("Resume",
                                      (lambda iid: lambda e: app.show_inspection(inspection_id=iid))(row["id"]),
                                      height=42)
                 if row["sync"] == "Draft"
                 else theme.outline_button("PDF", (lambda iid: lambda e: _pdf(iid))(row["id"]), height=42)),
            ],
            vertical_alignment=ft.CrossAxisAlignment.CENTER, spacing=10,
        )))

    if not cards:
        cards = [ft.Container(
            content=ft.Column(
                [ft.Icon(ft.Icons.HISTORY, color=theme.MUTED, size=46),
                 ft.Text("No inspections yet", size=15, weight=ft.FontWeight.BOLD, color=theme.TEXT),
                 ft.Text("Completed and draft inspections will be listed here.",
                         size=12, color=theme.MUTED, text_align=ft.TextAlign.CENTER)],
                spacing=8, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            padding=ft.Padding.all(30), alignment=ft.Alignment.CENTER,
        )]

    body_controls = []
    if message:
        body_controls.append(theme.banner(message[1], message[0]))
    body_controls += [reports_card, *cards]
    body = ft.Column(body_controls, spacing=12, scroll=ft.ScrollMode.AUTO, expand=True)

    return ft.Column(
        [theme.top_bar("Inspection History"),
         ft.Container(content=body, expand=True, padding=ft.Padding.all(16))],
        expand=True, spacing=0,
    )
