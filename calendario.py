# ══════════════════════════════════════════════════════════════════════
# calendario.py — Vista Calendario Scolastico AI (Docente e Studente)
# ══════════════════════════════════════════════════════════════════════

import calendar
import threading
import flet as ft
from datetime import date, timedelta, datetime

from styles import (
    PRIMARY_BG, SECONDARY_BG, TERTIARY_BG, CARD_BG,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED,
    ACCENT_BLUE, ACCENT_CYAN, ACCENT_RED,
    ACCENT_GREEN, ACCENT_PURPLE, ACCENT_YELLOW,
    BORDER_COLOR, BORDER_COLOR_LIGHT, BORDER_RADIUS,
    SUBJECTS_PALETTE,
    ICON_RESET, ICON_PLUS, ICON_SAVE,
    ICON_CLASS,
)
from utils_calendario import (
    GIORNI, MAX_ORE, MESI_NOMI, MESI_OPTS,
    carica_orario, salva_orario, cls_data, _empty,
    get_registro_giorno, chiave_data,
    peso, giorni_mat, g_nome, date_periodo,
)
from ui_helpers import (
    cal_section, cal_tf, cal_drop, pill, badge, info_box,
    ai_consiglio_box, classe_selector,
)
from registro import build_registro_docente_panel, build_registro_studente_panel
from chatbot import build_chat_panel


# ══════════════════════════════════════════════════════════════════════
# WIDGET CALENDARIO MENSILE
# ══════════════════════════════════════════════════════════════════════

