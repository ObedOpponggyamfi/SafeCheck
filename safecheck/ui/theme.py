"""Visual theme and reusable UI components.

Everything that defines the look of SafeCheck lives here: the colour palette
(green/amber/red/grey per the spec) and small builder functions that produce the
large, simple cards and buttons the field interface relies on.

Built for the Flet 0.85 API, so all buttons are ``Container``-based tap targets
which gives full control over the large, friendly styling field users need.
"""
from __future__ import annotations

from typing import Callable

import flet as ft

# --- Palette --------------------------------------------------------------
# Asanko-Gold inspired industrial system: deep charcoal navigation paired with a
# metallic gold brand accent on white/soft-grey surfaces. Gold is used as a fill
# (with dark text) for branding and primary actions; the safety status colours
# (green/amber/red/grey) are reserved strictly for state.
PRIMARY = "#1C2731"        # Deep charcoal-slate (navigation, headers, text)
PRIMARY_DARK = "#121A22"
GOLD = "#C8A227"           # Brand gold (primary actions, logo, accents)
GOLD_DARK = "#9A7B12"      # Gold for icons/lines on light surfaces
GOLD_TINT = "#F6EFD6"      # Light gold chip/background tint
ON_GOLD = "#1C2731"        # Dark text/icons placed on a gold fill
ACCENT = GOLD
BG = "#F4F4F2"             # App background (warm soft grey)
CARD = "#FFFFFF"           # Content surfaces
NEUTRAL_BG = "#EDEEEC"     # Unselected control surface
TEXT = "#1C2731"           # Primary text (charcoal)
MUTED = "#5E6873"          # Secondary text
BORDER = "#E3E3DD"         # Neutral borders
WHITE = "#FFFFFF"

# Status colours — used sparingly, only for state and action.
GREEN = "#1E7E34"   # Satisfactory / Yes / Fit for Use / Entry Approved / online
AMBER = "#C77700"   # Requires attention (kept orange, distinct from brand gold)
RED = "#C0392B"     # Danger / No Go / Entry Denied / No / failures
GREY = "#7B8794"    # Not applicable / N/A
ONLINE = GREEN
OFFLINE = MUTED

RESULT_COLORS = {
    "Fit for Use": GREEN,
    "Entry Approved": GREEN,
    "Requires Attention": AMBER,
    "No Go": RED,
    "Entry Denied": RED,
}


def result_color(result: str | None) -> str:
    """Colour to represent an inspection result string."""
    return RESULT_COLORS.get(result or "", MUTED)


def fmt_dt(dt) -> str:
    """Format a datetime for display, tolerating ``None``."""
    return dt.strftime("%d %b %Y, %H:%M") if dt else "—"


def answer_button(label: str, color: str, on_click, selected: bool = False) -> ft.Container:
    """A large Yes/No/N-A button — neutral until selected, then strong colour.

    Per the design direction, unselected buttons stay neutral so only the chosen
    answer receives emphasis.
    """
    label_text = ft.Text(label, size=16, weight=ft.FontWeight.BOLD,
                         color=WHITE if selected else MUTED)
    return ft.Container(
        content=label_text, height=54, expand=True, border_radius=10,
        alignment=ft.Alignment.CENTER,
        bgcolor=color if selected else NEUTRAL_BG,
        border=None if selected else ft.Border.all(1, BORDER),
        ink=True, on_click=on_click,
    )


def style_answer_button(btn: ft.Container, color: str, selected: bool) -> None:
    """Restyle an existing answer button in place for its selected state."""
    btn.bgcolor = color if selected else NEUTRAL_BG
    btn.border = None if selected else ft.Border.all(1, BORDER)
    btn.content.color = WHITE if selected else MUTED


# --- Small helpers --------------------------------------------------------
def txt(value, size=14, bold=False, color=TEXT, italic=False) -> ft.Text:
    return ft.Text(
        str(value),
        size=size,
        weight=ft.FontWeight.BOLD if bold else None,
        color=color,
        italic=italic,
    )


def big_button(
    label: str,
    on_click: Callable,
    *,
    bgcolor: str = GOLD,
    color: str | None = None,
    icon=None,
    expand: bool = False,
    width: int | None = None,
    height: int = 52,
) -> ft.Container:
    """A large, rounded, tappable primary button (gold brand fill by default).

    Text colour is chosen automatically for contrast: dark on a gold fill, white
    on any darker fill (e.g. a red destructive action).
    """
    if color is None:
        color = ON_GOLD if bgcolor == GOLD else WHITE
    row_controls = []
    if icon is not None:
        row_controls.append(ft.Icon(icon, color=color, size=20))
    row_controls.append(ft.Text(label, color=color, size=16, weight=ft.FontWeight.BOLD))
    return ft.Container(
        content=ft.Row(row_controls, alignment=ft.MainAxisAlignment.CENTER, spacing=8, tight=True),
        bgcolor=bgcolor,
        border_radius=12,
        height=height,
        width=width,
        padding=ft.Padding.symmetric(horizontal=18, vertical=0),
        alignment=ft.Alignment.CENTER,
        on_click=on_click,
        ink=True,
        expand=expand,
    )


