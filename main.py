import warnings
warnings.filterwarnings("ignore")

import flet as ft
import auth
import threading

from styles import (
    PRIMARY_BG, SECONDARY_BG, TERTIARY_BG, CARD_BG,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED,
    ACCENT_BLUE, ACCENT_CYAN, ACCENT_PURPLE, ACCENT_GREEN,
    ACCENT_YELLOW, ACCENT_RED, BORDER_COLOR, BORDER_COLOR_LIGHT,
    BORDER_RADIUS, SUBJECTS_PALETTE,
)
from utils_calendario import (
    carica_orario, salva_orario, cls_data, _empty,
    GIORNI, MAX_ORE, MESI_NOMI, MESI_OPTS,
    get_registro_giorno, chiave_data,
    peso, giorni_mat, g_nome, date_periodo,
)
from ui_helpers import cal_section, cal_tf, cal_drop, pill, badge, info_box, ai_consiglio_box
from registro import build_registro_docente_panel, build_registro_studente_panel
from chatbot import build_chat_panel


# ═══════════════════════════════════════════════════════════════════════
# LOGIN
# ═══════════════════════════════════════════════════════════════════════

def mostra_login(page: ft.Page, on_success):
    page.clean()
    page.bgcolor = PRIMARY_BG
    page.padding = 0

    ruolo_sel  = [None]
    errore_txt = ft.Text("", color=ACCENT_RED, size=12, text_align=ft.TextAlign.CENTER)

    user_input = ft.TextField(
        label="Username", width=340,
        color=TEXT_PRIMARY, border_color=BORDER_COLOR_LIGHT,
        focused_border_color=ACCENT_BLUE, border_radius=12,
        prefix_icon=ft.Icons.PERSON_OUTLINE, bgcolor=TERTIARY_BG,
    )
    pass_input = ft.TextField(
        label="Password", width=340,
        password=True, can_reveal_password=True,
        color=TEXT_PRIMARY, border_color=BORDER_COLOR_LIGHT,
        focused_border_color=ACCENT_BLUE, border_radius=12,
        prefix_icon=ft.Icons.LOCK_OUTLINE, bgcolor=TERTIARY_BG,
    )

    card_s_ref = ft.Ref[ft.Container]()
    card_d_ref = ft.Ref[ft.Container]()

    def aggiorna_ui():
        if card_s_ref.current:
            card_s_ref.current.border  = ft.border.all(2, ACCENT_BLUE   if ruolo_sel[0] == "studente" else BORDER_COLOR_LIGHT)
            card_s_ref.current.bgcolor = ACCENT_BLUE   + "25" if ruolo_sel[0] == "studente" else CARD_BG
        if card_d_ref.current:
            card_d_ref.current.border  = ft.border.all(2, ACCENT_PURPLE if ruolo_sel[0] == "docente"  else BORDER_COLOR_LIGHT)
            card_d_ref.current.bgcolor = ACCENT_PURPLE + "25" if ruolo_sel[0] == "docente"  else CARD_BG
        page.update()

    def sel_s(e): ruolo_sel[0] = "studente"; errore_txt.value = ""; aggiorna_ui()
    def sel_d(e): ruolo_sel[0] = "docente";  errore_txt.value = ""; aggiorna_ui()

    def login(e=None):
        u = user_input.value.strip()
        p = pass_input.value.strip()
        if not ruolo_sel[0]:
            errore_txt.value = "⚠️ Seleziona Studente o Docente"; page.update(); return
        if not u or not p:
            errore_txt.value = "⚠️ Inserisci username e password"; page.update(); return
        ok, msg = auth.verifica_login(u, p, ruolo_sel[0])
        if ok:
            on_success(ruolo_sel[0] == "studente", u, auth.get_nome_display(u))
        else:
            errore_txt.value = msg; page.update()

    pass_input.on_submit = login

    def role_card(ref, emoji, titolo, desc, on_click):
        return ft.Container(
            ref=ref, width=155,
            padding=ft.padding.symmetric(horizontal=14, vertical=20),
            border_radius=18, bgcolor=CARD_BG,
            border=ft.border.all(2, BORDER_COLOR_LIGHT),
            on_click=on_click, ink=True,
            content=ft.Column([
                ft.Text(emoji, size=38, text_align=ft.TextAlign.CENTER),
                ft.Text(titolo, size=14, weight="bold", color=TEXT_PRIMARY, text_align=ft.TextAlign.CENTER),
                ft.Text(desc, size=9, color=TEXT_MUTED, text_align=ft.TextAlign.CENTER),
            ], spacing=6, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
        )

    page.add(ft.Container(
        expand=True, alignment=ft.Alignment(0, 0),
        content=ft.Container(
            width=440, padding=44,
            border_radius=28, bgcolor=SECONDARY_BG,
            border=ft.border.all(1, BORDER_COLOR_LIGHT),
            content=ft.Column([
                ft.Text("🏫", size=52, text_align=ft.TextAlign.CENTER),
                ft.Text("Piattaforma Scolastica AI", size=22, weight="bold",
                        color=TEXT_PRIMARY, text_align=ft.TextAlign.CENTER),
                ft.Text("Accedi al tuo spazio personale", size=12,
                        color=TEXT_MUTED, text_align=ft.TextAlign.CENTER),
                ft.Container(height=6),
                ft.Text("Chi sei?", size=11, color=TEXT_SECONDARY, weight="bold"),
                ft.Row([
                    role_card(card_s_ref, "👨‍🎓", "Studente",
                              "Orario • Registro\nVerifiche • AI", sel_s),
                    role_card(card_d_ref, "👨‍🏫", "Docente",
                              "Classi • Registro\nVerifiche • AI", sel_d),
                ], spacing=16, alignment=ft.MainAxisAlignment.CENTER),
                ft.Container(height=4),
                user_input, pass_input, errore_txt,
                ft.Container(height=2),
                ft.FilledButton(
                    "ACCEDI", width=340, height=50, on_click=login,
                    style=ft.ButtonStyle(
                        bgcolor=ACCENT_BLUE, color="#ffffff",
                        shape=ft.RoundedRectangleBorder(radius=14),
                        text_style=ft.TextStyle(size=14, weight="bold", letter_spacing=1.5),
                    ),
                ),
                ft.Text("Credenziali: vedi credenziali.json",
                        size=9, color=TEXT_MUTED, text_align=ft.TextAlign.CENTER),
            ], spacing=12, horizontal_alignment=ft.CrossAxisAlignment.CENTER, tight=True),
        ),
    ))
    page.update()


# ═══════════════════════════════════════════════════════════════════════
# APP SHELL CON SIDEBAR
# ═══════════════════════════════════════════════════════════════════════

def avvia_app(page: ft.Page, is_student: bool, username: str, nome_display: str, on_logout):
    page.clean()
    page.bgcolor = PRIMARY_BG
    page.padding = 0

    from datetime import date
    oggi = date.today()
    oggi_nome = g_nome(oggi)

    root      = carica_orario()
    classi    = list(root.get("classi", {}).keys())
    ultima_cl = root.get("ultima_classe", classi[0] if classi else "")

    # Area contenuto principale (si aggiorna al click sulla sidebar)
    content_area = ft.Column([], expand=True, scroll=ft.ScrollMode.AUTO)

    # Voce sidebar selezionata
    sezione_attiva = ["home"]

    # ── Sidebar ──────────────────────────────────────────────────────

    VOCI_STUDENTE = [
        ("home",          "🏠", "Home"),
        ("orario",        "📅", "Orario"),
        ("registro",      "📖", "Registro"),
        ("verifiche",     "📝", "Verifiche"),
        ("interrogazioni","🎤", "Interrogazioni"),
        ("chat",          "🤖", "AI Chat"),
    ]
    VOCI_DOCENTE = [
        ("home",          "🏠", "Home"),
        ("orario",        "📋", "Gestione Orario"),
        ("registro",      "📖", "Registro"),
        ("verifiche",     "📝", "Verifiche"),
        ("interrogazioni","🎤", "Interrogazioni"),
        ("chat",          "🤖", "AI Chat"),
    ]
    voci = VOCI_STUDENTE if is_student else VOCI_DOCENTE

    nav_refs = {v[0]: ft.Ref[ft.Container]() for v in voci}

    def nav_item(key, emoji, label):
        is_sel = key == sezione_attiva[0]
        accent = ACCENT_BLUE if is_student else ACCENT_PURPLE
        return ft.Container(
            ref=nav_refs[key],
            padding=ft.padding.symmetric(horizontal=14, vertical=10),
            border_radius=14,
            bgcolor=accent + "25" if is_sel else "transparent",
            border=ft.border.all(1, accent + "60") if is_sel else ft.border.all(1, "transparent"),
            ink=True,
            on_click=lambda e, k=key: vai_a(k),
            content=ft.Row([
                ft.Text(emoji, size=18),
                ft.Text(label, size=12, color=TEXT_PRIMARY if is_sel else TEXT_SECONDARY,
                        weight="bold" if is_sel else None),
            ], spacing=10),
        )

    sidebar_voci = ft.Column([], spacing=4)

    def aggiorna_sidebar():
        sidebar_voci.controls = [nav_item(k, e, l) for k, e, l in voci]
        page.update()

    accent_main = ACCENT_BLUE if is_student else ACCENT_PURPLE
    ruolo_label = "Vista Studente" if is_student else "Pannello Docente"
    ruolo_emoji = "👨‍🎓" if is_student else "👨‍🏫"

    sidebar = ft.Container(
        width=220,
        bgcolor=SECONDARY_BG,
        border=ft.border.only(right=ft.BorderSide(1, BORDER_COLOR)),
        padding=ft.padding.symmetric(horizontal=12, vertical=20),
        content=ft.Column([
            # Logo
            ft.Container(
                padding=ft.padding.symmetric(horizontal=8, vertical=10),
                content=ft.Column([
                    ft.Text("🏫", size=32),
                    ft.Text("Piattaforma", size=13, weight="bold", color=TEXT_PRIMARY),
                    ft.Text("Scolastica AI", size=13, weight="bold", color=TEXT_PRIMARY),
                    ft.Text(ruolo_label, size=9, color=accent_main),
                ], spacing=2),
            ),
            ft.Divider(color=BORDER_COLOR, height=1),
            ft.Container(height=4),

            # Voci navigazione
            sidebar_voci,

            ft.Container(expand=True),  # spacer

            # Profilo + logout
            ft.Divider(color=BORDER_COLOR, height=1),
            ft.Container(
                padding=ft.padding.symmetric(horizontal=8, vertical=10),
                border_radius=14,
                bgcolor=accent_main + "15",
                border=ft.border.all(1, accent_main + "30"),
                content=ft.Column([
                    ft.Row([
                        ft.Text(ruolo_emoji, size=18),
                        ft.Text(nome_display, size=11, color=TEXT_PRIMARY,
                                weight="bold", max_lines=1, overflow=ft.TextOverflow.ELLIPSIS,
                                expand=True),
                    ], spacing=8),
                    ft.TextButton(
                        "🚪 Logout",
                        on_click=lambda e: on_logout(),
                        style=ft.ButtonStyle(
                            color=ACCENT_RED,
                            padding=ft.padding.symmetric(horizontal=0, vertical=0),
                        ),
                    ),
                ], spacing=4, tight=True),
            ),
        ], expand=True, spacing=4),
    )

    # ── Costruttori di ogni sezione ───────────────────────────────────

    def build_home():
        root2 = carica_orario()
        cl    = root2.get("ultima_classe", "")
        state = cls_data(root2, cl) if cl else _empty()

        def _card(icona, titolo, desc, colore, sezione):
            c = ft.Container(
                width=180, height=130,
                padding=ft.padding.symmetric(horizontal=16, vertical=18),
                border_radius=20, bgcolor=CARD_BG,
                border=ft.border.all(2, colore + "40"),
                ink=True, on_click=lambda e, s=sezione: vai_a(s),
                content=ft.Column([
                    ft.Container(
                        width=44, height=44, border_radius=14,
                        bgcolor=colore + "20",
                        border=ft.border.all(1, colore + "50"),
                        alignment=ft.Alignment(0, 0),
                        content=ft.Text(icona, size=22),
                    ),
                    ft.Text(titolo, size=13, weight="bold", color=TEXT_PRIMARY),
                    ft.Text(desc, size=9, color=TEXT_MUTED),
                ], spacing=6),
            )
            def hov(e, _c=c, _col=colore):
                _c.border  = ft.border.all(2, _col if e.data == "true" else _col + "40")
                _c.bgcolor = _col + "15" if e.data == "true" else CARD_BG
                page.update()
            c.on_hover = hov
            return c

        if is_student:
            cards = ft.Row([
                _card("📅","Orario",       "Settimanale e mensile", ACCENT_BLUE,   "orario"),
                _card("📖","Registro",     "Argomenti e compiti",   ACCENT_CYAN,   "registro"),
                _card("📝","Verifiche",    "Prossimi test",         ACCENT_RED,    "verifiche"),
                _card("🎤","Interrogazioni","Il mio giorno",        ACCENT_PURPLE, "interrogazioni"),
                _card("🤖","AI Chat",      "Chiedi all'AI",         ACCENT_GREEN,  "chat"),
            ], spacing=14, wrap=True)
        else:
            cards = ft.Row([
                _card("📋","Orario Classi","Gestione griglie",      ACCENT_PURPLE, "orario"),
                _card("📖","Registro",     "Argomenti e assenze",   ACCENT_CYAN,   "registro"),
                _card("📝","Verifiche",    "Pianifica test",        ACCENT_RED,    "verifiche"),
                _card("🎤","Interrogazioni","Periodi studenti",     ACCENT_YELLOW, "interrogazioni"),
                _card("🤖","AI Chat",      "Assistente didattica",  ACCENT_GREEN,  "chat"),
            ], spacing=14, wrap=True)

        # Orario di oggi (mini)
        ore_oggi = state.get("orario", {}).get(oggi_nome, {})
        n_ore = MAX_ORE.get(oggi_nome, 0) if oggi_nome in GIORNI else 0
        ore_ws = []
        for h in range(1, n_ore + 1):
            mi  = ore_oggi.get(h, {})
            mat = mi.get("materia", "").strip() if isinstance(mi, dict) else ""
            pro = mi.get("prof", "").strip()    if isinstance(mi, dict) else ""
            pal = SUBJECTS_PALETTE.get(mat, SUBJECTS_PALETTE["default"])
            ore_ws.append(ft.Container(
                padding=ft.padding.symmetric(horizontal=12, vertical=8),
                border_radius=10,
                bgcolor=pal["bg"] if mat else TERTIARY_BG,
                border=ft.border.all(1, pal["accent"] + "50" if mat else BORDER_COLOR),
                content=ft.Row([
                    ft.Container(width=26, height=26, border_radius=7,
                                 bgcolor=pal["accent"] + "25", alignment=ft.Alignment(0,0),
                                 content=ft.Text(str(h), size=10, weight="bold", color=pal["accent"])),
                    ft.Text(mat or "—", size=11, color=TEXT_PRIMARY,
                            weight="bold" if mat else None, expand=True),
                    ft.Text(pro, size=9, color=TEXT_MUTED),
                ], spacing=8),
            ))

        oggi_col = ft.Column(
            ore_ws if ore_ws else [
                ft.Text("Nessuna lezione oggi 🎉" if oggi_nome not in GIORNI
                        else "Orario non ancora inserito", size=11, color=TEXT_MUTED)
            ], spacing=5,
        )

        # Prossime verifiche mini
        from datetime import date as _date
        ver_items = []
        vv = sorted(
            [(_date(oggi.year, v["mese"], v["giorno_num"]), v)
             for v in state.get("verifiche", [])
             if v.get("mese") and v.get("giorno_num")
             and _date(oggi.year, v["mese"], v["giorno_num"]) >= oggi],
            key=lambda x: x[0],
        )
        for vd, v in vv[:5]:
            delta = (vd - oggi).days
            bc  = ACCENT_RED if delta <= 2 else ACCENT_YELLOW if delta <= 7 else ACCENT_GREEN
            pal = SUBJECTS_PALETTE.get(v.get("materia",""), SUBJECTS_PALETTE["default"])
            ver_items.append(ft.Container(
                padding=ft.padding.symmetric(horizontal=12, vertical=8),
                border_radius=10, bgcolor=pal["bg"],
                border=ft.border.all(1, pal["accent"] + "50"),
                content=ft.Row([
                    ft.Column([
                        ft.Text(v.get("materia","?"), size=11, color=TEXT_PRIMARY, weight="bold"),
                        ft.Text(f"{vd.strftime('%d %b')} · {v.get('tipo','')}", size=9, color=TEXT_SECONDARY),
                    ], spacing=2, expand=True),
                    ft.Container(
                        padding=ft.padding.symmetric(horizontal=8, vertical=3),
                        border_radius=10, bgcolor=bc + "20", border=ft.border.all(1, bc+"50"),
                        content=ft.Text("Oggi!" if delta==0 else f"tra {delta}gg",
                                        size=9, color=bc, weight="bold"),
                    ),
                ], spacing=10),
            ))
        ver_col = ft.Column(
            ver_items or [ft.Text("Nessuna verifica in programma 🎉", size=11, color=TEXT_MUTED)],
            spacing=5,
        )

        def sezione_box(titolo, icona, widget, accent=ACCENT_BLUE):
            return ft.Container(
                padding=ft.padding.symmetric(horizontal=18, vertical=16),
                border_radius=18, bgcolor=SECONDARY_BG,
                border=ft.border.all(1, BORDER_COLOR_LIGHT),
                content=ft.Column([
                    ft.Row([ft.Container(width=4, height=18, border_radius=2, bgcolor=accent),
                            ft.Text(f"{icona}  {titolo}", size=12, weight="bold", color=TEXT_PRIMARY)], spacing=8),
                    ft.Divider(color=BORDER_COLOR, height=1),
                    widget,
                ], spacing=8, tight=True),
            )

        benvenuto_msg = (
            f"Ciao, {nome_display} 👋" if is_student else f"Bentornato, {nome_display} 👨‍🏫"
        )
        subtitle = (
            f"Classe {cl or '—'} · {oggi_nome} {oggi.strftime('%d %B %Y')}"
            if is_student else
            f"{oggi_nome} {oggi.strftime('%d %B %Y')}"
        )

        content_area.controls = [ft.Container(
            padding=ft.padding.symmetric(horizontal=28, vertical=24),
            content=ft.Column([
                ft.Text(benvenuto_msg, size=26, weight="bold", color=TEXT_PRIMARY),
                ft.Text(subtitle, size=12, color=TEXT_MUTED),
                ft.Container(height=8),
                cards,
                ft.Container(height=16),
                ft.Row([
                    ft.Container(expand=True,
                                 content=sezione_box(f"Orario oggi — {oggi_nome}", "📋",
                                                     oggi_col, ACCENT_CYAN)),
                    ft.Container(width=20),
                    ft.Container(expand=True,
                                 content=sezione_box("Prossime Verifiche", "📝",
                                                     ver_col, ACCENT_RED)),
                ], spacing=0, vertical_alignment=ft.CrossAxisAlignment.START),
            ], spacing=12),
        )]
        page.update()

    # ── ORARIO ───────────────────────────────────────────────────────

    def build_orario():
        root2 = carica_orario()
        cl    = root2.get("ultima_classe", "")
        state = cls_data(root2, cl) if cl else _empty()

        if is_student:
            # Vista sola-lettura orario + calendario
            import calendar as _cal
            from datetime import date as _date

            # Mini orario settimanale
            oggi_g  = g_nome(_date.today())
            max_h   = max(MAX_ORE.values())
            rows    = [ft.Row(
                [ft.Container(width=30)] + [
                    ft.Container(expand=True, border_radius=6,
                                 bgcolor=ACCENT_BLUE + "25" if g == oggi_g else None,
                                 content=ft.Text(g[:3], size=8, weight="bold",
                                                 color=ACCENT_BLUE if g == oggi_g else TEXT_MUTED,
                                                 text_align=ft.TextAlign.CENTER))
                    for g in GIORNI
                ], spacing=2,
            )]
            for h in range(1, max_h + 1):
                row = [ft.Container(width=30,
                                    content=ft.Text(f"{h}ª", size=8, color=ACCENT_CYAN,
                                                    text_align=ft.TextAlign.CENTER))]
                for g in GIORNI:
                    if h > MAX_ORE[g]:
                        row.append(ft.Container(expand=True, height=28, border_radius=6,
                                                bgcolor="#0a0f1a"))
                    else:
                        m   = state["orario"].get(g, {}).get(h, {})
                        mat = m.get("materia","").strip() if isinstance(m,dict) else ""
                        pal = SUBJECTS_PALETTE.get(mat, SUBJECTS_PALETTE["default"]) if mat else None
                        row.append(ft.Container(
                            expand=True, height=28, border_radius=6,
                            bgcolor=pal["bg"] if mat else CARD_BG,
                            border=ft.border.all(1, ACCENT_BLUE if g==oggi_g else
                                                 (pal["accent"]+"50" if mat else BORDER_COLOR)),
                            padding=2,
                            content=ft.Text(
                                (mat[:5]+"…" if len(mat)>5 else mat), size=7,
                                color=TEXT_PRIMARY, text_align=ft.TextAlign.CENTER, max_lines=1,
                            ) if mat else ft.Container(),
                        ))
                rows.append(ft.Row(row, spacing=2))

            content_area.controls = [ft.Container(
                padding=ft.padding.symmetric(horizontal=28, vertical=24),
                content=ft.Column([
                    ft.Text("📅  Orario Settimanale", size=20, weight="bold", color=TEXT_PRIMARY),
                    ft.Text(f"Classe {cl or '—'}", size=12, color=TEXT_MUTED),
                    ft.Container(height=8),
                    ft.Container(
                        padding=16, border_radius=18,
                        bgcolor=SECONDARY_BG, border=ft.border.all(1, BORDER_COLOR_LIGHT),
                        content=ft.Column(rows, spacing=3),
                    ),
                ], spacing=12),
            )]
        else:
            # Vista docente: editor orario per ogni giorno
            tab_body = ft.Column([], spacing=5, scroll=ft.ScrollMode.AUTO, height=280)
            tab_row  = ft.Row([], spacing=4, wrap=True)
            mats = sorted({
                e.get("materia","") for d in state["orario"].values()
                for e in d.values() if isinstance(e,dict) and e.get("materia")
            })

            def make_rows(g):
                dd = state["orario"].setdefault(g, {})
                rr = []
                for h in range(1, MAX_ORE[g] + 1):
                    si = cal_tf(f"{h}ª Materia", width=190, value=dd.get(h,{}).get("materia","") if isinstance(dd.get(h,{}),dict) else "")
                    pi = cal_tf("Prof",           width=150, value=dd.get(h,{}).get("prof","")    if isinstance(dd.get(h,{}),dict) else "")
                    def sv(e, _g=g, _h=h, _s=si, _p=pi):
                        state["orario"].setdefault(_g,{})[_h] = {
                            "materia": _s.value.strip(), "prof": _p.value.strip()}
                        salva_orario(root2)
                    si.on_change = sv; pi.on_change = sv
                    rr.append(ft.Row([si, pi], spacing=8))
                return rr

            def switch(g):
                tab_body.controls = make_rows(g)
                for b in tab_row.controls:
                    b.style = ft.ButtonStyle(
                        bgcolor=ACCENT_PURPLE if b.data==g else CARD_BG,
                        color=TEXT_PRIMARY,
                        shape=ft.RoundedRectangleBorder(radius=14),
                        padding=ft.padding.symmetric(horizontal=12, vertical=6),
                    )
                page.update()

            for g in GIORNI:
                tab_row.controls.append(ft.FilledButton(
                    g[:3], data=g,
                    on_click=lambda e: switch(e.control.data),
                    style=ft.ButtonStyle(
                        bgcolor=ACCENT_PURPLE if g==GIORNI[0] else CARD_BG,
                        color=TEXT_PRIMARY,
                        shape=ft.RoundedRectangleBorder(radius=14),
                        padding=ft.padding.symmetric(horizontal=12, vertical=6),
                    ),
                ))
            tab_body.controls = make_rows(GIORNI[0])

            # Cambio classe
            from ui_helpers import classe_selector
            def on_cl(nuova):
                if not nuova: return
                root2["ultima_classe"] = nuova
                salva_orario(root2)
                build_orario()

            content_area.controls = [ft.Container(
                padding=ft.padding.symmetric(horizontal=28, vertical=24),
                content=ft.Column([
                    ft.Text("📋  Gestione Orario", size=20, weight="bold", color=TEXT_PRIMARY),
                    ft.Container(height=4),
                    classe_selector(cl, list(root2["classi"].keys()), on_cl, page),
                    ft.Container(height=8),
                    ft.Container(
                        padding=16, border_radius=18,
                        bgcolor=SECONDARY_BG, border=ft.border.all(1, BORDER_COLOR_LIGHT),
                        content=ft.Column([
                            ft.Row([ft.Container(width=4, height=18, border_radius=2, bgcolor=ACCENT_PURPLE),
                                    ft.Text("Orario Settimanale", size=13, weight="bold", color=TEXT_PRIMARY)], spacing=8),
                            ft.Divider(color=BORDER_COLOR, height=1),
                            tab_row,
                            tab_body,
                        ], spacing=10),
                    ),
                ], spacing=12),
            )]
        page.update()

    # ── REGISTRO ────────────────────────────────────────────────────

    def build_registro():
        from datetime import date as _date
        root2   = carica_orario()
        cl      = root2.get("ultima_classe","")
        state   = cls_data(root2, cl) if cl else _empty()
        oggi_dt = _date.today()

        # Calendario mensile integrato
        import calendar as _cal
        cal_ym  = [oggi_dt.year, oggi_dt.month]
        panel_holder = ft.Column([], spacing=0)
        cal_body     = ft.Column([], spacing=0, horizontal_alignment=ft.CrossAxisAlignment.CENTER)
        cal_lbl      = ft.Text("", size=14, weight="bold", color=TEXT_PRIMARY)

        def on_day_click(dt):
            if g_nome(dt) not in GIORNI:
                panel_holder.controls = [info_box("Questo giorno non è scolastico.", ACCENT_YELLOW)]
                page.update(); return
            if is_student:
                nome_s = state.get("nome_studente","Studente")
                panel_holder.controls = [build_registro_studente_panel(state, dt, nome_s, page)]
            else:
                def _on_save():
                    salva_orario(root2)
                    _draw_cal()
                panel_holder.controls = [build_registro_docente_panel(state, dt, page, _on_save, root=root2)]
            page.update()

        def _draw_cal():
            from styles import ACCENT_RED, ACCENT_PURPLE, ACCENT_CYAN
            ev = {}
            for v in state.get("verifiche",[]):
                if v.get("mese") == cal_ym[1] and v.get("giorno_num"):
                    ev.setdefault(v["giorno_num"],[]).append(("V", v.get("materia","")))
            reg_gg = set()
            for k in state.get("registro",{}):
                try:
                    rd = _date.fromisoformat(k)
                    if rd.year==cal_ym[0] and rd.month==cal_ym[1]:
                        r = state["registro"][k]
                        if r.get("argomenti") or r.get("compiti") or r.get("assenti"):
                            reg_gg.add(rd.day)
                except: pass

            hdr = ft.Row([ft.Container(width=44,
                content=ft.Text(n, size=8, color=TEXT_MUTED, text_align=ft.TextAlign.CENTER, weight="bold"))
                for n in ["L","M","M","G","V","S","D"]], spacing=3)
            rows = [hdr]
            for week in _cal.monthcalendar(cal_ym[0], cal_ym[1]):
                cells = []
                for wi, d in enumerate(week):
                    is_today = d != 0 and _date(cal_ym[0],cal_ym[1],d) == oggi_dt
                    evs      = ev.get(d,[]) if d!=0 else []
                    has_V    = any(t=="V" for t,_ in evs)
                    has_R    = d in reg_gg if d!=0 else False
                    dots = ft.Row([
                        ft.Container(width=6,height=6,border_radius=3,bgcolor=ACCENT_RED)    if has_V else ft.Container(),
                        ft.Container(width=6,height=6,border_radius=3,bgcolor=ACCENT_CYAN)   if has_R else ft.Container(),
                    ], spacing=2, alignment=ft.MainAxisAlignment.CENTER)
                    bg  = (ACCENT_BLUE if is_today else "#1c2a42" if wi>=5 else CARD_BG if d!=0 else "transparent")
                    brd = (ft.border.all(2,ACCENT_BLUE)       if is_today else
                           ft.border.all(1,ACCENT_RED+"80")   if has_V    else
                           ft.border.all(1,ACCENT_CYAN+"80")  if has_R    else None)
                    dt_obj = _date(cal_ym[0],cal_ym[1],d) if d!=0 else None
                    cells.append(ft.Container(
                        width=44, height=44, border_radius=10,
                        bgcolor=bg, border=brd, ink=bool(d!=0),
                        on_click=(lambda e, _dt=dt_obj: on_day_click(_dt)) if d!=0 else None,
                        content=ft.Column([
                            ft.Text(str(d) if d!=0 else "", size=10,
                                    color=TEXT_PRIMARY if is_today else TEXT_MUTED if wi>=5 else TEXT_SECONDARY,
                                    weight="bold" if is_today else None,
                                    text_align=ft.TextAlign.CENTER),
                            dots,
                        ], spacing=2, alignment=ft.MainAxisAlignment.CENTER,
                           horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                    ))
                rows.append(ft.Row(cells, spacing=3))
            cal_body.controls = [ft.Column(rows, spacing=3)]
            cal_lbl.value = f"{MESI_NOMI[cal_ym[1]]}  {cal_ym[0]}"
            page.update()

        def nav_cal(d):
            m, y = cal_ym[1]+d, cal_ym[0]
            if m>12: m,y=1,y+1
            elif m<1: m,y=12,y-1
            cal_ym[0],cal_ym[1]=y,m
            _draw_cal()

        cal_widget = ft.Container(
            padding=16, border_radius=18,
            bgcolor=SECONDARY_BG, border=ft.border.all(1,BORDER_COLOR_LIGHT),
            content=ft.Column([
                ft.Row([
                    ft.IconButton(ft.Icons.CHEVRON_LEFT, icon_color=ACCENT_BLUE, icon_size=20,
                                  on_click=lambda e: nav_cal(-1)),
                    ft.Container(expand=True,
                                 content=ft.Row([cal_lbl],alignment=ft.MainAxisAlignment.CENTER)),
                    ft.IconButton(ft.Icons.CHEVRON_RIGHT, icon_color=ACCENT_BLUE, icon_size=20,
                                  on_click=lambda e: nav_cal(1)),
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                cal_body,
            ], spacing=10, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
        )
        _draw_cal()

        hint = ft.Container(
            padding=ft.padding.symmetric(horizontal=14, vertical=12),
            border_radius=BORDER_RADIUS, bgcolor=TERTIARY_BG,
            border=ft.border.all(1, ACCENT_CYAN + "40"),
            content=ft.Column([
                ft.Text("Clicca su un giorno del calendario per aprire il registro.",
                        size=11, color=TEXT_MUTED),
                panel_holder,
            ], spacing=10, tight=True),
        )

        content_area.controls = [ft.Container(
            padding=ft.padding.symmetric(horizontal=28, vertical=24),
            content=ft.Column([
                ft.Text("📖  Registro Giornaliero", size=20, weight="bold", color=TEXT_PRIMARY),
                ft.Container(height=4),
                ft.Row([
                    cal_widget,
                    ft.Container(expand=True, content=hint),
                ], spacing=16, vertical_alignment=ft.CrossAxisAlignment.START),
            ], spacing=12),
        )]
        page.update()

    # ── VERIFICHE ────────────────────────────────────────────────────

    def build_verifiche():
        from datetime import date as _date
        root2 = carica_orario()
        cl    = root2.get("ultima_classe","")
        state = cls_data(root2, cl) if cl else _empty()
        oggi_dt = _date.today()
        mats  = sorted({
            e.get("materia","") for d in state["orario"].values()
            for e in d.values() if isinstance(e,dict) and e.get("materia")
        })

        if is_student:
            # Sola lettura
            upcoming = sorted(
                [(_date(oggi_dt.year, v["mese"], v["giorno_num"]), v)
                 for v in state.get("verifiche",[])
                 if v.get("mese") and v.get("giorno_num")
                 and _date(oggi_dt.year, v["mese"], v["giorno_num"]) >= oggi_dt],
                key=lambda x: x[0],
            )
            all_v = sorted(
                [(_date(oggi_dt.year, v["mese"], v["giorno_num"]), v)
                 for v in state.get("verifiche",[])
                 if v.get("mese") and v.get("giorno_num")],
                key=lambda x: x[0],
            )

            def ver_row(vd, v):
                delta = (vd - oggi_dt).days
                bc  = ACCENT_RED if delta <= 2 else ACCENT_YELLOW if delta <= 7 else (ACCENT_GREEN if delta >= 0 else TEXT_MUTED)
                pal = SUBJECTS_PALETTE.get(v.get("materia",""), SUBJECTS_PALETTE["default"])
                return ft.Container(
                    padding=ft.padding.symmetric(horizontal=14, vertical=12),
                    border_radius=14, bgcolor=pal["bg"],
                    border=ft.border.all(1, pal["accent"]+"60"),
                    content=ft.Row([
                        ft.Text("📝", size=18),
                        ft.Column([
                            ft.Text(v.get("materia","?"), size=13, color=TEXT_PRIMARY, weight="bold"),
                            ft.Text(f"{vd.strftime('%d %B %Y')} ({v.get('giorno_settimana','')}) · {v.get('tipo','')}",
                                    size=10, color=TEXT_SECONDARY),
                        ], spacing=2, expand=True),
                        ft.Container(
                            padding=ft.padding.symmetric(horizontal=10, vertical=4),
                            border_radius=12, bgcolor=bc+"20", border=ft.border.all(1,bc+"50"),
                            content=ft.Text(
                                "Oggi!" if delta==0 else f"tra {delta}gg" if delta>0 else "Passata",
                                size=10, color=bc, weight="bold"),
                        ),
                    ], spacing=12),
                )

            prossime_col = ft.Column(
                [ver_row(vd,v) for vd,v in upcoming] or
                [ft.Text("Nessuna verifica in programma 🎉", size=12, color=TEXT_MUTED)],
                spacing=8,
            )
            tutte_col = ft.Column(
                [ver_row(vd,v) for vd,v in all_v] or
                [ft.Text("Nessuna verifica inserita.", size=12, color=TEXT_MUTED)],
                spacing=8,
            )
            content_area.controls = [ft.Container(
                padding=ft.padding.symmetric(horizontal=28, vertical=24),
                content=ft.Column([
                    ft.Text("📝  Verifiche", size=20, weight="bold", color=TEXT_PRIMARY),
                    ft.Container(height=8),
                    cal_section("Prossime Verifiche", "📝", prossime_col, ACCENT_RED),
                    ft.Container(height=10),
                    cal_section("Tutte le Verifiche", "📋", tutte_col, ACCENT_BLUE),
                ], spacing=10),
            )]
        else:
            # Docente: aggiunta e rimozione
            mv = cal_drop("Materia", mats, width=170)
            vg = cal_tf("Giorno", width=80, kb=ft.KeyboardType.NUMBER)
            vm = cal_drop("Mese", MESI_OPTS, width=165)
            vc = cal_tf("Classe", width=90, value=cl)
            vt = cal_tf("Tipo", width=110, value="Scritto")
            ai_vbox = ft.Container(visible=False)

            def vmat_chg(e):
                if not mv.value: ai_vbox.visible=False; page.update(); return
                glist = giorni_mat(state, mv.value)
                if not glist: ai_vbox.visible=False; page.update(); return
                pesi = sorted([(g, peso(state,g)) for g in glist], key=lambda x:x[1])
                ai_vbox.content = ai_consiglio_box(
                    [f"✔ {pesi[0][0]} — peso {pesi[0][1]}  ← CONSIGLIATO"],
                    [f"  {g} — peso {p}" for g,p in pesi[1:]])
                ai_vbox.visible=True; page.update()
            mv.on_change = vmat_chg

            vlist_col = ft.Column([], spacing=6)

            def refresh_vlist():
                vlist_col.controls.clear()
                for v in sorted(state["verifiche"],
                                key=lambda x:(x.get("mese",0),x.get("giorno_num",0))):
                    pal = SUBJECTS_PALETTE.get(v.get("materia"),SUBJECTS_PALETTE["default"])
                    try:
                        from datetime import date as _d2
                        ds = _d2(oggi_dt.year,v["mese"],v["giorno_num"]).strftime("%d %b") + f" ({v['giorno_settimana']})"
                    except: ds="?"
                    def del_v(e,_v=v):
                        if _v in state["verifiche"]: state["verifiche"].remove(_v)
                        salva_orario(root2); refresh_vlist(); page.update()
                    vlist_col.controls.append(ft.Container(
                        padding=ft.padding.symmetric(horizontal=12,vertical=8),
                        border_radius=12, bgcolor=pal["bg"],
                        border=ft.border.all(1,pal["accent"]+"60"),
                        content=ft.Row([
                            ft.Text("📝",size=14),
                            ft.Column([
                                ft.Text(v.get("materia"),size=11,color=TEXT_PRIMARY,weight="bold"),
                                ft.Text(f"{ds} · classe {v.get('classe','')} · {v.get('tipo','')}",
                                        size=9,color=TEXT_SECONDARY),
                            ],spacing=1,expand=True),
                            ft.IconButton(ft.Icons.DELETE_OUTLINE,icon_color=ACCENT_RED,
                                          icon_size=16,on_click=del_v),
                        ],spacing=10),
                    ))
                page.update()

            def add_v(e):
                if not mv.value or not vg.value or not vm.value: return
                try:
                    from datetime import date as _d2
                    gn=int(vg.value); mn=int(vm.value.split(" - ")[0])
                    dt=_d2(oggi_dt.year,mn,gn); gs=g_nome(dt)
                except: return
                state["verifiche"].append({
                    "materia":mv.value,"giorno_num":gn,"mese":mn,
                    "giorno_settimana":gs,"classe":vc.value.strip(),"tipo":vt.value,
                })
                vg.value=""; vm.value=None
                salva_orario(root2); refresh_vlist()

            refresh_vlist()
            content_area.controls = [ft.Container(
                padding=ft.padding.symmetric(horizontal=28, vertical=24),
                content=ft.Column([
                    ft.Text("📝  Gestione Verifiche", size=20, weight="bold", color=TEXT_PRIMARY),
                    ft.Container(height=8),
                    cal_section("Aggiungi Verifica","📝", ft.Column([
                        ft.Row([mv],spacing=8), ai_vbox,
                        ft.Row([
                            ft.Column([ft.Text("Data",size=10,color=TEXT_MUTED),
                                       ft.Row([vg,vm],spacing=6)],spacing=4),
                            ft.Column([ft.Text("Classe / Tipo",size=10,color=TEXT_MUTED),
                                       ft.Row([vc,vt],spacing=6)],spacing=4),
                        ],spacing=16),
                        pill("➕ Aggiungi Verifica", add_v),
                    ], spacing=10), accent=ACCENT_RED),
                    ft.Container(height=10),
                    cal_section("Verifiche Programmate","📋", vlist_col, accent=ACCENT_BLUE),
                ], spacing=10),
            )]
        page.update()

    # ── INTERROGAZIONI ───────────────────────────────────────────────

    def build_interrogazioni():
        from datetime import date as _date, datetime as _dt
        root2 = carica_orario()
        cl    = root2.get("ultima_classe","")
        state = cls_data(root2, cl) if cl else _empty()
        oggi_dt = _date.today()
        mats  = sorted({
            e.get("materia","") for d in state["orario"].values()
            for e in d.values() if isinstance(e,dict) and e.get("materia")
        })
        nome_s = state.get("nome_studente","Studente")

        if is_student:
            pending   = [i for i in state.get("interrogazioni",[])
                         if nome_s not in i.get("assegnazioni",{})]
            confirmed = [(i, i["assegnazioni"][nome_s])
                         for i in state.get("interrogazioni",[])
                         if nome_s in i.get("assegnazioni",{})]

            ic = ft.Column(spacing=12)
            for interr in pending:
                mat = interr.get("materia","?")
                dd  = date_periodo(state, mat,
                                   interr.get("inizio_mese"), interr.get("inizio_giorno"),
                                   interr.get("fine_mese"),   interr.get("fine_giorno"))
                if not dd:
                    ic.controls.append(info_box(f"🎤 {mat}: nessun giorno disponibile.", ACCENT_YELLOW))
                    continue
                pesi = {d: peso(state,gn) for d,gn in dd}
                best = min(pesi, key=pesi.get)
                ai_box = ai_consiglio_box(
                    [f"✔ {best.strftime('%d %b')} ({g_nome(best)}) — peso {pesi[best]}  ← CONSIGLIATO"],
                    [f"  {d.strftime('%d %b')} ({gn}) — peso {pesi[d]}" for d,gn in dd if d!=best])
                opts = [f"{d.strftime('%d/%m')} – {gn}" for d,gn in dd]
                ddd  = cal_drop("Scegli data", opts, expand=True)
                ddd.value = f"{best.strftime('%d/%m')} – {g_nome(best)}"
                def conferma(e, _i=interr, _d=ddd):
                    if not _d.value: return
                    try:
                        gs,ms = _d.value.split(" – ")[0].split("/")
                        chosen = _date(oggi_dt.year,int(ms),int(gs))
                        _i.setdefault("assegnazioni",{})[nome_s] = g_nome(chosen)
                        salva_orario(root2); build_interrogazioni()
                    except: pass
                ic.controls.append(ft.Container(
                    padding=12, border_radius=14, bgcolor=TERTIARY_BG,
                    border=ft.border.all(1,ACCENT_PURPLE+"70"),
                    content=ft.Column([
                        ft.Row([ft.Text("🎤",size=16),
                                ft.Text(f"Interrogazione: {mat}",size=12,weight="bold",color=TEXT_PRIMARY)],spacing=8),
                        ai_box,
                        ft.Row([ddd, pill("Conferma", conferma, color=ACCENT_PURPLE)],
                               spacing=10, vertical_alignment=ft.CrossAxisAlignment.END),
                    ],spacing=8),
                ))

            cc = ft.Column(spacing=6)
            for interr, gs in confirmed:
                cc.controls.append(ft.Container(
                    padding=ft.padding.symmetric(horizontal=12,vertical=8),
                    border_radius=12, bgcolor=ACCENT_PURPLE+"15",
                    border=ft.border.all(1,ACCENT_PURPLE+"60"),
                    content=ft.Row([
                        ft.Text("✅",size=14),
                        ft.Column([
                            ft.Text(interr.get("materia","?"),size=11,color=TEXT_PRIMARY,weight="bold"),
                            ft.Text(f"Giorno: {gs}",size=9,color=TEXT_SECONDARY),
                        ],spacing=1,expand=True),
                    ],spacing=10),
                ))

            content_area.controls = [ft.Container(
                padding=ft.padding.symmetric(horizontal=28, vertical=24),
                content=ft.Column([
                    ft.Text("🎤  Interrogazioni", size=20, weight="bold", color=TEXT_PRIMARY),
                    ft.Container(height=8),
                    cal_section("Da confermare","🎤",
                                ic if ic.controls else ft.Text("Nessuna interrogazione da confermare.",size=11,color=TEXT_MUTED),
                                ACCENT_PURPLE),
                    ft.Container(height=10),
                    cal_section("Confermate","✅",
                                cc if cc.controls else ft.Text("Nessuna ancora confermata.",size=11,color=TEXT_MUTED),
                                ACCENT_GREEN),
                ],spacing=10),
            )]
        else:
            # Docente: apertura periodi
            mi  = cal_drop("Materia", mats, width=170)
            ig_ = cal_tf("Gg inizio", width=75, kb=ft.KeyboardType.NUMBER)
            im_ = cal_drop("Mese inizio", MESI_OPTS, width=165)
            fg_ = cal_tf("Gg fine",   width=75, kb=ft.KeyboardType.NUMBER)
            fm_ = cal_drop("Mese fine",   MESI_OPTS, width=165)
            ai_ibox = ft.Container(visible=False)

            def imat_chg(e):
                if not mi.value: ai_ibox.visible=False; page.update(); return
                glist = giorni_mat(state, mi.value)
                if not glist: ai_ibox.visible=False; page.update(); return
                pesi = sorted([(g,peso(state,g)) for g in glist],key=lambda x:x[1])
                ai_ibox.content = ai_consiglio_box(
                    [f"✔ {pesi[0][0]} — peso {pesi[0][1]}  ← CONSIGLIATO"],
                    [f"  {g} — peso {p}" for g,p in pesi[1:]])
                ai_ibox.visible=True; page.update()
            mi.on_change = imat_chg

            ilist_col = ft.Column([], spacing=6)
            def refresh_ilist():
                ilist_col.controls.clear()
                for i in state.get("interrogazioni",[]):
                    try: ps=f"{i['inizio_giorno']}/{i['inizio_mese']} → {i['fine_giorno']}/{i['fine_mese']}"
                    except: ps="?"
                    n_ass = len(i.get("assegnazioni",{}))
                    def del_i(e,_i=i):
                        if _i in state["interrogazioni"]: state["interrogazioni"].remove(_i)
                        salva_orario(root2); refresh_ilist(); page.update()
                    ilist_col.controls.append(ft.Container(
                        padding=ft.padding.symmetric(horizontal=12,vertical=8),
                        border_radius=12, bgcolor=TERTIARY_BG,
                        border=ft.border.all(1,ACCENT_PURPLE+"60"),
                        content=ft.Row([
                            ft.Text("🎤",size=14),
                            ft.Column([
                                ft.Text(i.get("materia"),size=11,color=TEXT_PRIMARY,weight="bold"),
                                ft.Text(f"📆 {ps} · {n_ass} studenti assegnati",size=9,color=TEXT_SECONDARY),
                            ],spacing=1,expand=True),
                            ft.IconButton(ft.Icons.DELETE_OUTLINE,icon_color=ACCENT_RED,
                                          icon_size=16,on_click=del_i),
                        ],spacing=10),
                    ))
                page.update()

            def apri_i(e):
                if not mi.value: return
                try:
                    im=int(im_.value.split(" - ")[0]); ig=int(ig_.value)
                    fm=int(fm_.value.split(" - ")[0]); fg=int(fg_.value)
                    from datetime import date as _d2
                    _d2(oggi_dt.year,im,ig); _d2(oggi_dt.year,fm,fg)
                except: return
                if any(i.get("materia")==mi.value for i in state["interrogazioni"]): return
                from datetime import datetime as _dt2
                state["interrogazioni"].append({
                    "id": f"{mi.value}_{_dt2.now().timestamp()}",
                    "materia":mi.value,
                    "inizio_giorno":ig,"inizio_mese":im,
                    "fine_giorno":fg,"fine_mese":fm,
                    "assegnazioni":{},
                })
                mi.value=None; ig_.value=""; im_.value=None
                fg_.value=""; fm_.value=None; ai_ibox.visible=False
                salva_orario(root2); refresh_ilist()

            refresh_ilist()
            content_area.controls = [ft.Container(
                padding=ft.padding.symmetric(horizontal=28, vertical=24),
                content=ft.Column([
                    ft.Text("🎤  Gestione Interrogazioni", size=20, weight="bold", color=TEXT_PRIMARY),
                    ft.Container(height=8),
                    cal_section("Apri Periodo Interrogazioni","🎤",ft.Column([
                        ft.Row([mi],spacing=8), ai_ibox,
                        ft.Row([
                            ft.Container(padding=10,border_radius=12,bgcolor=ACCENT_GREEN+"12",
                                border=ft.border.all(1,ACCENT_GREEN+"40"),
                                content=ft.Column([ft.Text("Data inizio",size=9,color=ACCENT_GREEN,weight="bold"),
                                                   ft.Row([ig_,im_],spacing=6)],spacing=5)),
                            ft.Container(padding=10,border_radius=12,bgcolor=ACCENT_RED+"12",
                                border=ft.border.all(1,ACCENT_RED+"40"),
                                content=ft.Column([ft.Text("Data fine",size=9,color=ACCENT_RED,weight="bold"),
                                                   ft.Row([fg_,fm_],spacing=6)],spacing=5)),
                        ],spacing=12),
                        pill("🎤 Apri Periodo", apri_i, color=ACCENT_PURPLE),
                    ],spacing=10),accent=ACCENT_PURPLE),
                    ft.Container(height=10),
                    cal_section("Periodi Attivi","📋",ilist_col,ACCENT_BLUE),
                ],spacing=10),
            )]
        page.update()

    # ── CHAT ─────────────────────────────────────────────────────────

    def build_chat():
        root2 = carica_orario()
        cl    = root2.get("ultima_classe","")
        chat  = build_chat_panel(
            page=page,
            get_state=lambda: cls_data(root2, cl) if cl else _empty(),
            get_classe=lambda: cl,
        )
        # Espandi la chat per occupare l'area intera
        chat.expand = True
        chat.width  = None
        content_area.controls = [ft.Container(
            expand=True,
            padding=ft.padding.symmetric(horizontal=28, vertical=24),
            content=ft.Column([
                ft.Text("🤖  Assistente AI", size=20, weight="bold", color=TEXT_PRIMARY),
                ft.Container(height=8),
                ft.Container(expand=True, content=chat),
            ], spacing=8, expand=True),
        )]
        page.update()

    # ── Router ───────────────────────────────────────────────────────

    BUILDERS = {
        "home":           build_home,
        "orario":         build_orario,
        "registro":       build_registro,
        "verifiche":      build_verifiche,
        "interrogazioni": build_interrogazioni,
        "chat":           build_chat,
    }

    def vai_a(sezione: str):
        sezione_attiva[0] = sezione
        aggiorna_sidebar()
        BUILDERS[sezione]()

    # ── Layout principale ─────────────────────────────────────────────

    aggiorna_sidebar()

    page.add(ft.Row([
        sidebar,
        ft.Container(expand=True, content=content_area),
    ], expand=True, spacing=0))

    vai_a("home")


# ═══════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════

def main(page: ft.Page):
    page.title         = "🏫 Piattaforma Scolastica AI"
    page.theme_mode    = ft.ThemeMode.DARK
    page.bgcolor       = PRIMARY_BG
    page.window_width  = 1400
    page.window_height = 900
    page.padding       = 0
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.vertical_alignment   = ft.MainAxisAlignment.CENTER

    def vai_login():
        mostra_login(page, on_success=dopo_login)

    def dopo_login(is_student: bool, username: str, nome_display: str):
        avvia_app(page, is_student, username, nome_display, on_logout=vai_login)

    vai_login()


if __name__ == "__main__":
    ft.app(target=main)