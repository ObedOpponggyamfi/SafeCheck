"""Dashboard screen — at-a-glance analytics with simple bar charts.

Bars are plain Containers sized in proportion to their value, so no external
charting library is needed.
"""
from __future__ import annotations

import flet as ft

from safecheck.core.database import SessionLocal
from safecheck.core.enums import FindingStatus
from safecheck.services import analytics_service, finding_service
from safecheck.ui import theme

_SYNC_COLORS = {
    "Draft": theme.MUTED, "Pending Sync": theme.AMBER, "Uploading": theme.PRIMARY,
    "Synced": theme.GREEN, "Sync Failed": theme.RED,
}
_FINDING_COLORS = {
    FindingStatus.OPEN.value: theme.RED, FindingStatus.IN_PROGRESS.value: theme.AMBER,
    FindingStatus.PENDING_VERIFICATION.value: theme.PRIMARY, FindingStatus.CLOSED.value: theme.GREEN,
}
_MAX_BAR_WIDTH = 170


def _bar(label: str, count: int, max_count: int, color: str) -> ft.Row:
    width = max(6, int(_MAX_BAR_WIDTH * count / max_count)) if count else 0
    return ft.Row(
        [
            ft.Text(label, size=12, color=theme.TEXT, width=145),
            ft.Container(bgcolor=color, width=width, height=14, border_radius=7),
            ft.Text(str(count), size=12, weight=ft.FontWeight.BOLD, color=theme.MUTED),
        ],
        vertical_alignment=ft.CrossAxisAlignment.CENTER, spacing=8,
    )


def _section(title: str, pairs, color_fn) -> ft.Control:
    content = [ft.Text(title, size=14, weight=ft.FontWeight.BOLD, color=theme.TEXT)]
    if not pairs or all(count == 0 for _, count in pairs):
        content.append(ft.Text("No data yet.", size=12, color=theme.MUTED))
    else:
        max_count = max(count for _, count in pairs) or 1
        content += [_bar(label, count, max_count, color_fn(label)) for label, count in pairs]
    return theme.card(ft.Column(content, spacing=8))


def build_dashboard(app, message=None) -> ft.Control:
    """Return the dashboard screen content."""
    with SessionLocal() as session:
        data = analytics_service.dashboard_data(session, inspector_id=app.user_id)

    totals = data["totals"]
    stat_cards = ft.Row(
        [
            theme.summary_card("Inspections", totals["inspections"], theme.PRIMARY),
            theme.summary_card("Completed today", totals["today"], theme.GREEN),
            theme.summary_card("This week", totals["this_week"], theme.PRIMARY),
            theme.summary_card("No Go", totals["no_go"], theme.RED),
            theme.summary_card("Open findings", totals["open_findings"], theme.AMBER),
        ],
        wrap=True, spacing=12, run_spacing=12,
    )

    findings_pairs = [(s, data["findings_by_status"].get(s, 0)) for s in finding_service.STATUS_FLOW]

    body_controls = []
    if message:
        body_controls.append(theme.banner(message[1], message[0]))
    body_controls += [
        stat_cards,
        _section("Results", data["results"], theme.result_color),
        _section("Synchronisation", data["sync"], lambda s: _SYNC_COLORS.get(s, theme.MUTED)),
        _section("Findings by status", findings_pairs, lambda s: _FINDING_COLORS.get(s, theme.MUTED)),
        _section("Top checklists", data["by_checklist"], lambda _l: theme.PRIMARY),
        ft.Container(height=8),
    ]
    body = ft.Column(body_controls, spacing=12, scroll=ft.ScrollMode.AUTO, expand=True)

    return ft.Column(
        [theme.top_bar("Dashboard", on_back=lambda e: app.show_home()),
         ft.Container(content=body, expand=True, padding=ft.Padding.all(16))],
        expand=True, spacing=0,
    )
