# ══════════════════════════════════════════════════════════════════════
# registro.py — Pannelli registro giornaliero (Docente + Studente)
# ══════════════════════════════════════════════════════════════════════

import threading
import flet as ft
from datetime import date

from styles import (
    SECONDARY_BG, TERTIARY_BG,
    TEXT_PRIMARY, TEXT_MUTED,
    ACCENT_BLUE, ACCENT_CYAN, ACCENT_RED,
    ACCENT_GREEN, ACCENT_YELLOW,
    BORDER_COLOR, BORDER_RADIUS,
    SUBJECTS_PALETTE, ICON_SAVE,
)
from utils_calendario import (
    GIORNI, MAX_ORE,
    get_registro_giorno, g_nome, salva_orario,
)
from ui_helpers import badge, pill, cal_tf


# ══════════════════════════════════════════════════════════════════════
# REGISTRO — VISTA DOCENTE
# ══════════════════════════════════════════════════════════════════════

def build_registro_docente_panel(
    state: dict,
    dt: date,
    page: ft.Page,
    on_save,            # callable() → aggiorna UI dopo salvataggio
    root: dict = None,  # root completo per salva_orario
) -> ft.Container:
    """Form per compilare argomenti, compiti e assenti del giorno dt."""

    reg  = get_registro_giorno(state, dt)
    gn   = g_nome(dt)
    ore_dt = state["orario"].get(gn, {})
    mats_oggi = list({
        ore_dt.get(h, {}).get("materia", "").strip()
        for h in range(1, MAX_ORE.get(gn, 6) + 1)
        if ore_dt.get(h, {}).get("materia", "").strip()
    })

    label_data = ft.Text(
        f"📖 Registro — {gn} {dt.strftime('%d/%m/%Y')}",
        size=14, weight="bold", color=TEXT_PRIMARY,
    )

    # Argomenti
    tf_arg = cal_tf(
        "Argomenti spiegati", expand=True,
        value=reg.get("argomenti", ""),
        multiline=True, min_lines=2, max_lines=5,
    )
    # Compiti
    tf_comp = cal_tf(
        "Compiti assegnati", expand=True,
        value=reg.get("compiti", ""),
        multiline=True, min_lines=2, max_lines=4,
    )

    # Assenti
    tf_nuovo_assente = cal_tf("Nome studente assente", width=220)
    assenti_list_col = ft.Column(spacing=4)

    def refresh_assenti():
        assenti_list_col.controls.clear()
        for nome in reg.get("assenti", []):
            def rimuovi(e, n=nome):
                if n in reg["assenti"]:
                    reg["assenti"].remove(n)
                refresh_assenti()
                page.update()

            assenti_list_col.controls.append(ft.Row([
                ft.Container(
                    padding=ft.padding.symmetric(horizontal=10, vertical=4),
                    border_radius=16,
                    bgcolor=ACCENT_RED + "20",
                    border=ft.border.all(1, ACCENT_RED + "50"),
                    content=ft.Text(nome, size=11, color=TEXT_PRIMARY),
                ),
                ft.IconButton(
                    ft.Icons.CLOSE,
                    icon_color=ACCENT_RED,
                    icon_size=14,
                    on_click=rimuovi,
                ),
            ], spacing=4))
        page.update()

    def aggiungi_assente(e):
        nome = tf_nuovo_assente.value.strip()
        if not nome:
            return
        reg.setdefault("assenti", [])
        if nome not in reg["assenti"]:
            reg["assenti"].append(nome)
        tf_nuovo_assente.value = ""
        refresh_assenti()

    tf_nuovo_assente.on_submit = aggiungi_assente
    refresh_assenti()

    # Salvataggio
    stato_salv = ft.Text("", size=10, color=ACCENT_GREEN)

    def salva(e):
        reg["argomenti"] = tf_arg.value.strip()
        reg["compiti"]   = tf_comp.value.strip()
        if root:
            salva_orario(root)
        stato_salv.value = "✅ Salvato!"
        page.update()
        on_save()

        def _clear():
            import time
            time.sleep(2)
            stato_salv.value = ""
            page.update()

        threading.Thread(target=_clear, daemon=True).start()

    # Materie del giorno
    mat_chips = ft.Row(
        [
            badge(m, SUBJECTS_PALETTE.get(m, SUBJECTS_PALETTE["default"])["accent"])
            for m in mats_oggi
        ] if mats_oggi else [ft.Text("Nessuna materia in orario", size=9, color=TEXT_MUTED)],
        spacing=6, wrap=True,
    )

    return ft.Container(
        padding=ft.padding.symmetric(horizontal=16, vertical=14),
        border_radius=BORDER_RADIUS,
        bgcolor=SECONDARY_BG,
        border=ft.border.all(2, ACCENT_CYAN + "60"),
        content=ft.Column([
            label_data,
            ft.Row([ft.Text("Materie oggi:", size=10, color=TEXT_MUTED), mat_chips],
                   spacing=8, wrap=True),
            ft.Divider(color=BORDER_COLOR, height=1),

            ft.Text("📚 Argomenti spiegati", size=11, weight="bold", color=ACCENT_CYAN),
            tf_arg,

            ft.Text("📝 Compiti assegnati", size=11, weight="bold", color=ACCENT_YELLOW),
            tf_comp,

            ft.Text("🙋 Assenti", size=11, weight="bold", color=ACCENT_RED),
            ft.Row([
                tf_nuovo_assente,
                pill("➕ Aggiungi", aggiungi_assente, color=ACCENT_RED),
            ], spacing=8, vertical_alignment=ft.CrossAxisAlignment.END),
            assenti_list_col,

            ft.Divider(color=BORDER_COLOR, height=1),
            ft.Row([
                pill(f"{ICON_SAVE} Salva registro", salva, color=ACCENT_GREEN),
                stato_salv,
            ], spacing=12, vertical_alignment=ft.CrossAxisAlignment.CENTER),
        ], spacing=10, tight=True),
    )


