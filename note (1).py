# ══════════════════════════════════════════════════════════════════════
# note.py — Sezione Note / Piano di Studi (Studente + Docente)
# v2 — Miglioramenti:
#   • Checkbox completamento obiettivi nel Piano di Studi
#   • Priorità (Alta / Media / Bassa) con colori
#   • Ricerca full-text nelle Note Libere
#   • Contatore parole / caratteri in Note Libere
#   • AI usa Anthropic API (non più Ollama locale)
#   • Fix bug _note_utente (doppio return)
#   • Step by Step: segna lezione come "completata"
# ══════════════════════════════════════════════════════════════════════

import threading
import json
import os
import flet as ft
from datetime import date

from styles import (
    PRIMARY_BG, SECONDARY_BG, TERTIARY_BG, CARD_BG,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED,
    ACCENT_BLUE, ACCENT_CYAN, ACCENT_GREEN, ACCENT_YELLOW,
    ACCENT_RED, ACCENT_PURPLE, ACCENT_ORANGE,
    BORDER_COLOR, BORDER_COLOR_LIGHT, BORDER_RADIUS,
    SUBJECTS_PALETTE, ICON_SAVE,
)
from utils_calendario import (
    GIORNI, MAX_ORE,
    salva_orario, g_nome,
)
from ui_helpers import pill, badge, cal_tf, cal_drop

NOTE_FILE = "note.json"

# Priorità
PRIORITA_OPTS  = ["🔴 Alta", "🟡 Media", "🟢 Bassa"]
PRIORITA_COLORI = {
    "🔴 Alta":  ACCENT_RED,
    "🟡 Media": ACCENT_YELLOW,
    "🟢 Bassa": ACCENT_GREEN,
}


# ── Chiamata Anthropic API ─────────────────────────────────────────────

def _call_anthropic(prompt: str, system: str = "Sei un assistente scolastico. Rispondi in italiano in modo conciso.") -> str:
    """Chiama claude-sonnet via fetch API (usabile in thread)."""
    import urllib.request
    import json as j

    payload = j.dumps({
        "model": "claude-sonnet-4-20250514",
        "max_tokens": 1000,
        "system": system,
        "messages": [{"role": "user", "content": prompt}],
    }).encode()

    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01",
        },
        method="POST",
    )
    try:
        resp = j.loads(urllib.request.urlopen(req, timeout=30).read())
        return resp["content"][0]["text"]
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        return f"⚠️ Errore API ({e.code}): {body[:200]}"
    except Exception as ex:
        return f"⚠️ {ex.__class__.__name__}: {str(ex)[:120]}"


# ── Persistenza note ──────────────────────────────────────────────────

def _carica_note() -> dict:
    if os.path.exists(NOTE_FILE):
        try:
            return json.load(open(NOTE_FILE, encoding="utf-8"))
        except Exception:
            pass
    return {}


