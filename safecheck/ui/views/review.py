"""Review screen — final check before submitting an inspection.

Submission happens here (not amongst the checklist questions). The screen lists
answered/unanswered counts, failed items and the system-generated result, and
clearly states anything that must be corrected before submitting.
"""
from __future__ import annotations

import flet as ft

from safecheck.core.database import SessionLocal
from safecheck.core.logging_config import get_logger
from safecheck.services import inspection_service
from safecheck.ui import theme

log = get_logger("ui.review")


def build_review(app, inspection_id: int, message=None) -> ft.Control:
    """Return the Review screen content for one inspection."""
    with SessionLocal() as session:
        inspection = inspection_service.get_inspection(session, inspection_id)
        if inspection is None:
            return _missing(app)
        summary = inspection_service.review_summary(session, inspection)
        data = {
            "checklist": inspection.template.name if inspection.template else "—",
            "asset": inspection.asset_number_text or "— not selected —",
            "datetime": theme.fmt_dt(inspection.start_time),
            "result": summary["result"],
            "answered": summary["answered"],
            "total": summary["total"],
            "photos": summary["photos"],
            "errors": list(summary["errors"]),
            "unanswered": [q.text for q in summary["unanswered"]],
            "failed": [(q.text, (r.comment or "").strip(), q.is_no_go)
                       for q, r in summary["failed"]],
            "no_go_count": len(summary["no_go_failures"]),
        }

    errors = data["errors"]
    banner_holder = ft.Container(visible=False)
    if message:
        banner_holder.content = theme.banner(message[1], message[0])
        banner_holder.visible = True
    elif errors:
        banner_holder.content = theme.banner(
            "Resolve before submitting:  " + "   ".join(f"• {e}" for e in errors), "error")
        banner_holder.visible = True

    # Summary card
    summary_card = theme.card(ft.Column(
        [
            ft.Row([ft.Text(data["checklist"], size=17, weight=ft.FontWeight.BOLD,
                            color=theme.TEXT, expand=True),
                    theme.result_chip(data["result"])],
                   vertical_alignment=ft.CrossAxisAlignment.CENTER, spacing=8),
            ft.Text(f"Asset: {data['asset']}", size=13, color=theme.TEXT),
            ft.Text(f"Inspector: {app.user_name}   •   {data['datetime']}", size=12, color=theme.MUTED),
            ft.Divider(height=12, color=theme.BORDER),
            ft.Row(
                [
                    _stat("Answered", f"{data['answered']}/{data['total']}", theme.PRIMARY),
                    _stat("Failed", str(len(data["failed"])),
                          theme.RED if data["failed"] else theme.GREEN),
                    _stat("No-Go fails", str(data["no_go_count"]),
                          theme.RED if data["no_go_count"] else theme.GREEN),
                    _stat("Photos", str(data["photos"]), theme.MUTED),
                ],
                spacing=10, wrap=True, run_spacing=10,
            ),
        ],
        spacing=8,
    ))

    sections = [banner_holder, summary_card]

    if data["unanswered"]:
        sections.append(theme.card(ft.Column(
            [ft.Text(f"Unanswered ({len(data['unanswered'])})", size=14,
                     weight=ft.FontWeight.BOLD, color=theme.RED),
             *[ft.Text(f"• {t}", size=13, color=theme.TEXT) for t in data["unanswered"][:30]]],
            spacing=6,
        )))

    if data["failed"]:
        failed_rows = []
        for text, comment, is_no_go in data["failed"]:
            header = [ft.Text(text, size=13, weight=ft.FontWeight.BOLD, color=theme.TEXT, expand=True)]
            if is_no_go:
                header.append(theme.badge("NO GO", theme.RED))
            failed_rows.append(ft.Column(
                [ft.Row(header, spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                 ft.Text(f"Comment: {comment or '—'}", size=12, color=theme.MUTED)],
                spacing=2,
            ))
        sections.append(theme.card(ft.Column(
            [ft.Text(f"Failed items ({len(data['failed'])})", size=14,
                     weight=ft.FontWeight.BOLD, color=theme.RED),
             *failed_rows],
            spacing=10,
        )))

    # Submit (duplicate-click guarded)
    state = {"busy": False}
    submit_btn = theme.big_button("Submit Inspection", lambda e: None, expand=True,
                                  icon=ft.Icons.CHECK_CIRCLE)

    def _submit(_event):
        if state["busy"]:
            return
        state["busy"] = True
        submit_btn.disabled = True
        submit_btn.bgcolor = theme.MUTED
        app.page.update()
        try:
            with SessionLocal() as session:
                inspection = inspection_service.get_inspection(session, inspection_id)
                inspection_service.submit_inspection(session, inspection)
        except inspection_service.InspectionValidationError as exc:
            log.warning("Review submit blocked: %s", exc.errors)
            app.show_review(inspection_id, message=(
                "error", "Resolve before submitting:  " + "   ".join(f"• {e}" for e in exc.errors)))
            return
        except Exception as exc:  # noqa: BLE001
            log.exception("Review submit failed")
            app.show_review(inspection_id, message=("error", f"Submission failed: {exc}"))
            return
        log.info("Inspection %s submitted from review.", inspection_id)
        app.show_success(inspection_id)

    submit_btn.on_click = _submit

    footer = ft.Container(
        content=ft.Row(
            [theme.outline_button("Back to Inspection",
                                  lambda e: app.show_inspection(inspection_id=inspection_id),
                                  expand=True),
             submit_btn],
            spacing=12,
        ),
        bgcolor=theme.CARD, padding=ft.Padding.all(12), border=ft.Border.all(1, theme.BORDER),
    )

    body = ft.Column([*sections, ft.Container(height=8)], spacing=12,
                     scroll=ft.ScrollMode.AUTO, expand=True)
    return ft.Column(
        [theme.top_bar("Review Inspection",
                       on_back=lambda e: app.show_inspection(inspection_id=inspection_id)),
         ft.Container(content=body, expand=True, padding=ft.Padding.all(16)),
         footer],
        expand=True, spacing=0,
    )


def _stat(label: str, value: str, color: str) -> ft.Container:
    return ft.Container(
        content=ft.Column(
            [ft.Text(value, size=20, weight=ft.FontWeight.BOLD, color=color),
             ft.Text(label, size=11, color=theme.MUTED)],
            spacing=0, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
        bgcolor=theme.NEUTRAL_BG, border_radius=10, padding=ft.Padding.symmetric(horizontal=14, vertical=8),
    )


def _missing(app) -> ft.Control:
    return ft.Column(
        [theme.top_bar("Review Inspection", on_back=lambda e: app.show_home()),
         ft.Container(content=theme.banner("Inspection not found.", "error"),
                      padding=ft.Padding.all(16))],
        expand=True, spacing=0,
    )