# ══════════════════════════════════════════════════════════════════════
# REGISTRO — VISTA STUDENTE
# ══════════════════════════════════════════════════════════════════════

def build_registro_studente_panel(
    state: dict,
    dt: date,
    nome_studente: str,
    page: ft.Page,
) -> ft.Container:
    """Vista sola lettura del registro per lo studente (presenza + argomenti + compiti)."""

    reg = get_registro_giorno(state, dt)
    gn  = g_nome(dt)

    era_presente = nome_studente not in reg.get("assenti", [])
    presenza_col = ACCENT_GREEN if era_presente else ACCENT_RED
    presenza_txt = "✅ Presente" if era_presente else "❌ Assente"

    argomenti = reg.get("argomenti", "").strip() or "—"
    compiti   = reg.get("compiti",   "").strip() or "—"

    ore_dt = state["orario"].get(gn, {})
    mats_oggi = list({
        ore_dt.get(h, {}).get("materia", "").strip()
        for h in range(1, MAX_ORE.get(gn, 6) + 1)
        if ore_dt.get(h, {}).get("materia", "").strip()
    })
    mat_chips = ft.Row(
        [
            badge(m, SUBJECTS_PALETTE.get(m, SUBJECTS_PALETTE["default"])["accent"])
            for m in mats_oggi
        ] if mats_oggi else [ft.Text("—", size=9, color=TEXT_MUTED)],
        spacing=6, wrap=True,
    )

    return ft.Container(
        padding=ft.padding.symmetric(horizontal=16, vertical=14),
        border_radius=BORDER_RADIUS,
        bgcolor=SECONDARY_BG,
        border=ft.border.all(2, ACCENT_CYAN + "60"),
        content=ft.Column([
            ft.Text(
                f"📖 Registro — {gn} {dt.strftime('%d/%m/%Y')}",
                size=14, weight="bold", color=TEXT_PRIMARY,
            ),
            ft.Row([ft.Text("Materie:", size=10, color=TEXT_MUTED), mat_chips],
                   spacing=8, wrap=True),
            ft.Divider(color=BORDER_COLOR, height=1),

            # Presenza
            ft.Container(
                padding=ft.padding.symmetric(horizontal=14, vertical=8),
                border_radius=12,
                bgcolor=presenza_col + "18",
                border=ft.border.all(1, presenza_col + "50"),
                content=ft.Row([
                    ft.Text(presenza_txt, size=13, weight="bold", color=presenza_col),
                ], spacing=8),
            ),

            # Argomenti
            ft.Text("📚 Argomenti spiegati", size=11, weight="bold", color=ACCENT_CYAN),
            ft.Container(
                padding=10, border_radius=10,
                bgcolor=ACCENT_CYAN + "10",
                border=ft.border.all(1, ACCENT_CYAN + "30"),
                content=ft.Text(argomenti, size=11, color=TEXT_PRIMARY, selectable=True),
            ),

            # Compiti
            ft.Text("📝 Compiti assegnati", size=11, weight="bold", color=ACCENT_YELLOW),
            ft.Container(
                padding=10, border_radius=10,
                bgcolor=ACCENT_YELLOW + "10",
                border=ft.border.all(1, ACCENT_YELLOW + "30"),
                content=ft.Text(compiti, size=11, color=TEXT_PRIMARY, selectable=True),
            ),
        ], spacing=10, tight=True),
    )
