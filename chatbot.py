# ══════════════════════════════════════════════════════════════════════
# chatbot.py — Pannello chat AI (sidebar)
# Usa Ollama in locale per rispondere a domande sull'orario scolastico.
# ══════════════════════════════════════════════════════════════════════

import threading
import flet as ft
from datetime import date

from styles import (
    SECONDARY_BG, CARD_BG,
    TEXT_PRIMARY, TEXT_MUTED,
    ACCENT_BLUE,
    BORDER_COLOR, BORDER_COLOR_LIGHT,
    CHAT_SIDEBAR_WIDTH, ChatMessageStyle,
)
from utils_calendario import (
    GIORNI, MAX_ORE,
    call_ollama, parse_data, get_registro_giorno, g_nome,
)


def build_chat_panel(
    page: ft.Page,
    get_state,          # callable() → state dict della classe corrente
    get_classe,         # callable() → str nome classe corrente
) -> ft.Container:
    """
    Costruisce e restituisce il pannello chat AI laterale.

    Parametri
    ---------
    get_state  : lambda che ritorna il dict `state` della classe attiva
    get_classe : lambda che ritorna il nome della classe attiva (str)
    """

    oggi = date.today()

    # ── Messaggi ──────────────────────────────────────────────────────
    chat_msgs = ft.Column(spacing=6, scroll=ft.ScrollMode.AUTO)
    chat_in   = ft.TextField(
        hint_text="Chiedi all'AI...",
        expand=True,
        border=ft.InputBorder.NONE,
        bgcolor="transparent",
        color=TEXT_PRIMARY,
        hint_style=ft.TextStyle(color=TEXT_MUTED),
        text_size=12,
    )
    chat_spin = ft.ProgressRing(
        width=16, height=16, stroke_width=2,
        color=ACCENT_BLUE, visible=False,
    )

    def add_msg(txt: str, ai: bool = False) -> None:
        bubble = ft.Container(
            width=220,
            padding=10,
            border_radius=14,
            bgcolor=ChatMessageStyle.ai_bg if ai else ChatMessageStyle.user_bg,
            border=ft.border.all(1, BORDER_COLOR_LIGHT),
            content=ft.Text(txt, size=10, color=TEXT_PRIMARY, selectable=True),
        )
        chat_msgs.controls.append(
            ft.Row(
                [ft.Text("🤖", size=14), bubble] if ai else [bubble],
                alignment=ft.MainAxisAlignment.START if ai else ft.MainAxisAlignment.END,
                spacing=6,
            )
        )
        page.update()

    def chat_send(e=None) -> None:
        q = (chat_in.value or "").strip()
        if not q:
            return
        add_msg(q)
        chat_in.value = ""
        chat_spin.visible = True
        page.update()

        state  = get_state()
        classe = get_classe()

        def fetch():
            dt = parse_data(q, oggi)
            if dt:
                gn = g_nome(dt)
                if gn in GIORNI:
                    mat = [
                        state["orario"].get(gn, {}).get(h, {}).get("materia", "—")
                        for h in range(1, MAX_ORE[gn] + 1)
                    ]
                    resp = f"📅 {dt:%d/%m/%Y} ({gn}):\n" + \
                           "\n".join(f"  {i+1}ª: {m}" for i, m in enumerate(mat))
                    reg = get_registro_giorno(state, dt)
                    if reg.get("argomenti"):
                        resp += f"\n\n📚 Argomenti: {reg['argomenti']}"
                    if reg.get("compiti"):
                        resp += f"\n📝 Compiti: {reg['compiti']}"
                else:
                    resp = f"{dt:%d/%m/%Y} è {gn} — non scolastico 🏖️"
            else:
                orario_txt = "\n".join(
                    f"{g}: {', '.join(state['orario'].get(g, {}).get(h, {}).get('materia', '') for h in range(1, MAX_ORE[g]+1))}"
                    for g in GIORNI
                )
                resp = call_ollama(
                    q,
                    f"Assistente scolastico. Classe: {classe}.\n"
                    f"Orario:\n{orario_txt}\nRispondi brevemente in italiano.",
                )
            chat_spin.visible = False
            add_msg(resp, ai=True)

        threading.Thread(target=fetch, daemon=True).start()

    chat_in.on_submit = chat_send

    # ── Layout ────────────────────────────────────────────────────────
    return ft.Container(
        width=CHAT_SIDEBAR_WIDTH,
        bgcolor=SECONDARY_BG,
        border=ft.border.only(left=ft.BorderSide(1, BORDER_COLOR)),
        padding=14,
        content=ft.Column([
            ft.Row([
                ft.Text("🤖", size=18),
                ft.Text("Assistente AI", size=13, weight="bold", color=TEXT_PRIMARY),
            ], spacing=8),
            ft.Divider(color=BORDER_COLOR, height=1),
            ft.Container(
                expand=True,
                content=ft.Column([chat_msgs], scroll=ft.ScrollMode.AUTO),
            ),
            ft.Row([chat_spin], alignment=ft.MainAxisAlignment.CENTER),
            ft.Container(
                border_radius=12,
                bgcolor=CARD_BG,
                border=ft.border.all(1, BORDER_COLOR_LIGHT),
                padding=ft.padding.symmetric(horizontal=10, vertical=6),
                content=ft.Row([
                    chat_in,
                    ft.IconButton(
                        ft.Icons.SEND_ROUNDED,
                        icon_color=ACCENT_BLUE,
                        icon_size=18,
                        on_click=chat_send,
                    ),
                ], spacing=4),
            ),
        ], spacing=8, expand=True),
    )
