# ══════════════════════════════════════════════════════════════════════
# main.py — App shell con Login + Registrazione (Studente / Docente)
# ══════════════════════════════════════════════════════════════════════

import warnings
warnings.filterwarnings("ignore")

import flet as ft
import auth
import threading
import socket

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


# ══════════════════════════════════════════════════════════════════════
# HELPER UI
# ══════════════════════════════════════════════════════════════════════

def _tf(label, password=False, hint="", width=340, prefix_icon=None):
    kw = dict(
        label=label,
        hint_text=hint,
        width=width,
        password=password,
        can_reveal_password=password,
        color=TEXT_PRIMARY,
        border_color=BORDER_COLOR_LIGHT,
        focused_border_color=ACCENT_BLUE,
        border_radius=12,
        content_padding=ft.padding.symmetric(horizontal=16, vertical=14),
        text_size=13,
        bgcolor=TERTIARY_BG,
        label_style=ft.TextStyle(color=TEXT_MUTED, size=11),
    )
    if prefix_icon:
        kw["prefix_icon"] = prefix_icon
    return ft.TextField(**kw)


def _link_btn(testo, on_click):
    return ft.TextButton(
        testo,
        on_click=on_click,
        style=ft.ButtonStyle(
            color=ACCENT_CYAN,
            padding=ft.padding.symmetric(horizontal=0, vertical=4),
            overlay_color="transparent",
        ),
    )


def _errore(ref):
    return ft.Text("", color=ACCENT_RED, size=12, text_align=ft.TextAlign.CENTER, ref=ref)


def _info(ref):
    return ft.Text("", color=ACCENT_GREEN, size=12, text_align=ft.TextAlign.CENTER, ref=ref)


def _card_header(emoji, titolo, sottotitolo, accent=ACCENT_BLUE):
    return ft.Column([
        ft.Container(
            width=64, height=64, border_radius=20,
            bgcolor=accent + "20",
            border=ft.border.all(1, accent + "50"),
            alignment=ft.Alignment(0, 0),
            content=ft.Text(emoji, size=32),
        ),
        ft.Text(titolo, size=20, weight="bold", color=TEXT_PRIMARY,
                text_align=ft.TextAlign.CENTER),
        ft.Text(sottotitolo, size=11, color=TEXT_MUTED,
                text_align=ft.TextAlign.CENTER),
    ], spacing=8, horizontal_alignment=ft.CrossAxisAlignment.CENTER)


def _divider_or():
    return ft.Row([
        ft.Container(expand=True, height=1, bgcolor=BORDER_COLOR),
        ft.Text("  oppure  ", size=10, color=TEXT_MUTED),
        ft.Container(expand=True, height=1, bgcolor=BORDER_COLOR),
    ], spacing=0, vertical_alignment=ft.CrossAxisAlignment.CENTER)


def _card_container(content):
    return ft.Container(
        width=440, padding=40,
        border_radius=28, bgcolor=SECONDARY_BG,
        border=ft.border.all(1, BORDER_COLOR_LIGHT),
        content=content,
    )


# ══════════════════════════════════════════════════════════════════════
# SCHERMATA LOGIN
# ══════════════════════════════════════════════════════════════════════

