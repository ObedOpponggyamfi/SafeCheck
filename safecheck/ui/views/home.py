"""Home screen — operational header, summary cards and checklist cards."""
from __future__ import annotations

import flet as ft

from safecheck.core.database import SessionLocal
from safecheck.services import inspection_service, sync_service
from safecheck.ui import theme

# Icon per checklist (falls back to a generic clipboard icon).
CHECKLIST_ICONS = {
    "Light Vehicle Inspection": ft.Icons.DIRECTIONS_CAR,
    "Visitor Vehicle Inspection": ft.Icons.AIRPORT_SHUTTLE,
    "Heavy Vehicle Inspection": ft.Icons.LOCAL_SHIPPING,
    "Excavator Inspection": ft.Icons.CONSTRUCTION,
    "Wheel Loader Inspection": ft.Icons.AGRICULTURE,
    "Bulldozer Inspection": ft.Icons.TERRAIN,
    "Grader Inspection": ft.Icons.ENGINEERING,
    "Drill Rig Inspection": ft.Icons.HARDWARE,
    "Forklift Inspection": ft.Icons.FORKLIFT,
    "Crane Inspection": ft.Icons.PRECISION_MANUFACTURING,
    "Generator Inspection": ft.Icons.BOLT,
}


def _status_header(app, online: bool, last_sync) -> ft.Control:
    """Logo + app name + current user + online/offline badge + last sync."""
    status_color = theme.ONLINE if online else theme.OFFLINE
    badge = ft.Container(
        content=ft.Row(
            [ft.Icon(ft.Icons.CIRCLE, color=theme.WHITE, size=9),
             ft.Text("Online" if online else "Offline", color=theme.WHITE, size=11,
                     weight=ft.FontWeight.BOLD)],
            spacing=5, tight=True),
        bgcolor=status_color, border_radius=8, padding=ft.Padding.symmetric(horizontal=8, vertical=4),
    )
    return theme.card(ft.Row(
        [
            ft.Container(content=ft.Icon(ft.Icons.VERIFIED_USER, color=theme.ON_GOLD, size=26),
                         bgcolor=theme.GOLD, border_radius=12, padding=ft.Padding.all(10)),
            ft.Column(
                [ft.Text("SafeCheck", size=16, weight=ft.FontWeight.BOLD, color=theme.TEXT),
                 ft.Text("Safety Inspection Management", size=11, color=theme.MUTED),
                 ft.Text(f"{app.user_name}  •  {app.user_role}", size=11, color=theme.MUTED)],
                spacing=1, expand=True),
            ft.Column(
                [badge, ft.Text(f"Last sync: {theme.fmt_dt(last_sync)}", size=10, color=theme.MUTED)],
                spacing=6, horizontal_alignment=ft.CrossAxisAlignment.END),
        ],
        vertical_alignment=ft.CrossAxisAlignment.CENTER, spacing=12,
    ))


def build_home(app, message=None) -> ft.Control:
    """Return the home screen content. *message* is an optional (kind, text)."""
    with SessionLocal() as session:
        counts = inspection_service.summary_counts(session, app.user_id)
        templates = inspection_service.list_templates(session)
        template_data = [(t.id, t.name, len(t.questions)) for t in templates]
        last_sync = sync_service.last_sync_time(session)
    online = sync_service.server_reachable()

    logout_btn = ft.Container(
        content=ft.Icon(ft.Icons.LOGOUT, color=theme.WHITE, size=22),
        on_click=lambda e: app.logout(), ink=True, border_radius=20, padding=ft.Padding.all(6),
    )

    summary = ft.Row(
        [
            theme.summary_card("In progress", counts["drafts"], theme.PRIMARY),
            theme.summary_card("Completed today", counts["completed_today"], theme.GREEN),
            theme.summary_card("Pending sync", counts["pending"], theme.AMBER),
            theme.summary_card("Open findings", counts["open_findings"], theme.PRIMARY),
            theme.summary_card("No Go", counts["no_go"], theme.RED),
        ],
        wrap=True, spacing=12, run_spacing=12,
    )

    checklist_cards = [
        theme.checklist_card(
            name, f"{count} checks",
            CHECKLIST_ICONS.get(name, ft.Icons.ASSIGNMENT),
            (lambda tid: lambda e: app.show_inspection(template_id=tid))(tid),
        )
        for tid, name, count in template_data
    ]

    dashboard_card = theme.card(
        ft.Row(
            [
                ft.Icon(ft.Icons.BAR_CHART, color=theme.PRIMARY, size=26),
                ft.Column(
                    [ft.Text("Dashboard", size=14, weight=ft.FontWeight.BOLD, color=theme.TEXT),
                     ft.Text("Results, sync and findings overview", size=12, color=theme.MUTED)],
                    spacing=2, expand=True),
                ft.Icon(ft.Icons.CHEVRON_RIGHT, color=theme.MUTED, size=24),
            ],
            vertical_alignment=ft.CrossAxisAlignment.CENTER, spacing=14,
        ),
        on_click=lambda e: app.show_dashboard(),
    )

    body_controls = []
    if message:
        body_controls.append(theme.banner(message[1], message[0]))
    body_controls += [
        _status_header(app, online, last_sync),
        ft.Text("Overview", size=15, weight=ft.FontWeight.BOLD, color=theme.TEXT),
        summary,
        dashboard_card,
        ft.Container(height=4),
        ft.Text("Start a new inspection", size=15, weight=ft.FontWeight.BOLD, color=theme.TEXT),
        ft.Text("Select a checklist to begin. Your answers save automatically.",
                size=12, color=theme.MUTED),
        *checklist_cards,
    ]

    body = ft.Column(body_controls, spacing=12, scroll=ft.ScrollMode.AUTO, expand=True)

    return ft.Column(
        [
            theme.top_bar("SafeCheck Offline", action=logout_btn),
            ft.Container(content=body, expand=True, padding=ft.Padding.all(16)),
        ],
        expand=True, spacing=0,
    )