def outline_button(label, on_click, *, color=PRIMARY, expand=False, height=52) -> ft.Container:
    """A large outlined (secondary) button."""
    return ft.Container(
        content=ft.Text(label, color=color, size=16, weight=ft.FontWeight.BOLD),
        bgcolor=WHITE,
        border=ft.Border.all(1.5, color),
        border_radius=12,
        height=height,
        alignment=ft.Alignment.CENTER,
        on_click=on_click,
        ink=True,
        expand=expand,
    )


def card(content, *, padding=16, on_click=None, bgcolor=CARD) -> ft.Container:
    """A white rounded card with a subtle border."""
    return ft.Container(
        content=content,
        bgcolor=bgcolor,
        border_radius=14,
        padding=ft.Padding.all(padding),
        border=ft.Border.all(1, BORDER),
        on_click=on_click,
        ink=bool(on_click),
    )


def top_bar(title: str, on_back: Callable | None = None, action: ft.Control | None = None) -> ft.Container:
    """A coloured header bar with an optional back button and trailing action."""
    leading = []
    if on_back is not None:
        leading.append(ft.Container(
            content=ft.Icon(ft.Icons.ARROW_BACK, color=WHITE, size=24),
            on_click=on_back, ink=True, border_radius=20, padding=ft.Padding.all(6),
        ))
    leading.append(ft.Text(title, color=WHITE, size=20, weight=ft.FontWeight.BOLD, expand=True))
    if action is not None:
        leading.append(action)
    return ft.Container(
        content=ft.Row(leading, vertical_alignment=ft.CrossAxisAlignment.CENTER, spacing=10),
        bgcolor=PRIMARY,
        padding=ft.Padding.symmetric(horizontal=16, vertical=14),
        border=ft.Border(bottom=ft.BorderSide(3, GOLD)),  # gold brand accent line
    )


def badge(label: str, color: str) -> ft.Container:
    """A small coloured pill, e.g. the 'NO GO' marker on a question."""
    return ft.Container(
        content=ft.Text(label, color=WHITE, size=11, weight=ft.FontWeight.BOLD),
        bgcolor=color,
        border_radius=8,
        padding=ft.Padding.symmetric(horizontal=8, vertical=3),
    )


def result_chip(result: str | None) -> ft.Container:
    """A coloured chip showing an inspection result."""
    color = result_color(result)
    return ft.Container(
        content=ft.Text(result or "In progress", color=WHITE, size=13, weight=ft.FontWeight.BOLD),
        bgcolor=color,
        border_radius=10,
        padding=ft.Padding.symmetric(horizontal=12, vertical=6),
    )


def summary_card(label: str, value: int, color: str) -> ft.Container:
    """A compact home-screen summary card: big number over a label."""
    return ft.Container(
        content=ft.Column(
            [
                ft.Text(str(value), size=28, weight=ft.FontWeight.BOLD, color=color),
                ft.Text(label, size=12, color=MUTED),
            ],
            spacing=2,
            horizontal_alignment=ft.CrossAxisAlignment.START,
        ),
        bgcolor=CARD,
        border_radius=14,
        padding=ft.Padding.all(14),
        border=ft.Border.all(1, BORDER),
        width=150,
        height=92,
    )


def checklist_card(name: str, subtitle: str, icon, on_click: Callable) -> ft.Container:
    """A large checklist card for the home screen."""
    return ft.Container(
        content=ft.Row(
            [
                ft.Container(
                    content=ft.Icon(icon, color=GOLD_DARK, size=28),
                    bgcolor=GOLD_TINT, border_radius=12, padding=ft.Padding.all(12),
                ),
                ft.Column(
                    [
                        ft.Text(name, size=16, weight=ft.FontWeight.BOLD, color=TEXT),
                        ft.Text(subtitle, size=12, color=MUTED),
                    ],
                    spacing=2, expand=True,
                ),
                ft.Icon(ft.Icons.CHEVRON_RIGHT, color=MUTED, size=24),
            ],
            vertical_alignment=ft.CrossAxisAlignment.CENTER, spacing=14,
        ),
        bgcolor=CARD, border_radius=14, padding=ft.Padding.all(14),
        border=ft.Border.all(1, BORDER), on_click=on_click, ink=True,
    )


def banner(message: str, kind: str = "info") -> ft.Container:
    """A dismissible-looking message banner (info/success/error)."""
    palette = {
        "info": ("#ECEEF1", PRIMARY, ft.Icons.INFO),
        "success": ("#E6F4EA", GREEN, ft.Icons.CHECK_CIRCLE),
        "error": ("#FDECEA", RED, ft.Icons.ERROR),
    }
    bg, fg, icon = palette.get(kind, palette["info"])
    return ft.Container(
        content=ft.Row(
            [ft.Icon(icon, color=fg, size=20),
             ft.Text(message, color=fg, size=13, expand=True)],
            spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        bgcolor=bg, border_radius=12, padding=ft.Padding.all(12),
        border=ft.Border.all(1, fg),
    )