def mostra_login(page: ft.Page, on_success, on_registra_studente, on_registra_docente):
    page.clean()
    page.bgcolor = PRIMARY_BG
    page.padding = 0

    ruolo_sel  = [None]
    err_ref    = ft.Ref[ft.Text]()

    user_input = _tf("Username o Email", prefix_icon=ft.Icons.PERSON_OUTLINE)
    pass_input = _tf("Password", password=True, prefix_icon=ft.Icons.LOCK_OUTLINE)

    card_s_ref = ft.Ref[ft.Container]()
    card_d_ref = ft.Ref[ft.Container]()

    def aggiorna_ui():
        if card_s_ref.current:
            sel_s = ruolo_sel[0] == "studente"
            card_s_ref.current.border  = ft.border.all(2, ACCENT_BLUE if sel_s else BORDER_COLOR_LIGHT)
            card_s_ref.current.bgcolor = (ACCENT_BLUE + "25") if sel_s else CARD_BG
        if card_d_ref.current:
            sel_d = ruolo_sel[0] == "docente"
            card_d_ref.current.border  = ft.border.all(2, ACCENT_PURPLE if sel_d else BORDER_COLOR_LIGHT)
            card_d_ref.current.bgcolor = (ACCENT_PURPLE + "25") if sel_d else CARD_BG
        page.update()

    def sel_s(e):
        ruolo_sel[0] = "studente"
        if err_ref.current: err_ref.current.value = ""
        aggiorna_ui()

    def sel_d(e):
        ruolo_sel[0] = "docente"
        if err_ref.current: err_ref.current.value = ""
        aggiorna_ui()

    def login(e=None):
        u = user_input.value.strip()
        p = pass_input.value.strip()
        if not ruolo_sel[0]:
            err_ref.current.value = "⚠️ Seleziona Studente o Docente"
            page.update(); return
        if not u or not p:
            err_ref.current.value = "⚠️ Inserisci username/email e password"
            page.update(); return
        ok, msg = auth.verifica_login(u, p, ruolo_sel[0])
        if ok:
            nome = auth.get_nome_display(u)
            on_success(ruolo_sel[0] == "studente", u, nome)
        else:
            err_ref.current.value = msg
            page.update()

    pass_input.on_submit = login

    def role_card(ref, emoji, titolo, desc, on_click):
        return ft.Container(
            ref=ref, width=160,
            padding=ft.padding.symmetric(horizontal=14, vertical=20),
            border_radius=18, bgcolor=CARD_BG,
            border=ft.border.all(2, BORDER_COLOR_LIGHT),
            on_click=on_click, ink=True,
            content=ft.Column([
                ft.Text(emoji, size=36, text_align=ft.TextAlign.CENTER),
                ft.Text(titolo, size=14, weight="bold", color=TEXT_PRIMARY,
                        text_align=ft.TextAlign.CENTER),
                ft.Text(desc, size=9, color=TEXT_MUTED, text_align=ft.TextAlign.CENTER),
            ], spacing=6, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
        )

    err_txt = ft.Text("", ref=err_ref, color=ACCENT_RED, size=12,
                      text_align=ft.TextAlign.CENTER)

    page.add(ft.Container(
        expand=True, alignment=ft.Alignment(0, 0),
        content=_card_container(ft.Column([
            _card_header("🏫", "Piattaforma Scolastica AI",
                         "Accedi al tuo spazio personale"),
            ft.Container(height=4),
            ft.Text("Chi sei?", size=11, color=TEXT_SECONDARY, weight="bold"),
            ft.Row([
                role_card(card_s_ref, "👨‍🎓", "Studente",
                          "Orario • Registro\nVerifiche • AI", sel_s),
                role_card(card_d_ref, "👨‍🏫", "Docente",
                          "Classi • Registro\nVerifiche • AI", sel_d),
            ], spacing=16, alignment=ft.MainAxisAlignment.CENTER),
            ft.Container(height=4),
            user_input,
            pass_input,
            err_txt,
            ft.Container(height=4),
            ft.FilledButton(
                "ACCEDI", width=360, height=50, on_click=login,
                style=ft.ButtonStyle(
                    bgcolor=ACCENT_BLUE, color="#ffffff",
                    shape=ft.RoundedRectangleBorder(radius=14),
                    text_style=ft.TextStyle(size=14, weight="bold", letter_spacing=1.5),
                ),
            ),
            _divider_or(),
            ft.Row([
                ft.Text("Sei uno studente?", size=11, color=TEXT_MUTED),
                _link_btn("Registrati", lambda e: on_registra_studente()),
            ], alignment=ft.MainAxisAlignment.CENTER, spacing=4),
            ft.Row([
                ft.Text("Sei un docente?", size=11, color=TEXT_MUTED),
                _link_btn("Crea account", lambda e: on_registra_docente()),
            ], alignment=ft.MainAxisAlignment.CENTER, spacing=4),
        ], spacing=12, horizontal_alignment=ft.CrossAxisAlignment.CENTER, tight=True)),
    ))
    page.update()


# ══════════════════════════════════════════════════════════════════════
# SCHERMATA REGISTRAZIONE STUDENTE
# ══════════════════════════════════════════════════════════════════════

def mostra_registrazione_studente(page: ft.Page, on_back, on_success):
    page.clean()
    page.bgcolor = PRIMARY_BG
    page.padding = 0

    err_ref  = ft.Ref[ft.Text]()
    info_ref = ft.Ref[ft.Text]()

    tf_codice  = _tf("Codice Scuola", hint="Es. SCUOLA2024",
                     prefix_icon=ft.Icons.SCHOOL_OUTLINED)
    tf_nome    = _tf("Nome e Cognome", prefix_icon=ft.Icons.BADGE_OUTLINED)
    tf_email   = _tf("Email", hint="mario.rossi@email.com",
                     prefix_icon=ft.Icons.EMAIL_OUTLINED)
    tf_classe  = _tf("Classe", hint="Es. 5F", width=340,
                     prefix_icon=ft.Icons.CLASS_OUTLINED)
    tf_pass    = _tf("Password", password=True,
                     prefix_icon=ft.Icons.LOCK_OUTLINED)
    tf_pass2   = _tf("Conferma Password", password=True,
                     prefix_icon=ft.Icons.LOCK_OUTLINED)

    spin = ft.ProgressRing(width=20, height=20, stroke_width=2,
                           color=ACCENT_BLUE, visible=False)

    def registra(e=None):
        if err_ref.current:  err_ref.current.value  = ""
        if info_ref.current: info_ref.current.value = ""
        page.update()

        codice = tf_codice.value.strip()
        nome   = tf_nome.value.strip()
        email  = tf_email.value.strip()
        classe = tf_classe.value.strip()
        pw1    = tf_pass.value.strip()
        pw2    = tf_pass2.value.strip()

        if not all([codice, nome, email, pw1]):
            err_ref.current.value = "⚠️ Compila tutti i campi obbligatori."
            page.update(); return

        if pw1 != pw2:
            err_ref.current.value = "⚠️ Le password non coincidono."
            page.update(); return

        spin.visible = True
        page.update()

        def _reg():
            ok, msg = auth.registra_studente(codice, email, nome, pw1, classe)
            spin.visible = False
            if ok:
                info_ref.current.value = msg
                page.update()
                import time; time.sleep(2)
                on_success("studente", email, nome)
            else:
                err_ref.current.value = msg
                page.update()

        threading.Thread(target=_reg, daemon=True).start()

    tf_pass2.on_submit = registra

    page.add(ft.Container(
        expand=True, alignment=ft.Alignment(0, 0),
        content=_card_container(ft.Column([
            _card_header("👨‍🎓", "Registrazione Studente",
                         "Inserisci i dati per creare il tuo account", ACCENT_BLUE),
            ft.Container(height=4),
            ft.Container(
                padding=ft.padding.symmetric(horizontal=12, vertical=8),
                border_radius=12, bgcolor=ACCENT_BLUE + "15",
                border=ft.border.all(1, ACCENT_BLUE + "40"),
                content=ft.Column([
                    ft.Text("📋  Cosa ti serve:", size=11, weight="bold", color=ACCENT_BLUE),
                    ft.Text("• Codice scuola (fornito dalla segreteria)", size=10, color=TEXT_MUTED),
                    ft.Text("• La tua email personale",                   size=10, color=TEXT_MUTED),
                    ft.Text("• Una password a tua scelta",                size=10, color=TEXT_MUTED),
                ], spacing=3, tight=True),
            ),
            tf_codice,
            tf_nome,
            ft.Row([tf_email], spacing=0),
            tf_classe,
            tf_pass,
            tf_pass2,
            ft.Text("", ref=err_ref,  color=ACCENT_RED,   size=12, text_align=ft.TextAlign.CENTER),
            ft.Text("", ref=info_ref, color=ACCENT_GREEN, size=12, text_align=ft.TextAlign.CENTER),
            ft.Row([spin], alignment=ft.MainAxisAlignment.CENTER),
            ft.FilledButton(
                "CREA ACCOUNT STUDENTE", width=360, height=50, on_click=registra,
                style=ft.ButtonStyle(
                    bgcolor=ACCENT_BLUE, color="#ffffff",
                    shape=ft.RoundedRectangleBorder(radius=14),
                    text_style=ft.TextStyle(size=13, weight="bold", letter_spacing=1),
                ),
            ),
            ft.Row([
                ft.Text("Hai già un account?", size=11, color=TEXT_MUTED),
                _link_btn("Accedi", lambda e: on_back()),
            ], alignment=ft.MainAxisAlignment.CENTER, spacing=4),
        ], spacing=12, horizontal_alignment=ft.CrossAxisAlignment.CENTER,
           tight=True, scroll=ft.ScrollMode.AUTO)),
    ))
    page.update()


# ══════════════════════════════════════════════════════════════════════
# SCHERMATA REGISTRAZIONE DOCENTE
# ══════════════════════════════════════════════════════════════════════

def mostra_registrazione_docente(page: ft.Page, on_back, on_success):
    page.clean()
    page.bgcolor = PRIMARY_BG
    page.padding = 0

    err_ref  = ft.Ref[ft.Text]()
    info_ref = ft.Ref[ft.Text]()

    tf_codice   = _tf("Codice Scuola", hint="Es. SCUOLA2024",
                      prefix_icon=ft.Icons.SCHOOL_OUTLINED)
    tf_username = _tf("Username fornito dalla scuola",
                      hint="Es. m.rossi  (in minuscolo)",
                      prefix_icon=ft.Icons.BADGE_OUTLINED)
    tf_nome     = _tf("Nome e Cognome", hint="Es. Mario Rossi",
                      prefix_icon=ft.Icons.PERSON_OUTLINED)
    tf_materia  = _tf("Materia principale (opzionale)",
                      hint="Es. Matematica",
                      prefix_icon=ft.Icons.BOOK_OUTLINED)
    tf_pass     = _tf("Password", password=True,
                      prefix_icon=ft.Icons.LOCK_OUTLINED)
    tf_pass2    = _tf("Conferma Password", password=True,
                      prefix_icon=ft.Icons.LOCK_OUTLINED)

    spin = ft.ProgressRing(width=20, height=20, stroke_width=2,
                           color=ACCENT_PURPLE, visible=False)

    def registra(e=None):
        if err_ref.current:  err_ref.current.value  = ""
        if info_ref.current: info_ref.current.value = ""
        page.update()

        codice   = tf_codice.value.strip()
        username = tf_username.value.strip()
        nome     = tf_nome.value.strip()
        materia  = tf_materia.value.strip()
        pw1      = tf_pass.value.strip()
        pw2      = tf_pass2.value.strip()

        if not all([codice, username, nome, pw1]):
            err_ref.current.value = "⚠️ Compila tutti i campi obbligatori."
            page.update(); return

        if pw1 != pw2:
            err_ref.current.value = "⚠️ Le password non coincidono."
            page.update(); return

        spin.visible = True
        page.update()

        def _reg():
            ok, msg = auth.registra_docente(codice, username, nome, pw1, materia)
            spin.visible = False
            if ok:
                info_ref.current.value = msg
                page.update()
                import time; time.sleep(2)
                on_success("docente", username, nome)
            else:
                err_ref.current.value = msg
                page.update()

        threading.Thread(target=_reg, daemon=True).start()

    tf_pass2.on_submit = registra

    page.add(ft.Container(
        expand=True, alignment=ft.Alignment(0, 0),
        content=_card_container(ft.Column([
            _card_header("👨‍🏫", "Registrazione Docente",
                         "Crea il tuo account istituzionale", ACCENT_PURPLE),
            ft.Container(height=4),
            ft.Container(
                padding=ft.padding.symmetric(horizontal=12, vertical=8),
                border_radius=12, bgcolor=ACCENT_PURPLE + "15",
                border=ft.border.all(1, ACCENT_PURPLE + "40"),
                content=ft.Column([
                    ft.Text("📋  Cosa ti serve:", size=11, weight="bold", color=ACCENT_PURPLE),
                    ft.Text("• Codice scuola (dalla segreteria / dirigente)", size=10, color=TEXT_MUTED),
                    ft.Text("• Username istituzionale (es. m.rossi)",          size=10, color=TEXT_MUTED),
                    ft.Text("• Una password sicura a tua scelta",              size=10, color=TEXT_MUTED),
                ], spacing=3, tight=True),
            ),
            tf_codice,
            tf_username,
            tf_nome,
            tf_materia,
            tf_pass,
            tf_pass2,
            ft.Text("", ref=err_ref,  color=ACCENT_RED,    size=12, text_align=ft.TextAlign.CENTER),
            ft.Text("", ref=info_ref, color=ACCENT_GREEN,  size=12, text_align=ft.TextAlign.CENTER),
            ft.Row([spin], alignment=ft.MainAxisAlignment.CENTER),
            ft.FilledButton(
                "CREA ACCOUNT DOCENTE", width=360, height=50, on_click=registra,
                style=ft.ButtonStyle(
                    bgcolor=ACCENT_PURPLE, color="#ffffff",
                    shape=ft.RoundedRectangleBorder(radius=14),
                    text_style=ft.TextStyle(size=13, weight="bold", letter_spacing=1),
                ),
            ),
            ft.Row([
                ft.Text("Hai già un account?", size=11, color=TEXT_MUTED),
                _link_btn("Accedi", lambda e: on_back()),
            ], alignment=ft.MainAxisAlignment.CENTER, spacing=4),
        ], spacing=12, horizontal_alignment=ft.CrossAxisAlignment.CENTER,
           tight=True, scroll=ft.ScrollMode.AUTO)),
    ))
    page.update()


# ══════════════════════════════════════════════════════════════════════
# APP SHELL CON SIDEBAR (invariata rispetto alla versione precedente)
# ══════════════════════════════════════════════════════════════════════

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

    content_area   = ft.Column([], expand=True, scroll=ft.ScrollMode.AUTO)
    sezione_attiva = ["home"]

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
        is_sel  = key == sezione_attiva[0]
        accent  = ACCENT_BLUE if is_student else ACCENT_PURPLE
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
            sidebar_voci,
            ft.Container(expand=True),
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
                                weight="bold", max_lines=1,
                                overflow=ft.TextOverflow.ELLIPSIS, expand=True),
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

    # ── sezioni: home, orario, registro, verifiche, interrogazioni, chat ──
    # (stessa implementazione della versione precedente — omessa per brevità)
    # Importa le funzioni build_* dal tuo main.py originale.

    def build_home():
        root2     = carica_orario()
        cl        = root2.get("ultima_classe", "")
        state     = cls_data(root2, cl) if cl else _empty()
        oggi_g    = g_nome(date.today())
        accent    = ACCENT_BLUE if is_student else ACCENT_PURPLE

        def _card(icona, titolo, desc, colore, sezione):
            c = ft.Container(
                width=175, height=125,
                padding=ft.padding.symmetric(horizontal=14, vertical=16),
                border_radius=20, bgcolor=CARD_BG,
                border=ft.border.all(2, colore + "40"),
                ink=True, on_click=lambda e, s=sezione: vai_a(s),
                content=ft.Column([
                    ft.Container(
                        width=40, height=40, border_radius=12,
                        bgcolor=colore + "20", border=ft.border.all(1, colore + "50"),
                        alignment=ft.Alignment(0, 0),
                        content=ft.Text(icona, size=20),
                    ),
                    ft.Text(titolo, size=12, weight="bold", color=TEXT_PRIMARY),
                    ft.Text(desc,   size=9,  color=TEXT_MUTED),
                ], spacing=5),
            )
            def hov(e, _c=c, _col=colore):
                _c.border  = ft.border.all(2, _col if e.data == "true" else _col + "40")
                _c.bgcolor = _col + "15" if e.data == "true" else CARD_BG
                page.update()
            c.on_hover = hov
            return c

        cards_items = (
            [("📅","Orario","Settimanale",ACCENT_BLUE,"orario"),
             ("📖","Registro","Argomenti",ACCENT_CYAN,"registro"),
             ("📝","Verifiche","Prossimi test",ACCENT_RED,"verifiche"),
             ("🎤","Interrogazioni","Il mio giorno",ACCENT_PURPLE,"interrogazioni"),
             ("🤖","AI Chat","Chiedi all'AI",ACCENT_GREEN,"chat")]
            if is_student else
            [("📋","Orario","Gestione",ACCENT_PURPLE,"orario"),
             ("📖","Registro","Argomenti",ACCENT_CYAN,"registro"),
             ("📝","Verifiche","Pianifica",ACCENT_RED,"verifiche"),
             ("🎤","Interrogazioni","Periodi",ACCENT_YELLOW,"interrogazioni"),
             ("🤖","AI Chat","Assistente",ACCENT_GREEN,"chat")]
        )
        cards = ft.Row([_card(*i) for i in cards_items], spacing=12, wrap=True)

        ore_oggi = state.get("orario", {}).get(oggi_g, {})
        n_ore    = MAX_ORE.get(oggi_g, 0) if oggi_g in GIORNI else 0
        ore_ws   = []
        for h in range(1, n_ore + 1):
            mi  = ore_oggi.get(h, {}) if isinstance(ore_oggi.get(h, {}), dict) else {}
            mat = mi.get("materia", "").strip()
            pro = mi.get("prof", "").strip()
            pal = SUBJECTS_PALETTE.get(mat, SUBJECTS_PALETTE["default"])
            ore_ws.append(ft.Container(
                padding=ft.padding.symmetric(horizontal=12, vertical=7),
                border_radius=10,
                bgcolor=pal["bg"] if mat else TERTIARY_BG,
                border=ft.border.all(1, pal["accent"] + "50" if mat else BORDER_COLOR),
                content=ft.Row([
                    ft.Container(width=24, height=24, border_radius=6,
                                 bgcolor=pal["accent"] + "25", alignment=ft.Alignment(0, 0),
                                 content=ft.Text(str(h), size=9, weight="bold", color=pal["accent"])),
                    ft.Text(mat or "—", size=11, color=TEXT_PRIMARY,
                            weight="bold" if mat else None, expand=True),
                    ft.Text(pro, size=9, color=TEXT_MUTED),
                ], spacing=8),
            ))

        oggi_col = ft.Column(
            ore_ws or [ft.Text(
                "Nessuna lezione oggi 🎉" if oggi_g not in GIORNI
                else "Orario non ancora inserito", size=11, color=TEXT_MUTED
            )], spacing=5,
        )

        def _box(titolo, icona, widget, acc=ACCENT_BLUE):
            return ft.Container(
                padding=ft.padding.symmetric(horizontal=18, vertical=14),
                border_radius=18, bgcolor=SECONDARY_BG,
                border=ft.border.all(1, BORDER_COLOR_LIGHT),
                content=ft.Column([
                    ft.Row([ft.Container(width=4, height=16, border_radius=2, bgcolor=acc),
                            ft.Text(f"{icona}  {titolo}", size=12,
                                    weight="bold", color=TEXT_PRIMARY)], spacing=8),
                    ft.Divider(color=BORDER_COLOR, height=1),
                    widget,
                ], spacing=8, tight=True),
            )

        # IP info banner
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
        except Exception:
            local_ip = "127.0.0.1"

        ip_banner = ft.Container(
            padding=ft.padding.symmetric(horizontal=14, vertical=8),
            border_radius=12,
            bgcolor=ACCENT_CYAN + "10",
            border=ft.border.all(1, ACCENT_CYAN + "30"),
            content=ft.Row([
                ft.Text("📡", size=16),
                ft.Column([
                    ft.Text("Server LAN attivo", size=11, weight="bold", color=ACCENT_CYAN),
                    ft.Text(f"Gli altri dispositivi possono connettersi a  http://{local_ip}:5000",
                            size=9, color=TEXT_MUTED, selectable=True),
                ], spacing=2, tight=True),
            ], spacing=10),
        ) if not is_student else ft.Container(height=0)

        benv = f"Ciao, {nome_display} 👋" if is_student else f"Bentornato, {nome_display} 👨‍🏫"
        sub  = (f"Classe {ultima_cl or '—'} · {oggi_g} {date.today().strftime('%d %B %Y')}"
                if is_student else f"{oggi_g} {date.today().strftime('%d %B %Y')}")

        content_area.controls = [ft.Container(
            padding=ft.padding.symmetric(horizontal=28, vertical=24),
            content=ft.Column([
                ft.Text(benv, size=24, weight="bold", color=TEXT_PRIMARY),
                ft.Text(sub,  size=11, color=TEXT_MUTED),
                ip_banner,
                ft.Container(height=4),
                cards,
                ft.Container(height=12),
                ft.Row([
                    ft.Container(expand=True,
                                 content=_box(f"Orario oggi — {oggi_g}", "📋",
                                              oggi_col, ACCENT_CYAN)),
                    ft.Container(width=20),
                    ft.Container(expand=True,
                                 content=_box("Prossime Verifiche", "📝",
                                              ft.Text("—", size=11, color=TEXT_MUTED),
                                              ACCENT_RED)),
                ], spacing=0, vertical_alignment=ft.CrossAxisAlignment.START),
            ], spacing=12),
        )]
        page.update()

    # ── Stato corrente classe ──────────────────────────────────────────
    classe_corrente = [ultima_cl or (classi[0] if classi else "")]

    def get_state():
        root2 = carica_orario()
        return cls_data(root2, classe_corrente[0])

    def get_classe():
        return classe_corrente[0]

    # ══════════════════════════════════════════════════════════════════
    # SEZIONE: ORARIO
    # ══════════════════════════════════════════════════════════════════

    def build_orario():
        from ui_helpers import classe_selector
        nonlocal root

        root2  = carica_orario()
        cl     = classe_corrente[0]
        state  = cls_data(root2, cl)
        classi2 = sorted(root2.get("classi", {}).keys())

        ora_attiva = ft.Ref[ft.Container]()
        ora_sel    = [None, None]   # [giorno, ora]

        MATERIE = [
            "Sistemi e Reti", "Informatica", "Telecomunicazioni",
            "Matematica", "Lingua inglese", "Italiano", "Storia",
            "Scienze", "Fisica", "Educazione Fisica", "Religione",
        ]

        grid_col = ft.Column(spacing=6)

        def _cell_content(giorno, ora):
            slot = state["orario"].get(giorno, {}).get(ora, {})
            mat  = slot.get("materia", "").strip() if isinstance(slot, dict) else str(slot).strip()
            pro  = slot.get("prof", "").strip()    if isinstance(slot, dict) else ""
            pal  = SUBJECTS_PALETTE.get(mat, SUBJECTS_PALETTE["default"])
            return mat, pro, pal

        edit_panel = ft.Column([], spacing=8, visible=False)

        def mostra_editor(giorno, ora):
            slot = state["orario"].get(giorno, {}).get(ora, {})
            mat  = slot.get("materia", "").strip() if isinstance(slot, dict) else ""
            pro  = slot.get("prof", "").strip()    if isinstance(slot, dict) else ""
            ora_sel[0] = giorno
            ora_sel[1] = ora

            dd_mat = cal_drop("Materia", [""] + MATERIE, expand=True)
            dd_mat.value = mat if mat in MATERIE else ""
            tf_pro = cal_tf("Professore", expand=True, value=pro)
            tf_mat_libero = cal_tf("Materia personalizzata", expand=True,
                                   value=mat if mat not in MATERIE else "")

            stato_txt = ft.Text("", size=10, color=ACCENT_GREEN)

            def salva_slot(e=None):
                m = dd_mat.value or tf_mat_libero.value.strip()
                p = tf_pro.value.strip()
                state["orario"].setdefault(giorno, {})[ora] = {"materia": m, "prof": p}
                salva_orario(root2)
                stato_txt.value = "✅ Salvato"
                page.update()
                build_orario()

            def cancella_slot(e=None):
                if giorno in state["orario"] and ora in state["orario"][giorno]:
                    del state["orario"][giorno][ora]
                    salva_orario(root2)
                page.update()
                build_orario()

            edit_panel.controls = [
                ft.Container(
                    padding=ft.padding.symmetric(horizontal=16, vertical=12),
                    border_radius=16, bgcolor=SECONDARY_BG,
                    border=ft.border.all(1, ACCENT_BLUE + "50"),
                    content=ft.Column([
                        ft.Text(f"✏️ {giorno} — {ora}ª ora",
                                size=12, weight="bold", color=TEXT_PRIMARY),
                        ft.Divider(color=BORDER_COLOR, height=1),
                        ft.Text("Materia dal menu:", size=10, color=TEXT_MUTED),
                        dd_mat,
                        ft.Text("oppure scrivi:", size=10, color=TEXT_MUTED),
                        tf_mat_libero,
                        tf_pro,
                        ft.Row([
                            pill("💾 Salva", salva_slot, color=ACCENT_GREEN),
                            pill("🗑️ Cancella", cancella_slot, color=ACCENT_RED),
                            stato_txt,
                        ], spacing=8),
                    ], spacing=8, tight=True),
                )
            ]
            edit_panel.visible = True
            page.update()

        def build_grid():
            grid_col.controls.clear()
            # Header giorni
            hdrs = [ft.Container(width=36)]
            for g in GIORNI:
                hdrs.append(ft.Container(
                    expand=True,
                    content=ft.Text(g, size=10, weight="bold",
                                    color=TEXT_PRIMARY, text_align=ft.TextAlign.CENTER),
                ))
            grid_col.controls.append(ft.Row(hdrs, spacing=4))
            # Righe ore
            max_ore = max(MAX_ORE.values())
            for h in range(1, max_ore + 1):
                row = [ft.Container(
                    width=36, height=44,
                    alignment=ft.Alignment(0, 0),
                    content=ft.Text(str(h), size=10, color=TEXT_MUTED, weight="bold"),
                )]
                for g in GIORNI:
                    if h > MAX_ORE.get(g, 0):
                        row.append(ft.Container(expand=True, height=44,
                                                bgcolor=CARD_BG + "30",
                                                border_radius=8))
                        continue
                    mat, pro, pal = _cell_content(g, h)
                    sel = (ora_sel[0] == g and ora_sel[1] == h)
                    cell = ft.Container(
                        expand=True, height=44,
                        border_radius=8,
                        bgcolor=pal["bg"] if mat else TERTIARY_BG,
                        border=ft.border.all(
                            2, (ACCENT_CYAN if sel else pal["accent"] + "70") if mat
                            else (ACCENT_CYAN if sel else BORDER_COLOR)
                        ),
                        ink=True,
                        on_click=lambda e, gg=g, hh=h: (mostra_editor(gg, hh) if not is_student else None),
                        content=ft.Column([
                            ft.Text(mat or ("—" if not is_student else ""),
                                    size=9, weight="bold" if mat else None,
                                    color=pal["accent"] if mat else TEXT_MUTED,
                                    max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                            ft.Text(pro, size=7, color=TEXT_MUTED,
                                    max_lines=1, overflow=ft.TextOverflow.ELLIPSIS)
                            if pro else ft.Container(height=0),
                        ], spacing=1, tight=True,
                           alignment=ft.MainAxisAlignment.CENTER),
                        padding=ft.padding.symmetric(horizontal=5, vertical=4),
                    )
                    row.append(cell)
                grid_col.controls.append(ft.Row(row, spacing=4))
            page.update()

        build_grid()

        def on_classe_change(nuova_cl):
            nonlocal root2
            if nuova_cl:
                classe_corrente[0] = nuova_cl
                root2.update(carica_orario())
                state.update(cls_data(root2, nuova_cl))
                root["ultima_classe"] = nuova_cl
                salva_orario(root)
                edit_panel.visible = False
                build_orario()

        # Pesi giornata
        def pesi_row():
            row = []
            for g in GIORNI:
                p = peso(state, g)
                col = ACCENT_GREEN if p < 6 else (ACCENT_YELLOW if p < 9 else ACCENT_RED)
                row.append(ft.Container(
                    expand=True,
                    content=ft.Column([
                        ft.Text(g[:3], size=8, color=TEXT_MUTED,
                                text_align=ft.TextAlign.CENTER),
                        ft.Text(f"{p:.1f}", size=10, weight="bold",
                                color=col, text_align=ft.TextAlign.CENTER),
                    ], spacing=1, horizontal_alignment=ft.CrossAxisAlignment.CENTER, tight=True),
                ))
            return ft.Row([ft.Container(width=36)] + row, spacing=4)

        main_col = ft.Column([
            ft.Text("📅 Gestione Orario" if not is_student else "📅 Orario Settimanale",
                    size=20, weight="bold", color=TEXT_PRIMARY),
            ft.Text("Clicca su una cella per modificarla" if not is_student
                    else "Visualizza il tuo orario settimanale",
                    size=11, color=TEXT_MUTED),
        ] + ([
            classe_selector(classe_corrente[0], classi2, on_classe_change, page)
        ] if not is_student else []) + [
            ft.Container(
                padding=ft.padding.symmetric(horizontal=18, vertical=14),
                border_radius=18, bgcolor=SECONDARY_BG,
                border=ft.border.all(1, BORDER_COLOR_LIGHT),
                content=ft.Column([
                    ft.Row([
                        ft.Container(width=4, height=18, border_radius=2, bgcolor=ACCENT_BLUE),
                        ft.Text("📋  Griglia oraria", size=12, weight="bold", color=TEXT_PRIMARY),
                    ], spacing=8),
                    ft.Divider(color=BORDER_COLOR, height=1),
                    grid_col,
                    ft.Divider(color=BORDER_COLOR, height=1),
                    ft.Row([
                        ft.Container(width=4, height=12, border_radius=2, bgcolor=ACCENT_YELLOW),
                        ft.Text("Peso giornata:", size=10, color=TEXT_MUTED, weight="bold"),
                    ], spacing=6),
                    pesi_row(),
                ], spacing=8, tight=True),
            ),
            edit_panel,
        ], spacing=14)

        content_area.controls = [ft.Container(
            padding=ft.padding.symmetric(horizontal=28, vertical=24),
            content=main_col,
        )]
        page.update()

    # ══════════════════════════════════════════════════════════════════
    # SEZIONE: REGISTRO
    # ══════════════════════════════════════════════════════════════════

    def build_registro():
        from datetime import date as ddate, timedelta
        root2 = carica_orario()
        cl    = classe_corrente[0]
        state = cls_data(root2, cl)

        dt_sel = [oggi]
        panel_ref = ft.Column([], spacing=0)

        def render_panel():
            if is_student:
                nome_s = state.get("nome_studente", nome_display)
                panel_ref.controls = [
                    build_registro_studente_panel(state, dt_sel[0], nome_s, page)
                ]
            else:
                panel_ref.controls = [
                    build_registro_docente_panel(
                        state, dt_sel[0], page,
                        on_save=lambda: salva_orario(root2),
                        root=root2,
                    )
                ]
            page.update()

        def cambia_data(delta):
            dt_sel[0] += timedelta(days=delta)
            render_panel()

        nav_row = ft.Row([
            ft.IconButton(ft.Icons.CHEVRON_LEFT, on_click=lambda e: cambia_data(-1),
                          icon_color=ACCENT_BLUE),
            ft.Text(f"{g_nome(dt_sel[0])} {dt_sel[0].strftime('%d/%m/%Y')}",
                    size=13, weight="bold", color=TEXT_PRIMARY),
            ft.IconButton(ft.Icons.CHEVRON_RIGHT, on_click=lambda e: cambia_data(1),
                          icon_color=ACCENT_BLUE),
            ft.TextButton("Oggi", on_click=lambda e: (dt_sel.__setitem__(0, oggi), render_panel()),
                          style=ft.ButtonStyle(color=ACCENT_CYAN)),
        ], spacing=4, alignment=ft.MainAxisAlignment.CENTER)

        render_panel()

        content_area.controls = [ft.Container(
            padding=ft.padding.symmetric(horizontal=28, vertical=24),
            content=ft.Column([
                ft.Text("📖 Registro Giornaliero", size=20, weight="bold", color=TEXT_PRIMARY),
                ft.Text("Argomenti • Compiti • Presenze", size=11, color=TEXT_MUTED),
                ft.Container(height=4),
                nav_row,
                panel_ref,
            ], spacing=12),
        )]
        page.update()

    # ══════════════════════════════════════════════════════════════════
    # SEZIONE: VERIFICHE
    # ══════════════════════════════════════════════════════════════════

    def build_verifiche():
        root2 = carica_orario()
        cl    = classe_corrente[0]
        state = cls_data(root2, cl)

        lista_col = ft.Column(spacing=6)

        MATERIE_V = [
            "Sistemi e Reti", "Informatica", "Telecomunicazioni",
            "Matematica", "Lingua inglese", "Italiano", "Storia",
            "Scienze", "Fisica", "Educazione Fisica", "Religione",
        ]

        def refresh_lista():
            lista_col.controls.clear()
            vv = state.get("verifiche", [])
            if not vv:
                lista_col.controls.append(
                    ft.Text("Nessuna verifica pianificata 🎉", size=12, color=TEXT_MUTED)
                )
            for idx, v in enumerate(vv):
                mat  = v.get("materia", "—")
                data = v.get("data", "")
                desc = v.get("descrizione", "")
                pal  = SUBJECTS_PALETTE.get(mat, SUBJECTS_PALETTE["default"])

                def elimina(e, i=idx):
                    state["verifiche"].pop(i)
                    salva_orario(root2)
                    refresh_lista()
                    page.update()

                lista_col.controls.append(ft.Container(
                    padding=ft.padding.symmetric(horizontal=14, vertical=10),
                    border_radius=14, bgcolor=pal["bg"],
                    border=ft.border.all(1, pal["accent"] + "60"),
                    content=ft.Row([
                        ft.Container(
                            width=4, height=50, border_radius=2, bgcolor=pal["accent"]
                        ),
                        ft.Column([
                            ft.Text(mat, size=12, weight="bold", color=pal["accent"]),
                            ft.Text(f"📅 {data}", size=10, color=TEXT_MUTED),
                            ft.Text(desc, size=10, color=TEXT_PRIMARY) if desc else ft.Container(height=0),
                        ], spacing=2, tight=True, expand=True),
                        ft.IconButton(
                            ft.Icons.DELETE_OUTLINE, icon_color=ACCENT_RED,
                            icon_size=16, on_click=elimina,
                            visible=not is_student,
                        ),
                    ], spacing=10),
                ))
            page.update()

        refresh_lista()

        if not is_student:
            dd_mat = cal_drop("Materia", MATERIE_V, width=200)
            tf_data = cal_tf("Data (es. 20/05/2025)", width=160)
            tf_desc = cal_tf("Descrizione (opzionale)", expand=True)
            stato_txt = ft.Text("", size=10, color=ACCENT_GREEN)

            def aggiungi(e=None):
                mat  = dd_mat.value or ""
                data = tf_data.value.strip()
                desc = tf_desc.value.strip()
                if not mat or not data:
                    stato_txt.value = "⚠️ Materia e data obbligatorie"
                    page.update(); return
                state["verifiche"].append({"materia": mat, "data": data, "descrizione": desc})
                salva_orario(root2)
                dd_mat.value = ""; tf_data.value = ""; tf_desc.value = ""
                stato_txt.value = "✅ Aggiunta!"
                refresh_lista()
                page.update()

            form = ft.Container(
                padding=ft.padding.symmetric(horizontal=16, vertical=12),
                border_radius=16, bgcolor=SECONDARY_BG,
                border=ft.border.all(1, ACCENT_RED + "40"),
                content=ft.Column([
                    ft.Text("➕ Aggiungi verifica", size=12, weight="bold", color=ACCENT_RED),
                    ft.Row([dd_mat, tf_data], spacing=8, wrap=True),
                    tf_desc,
                    ft.Row([
                        pill("💾 Aggiungi", aggiungi, color=ACCENT_RED),
                        stato_txt,
                    ], spacing=8),
                ], spacing=8, tight=True),
            )
        else:
            form = ft.Container(height=0)

        content_area.controls = [ft.Container(
            padding=ft.padding.symmetric(horizontal=28, vertical=24),
            content=ft.Column([
                ft.Text("📝 Verifiche", size=20, weight="bold", color=TEXT_PRIMARY),
                ft.Text("Piano delle verifiche per la classe " + cl, size=11, color=TEXT_MUTED),
                ft.Container(height=4),
                form,
                ft.Container(
                    padding=ft.padding.symmetric(horizontal=16, vertical=12),
                    border_radius=16, bgcolor=SECONDARY_BG,
                    border=ft.border.all(1, BORDER_COLOR_LIGHT),
                    content=ft.Column([
                        ft.Text("📋 Verifiche pianificate", size=12, weight="bold", color=TEXT_PRIMARY),
                        ft.Divider(color=BORDER_COLOR, height=1),
                        lista_col,
                    ], spacing=8, tight=True),
                ),
            ], spacing=14),
        )]
        page.update()

    # ══════════════════════════════════════════════════════════════════
    # SEZIONE: INTERROGAZIONI
    # ══════════════════════════════════════════════════════════════════

    def build_interrogazioni():
        root2 = carica_orario()
        cl    = classe_corrente[0]
        state = cls_data(root2, cl)

        lista_col = ft.Column(spacing=8)

        def refresh_lista():
            lista_col.controls.clear()
            iis = state.get("interrogazioni", [])
            if not iis:
                lista_col.controls.append(
                    ft.Text("Nessun periodo di interrogazione aperto.", size=12, color=TEXT_MUTED)
                )
            for idx, inter in enumerate(iis):
                mat  = inter.get("materia", "—")
                ini  = inter.get("data_inizio", "")
                fin  = inter.get("data_fine", "")
                pal  = SUBJECTS_PALETTE.get(mat, SUBJECTS_PALETTE["default"])
                assing = inter.get("assegnazioni", {})

                ass_rows = ft.Column([
                    ft.Row([
                        ft.Text(f"👤 {nome}", size=10, color=TEXT_PRIMARY, expand=True),
                        ft.Text(f"📅 {gg}", size=10, color=ACCENT_CYAN),
                    ]) for nome, gg in assing.items()
                ], spacing=3) if assing else ft.Text("Nessuno confermato", size=9, color=TEXT_MUTED)

                # Bottone prenota (studente)
                prenota_btn = ft.Container(height=0)
                if is_student:
                    dd_gg = cal_drop("Il mio giorno", GIORNI, width=160)
                    stato_p = ft.Text("", size=9, color=ACCENT_GREEN)

                    def prenota(e, i=idx, _dd=dd_gg, _st=stato_p):
                        gg = _dd.value
                        if not gg:
                            _st.value = "⚠️ Scegli un giorno"; page.update(); return
                        iis[i].setdefault("assegnazioni", {})[nome_display] = gg
                        salva_orario(root2)
                        _st.value = "✅ Confermato!"
                        refresh_lista()
                        page.update()

                    prenota_btn = ft.Row([dd_gg, pill("Prenota", prenota, color=ACCENT_PURPLE), stato_p],
                                         spacing=8, wrap=True)

                def elimina(e, i=idx):
                    state["interrogazioni"].pop(i)
                    salva_orario(root2)
                    refresh_lista()
                    page.update()

                lista_col.controls.append(ft.Container(
                    padding=ft.padding.symmetric(horizontal=14, vertical=10),
                    border_radius=14, bgcolor=pal["bg"],
                    border=ft.border.all(1, pal["accent"] + "60"),
                    content=ft.Column([
                        ft.Row([
                            ft.Text(mat, size=12, weight="bold", color=pal["accent"], expand=True),
                            ft.IconButton(ft.Icons.DELETE_OUTLINE, icon_color=ACCENT_RED,
                                          icon_size=16, on_click=elimina, visible=not is_student),
                        ]),
                        ft.Text(f"📅 Dal {ini} al {fin}", size=10, color=TEXT_MUTED),
                        ft.Divider(color=BORDER_COLOR, height=1),
                        ft.Text("Assegnazioni:", size=9, color=TEXT_MUTED, weight="bold"),
                        ass_rows,
                        prenota_btn,
                    ], spacing=5, tight=True),
                ))
            page.update()

        refresh_lista()

        if not is_student:
            MATERIE_I = [
                "Sistemi e Reti", "Informatica", "Telecomunicazioni",
                "Matematica", "Lingua inglese", "Italiano", "Storia",
                "Scienze", "Fisica", "Educazione Fisica", "Religione",
            ]
            dd_mat   = cal_drop("Materia", MATERIE_I, width=200)
            tf_ini   = cal_tf("Data inizio (es. 01/06/2025)", width=180)
            tf_fin   = cal_tf("Data fine   (es. 15/06/2025)", width=180)
            stato_txt = ft.Text("", size=10, color=ACCENT_GREEN)

            def aggiungi(e=None):
                mat = dd_mat.value or ""
                ini = tf_ini.value.strip()
                fin = tf_fin.value.strip()
                if not mat or not ini or not fin:
                    stato_txt.value = "⚠️ Tutti i campi sono obbligatori."
                    page.update(); return
                state["interrogazioni"].append({
                    "materia": mat, "data_inizio": ini, "data_fine": fin,
                    "assegnazioni": {}
                })
                salva_orario(root2)
                dd_mat.value = ""; tf_ini.value = ""; tf_fin.value = ""
                stato_txt.value = "✅ Periodo aggiunto!"
                refresh_lista()
                page.update()

            form = ft.Container(
                padding=ft.padding.symmetric(horizontal=16, vertical=12),
                border_radius=16, bgcolor=SECONDARY_BG,
                border=ft.border.all(1, ACCENT_YELLOW + "40"),
                content=ft.Column([
                    ft.Text("➕ Apri periodo interrogazioni", size=12, weight="bold", color=ACCENT_YELLOW),
                    ft.Row([dd_mat], spacing=8, wrap=True),
                    ft.Row([tf_ini, tf_fin], spacing=8, wrap=True),
                    ft.Row([
                        pill("💾 Aggiungi", aggiungi, color=ACCENT_YELLOW),
                        stato_txt,
                    ], spacing=8),
                ], spacing=8, tight=True),
            )
        else:
            form = ft.Container(height=0)

        content_area.controls = [ft.Container(
            padding=ft.padding.symmetric(horizontal=28, vertical=24),
            content=ft.Column([
                ft.Text("🎤 Interrogazioni", size=20, weight="bold", color=TEXT_PRIMARY),
                ft.Text("Periodi aperti — prenota il tuo giorno" if is_student
                        else "Gestione periodi di interrogazione", size=11, color=TEXT_MUTED),
                ft.Container(height=4),
                form,
                ft.Container(
                    padding=ft.padding.symmetric(horizontal=16, vertical=12),
                    border_radius=16, bgcolor=SECONDARY_BG,
                    border=ft.border.all(1, BORDER_COLOR_LIGHT),
                    content=ft.Column([
                        ft.Text("📋 Periodi attivi", size=12, weight="bold", color=TEXT_PRIMARY),
                        ft.Divider(color=BORDER_COLOR, height=1),
                        lista_col,
                    ], spacing=8, tight=True),
                ),
            ], spacing=14),
        )]
        page.update()

    # ══════════════════════════════════════════════════════════════════
    # SEZIONE: AI CHAT
    # ══════════════════════════════════════════════════════════════════

    def build_chat():
        chat_panel = build_chat_panel(page, get_state, get_classe)
        content_area.controls = [ft.Container(
            expand=True,
            padding=ft.padding.symmetric(horizontal=28, vertical=24),
            content=ft.Column([
                ft.Text("🤖 Assistente AI", size=20, weight="bold", color=TEXT_PRIMARY),
                ft.Text("Chiedi informazioni su orario, compiti, verifiche…",
                        size=11, color=TEXT_MUTED),
                ft.Container(height=4),
                ft.Container(expand=True, content=chat_panel),
            ], spacing=12, expand=True),
        )]
        page.update()

    # ══════════════════════════════════════════════════════════════════
    # ROUTER
    # ══════════════════════════════════════════════════════════════════

    def vai_a(sezione: str):
        sezione_attiva[0] = sezione
        aggiorna_sidebar()
        builders = {
            "home":           build_home,
            "orario":         build_orario,
            "registro":       build_registro,
            "verifiche":      build_verifiche,
            "interrogazioni": build_interrogazioni,
            "chat":           build_chat,
        }
        builders.get(sezione, build_home)()

    aggiorna_sidebar()
    page.add(ft.Row([
        sidebar,
        ft.Container(expand=True, content=content_area),
    ], expand=True, spacing=0))
    vai_a("home")


# ══════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════

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
        mostra_login(
            page,
            on_success=dopo_login,
            on_registra_studente=lambda: mostra_registrazione_studente(
                page, on_back=vai_login,
                on_success=lambda r, u, n: dopo_login(True, u, n)
            ),
            on_registra_docente=lambda: mostra_registrazione_docente(
                page, on_back=vai_login,
                on_success=lambda r, u, n: dopo_login(False, u, n)
            ),
        )

    def dopo_login(is_student: bool, username: str, nome_display: str):
        avvia_app(page, is_student, username, nome_display, on_logout=vai_login)

    # Avvia server Flask in background (accessibile dalla LAN)
    def _avvia_server():
        try:
            from server import avvia_server
            avvia_server(host="0.0.0.0", port=5000, debug=False)
        except Exception as ex:
            print(f"[Server] Errore avvio: {ex}")

    threading.Thread(target=_avvia_server, daemon=True).start()

    vai_login()


if __name__ == "__main__":
    ft.app(target=main)