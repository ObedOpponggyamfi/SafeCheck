"""Inspection screen — select an asset, answer Yes/No/N/A, comment, submit.

This is the most important screen for field users, so it stays deliberately
simple: a header, large answer buttons, and a small panel that only appears when
an item fails. Every answer is auto-saved to SQLite the moment it is tapped.
"""
from __future__ import annotations

import flet as ft

from safecheck.core.database import SessionLocal
from safecheck.core.enums import AnswerType
from safecheck.data.checklists import header_for
from safecheck.services import inspection_service, photo_service
from safecheck.ui import theme

ANSWER_COLORS = {
    AnswerType.YES.value: theme.GREEN,
    AnswerType.NO.value: theme.RED,
    AnswerType.NA.value: theme.GREY,
}


class InspectionScreen:
    """Builds and drives a single inspection. One open session for its lifetime."""

    def __init__(self, app, template_id: int):
        self.app = app
        self.page = app.page
        self.session = SessionLocal()

        self.template = inspection_service.get_template(self.session, template_id)
        self.questions = inspection_service.active_questions(self.session, template_id)
        self.assets = inspection_service.list_assets_for_template(self.session, self.template)
        self.header_specs = header_for(self.template.result_mode)
        self.inspection = inspection_service.start_inspection(
            self.session, template_id, self.app.user_id, self.app.site_id
        )

        # Control references kept so handlers can restyle in place.
        self.q_controls: dict[int, dict] = {}
        self.asset_buttons: dict[int, ft.Container] = {}
        self.header_fields: dict[str, ft.TextField] = {}
        self.banner_holder = ft.Container(visible=False)
        self.asset_info = ft.Text("No asset selected", size=13, color=theme.MUTED)
        self.progress_text = ft.Text("0 of 0 completed", size=13, color=theme.WHITE, weight=ft.FontWeight.BOLD)
        self.result_holder = ft.Container(content=theme.result_chip(None))
        self.general_comment = ft.TextField(
            label="General comment (optional)", multiline=True, min_lines=2, max_lines=4,
            border_color=theme.BORDER,
        )

    # -- Build -------------------------------------------------------------
    def build(self) -> ft.Control:
        body = ft.Column(
            [
                self.banner_holder,
                self._captured_card(),
                self._asset_card(),
                self._header_card(),
                ft.Text("Checklist", size=15, weight=ft.FontWeight.BOLD, color=theme.TEXT),
                *[self._question_card(q) for q in self.questions],
                self.general_comment,
                ft.Container(height=8),
            ],
            spacing=12, scroll=ft.ScrollMode.AUTO, expand=True,
        )

        footer = ft.Container(
            content=ft.Row(
                [
                    theme.outline_button("Save Draft", self._on_save_draft, expand=True),
                    theme.big_button("Submit Inspection", self._on_submit, expand=True),
                ],
                spacing=12,
            ),
            bgcolor=theme.CARD, padding=ft.Padding.all(12),
            border=ft.Border.all(1, theme.BORDER),
        )

        self._refresh_progress()
        return ft.Column(
            [
                theme.top_bar(self.template.name, on_back=self._on_back, action=self.progress_text),
                ft.Container(content=body, expand=True, padding=ft.Padding.all(16)),
                footer,
            ],
            expand=True, spacing=0,
        )

    # -- Sub-sections ------------------------------------------------------
    def _captured_card(self) -> ft.Control:
        return theme.card(ft.Column(
            [
                ft.Text("Automatically captured", size=13, weight=ft.FontWeight.BOLD, color=theme.MUTED),
                ft.Text(f"Inspector: {self.app.user_name}", size=13, color=theme.TEXT),
                ft.Text(f"Date & time: {theme.fmt_dt(self.inspection.start_time)}", size=13, color=theme.TEXT),
                ft.Text(f"Site: {self.app.site_name}", size=13, color=theme.TEXT),
            ],
            spacing=4,
        ))

    def _asset_card(self) -> ft.Control:
        buttons = []
        for asset in self.assets:
            btn = ft.Container(
                content=ft.Column(
                    [
                        ft.Text(asset.asset_number, size=14, weight=ft.FontWeight.BOLD, color=theme.TEXT),
                        ft.Text(asset.registration_number or asset.description or "", size=11, color=theme.MUTED),
                    ],
                    spacing=2,
                ),
                bgcolor=theme.WHITE, border=ft.Border.all(1.5, theme.BORDER), border_radius=12,
                padding=ft.Padding.all(12), on_click=(lambda a: lambda e: self._select_asset(a))(asset), ink=True,
            )
            self.asset_buttons[asset.id] = btn
            buttons.append(btn)

        if not buttons:
            buttons = [ft.Text("No assets available for this checklist.", size=12, color=theme.MUTED)]

        return theme.card(ft.Column(
            [
                ft.Text("Select vehicle / machine", size=14, weight=ft.FontWeight.BOLD, color=theme.TEXT),
                ft.Row(buttons, wrap=True, spacing=10, run_spacing=10),
                self.asset_info,
            ],
            spacing=10,
        ))

    def _header_card(self) -> ft.Control:
        fields = []
        for spec in self.header_specs:
            tf = ft.TextField(
                label=spec["label"], border_color=theme.BORDER,
                on_blur=(lambda attr: lambda e: self._save_header(attr, e.control.value))(spec["attr"]),
            )
            self.header_fields[spec["attr"]] = tf
            fields.append(tf)
        return theme.card(ft.Column(
            [ft.Text("Inspection details", size=14, weight=ft.FontWeight.BOLD, color=theme.TEXT), *fields],
            spacing=10,
        ))

    def _question_card(self, question) -> ft.Control:
        buttons = {}
        button_row = []
        for value in (AnswerType.YES.value, AnswerType.NO.value, AnswerType.NA.value):
            color = ANSWER_COLORS[value]
            label = ft.Text(value, size=16, weight=ft.FontWeight.BOLD, color=color)
            btn = ft.Container(
                content=label, height=52, expand=True, border_radius=12,
                alignment=ft.Alignment.CENTER, bgcolor=theme.WHITE, border=ft.Border.all(1.5, color), ink=True,
                on_click=(lambda q, v: lambda e: self._on_answer(q, v))(question.id, value),
            )
            buttons[value] = (btn, color)
            button_row.append(btn)

        comment = ft.TextField(
            label="What is wrong?", multiline=True, min_lines=2, max_lines=3, border_color=theme.BORDER,
            on_blur=(lambda qid: lambda e: self._save_comment(qid, e.control.value))(question.id),
        )
        photo_label = ft.Text("Photograph optional", size=12, color=theme.MUTED)
        panel = ft.Container(
            content=ft.Column(
                [
                    comment,
                    ft.Row(
                        [theme.outline_button("Add / take photo",
                                              (lambda qid: lambda e: self._on_add_photo(qid))(question.id),
                                              height=44),
                         photo_label],
                        spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                ],
                spacing=8,
            ),
            visible=False, padding=ft.Padding.only(top=8),
        )

        self.q_controls[question.id] = {
            "buttons": buttons, "panel": panel, "comment": comment, "photo_label": photo_label,
        }

        header_row = [ft.Text(question.text, size=15, color=theme.TEXT, expand=True)]
        if question.is_no_go:
            header_row.append(theme.badge("NO GO", theme.RED))

        return theme.card(ft.Column(
            [
                ft.Row(header_row, vertical_alignment=ft.CrossAxisAlignment.CENTER, spacing=8),
                ft.Row(button_row, spacing=8),
                panel,
            ],
            spacing=10,
        ))

    # -- Handlers ----------------------------------------------------------
    def _select_asset(self, asset):
        inspection_service.set_asset(self.session, self.inspection, asset)
        for asset_id, btn in self.asset_buttons.items():
            selected = asset_id == asset.id
            btn.bgcolor = theme.PRIMARY if selected else theme.WHITE
            btn.border = None if selected else ft.Border.all(1.5, theme.BORDER)
            for text_control in btn.content.controls:
                text_control.color = theme.WHITE if selected else theme.TEXT
        self.asset_info.value = f"Selected: {asset.asset_number}  •  {asset.registration_number or '—'}"
        self.asset_info.color = theme.TEXT
        # Prefill department/contractor header fields if the asset provided them.
        for attr in ("department_text", "contractor_text"):
            if attr in self.header_fields and getattr(self.inspection, attr):
                self.header_fields[attr].value = getattr(self.inspection, attr)
        self.page.update()

    def _save_header(self, attr, value):
        inspection_service.update_header(self.session, self.inspection, **{attr: value})

    def _save_comment(self, question_id, value):
        inspection_service.set_comment(self.session, self.inspection, question_id, value)

    def _on_answer(self, question_id, value):
        inspection_service.record_response(self.session, self.inspection, question_id, value)
        controls = self.q_controls[question_id]
        for ans, (btn, color) in controls["buttons"].items():
            selected = ans == value
            btn.bgcolor = color if selected else theme.WHITE
            btn.border = None if selected else ft.Border.all(1.5, color)
            btn.content.color = theme.WHITE if selected else color
        controls["panel"].visible = value == AnswerType.NO.value
        self._refresh_progress()
        self.page.update()

    def _on_add_photo(self, question_id):
        try:
            files = self.app.file_picker.pick_files(
                dialog_title="Select a photograph", allow_multiple=False,
                allowed_extensions=["jpg", "jpeg", "png", "webp", "bmp"],
            )
        except Exception as exc:  # noqa: BLE001 — show any picker failure to the user
            self._show_banner("error", f"Could not open file picker: {exc}")
            return
        if not files:
            return

        response = inspection_service.record_response(
            self.session, self.inspection, question_id, AnswerType.NO.value
        )
        try:
            stored = photo_service.save_compressed_photo(files[0].path, self.inspection.uuid)
        except Exception as exc:  # noqa: BLE001
            self._show_banner("error", f"Could not save photo: {exc}")
            return

        from safecheck.core import models  # local import avoids a UI->model cycle
        self.session.add(models.InspectionPhoto(
            inspection_id=self.inspection.id, response_id=response.id, file_path=stored,
        ))
        self.session.commit()
        self.q_controls[question_id]["photo_label"].value = "Photo added ✓"
        self.q_controls[question_id]["photo_label"].color = theme.GREEN
        self.page.update()

    def _on_save_draft(self, _event):
        self._persist_general()
        inspection_service.save_draft(self.session, self.inspection)
        self._close()
        self.app.show_home(message=("info", "Draft saved. You can finish it later."))

    def _on_submit(self, _event):
        self._persist_general()
        errors = inspection_service.validate_submission(self.session, self.inspection)
        if errors:
            self._show_banner("error", "  ".join(f"• {e}" for e in errors))
            return
        inspection_service.submit_inspection(self.session, self.inspection)
        self._close()
        self.app.show_home(message=(
            "success",
            "Inspection saved successfully. It will synchronize when internet is available.",
        ))

    def _on_back(self, _event):
        # Answers are already auto-saved; keep the inspection as a draft.
        self._persist_general()
        inspection_service.save_draft(self.session, self.inspection)
        self._close()
        self.app.show_home()

    # -- Helpers -----------------------------------------------------------
    def _persist_general(self):
        inspection_service.update_header(
            self.session, self.inspection, general_comment=self.general_comment.value
        )

    def _refresh_progress(self):
        answered, total = inspection_service.progress(self.session, self.inspection)
        self.progress_text.value = f"{answered} of {total} completed"
        result = inspection_service.compute_result(self.session, self.inspection)
        self.result_holder.content = theme.result_chip(result if answered else None)

    def _show_banner(self, kind, message):
        self.banner_holder.content = theme.banner(message, kind)
        self.banner_holder.visible = True
        self.page.update()

    def _close(self):
        try:
            self.session.close()
        except Exception:  # noqa: BLE001 — closing should never crash navigation
            pass
