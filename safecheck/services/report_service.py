"""Report generation — individual PDF reports and Excel registers.

* :func:`inspection_pdf`            — one inspection, full detail (ReportLab)
* :func:`inspection_register_xlsx`  — register of all inspections
* :func:`failed_items_xlsx`         — every failed item / finding
* :func:`no_go_xlsx`                — No Go inspections only
* :func:`asset_history_xlsx`        — inspection history grouped by asset

Excel writers use pandas + OpenPyXL. All files are written to ``REPORTS_DIR``.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Image as RLImage,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from sqlalchemy import select
from sqlalchemy.orm import Session

from safecheck.config import REPORTS_DIR
from safecheck.core import models
from safecheck.core.enums import InspectionResult

_ANSWER_BG = {
    "Yes": colors.HexColor("#E6F4EA"),
    "No": colors.HexColor("#FDECEA"),
    "N/A": colors.HexColor("#ECEFF1"),
}
_RESULT_COLOR = {
    "Fit for Use": "#2E7D32", "Entry Approved": "#2E7D32",
    "Requires Attention": "#EF8A00",
    "No Go": "#C62828", "Entry Denied": "#C62828",
}
_NO_GO_RESULTS = {InspectionResult.NO_GO.value, InspectionResult.ENTRY_DENIED.value}


def _timestamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def _fmt(dt) -> str:
    return dt.strftime("%Y-%m-%d %H:%M") if dt else ""


# ---------------------------------------------------------------------------
# PDF — individual inspection report
# ---------------------------------------------------------------------------
def inspection_pdf(session: Session, inspection_id: int, out_path: str | Path | None = None) -> str:
    """Render a full PDF report for one inspection and return its file path."""
    inspection = session.get(models.Inspection, inspection_id)
    if inspection is None:
        raise ValueError("Inspection not found")

    template = inspection.template
    asset = inspection.asset
    inspector = inspection.inspector
    questions = list(session.scalars(
        select(models.ChecklistQuestion)
        .where(models.ChecklistQuestion.template_id == inspection.template_id,
               models.ChecklistQuestion.is_active.is_(True))
        .order_by(models.ChecklistQuestion.display_order)
    ).all())
    responses = {r.question_id: r for r in inspection.responses}

    out_path = Path(out_path) if out_path else REPORTS_DIR / f"inspection_{inspection.uuid[:8]}_{_timestamp()}.pdf"
    styles = getSampleStyleSheet()
    cell = ParagraphStyle("cell", parent=styles["BodyText"], fontSize=8, leading=10)
    title = ParagraphStyle("title", parent=styles["Title"], fontSize=16)

    story = [
        Paragraph("SafeCheck Inspection Report", title),
        Paragraph(template.name if template else "Inspection", styles["Heading2"]),
        Spacer(1, 6),
    ]

    # Header details table
    details = [
        ("Asset number", inspection.asset_number_text or "—"),
        ("Registration", inspection.registration_text or "—"),
        ("Description", asset.description if asset else "—"),
        ("Inspector", inspector.full_name if inspector else "—"),
        ("Date / time", _fmt(inspection.completion_time or inspection.start_time)),
        ("Driver / operator", inspection.driver_operator or inspection.driver_name or "—"),
        ("Department", inspection.department_text or inspection.host_department or "—"),
        ("Result", inspection.result or "—"),
    ]
    header_table = Table([[Paragraph(f"<b>{k}</b>", cell), Paragraph(str(v), cell)] for k, v in details],
                         colWidths=[45 * mm, 125 * mm])
    header_table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#D9E0E8")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#F2F5F9")),
        ("TEXTCOLOR", (1, len(details) - 1), (1, len(details) - 1),
         colors.HexColor(_RESULT_COLOR.get(inspection.result, "#1A2233"))),
    ]))
    story += [header_table, Spacer(1, 10),
              Paragraph("Checklist responses", styles["Heading3"])]

    # Responses table
    table_data = [[Paragraph("<b>#</b>", cell), Paragraph("<b>Question</b>", cell),
                   Paragraph("<b>Answer</b>", cell), Paragraph("<b>Comment</b>", cell)]]
    answer_bg_cmds = []
    for index, question in enumerate(questions, start=1):
        response = responses.get(question.id)
        answer = response.answer if response else "—"
        comment = (response.comment if response else "") or ""
        label = question.text + (" (NO GO)" if question.is_no_go else "")
        table_data.append([Paragraph(str(index), cell), Paragraph(label, cell),
                           Paragraph(answer, cell), Paragraph(comment, cell)])
        if answer in _ANSWER_BG:
            answer_bg_cmds.append(("BACKGROUND", (2, index), (2, index), _ANSWER_BG[answer]))

    responses_table = Table(table_data, colWidths=[10 * mm, 95 * mm, 18 * mm, 47 * mm], repeatRows=1)
    responses_table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#D9E0E8")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0D47A1")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        *answer_bg_cmds,
    ]))
    story.append(responses_table)

    if inspection.general_comment:
        story += [Spacer(1, 8), Paragraph(f"<b>General comment:</b> {inspection.general_comment}", cell)]

    # Photographs
    photos = [p for p in inspection.photos if Path(p.file_path).exists()]
    if photos:
        story += [Spacer(1, 10), Paragraph("Photographs", styles["Heading3"])]
        for photo in photos:
            try:
                story.append(RLImage(photo.file_path, width=80 * mm, height=60 * mm, kind="proportional"))
                story.append(Spacer(1, 6))
            except Exception:  # noqa: BLE001 — skip unreadable images
                continue

    SimpleDocTemplate(str(out_path), pagesize=A4,
                      topMargin=15 * mm, bottomMargin=15 * mm,
                      leftMargin=18 * mm, rightMargin=18 * mm).build(story)
    return str(out_path)


# ---------------------------------------------------------------------------
# Excel reports
# ---------------------------------------------------------------------------
def _write_xlsx(rows: list[dict], out_path: Path, sheet_name: str) -> str:
    frame = pd.DataFrame(rows) if rows else pd.DataFrame(columns=["(no data)"])
    with pd.ExcelWriter(out_path, engine="openpyxl") as writer:
        frame.to_excel(writer, index=False, sheet_name=sheet_name)
    return str(out_path)


def inspection_register_xlsx(session: Session, out_path: str | Path | None = None,
                             inspector_id: int | None = None) -> str:
    """Excel register of all inspections."""
    stmt = select(models.Inspection).order_by(models.Inspection.created_at.desc())
    if inspector_id is not None:
        stmt = stmt.where(models.Inspection.inspector_id == inspector_id)
    rows = [
        {
            "Reference": i.uuid[:8].upper(),
            "Checklist": i.template.name if i.template else "",
            "Asset": i.asset_number_text or "",
            "Inspector": i.inspector.full_name if i.inspector else "",
            "Date": _fmt(i.completion_time or i.created_at),
            "Result": i.result or "",
            "Sync status": i.sync_status,
        }
        for i in session.scalars(stmt).all()
    ]
    out_path = Path(out_path) if out_path else REPORTS_DIR / f"inspection_register_{_timestamp()}.xlsx"
    return _write_xlsx(rows, out_path, "Inspections")


def failed_items_xlsx(session: Session, out_path: str | Path | None = None) -> str:
    """Excel report of every failed item (finding)."""
    rows = [
        {
            "Reference": f.reference[:8].upper(),
            "Checklist": f.checklist_name or "",
            "Failed item": f.failed_question_text or "",
            "Comment": f.comment or "",
            "No Go": "Yes" if f.is_no_go else "No",
            "Status": f.status,
            "Date": _fmt(f.finding_date),
        }
        for f in session.scalars(
            select(models.Finding).order_by(models.Finding.finding_date.desc())
        ).all()
    ]
    out_path = Path(out_path) if out_path else REPORTS_DIR / f"failed_items_{_timestamp()}.xlsx"
    return _write_xlsx(rows, out_path, "Failed items")


def no_go_xlsx(session: Session, out_path: str | Path | None = None) -> str:
    """Excel report of No Go inspections."""
    rows = [
        {
            "Reference": i.uuid[:8].upper(),
            "Checklist": i.template.name if i.template else "",
            "Asset": i.asset_number_text or "",
            "Inspector": i.inspector.full_name if i.inspector else "",
            "Date": _fmt(i.completion_time or i.created_at),
            "Result": i.result or "",
        }
        for i in session.scalars(
            select(models.Inspection)
            .where(models.Inspection.result.in_(list(_NO_GO_RESULTS)))
            .order_by(models.Inspection.created_at.desc())
        ).all()
    ]
    out_path = Path(out_path) if out_path else REPORTS_DIR / f"no_go_report_{_timestamp()}.xlsx"
    return _write_xlsx(rows, out_path, "No Go")


def asset_history_xlsx(session: Session, out_path: str | Path | None = None) -> str:
    """Excel inspection-history report grouped by asset."""
    rows = [
        {
            "Asset": i.asset_number_text or "",
            "Checklist": i.template.name if i.template else "",
            "Inspector": i.inspector.full_name if i.inspector else "",
            "Date": _fmt(i.completion_time or i.created_at),
            "Result": i.result or "",
            "Sync status": i.sync_status,
        }
        for i in session.scalars(
            select(models.Inspection).order_by(
                models.Inspection.asset_number_text, models.Inspection.created_at.desc())
        ).all()
    ]
    out_path = Path(out_path) if out_path else REPORTS_DIR / f"asset_history_{_timestamp()}.xlsx"
    return _write_xlsx(rows, out_path, "Asset history")