def build_cal(
    state: dict,
    anno: int,
    mese: int,
    cell: int = 52,
    on_day_click=None,
) -> ft.Column:
    """Restituisce il widget calendario mensile con dots evento."""

    oggi = date.today()

    # Raccoglie eventi verifica
    ev: dict[int, list] = {}
    for v in state.get("verifiche", []):
        if v.get("mese") == mese and v.get("giorno_num"):
            ev.setdefault(v["giorno_num"], []).append(("V", v.get("materia", "")))

    # Raccoglie eventi interrogazione
    for i in state.get("interrogazioni", []):
        mat  = i.get("materia", "")
        im_  = i.get("inizio_mese");   ig_ = i.get("inizio_giorno")
        fm_  = i.get("fine_mese");     fg_ = i.get("fine_giorno")
        if not all([im_, ig_, fm_, fg_]):
            continue
        for _, giorno_sett in i.get("assegnazioni", {}).items():
            try:
                ini = date(anno, im_, ig_)
                fin = date(anno, fm_, fg_)
                if fin < ini:
                    fin = date(anno + 1, fm_, fg_)
                cur = ini
                while cur <= fin:
                    if cur.year == anno and cur.month == mese and g_nome(cur) == giorno_sett:
                        ev.setdefault(cur.day, []).append(("I", mat))
                    cur += timedelta(days=1)
            except Exception:
                pass

    # Giorni con registro compilato
    reg_giorni: set[int] = set()
    for k in state.get("registro", {}):
        try:
            rd = date.fromisoformat(k)
            if rd.year == anno and rd.month == mese:
                r = state["registro"][k]
                if r.get("argomenti") or r.get("compiti") or r.get("assenti"):
                    reg_giorni.add(rd.day)
        except Exception:
            pass

    ts  = max(10, int(cell * 0.22))
    hdr = ft.Row([
        ft.Container(
            width=cell,
            content=ft.Text(
                n, size=8, color=TEXT_MUTED,
                text_align=ft.TextAlign.CENTER,
                weight="bold",
            ),
        )
        for n in ["L", "M", "M", "G", "V", "S", "D"]
    ], spacing=3)

    rows = [hdr]
    for week in calendar.monthcalendar(anno, mese):
        cells = []
        for wi, d in enumerate(week):
            is_today = d != 0 and date(anno, mese, d) == oggi
            evs      = ev.get(d, []) if d != 0 else []
            has_V    = any(t == "V" for t, _ in evs)
            has_I    = any(t == "I" for t, _ in evs)
            has_R    = d in reg_giorni if d != 0 else False

            tooltip_parts = [("📝 " if t == "V" else "🎤 ") + m for t, m in evs]
            if has_R:
                tooltip_parts.append("📖 Registro compilato")
            tooltip = "\n".join(tooltip_parts) if tooltip_parts else ""

            dots = ft.Row([
                ft.Container(width=6, height=6, border_radius=3, bgcolor=ACCENT_RED)    if has_V else ft.Container(),
                ft.Container(width=6, height=6, border_radius=3, bgcolor=ACCENT_PURPLE) if has_I else ft.Container(),
                ft.Container(width=6, height=6, border_radius=3, bgcolor=ACCENT_CYAN)   if has_R else ft.Container(),
            ], spacing=2, alignment=ft.MainAxisAlignment.CENTER)

            bg  = (ACCENT_BLUE if is_today
                   else "#1c2a42" if wi >= 5
                   else CARD_BG if d != 0
                   else "transparent")
            brd = (ft.border.all(2, ACCENT_BLUE)         if is_today else
                   ft.border.all(1, ACCENT_RED + "80")   if has_V    else
                   ft.border.all(1, ACCENT_CYAN + "80")  if has_R    else
                   ft.border.all(1, ACCENT_PURPLE + "60") if has_I   else None)

            dt_obj = date(anno, mese, d) if d != 0 else None

            def _click(e, _dt=dt_obj):
                if _dt and on_day_click:
                    on_day_click(_dt)

            cells.append(ft.Container(
                width=cell, height=cell, border_radius=10,
                bgcolor=bg, border=brd, tooltip=tooltip,
                on_click=_click if (d != 0 and on_day_click) else None,
                ink=bool(d != 0 and on_day_click),
                content=ft.Column([
                    ft.Text(
                        str(d) if d != 0 else "", size=ts,
                        color=TEXT_PRIMARY if is_today else TEXT_MUTED if wi >= 5 else TEXT_SECONDARY,
                        weight="bold" if is_today else None,
                        text_align=ft.TextAlign.CENTER,
                    ),
                    dots,
                ], spacing=2,
                alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            ))
        rows.append(ft.Row(cells, spacing=3))

    return ft.Column([
        ft.Column(rows, spacing=4),
        ft.Container(height=4),
        ft.Row([
            ft.Container(width=8, height=8, border_radius=4, bgcolor=ACCENT_RED),
            ft.Text("Verifica", size=9, color=TEXT_MUTED),
            ft.Container(width=10),
            ft.Container(width=8, height=8, border_radius=4, bgcolor=ACCENT_PURPLE),
            ft.Text("Interr.",  size=9, color=TEXT_MUTED),
            ft.Container(width=10),
            ft.Container(width=8, height=8, border_radius=4, bgcolor=ACCENT_CYAN),
            ft.Text("Registro", size=9, color=TEXT_MUTED),
        ], spacing=5),
    ], spacing=0, horizontal_alignment=ft.CrossAxisAlignment.CENTER)


# ══════════════════════════════════════════════════════════════════════
# FUNZIONE PRINCIPALE
# ══════════════════════════════════════════════════════════════════════

def avvia_calendario(page: ft.Page, is_student: bool = True, on_back=None):
    page.controls.clear()
    page.title   = "📅 Calendario Scolastico AI"
    page.bgcolor = PRIMARY_BG
    page.padding = 0
    page.update()

    root   = carica_orario()
    oggi   = date.today()
    cal_ym = [oggi.year, oggi.month]
    cur_cl = [root.get("ultima_classe", "") or
              (list(root["classi"].keys())[0] if root["classi"] else "")]

    # Pannello registro (si aggiorna al click sul giorno)
    registro_panel_holder = ft.Column([], spacing=0)

    # ── Callback apertura registro ─────────────────────────────────────

    def apri_registro_docente(dt: date):
        state = cls_data(root, cur_cl[0])
        if g_nome(dt) not in GIORNI:
            registro_panel_holder.controls = [
                info_box("📅 Questo giorno non è scolastico.", ACCENT_YELLOW)]
            page.update()
            return

        def _on_save():
            salva_orario(root)
            refresh_cal()

        panel = build_registro_docente_panel(state, dt, page, _on_save, root=root)
        registro_panel_holder.controls = [panel]
        page.update()

    def apri_registro_studente(dt: date):
        state  = cls_data(root, cur_cl[0])
        nome_s = state.get("nome_studente", "Studente")
        if g_nome(dt) not in GIORNI:
            registro_panel_holder.controls = [
                info_box("📅 Questo giorno non è scolastico.", ACCENT_YELLOW)]
            page.update()
            return
        panel = build_registro_studente_panel(state, dt, nome_s, page)
        registro_panel_holder.controls = [panel]
        page.update()

    # ── Pannello chat ──────────────────────────────────────────────────

    chat_panel = build_chat_panel(
        page=page,
        get_state=lambda: cls_data(root, cur_cl[0]),
        get_classe=lambda: cur_cl[0],
    )

    # ── Calendario widget ──────────────────────────────────────────────

    cal_body = ft.Column([], spacing=0, horizontal_alignment=ft.CrossAxisAlignment.CENTER)
    cal_lbl  = ft.Text("", size=15, weight="bold", color=TEXT_PRIMARY)

    def refresh_cal(large: bool = False):
        st = cls_data(root, cur_cl[0]) if cur_cl[0] else _empty()
        on_click_fn = apri_registro_docente if not is_student else apri_registro_studente
        cal_body.controls = [build_cal(
            st, cal_ym[0], cal_ym[1],
            cell=54 if large else 42,
            on_day_click=on_click_fn,
        )]
        cal_lbl.value = f"{MESI_NOMI[cal_ym[1]]}  {cal_ym[0]}"
        page.update()

    def nav_cal(d: int):
        m, y = cal_ym[1] + d, cal_ym[0]
        if m > 12: m, y = 1, y + 1
        elif m < 1: m, y = 12, y - 1
        cal_ym[0], cal_ym[1] = y, m
        refresh_cal(large=is_student)

    cal_widget = ft.Container(
        bgcolor=SECONDARY_BG,
        border=ft.border.all(1, BORDER_COLOR_LIGHT),
        border_radius=BORDER_RADIUS,
        padding=ft.padding.symmetric(horizontal=14, vertical=14),
        content=ft.Column([
            ft.Row([
                ft.IconButton(ft.Icons.CHEVRON_LEFT,  icon_color=ACCENT_BLUE, icon_size=20,
                              on_click=lambda e: nav_cal(-1)),
                ft.Container(expand=True,
                             content=ft.Row([cal_lbl], alignment=ft.MainAxisAlignment.CENTER)),
                ft.IconButton(ft.Icons.CHEVRON_RIGHT, icon_color=ACCENT_BLUE, icon_size=20,
                              on_click=lambda e: nav_cal(1)),
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            cal_body,
        ], spacing=10, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
    )

    # ── Topbar ─────────────────────────────────────────────────────────

    def torna_home(e):
        if on_back:
            on_back()

    topbar = ft.Container(
        height=52,
        padding=ft.padding.symmetric(horizontal=22, vertical=0),
        bgcolor=SECONDARY_BG,
        border=ft.border.only(bottom=ft.BorderSide(1, BORDER_COLOR)),
        content=ft.Row([
            ft.Row([
                ft.Text("📅", size=20),
                ft.Column([
                    ft.Text("CALENDARIO SCOLASTICO", size=13, weight="bold", color=TEXT_PRIMARY),
                    ft.Text("AI-powered", size=9, color=ACCENT_CYAN),
                ], spacing=0),
            ], spacing=10),
            ft.Container(expand=True),
            badge(f"{'👨‍🎓 Studente' if is_student else '👨‍🏫 Professore'}", ACCENT_BLUE),
            ft.Container(width=8),
            ft.TextButton(
                f"{ICON_RESET} Aggiorna",
                on_click=lambda e: (build_student if is_student else build_prof)(),
                style=ft.ButtonStyle(color=TEXT_MUTED,
                                     shape=ft.RoundedRectangleBorder(radius=20),
                                     padding=ft.padding.symmetric(horizontal=12, vertical=6)),
            ),
            ft.Container(width=8),
            ft.TextButton(
                "🏠 Home", on_click=torna_home,
                style=ft.ButtonStyle(color=ACCENT_CYAN,
                                     shape=ft.RoundedRectangleBorder(radius=20),
                                     padding=ft.padding.symmetric(horizontal=12, vertical=6)),
            ),
        ], vertical_alignment=ft.CrossAxisAlignment.CENTER),
    )

    # ══════════════════════════════════════════════════════════════════
    # VISTA PROFESSORE
    # ══════════════════════════════════════════════════════════════════

    prof_scroll = ft.Column(spacing=14, scroll=ft.ScrollMode.AUTO, expand=True)

    def build_prof():
        prof_scroll.controls.clear()
        cl    = cur_cl[0]
        state = cls_data(root, cl)
        mats  = sorted({
            e.get("materia", "")
            for d in state["orario"].values()
            for e in d.values()
            if e.get("materia")
        })

        def on_cl(nuova):
            if not nuova:
                return
            cur_cl[0] = nuova
            root["ultima_classe"] = nuova
            salva_orario(root)
            build_prof()

        prof_scroll.controls.append(
            classe_selector(cl, list(root["classi"].keys()), on_cl, page))

        # ── Orario settimanale ──────────────────────────────────────
        tab_body = ft.Column([], spacing=5, scroll=ft.ScrollMode.AUTO, height=220)
        tab_row  = ft.Row([], spacing=4, wrap=True)

        def make_rows(g):
            dd = state["orario"].setdefault(g, {})
            rows = []
            for h in range(1, MAX_ORE[g] + 1):
                si = cal_tf(f"{h}ª Materia", width=190, value=dd.get(h, {}).get("materia", ""))
                pi = cal_tf("Prof",          width=150, value=dd.get(h, {}).get("prof", ""))
                def sv(e, _g=g, _h=h, _s=si, _p=pi):
                    state["orario"].setdefault(_g, {})[_h] = {
                        "materia": _s.value.strip(), "prof": _p.value.strip()}
                    salva_orario(root)
                si.on_change = sv
                pi.on_change = sv
                rows.append(ft.Row([si, pi], spacing=8))
            return rows

        def switch(g):
            tab_body.controls = make_rows(g)
            for b in tab_row.controls:
                b.style = ft.ButtonStyle(
                    bgcolor=ACCENT_BLUE if b.data == g else CARD_BG,
                    color=TEXT_PRIMARY,
                    shape=ft.RoundedRectangleBorder(radius=16),
                    padding=ft.padding.symmetric(horizontal=12, vertical=6),
                )
            page.update()

        for g in GIORNI:
            tab_row.controls.append(ft.FilledButton(
                g[:3], data=g,
                on_click=lambda e: switch(e.control.data),
                style=ft.ButtonStyle(
                    bgcolor=ACCENT_BLUE if g == GIORNI[0] else CARD_BG,
                    color=TEXT_PRIMARY,
                    shape=ft.RoundedRectangleBorder(radius=16),
                    padding=ft.padding.symmetric(horizontal=12, vertical=6),
                ),
            ))
        tab_body.controls = make_rows(GIORNI[0])
        prof_scroll.controls.append(
            cal_section("Orario Classe", "📋",
                        ft.Column([tab_row, tab_body], spacing=10)))

        # ── Registro giornaliero ────────────────────────────────────
        hint_registro = ft.Container(
            padding=ft.padding.symmetric(horizontal=14, vertical=12),
            border_radius=BORDER_RADIUS, bgcolor=TERTIARY_BG,
            border=ft.border.all(1, ACCENT_CYAN + "40"),
            content=ft.Column([
                ft.Row([ft.Text("📖", size=18),
                        ft.Text("Registro Giornaliero", size=13, weight="bold", color=TEXT_PRIMARY)],
                       spacing=8),
                ft.Text("Clicca su un giorno del calendario per aprire il registro.",
                        size=11, color=TEXT_MUTED),
                registro_panel_holder,
            ], spacing=10, tight=True),
        )
        prof_scroll.controls.append(hint_registro)

        # ── Verifiche ───────────────────────────────────────────────
        mv = cal_drop("Materia", mats, width=170)
        vg = cal_tf("Gg", width=70, kb=ft.KeyboardType.NUMBER)
        vm = cal_drop("Mese", MESI_OPTS, width=165)
        vc = cal_tf("Classe", width=90, value=cl)
        vt = cal_tf("Tipo",   width=110, value="Scritto")
        ai_vbox = ft.Container(visible=False)

        def vmat_chg(e):
            if not mv.value:
                ai_vbox.visible = False; page.update(); return
            glist = giorni_mat(state, mv.value)
            if not glist:
                ai_vbox.visible = False; page.update(); return
            pesi = sorted([(g, peso(state, g)) for g in glist], key=lambda x: x[1])
            best = pesi[0][0]
            ai_vbox.content = ai_consiglio_box(
                [f"✔ {best} — peso {pesi[0][1]}  ← CONSIGLIATO"],
                [f"  {g} — peso {p}" for g, p in pesi[1:]] + ["(Scegli la data che preferisci)"],
            )
            ai_vbox.visible = True; page.update()
        mv.on_change = vmat_chg

        def add_v(e):
            if not mv.value or not vg.value or not vm.value:
                return
            try:
                gn = int(vg.value); mn = int(vm.value.split(" - ")[0])
                dt = date(oggi.year, mn, gn); gs = g_nome(dt)
            except Exception:
                return
            state["verifiche"].append({
                "materia": mv.value, "giorno_num": gn, "mese": mn,
                "giorno_settimana": gs, "classe": vc.value.strip(), "tipo": vt.value,
            })
            vg.value = ""; vm.value = None
            salva_orario(root); build_prof(); refresh_cal()

        vlist = ft.Column(spacing=5)
        for v in sorted(state["verifiche"],
                        key=lambda x: (x.get("mese", 0), x.get("giorno_num", 0))):
            pal = SUBJECTS_PALETTE.get(v.get("materia"), SUBJECTS_PALETTE["default"])
            try:
                ds = (date(oggi.year, v["mese"], v["giorno_num"]).strftime("%d %b") +
                      f" ({v['giorno_settimana']})")
            except Exception:
                ds = "?"
            def del_v(e, _v=v):
                state["verifiche"].remove(_v)
                salva_orario(root); build_prof(); refresh_cal()
            vlist.controls.append(ft.Container(
                padding=ft.padding.symmetric(horizontal=12, vertical=8),
                border_radius=12, bgcolor=pal["bg"],
                border=ft.border.all(1, pal["accent"] + "60"),
                content=ft.Row([
                    ft.Text("📝", size=14),
                    ft.Column([
                        ft.Text(v.get("materia"), size=11, color=TEXT_PRIMARY, weight="bold"),
                        ft.Text(f"{ds} · classe {v.get('classe','')} · {v.get('tipo','')}",
                                size=9, color=TEXT_SECONDARY),
                    ], spacing=1, expand=True),
                    ft.IconButton(ft.Icons.DELETE_OUTLINE, icon_color=ACCENT_RED,
                                  icon_size=16, on_click=del_v),
                ], spacing=10),
            ))

        prof_scroll.controls.append(cal_section("Verifiche", "📝", ft.Column([
            ft.Row([mv], spacing=8), ai_vbox,
            ft.Row([
                ft.Column([ft.Text("Data", size=10, color=TEXT_MUTED),
                           ft.Row([vg, vm], spacing=6)], spacing=4),
                ft.Column([ft.Text("Classe / Tipo", size=10, color=TEXT_MUTED),
                           ft.Row([vc, vt], spacing=6)], spacing=4),
            ], spacing=16),
            pill(f"{ICON_PLUS} Aggiungi Verifica", add_v),
            ft.Divider(color=BORDER_COLOR, height=1),
            vlist,
        ], spacing=10), accent=ACCENT_RED))

        # ── Interrogazioni ──────────────────────────────────────────
        mi  = cal_drop("Materia", mats, width=170)
        ig_ = cal_tf("Gg inizio", width=75, kb=ft.KeyboardType.NUMBER)
        im_ = cal_drop("Mese inizio", MESI_OPTS, width=165)
        fg_ = cal_tf("Gg fine",   width=75, kb=ft.KeyboardType.NUMBER)
        fm_ = cal_drop("Mese fine",   MESI_OPTS, width=165)
        ai_ibox = ft.Container(visible=False)

        def imat_chg(e):
            if not mi.value:
                ai_ibox.visible = False; page.update(); return
            glist = giorni_mat(state, mi.value)
            if not glist:
                ai_ibox.visible = False; page.update(); return
            pesi = sorted([(g, peso(state, g)) for g in glist], key=lambda x: x[1])
            best = pesi[0][0]
            ai_ibox.content = ai_consiglio_box(
                [f"✔ {best} — peso {pesi[0][1]}  ← GIORNO CONSIGLIATO"],
                [f"  {g} — peso {p}" for g, p in pesi[1:]] + ["(Puoi impostare il periodo liberamente)"],
            )
            ai_ibox.visible = True; page.update()
        mi.on_change = imat_chg

        def apri_i(e):
            if not mi.value:
                return
            try:
                im = int(im_.value.split(" - ")[0]); ig = int(ig_.value)
                fm = int(fm_.value.split(" - ")[0]); fg = int(fg_.value)
                date(oggi.year, im, ig); date(oggi.year, fm, fg)
            except Exception:
                return
            if any(i.get("materia") == mi.value for i in state["interrogazioni"]):
                return
            state["interrogazioni"].append({
                "id": f"{mi.value}_{datetime.now().timestamp()}",
                "materia": mi.value,
                "inizio_giorno": ig, "inizio_mese": im,
                "fine_giorno":   fg, "fine_mese":   fm,
                "assegnazioni": {},
            })
            mi.value = None; ig_.value = ""; im_.value = None
            fg_.value = ""; fm_.value = None; ai_ibox.visible = False
            salva_orario(root); build_prof(); refresh_cal()

        ilist = ft.Column(spacing=5)
        for i in state["interrogazioni"]:
            try:
                ps = f"{i['inizio_giorno']}/{i['inizio_mese']} → {i['fine_giorno']}/{i['fine_mese']}"
            except Exception:
                ps = "?"
            def del_i(e, _i=i):
                state["interrogazioni"].remove(_i)
                salva_orario(root); build_prof(); refresh_cal()
            ilist.controls.append(ft.Container(
                padding=ft.padding.symmetric(horizontal=12, vertical=8),
                border_radius=12, bgcolor=TERTIARY_BG,
                border=ft.border.all(1, ACCENT_PURPLE + "60"),
                content=ft.Row([
                    ft.Text("🎤", size=14),
                    ft.Column([
                        ft.Text(i.get("materia"), size=11, color=TEXT_PRIMARY, weight="bold"),
                        ft.Text(f"📆 {ps} · {len(i.get('assegnazioni', {}))} assegnati",
                                size=9, color=TEXT_SECONDARY),
                    ], spacing=1, expand=True),
                    ft.IconButton(ft.Icons.DELETE_OUTLINE, icon_color=ACCENT_RED,
                                  icon_size=16, on_click=del_i),
                ], spacing=10),
            ))

        prof_scroll.controls.append(cal_section("Interrogazioni — Periodi", "🎤", ft.Column([
            ft.Row([mi], spacing=8), ai_ibox,
            ft.Row([
                ft.Container(padding=10, border_radius=12, bgcolor=ACCENT_GREEN + "12",
                    border=ft.border.all(1, ACCENT_GREEN + "40"),
                    content=ft.Column([
                        ft.Text("Data inizio", size=9, color=ACCENT_GREEN, weight="bold"),
                        ft.Row([ig_, im_], spacing=6),
                    ], spacing=5)),
                ft.Container(padding=10, border_radius=12, bgcolor=ACCENT_RED + "12",
                    border=ft.border.all(1, ACCENT_RED + "40"),
                    content=ft.Column([
                        ft.Text("Data fine", size=9, color=ACCENT_RED, weight="bold"),
                        ft.Row([fg_, fm_], spacing=6),
                    ], spacing=5)),
            ], spacing=12),
            pill("🎤 Apri Periodo", apri_i, color=ACCENT_PURPLE),
            ft.Divider(color=BORDER_COLOR, height=1),
            ilist,
        ], spacing=10), accent=ACCENT_PURPLE))

        refresh_cal()
        page.update()

    # ══════════════════════════════════════════════════════════════════
    # VISTA STUDENTE
    # ══════════════════════════════════════════════════════════════════

    student_scroll = ft.Column(spacing=14, scroll=ft.ScrollMode.AUTO, expand=True)

    def build_student():
        student_scroll.controls.clear()
        cl    = cur_cl[0]
        state = cls_data(root, cl) if cl else _empty()

        def on_cl(nuova):
            if not nuova:
                return
            cur_cl[0] = nuova
            root["ultima_classe"] = nuova
            salva_orario(root)
            build_student()

        student_scroll.controls.append(
            classe_selector(cl, list(root["classi"].keys()), on_cl, page))

        # Nome studente per presenza
        nome_s = state.get("nome_studente", "")
        tf_nome = cal_tf("Il mio nome (per le presenze)", width=260, value=nome_s)
        def salva_nome(e):
            state["nome_studente"] = tf_nome.value.strip()
            salva_orario(root)
        tf_nome.on_blur   = salva_nome
        tf_nome.on_submit = salva_nome

        student_scroll.controls.append(ft.Container(
            padding=ft.padding.symmetric(horizontal=16, vertical=10),
            border_radius=BORDER_RADIUS, bgcolor=SECONDARY_BG,
            border=ft.border.all(1, ACCENT_PURPLE + "40"),
            content=ft.Column([
                ft.Row([ft.Text("👤", size=16),
                        ft.Text("Il mio profilo", size=12, weight="bold", color=TEXT_PRIMARY)],
                       spacing=8),
                ft.Row([tf_nome,
                        ft.Text("← Invio per salvare", size=9, color=TEXT_MUTED)],
                       spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            ], spacing=8, tight=True),
        ))

        # Mini orario settimanale
        oggi_g = g_nome(date.today())
        max_h  = max(MAX_ORE.values())
        mini   = [ft.Row(
            [ft.Container(width=32)] + [
                ft.Container(
                    expand=True, border_radius=6,
                    bgcolor=ACCENT_BLUE + "25" if g == oggi_g else None,
                    content=ft.Text(
                        g[:3], size=8, weight="bold",
                        color=ACCENT_BLUE if g == oggi_g else TEXT_MUTED,
                        text_align=ft.TextAlign.CENTER,
                    ),
                )
                for g in GIORNI
            ], spacing=2,
        )]
        for h in range(1, max_h + 1):
            row = [ft.Container(
                width=32,
                content=ft.Text(f"{h}ª", size=8, color=ACCENT_CYAN,
                                text_align=ft.TextAlign.CENTER),
            )]
            for g in GIORNI:
                if h > MAX_ORE[g]:
                    row.append(ft.Container(expand=True, height=26,
                                            bgcolor=CARD_BG + "22", border_radius=6))
                else:
                    m   = state["orario"].get(g, {}).get(h, {}).get("materia", "").strip()
                    pal = SUBJECTS_PALETTE.get(m, SUBJECTS_PALETTE["default"]) if m else None
                    row.append(ft.Container(
                        expand=True, height=26, border_radius=6,
                        bgcolor=CARD_BG + "33" if not m else pal["bg"],
                        border=ft.border.all(1,
                            ACCENT_BLUE if g == oggi_g else
                            (BORDER_COLOR if not m else pal["accent"] + "50")),
                        padding=2,
                        content=ft.Text(
                            (m[:5] + "…" if len(m) > 5 else m), size=7,
                            color=TEXT_PRIMARY, text_align=ft.TextAlign.CENTER, max_lines=1,
                        ) if m else ft.Container(),
                    ))
            mini.append(ft.Row(row, spacing=2))

        mini_widget = ft.Container(
            padding=ft.padding.symmetric(horizontal=12, vertical=10),
            border_radius=BORDER_RADIUS, bgcolor=SECONDARY_BG,
            border=ft.border.all(1, BORDER_COLOR_LIGHT),
            content=ft.Column([
                ft.Text("Orario Settimanale", size=11, weight="bold", color=TEXT_MUTED),
                ft.Column(mini, spacing=2),
            ], spacing=8),
        )

        cal_widget.expand = True
        student_scroll.controls.append(ft.Row([
            ft.Container(expand=True, content=cal_widget),
            ft.Container(width=330, content=mini_widget),
        ], spacing=12, vertical_alignment=ft.CrossAxisAlignment.START))

        # Registro (placeholder cliccabile)
        hint_registro = ft.Container(
            padding=ft.padding.symmetric(horizontal=14, vertical=12),
            border_radius=BORDER_RADIUS, bgcolor=TERTIARY_BG,
            border=ft.border.all(1, ACCENT_CYAN + "40"),
            content=ft.Column([
                ft.Row([ft.Text("📖", size=18),
                        ft.Text("Registro Giornaliero", size=13, weight="bold", color=TEXT_PRIMARY)],
                       spacing=8),
                ft.Text("Clicca su un giorno del calendario per vedere argomenti, compiti e presenza.",
                        size=11, color=TEXT_MUTED),
                registro_panel_holder,
            ], spacing=10, tight=True),
        )
        student_scroll.controls.append(hint_registro)

        # Prossime verifiche
        upcoming = sorted(
            [(date(oggi.year, v["mese"], v["giorno_num"]), v)
             for v in state.get("verifiche", [])
             if all([v.get("mese"), v.get("giorno_num")]) and
             date(oggi.year, v["mese"], v["giorno_num"]) >= oggi],
            key=lambda x: x[0],
        )
        if upcoming:
            vf = ft.Column(spacing=6)
            for vd, v in upcoming[:6]:
                pal   = SUBJECTS_PALETTE.get(v.get("materia"), SUBJECTS_PALETTE["default"])
                delta = (vd - oggi).days
                bc    = ACCENT_RED if delta <= 2 else ACCENT_YELLOW if delta <= 7 else ACCENT_GREEN
                vf.controls.append(ft.Container(
                    padding=ft.padding.symmetric(horizontal=12, vertical=8),
                    border_radius=12, bgcolor=pal["bg"],
                    border=ft.border.all(1, pal["accent"] + "60"),
                    content=ft.Row([
                        ft.Text("📝", size=16),
                        ft.Column([
                            ft.Text(v.get("materia"), size=11, color=TEXT_PRIMARY, weight="bold"),
                            ft.Text(
                                f"{vd.strftime('%d %b')} ({v.get('giorno_settimana','')}) · {v.get('tipo','')}",
                                size=9, color=TEXT_SECONDARY,
                            ),
                        ], spacing=1, expand=True),
                        badge("OGGI!" if delta == 0 else f"tra {delta}gg", bc),
                    ], spacing=10),
                ))
            student_scroll.controls.append(
                cal_section("Prossime Verifiche", "📝", vf, accent=ACCENT_RED))

        # Riepilogo assenze mese corrente
        nome_studente = state.get("nome_studente", "")
        if nome_studente:
            assenze_mese = []
            for k, reg in state.get("registro", {}).items():
                try:
                    rd = date.fromisoformat(k)
                    if rd.year == oggi.year and rd.month == oggi.month:
                        if nome_studente in reg.get("assenti", []):
                            assenze_mese.append(rd)
                except Exception:
                    pass
            assenze_mese.sort()
            if assenze_mese:
                items = ft.Column(spacing=4)
                for ad in assenze_mese:
                    items.controls.append(ft.Container(
                        padding=ft.padding.symmetric(horizontal=10, vertical=5),
                        border_radius=10, bgcolor=ACCENT_RED + "15",
                        border=ft.border.all(1, ACCENT_RED + "40"),
                        content=ft.Text(
                            f"❌ {ad.strftime('%d %B %Y')} ({g_nome(ad)})",
                            size=10, color=TEXT_PRIMARY,
                        ),
                    ))
                student_scroll.controls.append(
                    cal_section(f"Mie assenze — {MESI_NOMI[oggi.month]}", "📋",
                                items, accent=ACCENT_RED))

        # Interrogazioni da confermare
        nome_s2 = state.get("nome_studente", "Studente")
        pending = [i for i in state.get("interrogazioni", [])
                   if nome_s2 not in i.get("assegnazioni", {})]
        if pending:
            ic = ft.Column(spacing=12)
            for interr in pending:
                mat = interr.get("materia", "?")
                dd  = date_periodo(
                    state, mat,
                    interr.get("inizio_mese"), interr.get("inizio_giorno"),
                    interr.get("fine_mese"),   interr.get("fine_giorno"),
                )
                if not dd:
                    ic.controls.append(info_box(
                        f"🎤 {mat}: nessun giorno disponibile — parla col prof.",
                        ACCENT_YELLOW,
                    ))
                    continue
                pesi = {d: peso(state, gn) for d, gn in dd}
                best = min(pesi, key=pesi.get)
                lines_ok = [f"✔ {best.strftime('%d %b')} ({g_nome(best)}) — peso {pesi[best]}  ← CONSIGLIATO"]
                lines_no = [f"  {d.strftime('%d %b')} ({gn}) — peso {pesi[d]}" for d, gn in dd if d != best]
                ai_box   = ai_consiglio_box(lines_ok, lines_no)
                opts     = [f"{d.strftime('%d/%m')} – {gn}" for d, gn in dd]
                ddd      = cal_drop("Scegli data", opts, expand=True)
                ddd.value = f"{best.strftime('%d/%m')} – {g_nome(best)}"

                def conferma(e, _i=interr, _d=ddd):
                    if not _d.value:
                        return
                    try:
                        gs, ms = _d.value.split(" – ")[0].split("/")
                        chosen = date(oggi.year, int(ms), int(gs))
                        _i.setdefault("assegnazioni", {})[nome_s2] = g_nome(chosen)
                        salva_orario(root)
                        build_student()
                        page.update()
                    except Exception:
                        pass

                ic.controls.append(ft.Container(
                    padding=12, border_radius=14, bgcolor=TERTIARY_BG,
                    border=ft.border.all(1, ACCENT_PURPLE + "70"),
                    content=ft.Column([
                        ft.Row([ft.Text("🎤", size=16),
                                ft.Text(f"Interrogazione: {mat}", size=12,
                                        weight="bold", color=TEXT_PRIMARY)], spacing=8),
                        ai_box,
                        ft.Row([ddd, pill("Conferma", conferma, color=ACCENT_PURPLE)],
                               spacing=10, vertical_alignment=ft.CrossAxisAlignment.END),
                    ], spacing=8),
                ))
            student_scroll.controls.append(
                cal_section("Scegli Giorno Interrogazione", "🎤", ic, accent=ACCENT_PURPLE))

        # Interrogazioni confermate
        confirmed = [
            (i, i["assegnazioni"][nome_s2])
            for i in state.get("interrogazioni", [])
            if nome_s2 in i.get("assegnazioni", {})
        ]
        if confirmed:
            cc = ft.Column(spacing=6)
            for interr, giorno_sett in confirmed:
                mat = interr.get("materia", "?")
                cc.controls.append(ft.Container(
                    padding=ft.padding.symmetric(horizontal=12, vertical=8),
                    border_radius=12, bgcolor=ACCENT_PURPLE + "15",
                    border=ft.border.all(1, ACCENT_PURPLE + "60"),
                    content=ft.Row([
                        ft.Text("✅", size=14),
                        ft.Column([
                            ft.Text(mat, size=11, color=TEXT_PRIMARY, weight="bold"),
                            ft.Text(f"Giorno: {giorno_sett}", size=9, color=TEXT_SECONDARY),
                        ], spacing=1, expand=True),
                    ], spacing=10),
                ))
            student_scroll.controls.append(
                cal_section("Interrogazioni Confermate", "✅", cc, accent=ACCENT_GREEN))

        refresh_cal(large=True)
        page.update()

    # ── Layout finale ──────────────────────────────────────────────────

    if is_student:
        page.add(ft.Column([
            topbar,
            ft.Row([
                ft.Container(
                    expand=True,
                    padding=ft.padding.symmetric(horizontal=18, vertical=14),
                    content=student_scroll,
                ),
                chat_panel,
            ], expand=True, spacing=0, vertical_alignment=ft.CrossAxisAlignment.START),
        ], spacing=0, expand=True))
        build_student()
    else:
        cal_side = ft.Container(
            width=420, bgcolor=SECONDARY_BG,
            border=ft.border.only(left=ft.BorderSide(1, BORDER_COLOR)),
            padding=ft.padding.symmetric(horizontal=16, vertical=14),
            content=ft.Column([
                ft.Text("Calendario Mensile", size=11, weight="bold", color=TEXT_MUTED),
                ft.Text("Clicca un giorno per aprire il registro", size=9, color=ACCENT_CYAN),
                ft.Divider(color=BORDER_COLOR, height=1),
                cal_widget,
            ], spacing=10),
        )
        page.add(ft.Column([
            topbar,
            ft.Row([
                ft.Container(
                    expand=True,
                    padding=ft.padding.symmetric(horizontal=18, vertical=14),
                    content=prof_scroll,
                ),
                cal_side,
                chat_panel,
            ], expand=True, spacing=0, vertical_alignment=ft.CrossAxisAlignment.START),
        ], spacing=0, expand=True))
        build_prof()

    page.update()
