"""Findings screens — list with status filter, and a detail/workflow view."""
from __future__ import annotations

from datetime import datetime

import flet as ft

from safecheck.core import models
from safecheck.core.database import SessionLocal
from safecheck.core.enums import FindingStatus
from safecheck.services import finding_service
from safecheck.ui import theme

# Colour per finding status.
STATUS_COLORS = {
    FindingStatus.OPEN.value: theme.RED,
    FindingStatus.IN_PROGRESS.value: theme.AMBER,
    FindingStatus.PENDING_VERIFICATION.value: theme.PRIMARY,
    FindingStatus.CLOSED.value: theme.GREEN,
}


def _status_pill(status: str) -> ft.Container:
    return ft.Container(
        content=ft.Text(status, color=theme.WHITE, size=11, weight=ft.FontWeight.BOLD),
        bgcolor=STATUS_COLORS.get(status, theme.MUTED),
        border_radius=8, padding=ft.Padding.symmetric(horizontal=8, vertical=3),
    )


def _parse_date(value: str | None) -> datetime | None:
    value = (value or "").strip()
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


# ---------------------------------------------------------------------------
# Findings list
# ---------------------------------------------------------------------------
def build_findings(app, message=None, status: str | None = None) -> ft.Control:
    """List of findings with a status filter. *status* None means "All"."""
    with SessionLocal() as session:
        findings = finding_service.list_findings(session, inspector_id=app.user_id, status=status)
        counts = finding_service.status_counts(session, inspector_id=app.user_id)
        rows = [
            {
                "id": f.id, "checklist": f.checklist_name or "—",
                "question": f.failed_question_text or "—",
                "date": theme.fmt_dt(f.finding_date), "status": f.status, "is_no_go": f.is_no_go,
            }
            for f in findings
        ]

    # Filter chips: All + the four statuses.
    chips = []
    for label, value in [("All", None)] + [(s, s) for s in finding_service.STATUS_FLOW]:
        active = value == status
        count = sum(counts.values()) if value is None else counts.get(value, 0)
        chips.append(ft.Container(
            content=ft.Text(f"{label} ({count})", size=12,
                            color=theme.WHITE if active else theme.MUTED,
                            weight=ft.FontWeight.BOLD if active else None),
            bgcolor=theme.PRIMARY if active else theme.CARD,
            border=ft.Border.all(1, theme.PRIMARY if active else theme.BORDER),
            border_radius=20, padding=ft.Padding.symmetric(horizontal=12, vertical=7),
            on_click=(lambda v: lambda e: app.show_findings(status=v))(value), ink=True,
        ))

    cards = []
    for row in rows:
        header = [ft.Text(row["question"], size=14, weight=ft.FontWeight.BOLD,
                          color=theme.TEXT, expand=True)]
        if row["is_no_go"]:
            header.append(theme.badge("NO GO", theme.RED))
        cards.append(theme.card(
            ft.Column(
                [
                    ft.Row(header, vertical_alignment=ft.CrossAxisAlignment.CENTER, spacing=8),
                    ft.Text(f"{row['checklist']}  •  {row['date']}", size=12, color=theme.MUTED),
                    ft.Row([_status_pill(row["status"]),
                            ft.Text("Tap to manage", size=11, color=theme.MUTED, expand=True)],
                           vertical_alignment=ft.CrossAxisAlignment.CENTER, spacing=8),
                ],
                spacing=6,
            ),
            on_click=(lambda fid: lambda e: app.show_finding_detail(fid))(row["id"]),
        ))

    if not cards:
        cards = [ft.Container(
            content=ft.Column(
                [ft.Icon(ft.Icons.CHECK_CIRCLE, color=theme.GREEN, size=46),
                 ft.Text("No findings", size=15, weight=ft.FontWeight.BOLD, color=theme.TEXT),
                 ft.Text("Findings are raised automatically from failed checklist items.",
                         size=12, color=theme.MUTED, text_align=ft.TextAlign.CENTER)],
                spacing=8, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            padding=ft.Padding.all(30), alignment=ft.Alignment.CENTER,
        )]

    body_controls = []
    if message:
        body_controls.append(theme.banner(message[1], message[0]))
    body_controls += [ft.Row(chips, wrap=True, spacing=8, run_spacing=8), *cards]
    body = ft.Column(body_controls, spacing=12, scroll=ft.ScrollMode.AUTO, expand=True)

    return ft.Column(
        [theme.top_bar("Findings"),
         ft.Container(content=body, expand=True, padding=ft.Padding.all(16))],
        expand=True, spacing=0,
    )


# ---------------------------------------------------------------------------
# Finding detail + workflow
# ---------------------------------------------------------------------------
def build_finding_detail(app, finding_id: int, message=None) -> ft.Control:
    """Detail view: finding info, status workflow and corrective actions."""
    with SessionLocal() as session:
        finding = finding_service.get_finding(session, finding_id)
        if finding is None:
            return build_findings(app, message=("error", "Finding not found."))

        asset = session.get(models.Asset, finding.asset_id) if finding.asset_id else None
        inspector = session.get(models.User, finding.inspector_id) if finding.inspector_id else None
        data = {
            "id": finding.id, "checklist": finding.checklist_name or "—",
            "question": finding.failed_question_text or "—", "comment": finding.comment or "—",
            "asset": asset.asset_number if asset else (finding.department_text or "—"),
            "department": finding.department_text or "—", "contractor": finding.contractor_text or "—",
            "inspector": inspector.full_name if inspector else "—",
            "date": theme.fmt_dt(finding.finding_date), "status": finding.status,
            "is_no_go": finding.is_no_go, "photo": finding.photo_path,
        }
        actions = [
            {"description": a.description, "responsible": a.responsible_person or "—",
             "due": theme.fmt_dt(a.due_date) if a.due_date else "—", "status": a.status}
            for a in finding_service.list_corrective_actions(session, finding_id)
        ]

    # Info card
    info_header = [ft.Text(data["question"], size=16, weight=ft.FontWeight.BOLD,
                           color=theme.TEXT, expand=True)]
    if data["is_no_go"]:
        info_header.append(theme.badge("NO GO", theme.RED))
    info_rows = [
        ft.Row(info_header, vertical_alignment=ft.CrossAxisAlignment.CENTER, spacing=8),
        ft.Text(f"Checklist: {data['checklist']}", size=13, color=theme.TEXT),
        ft.Text(f"Comment: {data['comment']}", size=13, color=theme.TEXT),
        ft.Text(f"Asset: {data['asset']}   •   {data['date']}", size=12, color=theme.MUTED),
        ft.Text(f"Inspector: {data['inspector']}", size=12, color=theme.MUTED),
    ]
    if data["photo"]:
        info_rows.append(ft.Image(src=data["photo"], height=180, fit=ft.BoxFit.CONTAIN,
                                  border_radius=10, error_content=ft.Text("Photo unavailable",
                                                                          size=11, color=theme.MUTED)))
    info_card = theme.card(ft.Column(info_rows, spacing=8))

    # Status workflow buttons
    def _set_status(value):
        with SessionLocal() as session:
            finding = finding_service.get_finding(session, finding_id)
            finding_service.set_finding_status(session, finding, value)
        app.show_finding_detail(finding_id, message=("success", f"Status set to {value}."))

    status_buttons = []
    for value in finding_service.STATUS_FLOW:
        selected = value == data["status"]
        color = STATUS_COLORS.get(value, theme.PRIMARY)
        status_buttons.append(ft.Container(
            content=ft.Text(value, size=12, weight=ft.FontWeight.BOLD,
                            color=theme.WHITE if selected else color),
            bgcolor=color if selected else theme.WHITE,
            border=None if selected else ft.Border.all(1.5, color),
            border_radius=10, padding=ft.Padding.symmetric(horizontal=12, vertical=9),
            on_click=(lambda v: lambda e: _set_status(v))(value), ink=True,
        ))
    status_card = theme.card(ft.Column(
        [ft.Text("Status", size=14, weight=ft.FontWeight.BOLD, color=theme.TEXT),
         ft.Row(status_buttons, wrap=True, spacing=8, run_spacing=8)],
        spacing=10,
    ))

    # Corrective actions: existing + add form
    desc = ft.TextField(label="Corrective action", multiline=True, min_lines=2, max_lines=3,
                        border_color=theme.BORDER)
    responsible = ft.TextField(label="Responsible person (optional)", border_color=theme.BORDER)
    due = ft.TextField(label="Due date (optional, YYYY-MM-DD)", border_color=theme.BORDER)

    def _add_action(_event):
        if not (desc.value or "").strip():
            app.show_finding_detail(finding_id, message=("error", "Enter a corrective action first."))
            return
        with SessionLocal() as session:
            finding = finding_service.get_finding(session, finding_id)
            finding_service.add_corrective_action(
                session, finding, desc.value.strip(),
                responsible_person=(responsible.value or "").strip() or None,
                due_date=_parse_date(due.value),
            )
        app.show_finding_detail(finding_id, message=("success", "Corrective action added."))

    action_items = [
        theme.card(ft.Column(
            [ft.Text(a["description"], size=13, color=theme.TEXT),
             ft.Text(f"Responsible: {a['responsible']}   •   Due: {a['due']}   •   {a['status']}",
                     size=11, color=theme.MUTED)],
            spacing=4), bgcolor="#F8FAFC")
        for a in actions
    ] or [ft.Text("No corrective actions yet.", size=12, color=theme.MUTED)]

    actions_card = theme.card(ft.Column(
        [ft.Text("Corrective actions", size=14, weight=ft.FontWeight.BOLD, color=theme.TEXT),
         *action_items,
         ft.Divider(height=10, color=theme.BORDER),
         desc, responsible, due,
         theme.big_button("Add corrective action", _add_action, expand=True, height=46)],
        spacing=10,
    ))

    body_controls = []
    if message:
        body_controls.append(theme.banner(message[1], message[0]))
    body_controls += [info_card, status_card, actions_card, ft.Container(height=8)]
    body = ft.Column(body_controls, spacing=12, scroll=ft.ScrollMode.AUTO, expand=True)

    return ft.Column(
        [theme.top_bar("Finding", on_back=lambda e: app.show_findings()),
         ft.Container(content=body, expand=True, padding=ft.Padding.all(16))],
        expand=True, spacing=0,
    )
