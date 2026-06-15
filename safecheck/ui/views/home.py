"""Home screen — summary cards and large checklist cards."""
from __future__ import annotations

import flet as ft

from safecheck.core.database import SessionLocal
from safecheck.services import inspection_service
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


def build_home(app, message=None) -> ft.Control:
    """Return the home screen content. *message* is an optional (kind, text)."""
    with SessionLocal() as session:
        counts = inspection_service.summary_counts(session, app.user_id)
        templates = inspection_service.list_templates(session)
        template_data = [(t.id, t.name, len(t.questions)) for t in templates]

    logout_btn = ft.Container(
        content=ft.Icon(ft.Icons.LOGOUT, color=theme.WHITE, size=22),
        on_click=lambda e: app.logout(), ink=True, border_radius=20, padding=ft.Padding.all(6),
    )

    summary = ft.Row(
        [
            theme.summary_card("Completed today", counts["completed_today"], theme.GREEN),
            theme.summary_card("Draft inspections", counts["drafts"], theme.MUTED),
            theme.summary_card("Pending sync", counts["pending"], theme.AMBER),
            theme.summary_card("No Go", counts["no_go"], theme.RED),
            theme.summary_card("Open findings", counts["open_findings"], theme.PRIMARY),
        ],
        wrap=True, spacing=12, run_spacing=12,
    )

    checklist_cards = [
        theme.checklist_card(
            name, f"{count} checks",
            CHECKLIST_ICONS.get(name, ft.Icons.ASSIGNMENT),
            (lambda tid: lambda e: app.show_inspection(tid))(tid),
        )
        for tid, name, count in template_data
    ]

    body_controls = []
    if message:
        body_controls.append(theme.banner(message[1], message[0]))
    body_controls += [
        ft.Text(f"Hello, {app.user_name}", size=20, weight=ft.FontWeight.BOLD, color=theme.TEXT),
        ft.Text(app.user_role, size=13, color=theme.MUTED),
        ft.Container(height=4),
        ft.Text("Overview", size=15, weight=ft.FontWeight.BOLD, color=theme.TEXT),
        summary,
        ft.Container(height=8),
        ft.Text("Start an inspection", size=15, weight=ft.FontWeight.BOLD, color=theme.TEXT),
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
