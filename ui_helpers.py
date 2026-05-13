# ══════════════════════════════════════════════════════════════════════
# ui_helpers.py — Widget UI riutilizzabili (bottoni, badge, sezioni…)
# ══════════════════════════════════════════════════════════════════════

import flet as ft
from styles import (
    SECONDARY_BG, TERTIARY_BG, CARD_BG,
    TEXT_PRIMARY, TEXT_MUTED, TEXT_SECONDARY,
    ACCENT_BLUE, ACCENT_CYAN, ACCENT_GREEN, ACCENT_YELLOW,
    BORDER_COLOR, BORDER_COLOR_LIGHT, BORDER_RADIUS,
    ICON_CLASS,
)


# ── Sezione con titolo e bordo colorato ──────────────────────────────

def cal_section(title: str, icon: str, content: ft.Control, accent: str = ACCENT_BLUE) -> ft.Container:
    return ft.Container(
        padding=ft.padding.symmetric(horizontal=16, vertical=12),
        border_radius=BORDER_RADIUS,
        bgcolor=SECONDARY_BG,
        border=ft.border.all(1, BORDER_COLOR_LIGHT),
        content=ft.Column([
            ft.Row([
                ft.Container(width=4, height=20, border_radius=2, bgcolor=accent),
                ft.Text(f"{icon}  {title}", size=13, weight="bold", color=TEXT_PRIMARY),
            ], spacing=8),
            ft.Divider(color=BORDER_COLOR, height=1),
            content,
        ], spacing=10, tight=True),
    )


# ── TextField stile scuro ─────────────────────────────────────────────

def cal_tf(
    label: str,
    width=None,
    value: str = "",
    expand: bool = False,
    kb=None,
    multiline: bool = False,
    min_lines: int = 1,
    max_lines: int = 3,
) -> ft.TextField:
    kw = dict(
        label=label,
        value=value,
        color=TEXT_PRIMARY,
        label_style=ft.TextStyle(color=TEXT_MUTED, size=11),
        border_color=BORDER_COLOR_LIGHT,
        focused_border_color=ACCENT_BLUE,
        border_radius=10,
        content_padding=ft.padding.symmetric(horizontal=12, vertical=8),
        text_size=12,
        multiline=multiline,
        min_lines=min_lines,
        max_lines=max_lines,
    )
    if width:  kw["width"]  = width
    if expand: kw["expand"] = True
    if kb:     kw["keyboard_type"] = kb
    return ft.TextField(**kw)


# ── Dropdown stile scuro ──────────────────────────────────────────────

def cal_drop(label: str, opts: list, width=None, expand: bool = False) -> ft.Dropdown:
    kw = dict(
        label=label,
        options=[ft.dropdown.Option(o) for o in opts],
        color=TEXT_PRIMARY,
        label_style=ft.TextStyle(color=TEXT_MUTED, size=11),
        border_color=BORDER_COLOR_LIGHT,
        focused_border_color=ACCENT_BLUE,
        border_radius=10,
    )
    if width:  kw["width"]  = width
    if expand: kw["expand"] = True
    return ft.Dropdown(**kw)


# ── Bottone pill arrotondato ──────────────────────────────────────────

def pill(text: str, on_click, color: str = ACCENT_BLUE) -> ft.FilledButton:
    return ft.FilledButton(
        text,
        on_click=on_click,
        style=ft.ButtonStyle(
            bgcolor=color,
            color="#ffffff",
            shape=ft.RoundedRectangleBorder(radius=20),
            padding=ft.padding.symmetric(horizontal=16, vertical=8),
        ),
    )


# ── Badge colorato ────────────────────────────────────────────────────

def badge(text: str, color: str) -> ft.Container:
    return ft.Container(
        padding=ft.padding.symmetric(horizontal=10, vertical=3),
        border_radius=20,
        bgcolor=color + "25",
        border=ft.border.all(1, color + "60"),
        content=ft.Text(text, size=9, color=color, weight="bold"),
    )


# ── Info box ──────────────────────────────────────────────────────────

def info_box(text: str, color: str = ACCENT_BLUE) -> ft.Container:
    return ft.Container(
        padding=10,
        border_radius=12,
        bgcolor=color + "18",
        border=ft.border.all(1, color + "40"),
        content=ft.Text(text, size=10, color=color),
    )


# ── Box consiglio AI ──────────────────────────────────────────────────

def ai_consiglio_box(lines_ok: list[str], lines_no: list[str]) -> ft.Container:
    controls = [ft.Text("💡 Consiglio AI", size=11, weight="bold", color="#ffffff")]
    for l in lines_ok:
        controls.append(ft.Container(
            padding=ft.padding.symmetric(horizontal=8, vertical=5),
            border_radius=8,
            bgcolor=ACCENT_GREEN,
            content=ft.Text(l, size=10, color="#031a08", weight="bold"),
        ))
    for l in lines_no:
        controls.append(ft.Text(l, size=9, color="#8ab4d4"))
    return ft.Container(
        padding=12,
        border_radius=12,
        bgcolor="#071510",
        border=ft.border.all(1, ACCENT_GREEN),
        content=ft.Column(controls, spacing=5, tight=True),
    )


# ── Chip classe (bottone selezionato/non) ─────────────────────────────

def classe_chip(label: str, selected: bool, on_click) -> ft.FilledButton:
    return ft.FilledButton(
        label,
        on_click=on_click,
        style=ft.ButtonStyle(
            bgcolor=ACCENT_BLUE + "30" if selected else CARD_BG,
            color=TEXT_PRIMARY,
            shape=ft.RoundedRectangleBorder(radius=16),
            padding=ft.padding.symmetric(horizontal=12, vertical=5),
        ),
    )


# ── Selettore classe (input + chips) ─────────────────────────────────

def classe_selector(
    current: str,
    classi_list: list[str],
    on_change,
    page: ft.Page,
) -> ft.Container:
    inp = cal_tf("Classe", width=130, value=current)
    inp.on_submit = lambda e: on_change(inp.value.strip().upper())
    inp.on_blur   = lambda e: on_change(inp.value.strip().upper())
    chips_row = ft.Row(
        [classe_chip(c, c == current, lambda e, c=c: on_change(c)) for c in classi_list],
        spacing=5,
        wrap=True,
    )
    return ft.Container(
        padding=ft.padding.symmetric(horizontal=16, vertical=12),
        border_radius=BORDER_RADIUS,
        bgcolor=SECONDARY_BG,
        border=ft.border.all(1, ACCENT_CYAN + "40"),
        content=ft.Column([
            ft.Row([
                ft.Container(width=4, height=20, border_radius=2, bgcolor=ACCENT_CYAN),
                ft.Text(f"{ICON_CLASS}  Classe", size=13, weight="bold", color=TEXT_PRIMARY),
                ft.Container(expand=True),
                ft.Text(
                    "Dati caricati ✓" if current in classi_list else "Nuova classe",
                    size=9,
                    color=ACCENT_GREEN if current in classi_list else ACCENT_YELLOW,
                ),
            ], spacing=8),
            ft.Divider(color=BORDER_COLOR, height=1),
            ft.Row(
                [inp, ft.Text("← Invio per cambiare", size=9, color=TEXT_MUTED)],
                spacing=10,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            chips_row if classi_list else ft.Container(height=0),
        ], spacing=8, tight=True),
    )