def _salva_note(data: dict) -> None:
    json.dump(data, open(NOTE_FILE, "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)


def _note_utente(username: str) -> tuple[dict, str]:
    """Ritorna (data_root, username). Crea la struttura se assente."""
    data = _carica_note()
    data.setdefault(username, {
        "piano_studi":  [],
        "step_by_step": [],
        "note_libere":  "",
    })
    return data, username


# ══════════════════════════════════════════════════════════════════════
# BUILD PRINCIPALE
# ══════════════════════════════════════════════════════════════════════

def build_note_panel(
    page: ft.Page,
    username: str,
    is_student: bool,
    get_state,    # callable() → state dict classe corrente
    get_classe,   # callable() → str nome classe
) -> ft.Container:
    """
    Pannello Note / Piano di Studi.
    Tab 1 — Piano di Studi   (obiettivi + priorità + completamento)
    Tab 2 — Step by Step     (lezioni settimanali + completamento + AI)
    Tab 3 — Note Libere      (editor + ricerca + contatore + AI)
    """

    data_root, uk = _note_utente(username)
    ud = data_root[uk]

    # ── Tab bar ───────────────────────────────────────────────────────
    tab_attivo = [0]
    body_col   = ft.Column(spacing=0, expand=True)

    TAB_LABELS = [
        ("🎯", "Piano di Studi"),
        ("🪜", "Step by Step"),
        ("📝", "Note Libere"),
    ]
    tab_refs = [ft.Ref[ft.Container]() for _ in TAB_LABELS]

    def _aggiorna_tab_style():
        for i, ref in enumerate(tab_refs):
            if ref.current:
                sel = (i == tab_attivo[0])
                ref.current.bgcolor = ACCENT_BLUE + "30" if sel else "transparent"
                ref.current.border  = ft.border.all(
                    2 if sel else 1,
                    ACCENT_BLUE if sel else BORDER_COLOR_LIGHT,
                )
        page.update()

    def _vai_tab(idx):
        tab_attivo[0] = idx
        _aggiorna_tab_style()
        _render_tab()

    def _tab_btn(idx, icona, label):
        return ft.Container(
            ref=tab_refs[idx],
            padding=ft.padding.symmetric(horizontal=14, vertical=8),
            border_radius=12,
            bgcolor="transparent",
            border=ft.border.all(1, BORDER_COLOR_LIGHT),
            ink=True,
            on_click=lambda e, i=idx: _vai_tab(i),
            content=ft.Row([
                ft.Text(icona, size=14),
                ft.Text(label, size=11, weight="bold", color=TEXT_PRIMARY),
            ], spacing=6, tight=True),
        )

    tab_bar = ft.Row(
        [_tab_btn(i, ico, lbl) for i, (ico, lbl) in enumerate(TAB_LABELS)],
        spacing=8, wrap=True,
    )

    # ══════════════════════════════════════════════════════════════════
    # TAB 1 — PIANO DI STUDI
    # ══════════════════════════════════════════════════════════════════

    def _build_piano():
        piano      = ud.setdefault("piano_studi", [])
        stato_salv = ft.Text("", size=10, color=ACCENT_GREEN)

        # Form aggiunta
        tf_obiettivo = cal_tf("Obiettivo *", expand=True)
        tf_argomento = cal_tf("Argomenti / Contenuti", expand=True)
        tf_data      = cal_tf("Scadenza (es. 25/05/2025)", width=180)

        MATERIE = [
            "Sistemi e Reti", "Informatica", "Telecomunicazioni",
            "Matematica", "Lingua inglese", "Italiano", "Storia",
            "Scienze", "Fisica", "Educazione Fisica", "Religione",
        ]
        dd_materia  = cal_drop("Materia", MATERIE, width=200)
        dd_priorita = cal_drop("Priorità", PRIORITA_OPTS, width=160)

        righe_col  = ft.Column(spacing=6)
        stat_label = ft.Text("", size=10, color=TEXT_MUTED)

        def _salva_piano():
            dr2 = _carica_note()
            dr2.setdefault(uk, ud)
            dr2[uk]["piano_studi"] = piano
            _salva_note(dr2)

        def _toggle_completato(idx):
            piano[idx]["completato"] = not piano[idx].get("completato", False)
            _salva_piano()
            _refresh_righe()
            page.update()

        def _refresh_righe():
            righe_col.controls.clear()

            totale     = len(piano)
            completati = sum(1 for v in piano if v.get("completato"))
            perc       = int(completati / totale * 100) if totale else 0
            stat_label.value = f"✅ {completati}/{totale} completati ({perc}%)"

            # Header
            righe_col.controls.append(ft.Container(
                padding=ft.padding.symmetric(horizontal=10, vertical=6),
                border_radius=8, bgcolor=TERTIARY_BG,
                content=ft.Row([
                    ft.Container(width=26),
                    ft.Text("🎯  Obiettivo",  size=10, weight="bold", color=TEXT_MUTED, expand=2),
                    ft.Text("📖  Argomenti",  size=10, weight="bold", color=TEXT_MUTED, expand=2),
                    ft.Text("🏫  Materia",    size=10, weight="bold", color=TEXT_MUTED, expand=2),
                    ft.Text("⚡ Priorità",    size=10, weight="bold", color=TEXT_MUTED, expand=1),
                    ft.Text("📅  Scadenza",   size=10, weight="bold", color=TEXT_MUTED, expand=1),
                    ft.Container(width=36),
                ], spacing=8),
            ))

            if not piano:
                righe_col.controls.append(ft.Container(
                    padding=ft.padding.symmetric(vertical=20),
                    content=ft.Text(
                        "Nessun obiettivo ancora — aggiungine uno qui sotto",
                        size=11, color=TEXT_MUTED, text_align=ft.TextAlign.CENTER,
                    ),
                ))

            # Ordina: prima non-completati, poi completati
            ordinati = sorted(enumerate(piano), key=lambda x: x[1].get("completato", False))

            for idx, voce in ordinati:
                pal        = SUBJECTS_PALETTE.get(voce.get("materia", ""), SUBJECTS_PALETTE["default"])
                completato = voce.get("completato", False)
                prio       = voce.get("priorita", "🟢 Bassa")
                prio_col   = PRIORITA_COLORI.get(prio, ACCENT_GREEN)

                def elimina(e, i=idx):
                    piano.pop(i)
                    _salva_piano()
                    _refresh_righe()
                    page.update()

                def toggle(e, i=idx):
                    _toggle_completato(i)

                riga_bg = TERTIARY_BG if completato else pal["bg"]

                riga = ft.Container(
                    padding=ft.padding.symmetric(horizontal=10, vertical=8),
                    border_radius=10,
                    bgcolor=riga_bg,
                    border=ft.border.all(
                        1,
                        (ACCENT_GREEN + "70") if completato else (pal["accent"] + "50"),
                    ),
                    opacity=0.55 if completato else 1.0,
                    content=ft.Row([
                        ft.Checkbox(
                            value=completato,
                            on_change=toggle,
                            active_color=ACCENT_GREEN,
                        ),
                        ft.Text(
                            voce.get("obiettivo", "—"),
                            size=11, color=TEXT_PRIMARY, expand=2,
                            overflow=ft.TextOverflow.ELLIPSIS,
                            spans=[ft.TextSpan(
                                style=ft.TextStyle(decoration=ft.TextDecoration.LINE_THROUGH)
                            )] if completato else [],
                        ),
                        ft.Text(voce.get("argomenti", "—"), size=10,
                                color=TEXT_SECONDARY, expand=2,
                                overflow=ft.TextOverflow.ELLIPSIS),
                        ft.Container(
                            expand=2,
                            content=badge(voce.get("materia", "—"), pal["accent"]),
                        ),
                        ft.Container(
                            expand=1,
                            content=badge(prio, prio_col),
                        ),
                        ft.Text(voce.get("data", "—"), size=10,
                                color=ACCENT_CYAN, expand=1),
                        ft.IconButton(
                            ft.Icons.DELETE_OUTLINE,
                            icon_color=ACCENT_RED, icon_size=16,
                            on_click=elimina,
                        ),
                    ], spacing=8),
                )
                righe_col.controls.append(riga)
            page.update()

        def aggiungi_voce(e=None):
            ob = tf_obiettivo.value.strip()
            ar = tf_argomento.value.strip()
            ma = dd_materia.value or ""
            da = tf_data.value.strip()
            pr = dd_priorita.value or "🟢 Bassa"
            if not ob:
                stato_salv.value = "⚠️ Inserisci almeno l'obiettivo."
                page.update(); return
            piano.append({
                "obiettivo":  ob,
                "argomenti":  ar,
                "materia":    ma,
                "data":       da,
                "priorita":   pr,
                "completato": False,
            })
            _salva_piano()
            tf_obiettivo.value = ""
            tf_argomento.value = ""
            dd_materia.value   = None
            dd_priorita.value  = None
            tf_data.value      = ""
            stato_salv.value   = "✅ Obiettivo aggiunto!"
            _refresh_righe()
            page.update()

            def _clear():
                import time; time.sleep(2)
                stato_salv.value = ""
                page.update()
            threading.Thread(target=_clear, daemon=True).start()

        _refresh_righe()

        # Pulsante AI: suggerisce un piano di studio
        ai_spin_piano = ft.ProgressRing(width=16, height=16, stroke_width=2,
                                        color=ACCENT_BLUE, visible=False)
        ai_box_piano  = ft.Container(
            visible=False, padding=10, border_radius=12,
            bgcolor=ACCENT_BLUE + "10",
            border=ft.border.all(1, ACCENT_BLUE + "40"),
            content=ft.Text("", size=10, color=TEXT_PRIMARY, selectable=True),
        )

        def suggerisci_piano_ai(e=None):
            non_completati = [v for v in piano if not v.get("completato")]
            if not non_completati:
                ai_box_piano.content.value = "Tutti gli obiettivi sono completati! 🎉"
                ai_box_piano.visible = True
                page.update(); return
            ai_spin_piano.visible = True
            page.update()

            def _fetch():
                lista = "\n".join(
                    f"- [{v.get('priorita','?')}] {v.get('obiettivo','')} "
                    f"(Materia: {v.get('materia','?')}, Scadenza: {v.get('data','?')})"
                    for v in non_completati
                )
                prompt = (
                    f"Ho questi obiettivi di studio non ancora completati:\n{lista}\n\n"
                    "Suggerisci come organizzare lo studio in modo efficace, "
                    "rispettando le priorità e le scadenze. Sii conciso e pratico."
                )
                resp = _call_anthropic(prompt)
                ai_box_piano.content.value = resp
                ai_box_piano.visible  = True
                ai_spin_piano.visible = False
                page.update()

            threading.Thread(target=_fetch, daemon=True).start()

        form_aggiungi = ft.Container(
            padding=ft.padding.symmetric(horizontal=14, vertical=12),
            border_radius=14, bgcolor=SECONDARY_BG,
            border=ft.border.all(1, ACCENT_BLUE + "40"),
            content=ft.Column([
                ft.Text("➕  Aggiungi obiettivo", size=11, weight="bold", color=ACCENT_BLUE),
                ft.Row([tf_obiettivo, tf_argomento], spacing=8),
                ft.Row([dd_materia, dd_priorita, tf_data], spacing=8, wrap=True),
                ft.Row([
                    pill(f"{ICON_SAVE} Aggiungi", aggiungi_voce, color=ACCENT_BLUE),
                    stato_salv,
                ], spacing=12, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            ], spacing=8, tight=True),
        )

        return ft.Column([
            ft.Row([
                ft.Text("🎯  Piano di Studi", size=14, weight="bold", color=TEXT_PRIMARY),
                ft.Container(expand=True),
                stat_label,
            ]),
            ft.Text("Organizza obiettivi, priorità e scadenze per materia.",
                    size=10, color=TEXT_MUTED),
            ft.Divider(color=BORDER_COLOR, height=1),
            ft.Container(
                padding=ft.padding.symmetric(horizontal=14, vertical=12),
                border_radius=14, bgcolor=SECONDARY_BG,
                border=ft.border.all(1, BORDER_COLOR_LIGHT),
                content=ft.Column([righe_col], spacing=0, tight=True),
            ),
            form_aggiungi,
            ft.Row([
                ft.FilledButton(
                    "💡 Suggerisci piano con AI",
                    on_click=suggerisci_piano_ai,
                    style=ft.ButtonStyle(
                        bgcolor=ACCENT_BLUE + "30", color=ACCENT_BLUE,
                        shape=ft.RoundedRectangleBorder(radius=20),
                        padding=ft.padding.symmetric(horizontal=16, vertical=8),
                    ),
                ),
                ai_spin_piano,
            ], spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            ai_box_piano,
        ], spacing=10, tight=True)

    # ══════════════════════════════════════════════════════════════════
    # TAB 2 — STEP BY STEP
    # ══════════════════════════════════════════════════════════════════

    def _build_step():
        steps      = ud.setdefault("step_by_step", [])
        stato_salv = ft.Text("", size=10, color=ACCENT_GREEN)
        ai_spin    = ft.ProgressRing(width=16, height=16, stroke_width=2,
                                     color=ACCENT_CYAN, visible=False)

        tf_titolo = cal_tf("Titolo lezione / argomento", expand=True)
        tf_note   = cal_tf("Note", expand=True, multiline=True,
                           min_lines=2, max_lines=3)
        dd_giorno = cal_drop("Giorno", GIORNI, width=140)

        steps_col = ft.Column(spacing=6)

        def _salva_steps():
            dr2 = _carica_note()
            dr2.setdefault(uk, ud)
            dr2[uk]["step_by_step"] = steps
            _salva_note(dr2)

        def _toggle_step(idx):
            steps[idx]["completato"] = not steps[idx].get("completato", False)
            _salva_steps()
            _refresh_steps()
            page.update()

        def _refresh_steps():
            steps_col.controls.clear()

            per_giorno: dict[str, list] = {}
            for idx, s in enumerate(steps):
                g = s.get("giorno", "—")
                per_giorno.setdefault(g, []).append((idx, s))

            for giorno in GIORNI:
                grp = per_giorno.get(giorno, [])
                if not grp:
                    continue

                completati_g = sum(1 for _, s in grp if s.get("completato"))
                steps_col.controls.append(ft.Container(
                    padding=ft.padding.symmetric(horizontal=8, vertical=4),
                    border_radius=8, bgcolor=TERTIARY_BG,
                    content=ft.Row([
                        ft.Text(giorno, size=11, weight="bold", color=ACCENT_CYAN, expand=True),
                        ft.Text(f"{completati_g}/{len(grp)} ✓",
                                size=9, color=ACCENT_GREEN if completati_g == len(grp) else TEXT_MUTED),
                    ]),
                ))

                for idx, step in grp:
                    completato = step.get("completato", False)

                    def elimina(e, i=idx):
                        steps.pop(i)
                        _salva_steps()
                        _refresh_steps()
                        page.update()

                    def toggle(e, i=idx):
                        _toggle_step(i)

                    steps_col.controls.append(ft.Container(
                        padding=ft.padding.symmetric(horizontal=12, vertical=8),
                        border_radius=10,
                        bgcolor=CARD_BG,
                        opacity=0.55 if completato else 1.0,
                        border=ft.border.all(
                            1,
                            (ACCENT_GREEN + "50") if completato else (ACCENT_PURPLE + "40"),
                        ),
                        content=ft.Row([
                            ft.Container(
                                width=4, height=40, border_radius=2,
                                bgcolor=ACCENT_GREEN if completato else ACCENT_PURPLE,
                            ),
                            ft.Column([
                                ft.Text(step.get("titolo", "—"), size=11,
                                        weight="bold", color=TEXT_PRIMARY),
                                ft.Text(step.get("note", ""), size=9,
                                        color=TEXT_MUTED,
                                        overflow=ft.TextOverflow.ELLIPSIS, max_lines=2),
                            ], spacing=2, tight=True, expand=True),
                            ft.Checkbox(
                                value=completato,
                                on_change=toggle,
                                active_color=ACCENT_GREEN,
                                tooltip="Segna come completata",
                            ),
                            ft.IconButton(
                                ft.Icons.DELETE_OUTLINE,
                                icon_color=ACCENT_RED, icon_size=14,
                                on_click=elimina,
                            ),
                        ], spacing=10),
                    ))

            if not steps:
                steps_col.controls.append(
                    ft.Text("Nessuna lezione ancora.", size=11, color=TEXT_MUTED)
                )
            page.update()

        def aggiungi_step(e=None):
            titolo = tf_titolo.value.strip()
            note   = tf_note.value.strip()
            giorno = dd_giorno.value or ""
            if not titolo or not giorno:
                stato_salv.value = "⚠️ Inserisci titolo e giorno."
                page.update(); return
            steps.append({"titolo": titolo, "note": note,
                          "giorno": giorno, "completato": False})
            _salva_steps()
            tf_titolo.value  = ""
            tf_note.value    = ""
            dd_giorno.value  = None
            stato_salv.value = "✅ Lezione aggiunta!"
            _refresh_steps()
            page.update()

            def _clear():
                import time; time.sleep(2)
                stato_salv.value = ""
                page.update()
            threading.Thread(target=_clear, daemon=True).start()

        # AI result box
        ai_result_box = ft.Container(
            visible=False, padding=10, border_radius=12,
            bgcolor=ACCENT_CYAN + "10",
            border=ft.border.all(1, ACCENT_CYAN + "40"),
            content=ft.Text("", size=10, color=TEXT_PRIMARY, selectable=True),
        )

        def sintetizza_ai(e=None):
            if not steps:
                ai_result_box.content.value = "Aggiungi prima delle lezioni."
                ai_result_box.visible = True
                page.update(); return

            classe = get_classe()
            ai_spin.visible = True
            page.update()

            def _fetch():
                riepilogo = "\n".join(
                    f"- {s.get('giorno','?')}: {s.get('titolo','')} "
                    f"({'✓ completata' if s.get('completato') else 'da fare'})"
                    for s in steps
                )
                prompt = (
                    f"Classe {classe}. Piano lezioni step by step:\n{riepilogo}\n\n"
                    "Sintetizza in 3-5 punti chiave e suggerisci come strutturare "
                    "gli appunti per prepararsi al meglio. Indica quali lezioni "
                    "non completate richiedono più attenzione."
                )
                resp = _call_anthropic(prompt)
                ai_result_box.content.value = resp
                ai_result_box.visible  = True
                ai_spin.visible = False
                page.update()

            threading.Thread(target=_fetch, daemon=True).start()

        _refresh_steps()

        # Panoramica settimana
        settimana_cols = []
        for g in GIORNI:
            grp = [s for s in steps if s.get("giorno") == g]
            items = [
                ft.Container(
                    padding=ft.padding.symmetric(horizontal=6, vertical=4),
                    border_radius=6,
                    bgcolor=(ACCENT_GREEN + "20") if s.get("completato") else (ACCENT_PURPLE + "20"),
                    border=ft.border.all(
                        1,
                        (ACCENT_GREEN + "50") if s.get("completato") else (ACCENT_PURPLE + "50"),
                    ),
                    content=ft.Text(
                        ("✓ " if s.get("completato") else "") + s.get("titolo", "")[:20],
                        size=9, color=TEXT_PRIMARY,
                    ),
                ) for s in grp
            ]
            settimana_cols.append(ft.Container(
                expand=True,
                padding=ft.padding.symmetric(horizontal=6, vertical=8),
                border_radius=10, bgcolor=TERTIARY_BG,
                border=ft.border.all(1, BORDER_COLOR_LIGHT),
                content=ft.Column(
                    [
                        ft.Text(g[:3].upper(), size=9, weight="bold", color=ACCENT_CYAN),
                        ft.Divider(color=BORDER_COLOR, height=1),
                    ] + (items if items else [ft.Text("—", size=9, color=TEXT_MUTED)]),
                    spacing=4, tight=True,
                ),
            ))

        settimana_row = ft.Row(settimana_cols, spacing=6, expand=True)

        form_step = ft.Container(
            padding=ft.padding.symmetric(horizontal=14, vertical=12),
            border_radius=14, bgcolor=SECONDARY_BG,
            border=ft.border.all(1, ACCENT_PURPLE + "40"),
            content=ft.Column([
                ft.Text("➕  Aggiungi lezione", size=11, weight="bold", color=ACCENT_PURPLE),
                ft.Row([tf_titolo, dd_giorno], spacing=8, wrap=True),
                tf_note,
                ft.Row([
                    pill(f"{ICON_SAVE} Aggiungi", aggiungi_step, color=ACCENT_PURPLE),
                    stato_salv,
                ], spacing=12, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            ], spacing=8, tight=True),
        )

        return ft.Column([
            ft.Text("🪜  Step by Step", size=14, weight="bold", color=TEXT_PRIMARY),
            ft.Text("Pianifica le lezioni — spunta quelle già studiate.",
                    size=10, color=TEXT_MUTED),
            ft.Divider(color=BORDER_COLOR, height=1),

            ft.Container(
                padding=ft.padding.symmetric(horizontal=14, vertical=10),
                border_radius=14, bgcolor=SECONDARY_BG,
                border=ft.border.all(1, BORDER_COLOR_LIGHT),
                content=ft.Column([
                    ft.Text("📅  Panoramica settimana", size=11,
                            weight="bold", color=TEXT_PRIMARY),
                    ft.Divider(color=BORDER_COLOR, height=1),
                    settimana_row,
                ], spacing=8, tight=True),
            ),

            ft.Container(
                padding=ft.padding.symmetric(horizontal=14, vertical=12),
                border_radius=14, bgcolor=SECONDARY_BG,
                border=ft.border.all(1, BORDER_COLOR_LIGHT),
                content=steps_col,
            ),

            form_step,

            ft.Row([
                ft.FilledButton(
                    "💡 Sintetizza appunti con AI",
                    on_click=sintetizza_ai,
                    style=ft.ButtonStyle(
                        bgcolor=ACCENT_CYAN + "30", color=ACCENT_CYAN,
                        shape=ft.RoundedRectangleBorder(radius=20),
                        padding=ft.padding.symmetric(horizontal=16, vertical=8),
                    ),
                ),
                ai_spin,
            ], spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER),

            ai_result_box,
        ], spacing=10, tight=True)

    # ══════════════════════════════════════════════════════════════════
    # TAB 3 — NOTE LIBERE
    # ══════════════════════════════════════════════════════════════════

    def _build_note_libere():
        testo_iniziale = ud.get("note_libere", "")
        stato_salv     = ft.Text("", size=10, color=ACCENT_GREEN)
        contatore_txt  = ft.Text(
            f"{len(testo_iniziale)} caratteri · {len(testo_iniziale.split()) if testo_iniziale else 0} parole",
            size=9, color=TEXT_MUTED,
        )

        tf_cerca = ft.TextField(
            hint_text="🔍 Cerca nel testo…",
            expand=True,
            border=ft.InputBorder.OUTLINE,
            border_color=BORDER_COLOR_LIGHT,
            focused_border_color=ACCENT_YELLOW,
            color=TEXT_PRIMARY,
            hint_style=ft.TextStyle(color=TEXT_MUTED, size=11),
            text_size=11,
            border_radius=10,
            content_padding=ft.padding.symmetric(horizontal=12, vertical=8),
            bgcolor=CARD_BG,
        )
        cerca_result = ft.Text("", size=9, color=ACCENT_YELLOW)

        tf_note = ft.TextField(
            value=testo_iniziale,
            multiline=True, min_lines=12, max_lines=30,
            expand=True,
            hint_text="Scrivi qui i tuoi appunti, riflessioni, idee…",
            color=TEXT_PRIMARY,
            hint_style=ft.TextStyle(color=TEXT_MUTED, size=11),
            border_color=BORDER_COLOR_LIGHT,
            focused_border_color=ACCENT_YELLOW,
            border_radius=14,
            content_padding=ft.padding.symmetric(horizontal=16, vertical=14),
            text_size=12,
            bgcolor=CARD_BG,
        )

        def _aggiorna_contatore(e=None):
            testo = tf_note.value or ""
            parole = len(testo.split()) if testo.strip() else 0
            contatore_txt.value = f"{len(testo)} caratteri · {parole} parole"
            page.update()

        tf_note.on_change = _aggiorna_contatore

        def cerca(e=None):
            query = tf_cerca.value.strip().lower()
            if not query:
                cerca_result.value = ""
                page.update(); return
            testo = tf_note.value or ""
            occorrenze = testo.lower().count(query)
            if occorrenze:
                cerca_result.value = f"🔍 '{query}' trovato {occorrenze} volta/e"
            else:
                cerca_result.value = f"❌ '{query}' non trovato"
            page.update()

        tf_cerca.on_submit = cerca
        tf_cerca.on_change = cerca

        def salva_note(e=None):
            dr2 = _carica_note()
            dr2.setdefault(uk, ud)
            dr2[uk]["note_libere"] = tf_note.value.strip()
            _salva_note(dr2)
            stato_salv.value = "✅ Note salvate!"
            page.update()

            def _clear():
                import time; time.sleep(2)
                stato_salv.value = ""
                page.update()
            threading.Thread(target=_clear, daemon=True).start()

        ai_spin = ft.ProgressRing(width=16, height=16, stroke_width=2,
                                  color=ACCENT_YELLOW, visible=False)
        ai_box  = ft.Container(
            visible=False, padding=10, border_radius=12,
            bgcolor=ACCENT_YELLOW + "10",
            border=ft.border.all(1, ACCENT_YELLOW + "40"),
            content=ft.Text("", size=10, color=TEXT_PRIMARY, selectable=True),
        )

        def riassumi_ai(e=None):
            testo = tf_note.value.strip()
            if not testo:
                ai_box.content.value = "Nessun testo da riassumere."
                ai_box.visible = True
                page.update(); return
            ai_spin.visible = True
            page.update()

            def _fetch():
                prompt = (
                    "Riassumi in modo chiaro e strutturato le seguenti note scolastiche. "
                    "Usa bullet point organizzati per argomento. "
                    "Evidenzia i concetti chiave con ⭐. "
                    f"Rispondi in italiano.\n\n---\n{testo[:3000]}"
                )
                resp = _call_anthropic(prompt)
                ai_box.content.value = resp
                ai_box.visible  = True
                ai_spin.visible = False
                page.update()

            threading.Thread(target=_fetch, daemon=True).start()

        return ft.Column([
            ft.Text("📝  Note Libere", size=14, weight="bold", color=TEXT_PRIMARY),
            ft.Text("Spazio personale per appunti, riflessioni e idee.",
                    size=10, color=TEXT_MUTED),
            ft.Divider(color=BORDER_COLOR, height=1),

            # Barra ricerca
            ft.Container(
                padding=ft.padding.symmetric(horizontal=12, vertical=8),
                border_radius=10, bgcolor=SECONDARY_BG,
                border=ft.border.all(1, BORDER_COLOR_LIGHT),
                content=ft.Row([
                    tf_cerca,
                    ft.Container(width=8),
                    cerca_result,
                ], spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            ),

            tf_note,
            ft.Row([contatore_txt], alignment=ft.MainAxisAlignment.END),
            ft.Row([
                pill(f"{ICON_SAVE} Salva note", salva_note, color=ACCENT_YELLOW),
                ft.FilledButton(
                    "💡 Riassumi con AI",
                    on_click=riassumi_ai,
                    style=ft.ButtonStyle(
                        bgcolor=ACCENT_CYAN + "25", color=ACCENT_CYAN,
                        shape=ft.RoundedRectangleBorder(radius=20),
                        padding=ft.padding.symmetric(horizontal=14, vertical=8),
                    ),
                ),
                ai_spin,
                stato_salv,
            ], spacing=10, wrap=True,
               vertical_alignment=ft.CrossAxisAlignment.CENTER),
            ai_box,
        ], spacing=10, tight=True)

    # ── Render tab attivo ─────────────────────────────────────────────

    def _render_tab():
        body_col.controls.clear()
        builders = [_build_piano, _build_step, _build_note_libere]
        body_col.controls.append(builders[tab_attivo[0]]())
        page.update()

    _render_tab()
    _aggiorna_tab_style()

    return ft.Container(
        expand=True,
        padding=ft.padding.symmetric(horizontal=28, vertical=24),
        content=ft.Column([
            ft.Text("📒  Note & Piano di Studi", size=20, weight="bold",
                    color=TEXT_PRIMARY),
            ft.Text(
                "Organizza i tuoi obiettivi, le lezioni e i tuoi appunti personali.",
                size=11, color=TEXT_MUTED,
            ),
            ft.Container(height=4),
            tab_bar,
            ft.Divider(color=BORDER_COLOR, height=1),
            ft.Container(
                expand=True,
                content=ft.Column(
                    [body_col],
                    scroll=ft.ScrollMode.AUTO,
                    expand=True,
                ),
            ),
        ], spacing=12, expand=True),
    )
