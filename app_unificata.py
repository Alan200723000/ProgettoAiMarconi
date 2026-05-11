    """
    app_unificata.py
    ────────────────
    Fusione di:
    • styles.py          → costanti di stile / palette
    • test_calendario.py → Calendario Scolastico AI (professore + studente)
    • test4.py           → AI Workspace (mappe concettuali da PDF)

    NOVITÀ:
    • Docente: registra argomenti spiegati, compiti assegnati, assenti per ogni giorno
    • Studente: vede presenze, compiti e argomenti del giorno selezionato

    Avvio:  python app_unificata.py
    """

    # ══════════════════════════════════════════════════════════════════════
    # SEZIONE 1 — STILI
    # ══════════════════════════════════════════════════════════════════════

    PRIMARY_BG    = "#080e1a"
    SECONDARY_BG  = "#0d1528"
    TERTIARY_BG   = "#111e35"
    CARD_BG       = "#162035"

    TEXT_PRIMARY   = "#e8f0fe"
    TEXT_SECONDARY = "#94a3b8"
    TEXT_MUTED     = "#4a5a75"
    TEXT_SUBTLE    = "#2d3d55"

    ACCENT_BLUE   = "#4f8ef7"
    ACCENT_CYAN   = "#22d3ee"
    ACCENT_RED    = "#fb7185"
    ACCENT_GREEN  = "#34d399"
    ACCENT_PURPLE = "#a78bfa"
    ACCENT_YELLOW = "#fbbf24"
    ACCENT_ORANGE = "#fb923c"

    SUBJECTS_PALETTE = {
        "Sistemi e Reti":    {"bg": "#0f2545", "accent": "#3b82f6"},
        "Informatica":       {"bg": "#0e1f3e", "accent": "#60a5fa"},
        "Telecomunicazioni": {"bg": "#0a2d22", "accent": "#10b981"},
        "Matematica":        {"bg": "#0f2535", "accent": "#22d3ee"},
        "Lingua inglese":    {"bg": "#1e1040", "accent": "#a78bfa"},
        "Italiano":          {"bg": "#3a1018", "accent": "#fb7185"},
        "Storia":            {"bg": "#2a1505", "accent": "#f97316"},
        "Scienze":           {"bg": "#0f2a12", "accent": "#4ade80"},
        "Fisica":            {"bg": "#0a1e30", "accent": "#06b6d4"},
        "Educazione Fisica": {"bg": "#2a1e08", "accent": "#fbbf24"},
        "Religione":         {"bg": "#1a2510", "accent": "#84cc16"},
        "default":           {"bg": "#14202e", "accent": "#4a5a75"},
    }

    BORDER_COLOR        = "#1a2540"
    BORDER_COLOR_LIGHT  = "#253550"
    BORDER_RADIUS       = 18
    BORDER_RADIUS_SMALL = 12

    CHAT_SIDEBAR_WIDTH  = 300

    ICON_CALENDAR     = "📅"; ICON_STUDENT = "👨‍🎓"; ICON_TEACHER = "👨‍🏫"; ICON_AI = "🤖"
    ICON_CHECK        = "✅"; ICON_VERIFY  = "📝"; ICON_INTERROGATION = "🎤"; ICON_SAVE = "💾"
    ICON_RESET        = "🧹"; ICON_SUGGEST = "💡"; ICON_PLUS = "➕"; WARNING = "⚠️"
    ICON_CLASS        = "🏫"

    class ChatMessageStyle:
        user_bg = "#163256"
        ai_bg   = "#1e2d45"

    class GridStyle:
        cell_height   = 50
        mini_height   = 28
        row_spacing   = 4
        border_radius = 10


    # ══════════════════════════════════════════════════════════════════════
    # SEZIONE 2 — IMPORTS COMUNI
    # ══════════════════════════════════════════════════════════════════════

    import flet as ft
    import os, re, json, calendar, threading, warnings, webbrowser
    import tempfile, base64
    import urllib.request, urllib.error
    from datetime import datetime, timedelta, date
    import tkinter as tk
    from tkinter import filedialog
    import PyPDF2

    from langchain_ollama import OllamaLLM, OllamaEmbeddings
    from langchain_core.prompts import ChatPromptTemplate
    from langchain_community.vectorstores import Chroma
    from langchain_text_splitters import RecursiveCharacterTextSplitter
    from langchain_community.document_loaders import TextLoader
    from langchain_core.runnables import RunnablePassthrough
    from langchain_core.output_parsers import StrOutputParser
    from pyvis.network import Network

    import speech_recognition as sr

    try:
        from gtts import gTTS
        TTS_DISPONIBILE = True
    except ImportError:
        TTS_DISPONIBILE = False
        print("⚠️ gTTS non installato. Installa con: pip install gTTS")

    try:
        import pygame
        pygame.mixer.init()
        PYGAME_DISPONIBILE = True
    except ImportError:
        PYGAME_DISPONIBILE = False
        print("⚠️ pygame non installato. Installa con: pip install pygame")

    warnings.filterwarnings("ignore")


    # ══════════════════════════════════════════════════════════════════════
    # SEZIONE 3 — CALENDARIO SCOLASTICO
    # ══════════════════════════════════════════════════════════════════════

    SAVE_FILE  = "orario.json"
    GIORNI     = ["Lunedì","Martedì","Mercoledì","Giovedì","Venerdì"]
    MAX_ORE    = {"Lunedì":7,"Martedì":6,"Mercoledì":6,"Giovedì":6,"Venerdì":7}
    MESI_NOMI  = ["","Gennaio","Febbraio","Marzo","Aprile","Maggio","Giugno",
                "Luglio","Agosto","Settembre","Ottobre","Novembre","Dicembre"]
    MESI_OPTS  = [f"{i} - {MESI_NOMI[i]}" for i in range(1, 13)]
    LIGHT      = {"Educazione Fisica","Religione","Arte","Musica"}
    LAB        = {"Sistemi e Reti","Informatica","Telecomunicazioni","Fisica","Chimica","Scienze"}

    # ── Persistenza ──────────────────────────────────────────────────────

    def _empty():
        return {
            "orario": {},
            "verifiche": [],
            "interrogazioni": [],
            "registro": {}   # chiave: "YYYY-MM-DD" → {argomenti, compiti, assenti:[]}
        }

    def carica_orario():
        if os.path.exists(SAVE_FILE):
            try:
                d = json.load(open(SAVE_FILE, encoding="utf-8"))
                if "classi" not in d:
                    cl = d.get("classe", "4G")
                    d  = {"classi": {cl: {"orario": d.get("orario", {}),
                                        "verifiche": d.get("verifiche", []),
                                        "interrogazioni": d.get("interrogazioni", []),
                                        "registro": d.get("registro", {})}},
                        "ultima_classe": cl}
                for data in d["classi"].values():
                    data["orario"] = {
                        g: {int(h): (v if isinstance(v, dict) else {"materia": str(v), "prof": ""})
                            for h, v in ore.items()}
                        for g, ore in data.get("orario", {}).items()
                    }
                    data.setdefault("verifiche", [])
                    data.setdefault("interrogazioni", [])
                    data.setdefault("registro", {})
                return d
            except:
                pass
        return {"classi": {}, "ultima_classe": ""}

    def salva_orario(r):
        json.dump(r, open(SAVE_FILE, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

    def cls_data(r, c):
        r["classi"].setdefault(c, _empty())
        d = r["classi"][c]
        d.setdefault("registro", {})
        return d

    def chiave_data(dt: date) -> str:
        return dt.strftime("%Y-%m-%d")

    def get_registro_giorno(state: dict, dt: date) -> dict:
        k = chiave_data(dt)
        state["registro"].setdefault(k, {"argomenti": "", "compiti": "", "assenti": []})
        return state["registro"][k]

    # ── AI calendario ────────────────────────────────────────────────────

    def call_ollama(prompt, system="Sei un assistente scolastico. Rispondi brevemente in italiano."):
        import json as j
        try:
            payload = j.dumps({
                "model": "llama3",
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user",   "content": prompt}
                ],
                "stream": False
            }).encode()
            req = urllib.request.Request(
                "http://localhost:11434/api/chat",
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            return j.loads(urllib.request.urlopen(req, timeout=30).read())["message"]["content"]
        except urllib.error.URLError:
            return "⚠️ Ollama non raggiungibile — avvia con: ollama serve"
        except Exception as ex:
            return f"⚠️ {ex.__class__.__name__}: {str(ex)[:100]}"

    # ── Logica orario ────────────────────────────────────────────────────

    def peso(state, g):
        day = state["orario"].get(g, {})
        n   = MAX_ORE[g]
        mat = [day.get(h, {}).get("materia", "").strip() for h in range(1, n+1)]
        edge_pen = sum(1.2 for idx in [0, n-1]
                    if idx < len(mat) and mat[idx] and mat[idx] not in LIGHT)
        filled = [m for m in mat if m]
        n_l = sum(1 for m in filled if m in LIGHT)
        n_b = sum(1 for m in filled if m in LAB)
        mx, cu, cm = 0, 0, ""
        for m in filled:
            if m not in LIGHT and m not in LAB:
                cu = cu+1 if m == cm else 1; cm = m; mx = max(mx, cu)
            else:
                cu, cm = 0, ""
        p = n - n_l - n_b*0.5 + mx*0.8 + edge_pen
        for v in state.get("verifiche", []):
            if v.get("giorno_settimana") == g: p += 2
        for i in state.get("interrogazioni", []):
            for gg in i.get("assegnazioni", {}).values():
                if gg == g: p += 1
        return round(p, 2)

    def giorni_mat(state, mat):
        return [g for g in GIORNI
                if any(state["orario"].get(g, {}).get(h, {}).get("materia") == mat
                    for h in range(1, MAX_ORE[g]+1))]

    def g_nome(dt):
        return ["Lunedì","Martedì","Mercoledì","Giovedì","Venerdì","Sabato","Domenica"][dt.weekday()]

    def date_periodo(state, mat, im, ig, fm, fg):
        oggi = date.today()
        try:
            ini = date(oggi.year, im, ig)
            fin = date(oggi.year, fm, fg)
            if fin < ini: fin = date(oggi.year+1, fm, fg)
        except:
            return []
        gm  = set(giorni_mat(state, mat))
        res, cur = [], ini
        while cur <= fin:
            gn = g_nome(cur)
            if gn in gm: res.append((cur, gn))
            cur += timedelta(days=1)
        return res

    def parse_data(testo, oggi):
        t = testo.lower()
        if "domani"     in t: return oggi + timedelta(1)
        if "dopodomani" in t: return oggi + timedelta(2)
        if "oggi"       in t: return oggi
        mesi = {"gennaio":1,"febbraio":2,"marzo":3,"aprile":4,"maggio":5,"giugno":6,
                "luglio":7,"agosto":8,"settembre":9,"ottobre":10,"novembre":11,"dicembre":12}
        for nome, num in mesi.items():
            if nome in t:
                for p in t.split():
                    if p.isdigit():
                        a = oggi.year if num >= oggi.month else oggi.year+1
                        try: return date(a, num, int(p))
                        except: pass
        return None

    # ── Widget UI helpers ─────────────────────────────────────────────────

    def cal_section(title, icon, content, accent=ACCENT_BLUE):
        return ft.Container(
            padding=ft.padding.symmetric(horizontal=16, vertical=12),
            border_radius=BORDER_RADIUS, bgcolor=SECONDARY_BG,
            border=ft.border.all(1, BORDER_COLOR_LIGHT),
            content=ft.Column([
                ft.Row([
                    ft.Container(width=4, height=20, border_radius=2, bgcolor=accent),
                    ft.Text(f"{icon}  {title}", size=13, weight="bold", color=TEXT_PRIMARY)
                ], spacing=8),
                ft.Divider(color=BORDER_COLOR, height=1),
                content
            ], spacing=10, tight=True))

    def cal_tf(label, width=None, value="", expand=False, kb=None, multiline=False, min_lines=1, max_lines=3):
        kw = dict(label=label, value=value, color=TEXT_PRIMARY,
                label_style=ft.TextStyle(color=TEXT_MUTED, size=11),
                border_color=BORDER_COLOR_LIGHT, focused_border_color=ACCENT_BLUE,
                border_radius=10,
                content_padding=ft.padding.symmetric(horizontal=12, vertical=8),
                text_size=12,
                multiline=multiline, min_lines=min_lines, max_lines=max_lines)
        if width:  kw["width"]  = width
        if expand: kw["expand"] = True
        if kb:     kw["keyboard_type"] = kb
        return ft.TextField(**kw)

    def cal_drop(label, opts, width=None, expand=False):
        kw = dict(label=label,
                options=[ft.dropdown.Option(o) for o in opts],
                color=TEXT_PRIMARY,
                label_style=ft.TextStyle(color=TEXT_MUTED, size=11),
                border_color=BORDER_COLOR_LIGHT,
                focused_border_color=ACCENT_BLUE,
                border_radius=10)
        if width:  kw["width"]  = width
        if expand: kw["expand"] = True
        return ft.Dropdown(**kw)

    def pill(text, on_click, color=ACCENT_BLUE):
        return ft.FilledButton(text, on_click=on_click,
            style=ft.ButtonStyle(bgcolor=color, color="#ffffff",
                shape=ft.RoundedRectangleBorder(radius=20),
                padding=ft.padding.symmetric(horizontal=16, vertical=8)))

    def badge(text, color):
        return ft.Container(
            padding=ft.padding.symmetric(horizontal=10, vertical=3),
            border_radius=20, bgcolor=color+"25", border=ft.border.all(1, color+"60"),
            content=ft.Text(text, size=9, color=color, weight="bold"))

    def info_box(text, color=ACCENT_BLUE):
        return ft.Container(padding=10, border_radius=12, bgcolor=color+"18",
            border=ft.border.all(1, color+"40"),
            content=ft.Text(text, size=10, color=color))

    def ai_consiglio_box(lines_ok, lines_no):
        controls = [ft.Text("💡 Consiglio AI", size=11, weight="bold", color="#ffffff")]
        for l in lines_ok:
            controls.append(ft.Container(
                padding=ft.padding.symmetric(horizontal=8, vertical=5), border_radius=8,
                bgcolor=ACCENT_GREEN,
                content=ft.Text(l, size=10, color="#031a08", weight="bold")))
        for l in lines_no:
            controls.append(ft.Text(l, size=9, color="#8ab4d4"))
        return ft.Container(padding=12, border_radius=12, bgcolor="#071510",
            border=ft.border.all(1, ACCENT_GREEN),
            content=ft.Column(controls, spacing=5, tight=True))

    def classe_chip(label, selected, on_click):
        return ft.FilledButton(label, on_click=on_click,
            style=ft.ButtonStyle(
                bgcolor=ACCENT_BLUE+"30" if selected else CARD_BG,
                color=TEXT_PRIMARY,
                shape=ft.RoundedRectangleBorder(radius=16),
                padding=ft.padding.symmetric(horizontal=12, vertical=5)))

    def classe_selector(current, classi_list, on_change, page):
        inp = cal_tf("Classe", width=130, value=current)
        inp.on_submit = lambda e: on_change(inp.value.strip().upper())
        inp.on_blur   = lambda e: on_change(inp.value.strip().upper())
        chips_row = ft.Row(
            [classe_chip(c, c == current, lambda e, c=c: on_change(c)) for c in classi_list],
            spacing=5, wrap=True)
        return ft.Container(
            padding=ft.padding.symmetric(horizontal=16, vertical=12),
            border_radius=BORDER_RADIUS, bgcolor=SECONDARY_BG,
            border=ft.border.all(1, ACCENT_CYAN+"40"),
            content=ft.Column([
                ft.Row([
                    ft.Container(width=4, height=20, border_radius=2, bgcolor=ACCENT_CYAN),
                    ft.Text(f"{ICON_CLASS}  Classe", size=13, weight="bold", color=TEXT_PRIMARY),
                    ft.Container(expand=True),
                    ft.Text("Dati caricati ✓" if current in classi_list else "Nuova classe",
                            size=9, color=ACCENT_GREEN if current in classi_list else ACCENT_YELLOW)
                ], spacing=8),
                ft.Divider(color=BORDER_COLOR, height=1),
                ft.Row([inp, ft.Text("← Invio per cambiare", size=9, color=TEXT_MUTED)],
                    spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                chips_row if classi_list else ft.Container(height=0),
            ], spacing=8, tight=True))

    def build_cal(state, anno, mese, cell=52, on_day_click=None):
        """
        Costruisce il widget calendario mensile.
        on_day_click: callable(date) oppure None
        """
        oggi = date.today()
        ev   = {}
        for v in state.get("verifiche", []):
            if v.get("mese") == mese and v.get("giorno_num"):
                ev.setdefault(v["giorno_num"], []).append(("V", v.get("materia", "")))
        for i in state.get("interrogazioni", []):
            mat = i.get("materia", "")
            im, ig = i.get("inizio_mese"), i.get("inizio_giorno")
            fm, fg = i.get("fine_mese"),   i.get("fine_giorno")
            if not all([im, ig, fm, fg]): continue
            for nome_s, giorno_sett in i.get("assegnazioni", {}).items():
                try:
                    ini = date(anno, im, ig); fin = date(anno, fm, fg)
                    if fin < ini: fin = date(anno+1, fm, fg)
                    cur = ini
                    while cur <= fin:
                        if cur.year == anno and cur.month == mese and g_nome(cur) == giorno_sett:
                            ev.setdefault(cur.day, []).append(("I", f"{mat}"))
                        cur += timedelta(days=1)
                except:
                    pass

        # Giorni con registro compilato
        reg_giorni = set()
        for k in state.get("registro", {}):
            try:
                rd = date.fromisoformat(k)
                if rd.year == anno and rd.month == mese:
                    r = state["registro"][k]
                    if r.get("argomenti") or r.get("compiti") or r.get("assenti"):
                        reg_giorni.add(rd.day)
            except:
                pass

        ts  = max(10, int(cell*0.22))
        hdr = ft.Row([
            ft.Container(width=cell,
                        content=ft.Text(n, size=8, color=TEXT_MUTED,
                                        text_align=ft.TextAlign.CENTER, weight="bold"))
            for n in ["L","M","M","G","V","S","D"]
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
                tooltip_parts = [("📝 " if t=="V" else "🎤 ")+m for t, m in evs]
                if has_R: tooltip_parts.append("📖 Registro compilato")
                tooltip = "\n".join(tooltip_parts) if tooltip_parts else ""
                dots = ft.Row([
                    ft.Container(width=6, height=6, border_radius=3, bgcolor=ACCENT_RED)    if has_V else ft.Container(),
                    ft.Container(width=6, height=6, border_radius=3, bgcolor=ACCENT_PURPLE) if has_I else ft.Container(),
                    ft.Container(width=6, height=6, border_radius=3, bgcolor=ACCENT_CYAN)   if has_R else ft.Container(),
                ], spacing=2, alignment=ft.MainAxisAlignment.CENTER)
                bg  = ACCENT_BLUE if is_today else ("#1c2a42" if wi >= 5 else CARD_BG if d != 0 else "transparent")
                brd = (ft.border.all(2, ACCENT_BLUE) if is_today else
                    ft.border.all(1, ACCENT_RED+"80") if has_V else
                    ft.border.all(1, ACCENT_CYAN+"80") if has_R else
                    ft.border.all(1, ACCENT_PURPLE+"60") if has_I else None)

                dt_obj = date(anno, mese, d) if d != 0 else None
                def _click(e, _dt=dt_obj):
                    if _dt and on_day_click: on_day_click(_dt)

                cells.append(ft.Container(
                    width=cell, height=cell, border_radius=10, bgcolor=bg, border=brd,
                    tooltip=tooltip,
                    on_click=_click if (d != 0 and on_day_click) else None,
                    ink=True if (d != 0 and on_day_click) else False,
                    content=ft.Column([
                        ft.Text(str(d) if d != 0 else "", size=ts,
                                color=TEXT_PRIMARY if is_today else TEXT_MUTED if wi >= 5 else TEXT_SECONDARY,
                                weight="bold" if is_today else None,
                                text_align=ft.TextAlign.CENTER),
                        dots
                    ], spacing=2,
                    alignment=ft.MainAxisAlignment.CENTER,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER)))
            rows.append(ft.Row(cells, spacing=3))
        return ft.Column([
            ft.Column(rows, spacing=4), ft.Container(height=4),
            ft.Row([
                ft.Container(width=8, height=8, border_radius=4, bgcolor=ACCENT_RED),
                ft.Text("Verifica", size=9, color=TEXT_MUTED),
                ft.Container(width=10),
                ft.Container(width=8, height=8, border_radius=4, bgcolor=ACCENT_PURPLE),
                ft.Text("Interr.", size=9, color=TEXT_MUTED),
                ft.Container(width=10),
                ft.Container(width=8, height=8, border_radius=4, bgcolor=ACCENT_CYAN),
                ft.Text("Registro", size=9, color=TEXT_MUTED),
            ], spacing=5),
        ], spacing=0, horizontal_alignment=ft.CrossAxisAlignment.CENTER)


    # ══════════════════════════════════════════════════════════════════════
    # PANNELLO REGISTRO GIORNALIERO — DOCENTE
    # ══════════════════════════════════════════════════════════════════════

    def build_registro_docente_panel(state, dt: date, page, on_save):
        """
        Ritorna un Container con il form per compilare il registro del giorno dt.
        on_save: callable() → viene chiamato dopo il salvataggio per aggiornare la UI
        """
        reg    = get_registro_giorno(state, dt)
        gn     = g_nome(dt)
        ore_dt = state["orario"].get(gn, {})
        mats_oggi = list({ore_dt.get(h, {}).get("materia", "").strip()
                        for h in range(1, MAX_ORE.get(gn, 6)+1)
                        if ore_dt.get(h, {}).get("materia", "").strip()})

        label_data = ft.Text(
            f"📖 Registro — {gn} {dt.strftime('%d/%m/%Y')}",
            size=14, weight="bold", color=TEXT_PRIMARY)

        # --- Argomenti ---
        tf_arg = cal_tf("Argomenti spiegati", expand=True,
                        value=reg.get("argomenti", ""),
                        multiline=True, min_lines=2, max_lines=5)

        # --- Compiti ---
        tf_comp = cal_tf("Compiti assegnati", expand=True,
                        value=reg.get("compiti", ""),
                        multiline=True, min_lines=2, max_lines=4)

        # --- Assenti ---
        tf_nuovo_assente = cal_tf("Nome studente assente", width=220)

        assenti_list_col = ft.Column(spacing=4)

        def refresh_assenti():
            assenti_list_col.controls.clear()
            for nome in reg.get("assenti", []):
                def rimuovi(e, n=nome):
                    if n in reg["assenti"]: reg["assenti"].remove(n)
                    refresh_assenti(); page.update()
                assenti_list_col.controls.append(ft.Row([
                    ft.Container(
                        padding=ft.padding.symmetric(horizontal=10, vertical=4),
                        border_radius=16, bgcolor=ACCENT_RED+"20",
                        border=ft.border.all(1, ACCENT_RED+"50"),
                        content=ft.Text(nome, size=11, color=TEXT_PRIMARY)),
                    ft.IconButton(ft.Icons.CLOSE, icon_color=ACCENT_RED, icon_size=14,
                                on_click=rimuovi)
                ], spacing=4))
            page.update()

        def aggiungi_assente(e):
            nome = tf_nuovo_assente.value.strip()
            if not nome: return
            reg.setdefault("assenti", [])
            if nome not in reg["assenti"]:
                reg["assenti"].append(nome)
            tf_nuovo_assente.value = ""
            refresh_assenti()

        tf_nuovo_assente.on_submit = aggiungi_assente
        refresh_assenti()

        # --- Salva ---
        stato_salv = ft.Text("", size=10, color=ACCENT_GREEN)

        def salva(e):
            reg["argomenti"] = tf_arg.value.strip()
            reg["compiti"]   = tf_comp.value.strip()
            # assenti già aggiornati live
            salva_orario
            stato_salv.value = "✅ Salvato!"; page.update()
            on_save()
            import threading as _t
            def _clear():
                import time; time.sleep(2)
                stato_salv.value = ""; page.update()
            _t.Thread(target=_clear, daemon=True).start()

        row_assenti_input = ft.Row([
            tf_nuovo_assente,
            pill("➕ Aggiungi", aggiungi_assente, color=ACCENT_RED)
        ], spacing=8, vertical_alignment=ft.CrossAxisAlignment.END)

        # Materie del giorno come info
        mat_chips = ft.Row(
            [badge(m, SUBJECTS_PALETTE.get(m, SUBJECTS_PALETTE["default"])["accent"])
            for m in mats_oggi] if mats_oggi else [ft.Text("Nessuna materia in orario", size=9, color=TEXT_MUTED)],
            spacing=6, wrap=True)

        return ft.Container(
            padding=ft.padding.symmetric(horizontal=16, vertical=14),
            border_radius=BORDER_RADIUS,
            bgcolor=SECONDARY_BG,
            border=ft.border.all(2, ACCENT_CYAN+"60"),
            content=ft.Column([
                label_data,
                ft.Row([ft.Text("Materie oggi:", size=10, color=TEXT_MUTED), mat_chips], spacing=8, wrap=True),
                ft.Divider(color=BORDER_COLOR, height=1),

                ft.Text("📚 Argomenti spiegati", size=11, weight="bold", color=ACCENT_CYAN),
                tf_arg,

                ft.Text("📝 Compiti assegnati", size=11, weight="bold", color=ACCENT_YELLOW),
                tf_comp,

                ft.Text("🙋 Assenti", size=11, weight="bold", color=ACCENT_RED),
                row_assenti_input,
                assenti_list_col,

                ft.Divider(color=BORDER_COLOR, height=1),
                ft.Row([
                    pill(f"{ICON_SAVE} Salva registro", salva, color=ACCENT_GREEN),
                    stato_salv
                ], spacing=12, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            ], spacing=10, tight=True))


    # ══════════════════════════════════════════════════════════════════════
    # PANNELLO REGISTRO GIORNALIERO — STUDENTE
    # ══════════════════════════════════════════════════════════════════════

    def build_registro_studente_panel(state, dt: date, nome_studente: str, page):
        """
        Ritorna un Container con la vista del registro per lo studente.
        """
        reg = get_registro_giorno(state, dt)
        gn  = g_nome(dt)

        era_presente = nome_studente not in reg.get("assenti", [])
        presenza_col = ACCENT_GREEN if era_presente else ACCENT_RED
        presenza_txt = "✅ Presente" if era_presente else "❌ Assente"

        argomenti = reg.get("argomenti", "").strip() or "—"
        compiti   = reg.get("compiti",   "").strip() or "—"

        ore_dt = state["orario"].get(gn, {})
        mats_oggi = list({ore_dt.get(h, {}).get("materia", "").strip()
                        for h in range(1, MAX_ORE.get(gn, 6)+1)
                        if ore_dt.get(h, {}).get("materia", "").strip()})
        mat_chips = ft.Row(
            [badge(m, SUBJECTS_PALETTE.get(m, SUBJECTS_PALETTE["default"])["accent"])
            for m in mats_oggi] if mats_oggi else [ft.Text("—", size=9, color=TEXT_MUTED)],
            spacing=6, wrap=True)

        return ft.Container(
            padding=ft.padding.symmetric(horizontal=16, vertical=14),
            border_radius=BORDER_RADIUS,
            bgcolor=SECONDARY_BG,
            border=ft.border.all(2, ACCENT_CYAN+"60"),
            content=ft.Column([
                ft.Text(f"📖 Registro — {gn} {dt.strftime('%d/%m/%Y')}",
                        size=14, weight="bold", color=TEXT_PRIMARY),
                ft.Row([ft.Text("Materie:", size=10, color=TEXT_MUTED), mat_chips], spacing=8, wrap=True),
                ft.Divider(color=BORDER_COLOR, height=1),

                # Presenza
                ft.Container(
                    padding=ft.padding.symmetric(horizontal=14, vertical=8),
                    border_radius=12,
                    bgcolor=presenza_col+"18",
                    border=ft.border.all(1, presenza_col+"50"),
                    content=ft.Row([
                        ft.Text(presenza_txt, size=13, weight="bold", color=presenza_col),
                    ], spacing=8)),

                # Argomenti
                ft.Text("📚 Argomenti spiegati", size=11, weight="bold", color=ACCENT_CYAN),
                ft.Container(
                    padding=10, border_radius=10,
                    bgcolor=ACCENT_CYAN+"10", border=ft.border.all(1, ACCENT_CYAN+"30"),
                    content=ft.Text(argomenti, size=11, color=TEXT_PRIMARY, selectable=True)),

                # Compiti
                ft.Text("📝 Compiti assegnati", size=11, weight="bold", color=ACCENT_YELLOW),
                ft.Container(
                    padding=10, border_radius=10,
                    bgcolor=ACCENT_YELLOW+"10", border=ft.border.all(1, ACCENT_YELLOW+"30"),
                    content=ft.Text(compiti, size=11, color=TEXT_PRIMARY, selectable=True)),

            ], spacing=10, tight=True))


    # ══════════════════════════════════════════════════════════════════════
    # FUNZIONE PRINCIPALE CALENDARIO
    # ══════════════════════════════════════════════════════════════════════

    def avvia_calendario(page: ft.Page, is_student: bool = True, on_back=None):
        page.controls.clear()
        page.title      = "📅 Calendario Scolastico AI"
        page.bgcolor    = PRIMARY_BG
        page.padding    = 0
        page.update()

        root   = carica_orario()
        oggi   = date.today()
        cal_ym = [oggi.year, oggi.month]
        cur_cl = [root.get("ultima_classe", "") or
                (list(root["classi"].keys())[0] if root["classi"] else "")]

        # Giorno selezionato nel calendario (per aprire il registro)
        selected_day = [None]  # type: list[date|None]

        # ── Pannello registro (cambia in base al giorno cliccato) ─────────
        registro_panel_holder = ft.Column([], spacing=0)

        def apri_registro_docente(dt: date):
            selected_day[0] = dt
            state = cls_data(root, cur_cl[0])
            if g_nome(dt) not in GIORNI:
                registro_panel_holder.controls = [
                    info_box("📅 Questo giorno non è scolastico.", ACCENT_YELLOW)]
                page.update()
                return
            def _on_save():
                salva_orario(root)
                refresh_cal()
            panel = build_registro_docente_panel(state, dt, page, _on_save)
            registro_panel_holder.controls = [panel]
            page.update()

        def apri_registro_studente(dt: date):
            selected_day[0] = dt
            state = cls_data(root, cur_cl[0])
            nome_s = state.get("nome_studente", "Studente")
            if g_nome(dt) not in GIORNI:
                registro_panel_holder.controls = [
                    info_box("📅 Questo giorno non è scolastico.", ACCENT_YELLOW)]
                page.update()
                return
            panel = build_registro_studente_panel(state, dt, nome_s, page)
            registro_panel_holder.controls = [panel]
            page.update()

        # ── Chat panel ────────────────────────────────────────────────────
        chat_msgs = ft.Column(spacing=6, scroll=ft.ScrollMode.AUTO)
        chat_in   = ft.TextField(
            hint_text="Chiedi all'AI...", expand=True,
            border=ft.InputBorder.NONE, bgcolor="transparent", color=TEXT_PRIMARY,
            hint_style=ft.TextStyle(color=TEXT_MUTED), text_size=12)
        chat_spin = ft.ProgressRing(width=16, height=16, stroke_width=2,
                                    color=ACCENT_BLUE, visible=False)

        def add_msg(txt, ai=False):
            bubble = ft.Container(
                width=220, padding=10, border_radius=14,
                bgcolor=ChatMessageStyle.ai_bg if ai else ChatMessageStyle.user_bg,
                border=ft.border.all(1, BORDER_COLOR_LIGHT),
                content=ft.Text(txt, size=10, color=TEXT_PRIMARY, selectable=True))
            chat_msgs.controls.append(
                ft.Row([ft.Text("🤖", size=14), bubble] if ai else [bubble],
                    alignment=ft.MainAxisAlignment.START if ai else ft.MainAxisAlignment.END,
                    spacing=6))
            page.update()

        def chat_send(e=None):
            q = (chat_in.value or "").strip()
            if not q: return
            add_msg(q); chat_in.value = ""; chat_spin.visible = True; page.update()
            state = cls_data(root, cur_cl[0])
            def fetch():
                dt = parse_data(q, oggi)
                if dt:
                    gn = g_nome(dt)
                    if gn in GIORNI:
                        mat = [state["orario"].get(gn, {}).get(h, {}).get("materia", "—")
                            for h in range(1, MAX_ORE[gn]+1)]
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
                        f"{g}: {', '.join(state['orario'].get(g,{}).get(h,{}).get('materia','') for h in range(1,MAX_ORE[g]+1))}"
                        for g in GIORNI)
                    resp = call_ollama(
                        q,
                        f"Assistente scolastico. Classe:{cur_cl[0]}.\nOrario:\n{orario_txt}\nRispondi brevemente in italiano.")
                chat_spin.visible = False; add_msg(resp, ai=True)
            threading.Thread(target=fetch, daemon=True).start()
        chat_in.on_submit = chat_send

        chat_panel = ft.Container(
            width=CHAT_SIDEBAR_WIDTH, bgcolor=SECONDARY_BG,
            border=ft.border.only(left=ft.BorderSide(1, BORDER_COLOR)), padding=14,
            content=ft.Column([
                ft.Row([ft.Text("🤖", size=18),
                        ft.Text("Assistente AI", size=13, weight="bold", color=TEXT_PRIMARY)],
                    spacing=8),
                ft.Divider(color=BORDER_COLOR, height=1),
                ft.Container(expand=True,
                            content=ft.Column([chat_msgs], scroll=ft.ScrollMode.AUTO)),
                ft.Row([chat_spin], alignment=ft.MainAxisAlignment.CENTER),
                ft.Container(
                    border_radius=12, bgcolor=CARD_BG,
                    border=ft.border.all(1, BORDER_COLOR_LIGHT),
                    padding=ft.padding.symmetric(horizontal=10, vertical=6),
                    content=ft.Row([
                        chat_in,
                        ft.IconButton(ft.Icons.SEND_ROUNDED, icon_color=ACCENT_BLUE,
                                    icon_size=18, on_click=chat_send)
                    ], spacing=4))
            ], spacing=8, expand=True))

        # ── Calendario widget ─────────────────────────────────────────────
        cal_body = ft.Column([], spacing=0, horizontal_alignment=ft.CrossAxisAlignment.CENTER)
        cal_lbl  = ft.Text("", size=15, weight="bold", color=TEXT_PRIMARY)

        def refresh_cal(large=False):
            st = cls_data(root, cur_cl[0]) if cur_cl[0] else _empty()
            on_click_fn = apri_registro_docente if not is_student else apri_registro_studente
            cal_body.controls = [build_cal(st, cal_ym[0], cal_ym[1],
                                        cell=54 if large else 42,
                                        on_day_click=on_click_fn)]
            cal_lbl.value = f"{MESI_NOMI[cal_ym[1]]}  {cal_ym[0]}"
            page.update()

        def nav_cal(d):
            m, y = cal_ym[1]+d, cal_ym[0]
            if m > 12: m, y = 1, y+1
            elif m < 1: m, y = 12, y-1
            cal_ym[0], cal_ym[1] = y, m
            refresh_cal(large=is_student)

        cal_widget = ft.Container(
            bgcolor=SECONDARY_BG, border=ft.border.all(1, BORDER_COLOR_LIGHT),
            border_radius=BORDER_RADIUS,
            padding=ft.padding.symmetric(horizontal=14, vertical=14),
            content=ft.Column([
                ft.Row([
                    ft.IconButton(ft.Icons.CHEVRON_LEFT, icon_color=ACCENT_BLUE,
                                icon_size=20, on_click=lambda e: nav_cal(-1)),
                    ft.Container(expand=True,
                                content=ft.Row([cal_lbl], alignment=ft.MainAxisAlignment.CENTER)),
                    ft.IconButton(ft.Icons.CHEVRON_RIGHT, icon_color=ACCENT_BLUE,
                                icon_size=20, on_click=lambda e: nav_cal(1)),
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                cal_body,
            ], spacing=10, horizontal_alignment=ft.CrossAxisAlignment.CENTER))

        # ── Topbar ────────────────────────────────────────────────────────
        def torna_home(e):
            if on_back: on_back()

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
                        ft.Text("AI-powered", size=9, color=ACCENT_CYAN)
                    ], spacing=0)
                ], spacing=10),
                ft.Container(expand=True),
                badge(f"{'👨‍🎓 Studente' if is_student else '👨‍🏫 Professore'}", ACCENT_BLUE),
                ft.Container(width=8),
                ft.TextButton(
                    f"{ICON_RESET} Aggiorna",
                    on_click=lambda e: (build_student if is_student else build_prof)(),
                    style=ft.ButtonStyle(color=TEXT_MUTED,
                                        shape=ft.RoundedRectangleBorder(radius=20),
                                        padding=ft.padding.symmetric(horizontal=12, vertical=6))),
                ft.Container(width=8),
                ft.TextButton(
                    "🏠 Home",
                    on_click=torna_home,
                    style=ft.ButtonStyle(color=ACCENT_CYAN,
                                        shape=ft.RoundedRectangleBorder(radius=20),
                                        padding=ft.padding.symmetric(horizontal=12, vertical=6))),
            ], vertical_alignment=ft.CrossAxisAlignment.CENTER))

        # ══════════════════════════════════════════════════════════════════
        # VISTA PROFESSORE
        # ══════════════════════════════════════════════════════════════════

        prof_scroll = ft.Column(spacing=14, scroll=ft.ScrollMode.AUTO, expand=True)

        def build_prof():
            prof_scroll.controls.clear()
            cl    = cur_cl[0]
            state = cls_data(root, cl)
            mats  = sorted({e.get("materia", "") for d in state["orario"].values()
                            for e in d.values() if e.get("materia")})

            def on_cl(nuova):
                if not nuova: return
                cur_cl[0] = nuova; root["ultima_classe"] = nuova
                salva_orario(root); build_prof()

            prof_scroll.controls.append(
                classe_selector(cl, list(root["classi"].keys()), on_cl, page))

            tab_body = ft.Column([], spacing=5, scroll=ft.ScrollMode.AUTO, height=220)
            tab_row  = ft.Row([], spacing=4, wrap=True)

            def make_rows(g):
                dd = state["orario"].setdefault(g, {})
                rows = []
                for h in range(1, MAX_ORE[g]+1):
                    si = cal_tf(f"{h}ª Materia", width=190, value=dd.get(h, {}).get("materia", ""))
                    pi = cal_tf("Prof",           width=150, value=dd.get(h, {}).get("prof", ""))
                    def sv(e, _g=g, _h=h, _s=si, _p=pi):
                        state["orario"].setdefault(_g, {})[_h] = {
                            "materia": _s.value.strip(), "prof": _p.value.strip()}
                        salva_orario(root)
                    si.on_change = sv; pi.on_change = sv
                    rows.append(ft.Row([si, pi], spacing=8))
                return rows

            def switch(g):
                tab_body.controls = make_rows(g)
                for b in tab_row.controls:
                    b.style = ft.ButtonStyle(
                        bgcolor=ACCENT_BLUE if b.data == g else CARD_BG,
                        color=TEXT_PRIMARY,
                        shape=ft.RoundedRectangleBorder(radius=16),
                        padding=ft.padding.symmetric(horizontal=12, vertical=6))
                page.update()

            for g in GIORNI:
                tab_row.controls.append(ft.FilledButton(
                    g[:3], data=g, on_click=lambda e: switch(e.control.data),
                    style=ft.ButtonStyle(
                        bgcolor=ACCENT_BLUE if g == GIORNI[0] else CARD_BG,
                        color=TEXT_PRIMARY,
                        shape=ft.RoundedRectangleBorder(radius=16),
                        padding=ft.padding.symmetric(horizontal=12, vertical=6))))
            tab_body.controls = make_rows(GIORNI[0])
            prof_scroll.controls.append(
                cal_section("Orario Classe", "📋",
                            ft.Column([tab_row, tab_body], spacing=10)))

            # ── Registro giornaliero (pannello placeholder) ───────────────
            hint_registro = ft.Container(
                padding=ft.padding.symmetric(horizontal=14, vertical=12),
                border_radius=BORDER_RADIUS, bgcolor=TERTIARY_BG,
                border=ft.border.all(1, ACCENT_CYAN+"40"),
                content=ft.Column([
                    ft.Row([ft.Text("📖", size=18),
                            ft.Text("Registro Giornaliero", size=13, weight="bold", color=TEXT_PRIMARY)],
                        spacing=8),
                    ft.Text("Clicca su un giorno del calendario per aprire il registro.",
                            size=11, color=TEXT_MUTED),
                    registro_panel_holder,
                ], spacing=10, tight=True))
            prof_scroll.controls.append(hint_registro)

            # ── Verifiche ─────────────────────────────────────────────────
            mv = cal_drop("Materia", mats, width=170)
            vg = cal_tf("Gg", width=70, kb=ft.KeyboardType.NUMBER)
            vm = cal_drop("Mese", MESI_OPTS, width=165)
            vc = cal_tf("Classe", width=90, value=cl)
            vt = cal_tf("Tipo",   width=110, value="Scritto")
            ai_vbox = ft.Container(visible=False)

            def vmat_chg(e):
                if not mv.value: ai_vbox.visible = False; page.update(); return
                glist = giorni_mat(state, mv.value)
                if not glist: ai_vbox.visible = False; page.update(); return
                pesi = sorted([(g, peso(state, g)) for g in glist], key=lambda x: x[1])
                best = pesi[0][0]
                ai_vbox.content = ai_consiglio_box(
                    [f"✔ {best} — peso {pesi[0][1]}  ← CONSIGLIATO"],
                    [f"  {g} — peso {p}" for g, p in pesi[1:]] + ["(Scegli la data che preferisci)"])
                ai_vbox.visible = True; page.update()
            mv.on_change = vmat_chg

            def add_v(e):
                if not mv.value or not vg.value or not vm.value: return
                try:
                    gn = int(vg.value); mn = int(vm.value.split(" - ")[0])
                    dt = date(oggi.year, mn, gn); gs = g_nome(dt)
                except:
                    return
                state["verifiche"].append({
                    "materia": mv.value, "giorno_num": gn, "mese": mn,
                    "giorno_settimana": gs, "classe": vc.value.strip(), "tipo": vt.value})
                vg.value = ""; vm.value = None
                salva_orario(root); build_prof(); refresh_cal()

            vlist = ft.Column(spacing=5)
            for v in sorted(state["verifiche"],
                            key=lambda x: (x.get("mese", 0), x.get("giorno_num", 0))):
                pal = SUBJECTS_PALETTE.get(v.get("materia"), SUBJECTS_PALETTE["default"])
                try:
                    ds = (date(oggi.year, v["mese"], v["giorno_num"]).strftime("%d %b") +
                        f" ({v['giorno_settimana']})")
                except:
                    ds = "?"
                def del_v(e, _v=v):
                    state["verifiche"].remove(_v); salva_orario(root); build_prof(); refresh_cal()
                vlist.controls.append(ft.Container(
                    padding=ft.padding.symmetric(horizontal=12, vertical=8),
                    border_radius=12, bgcolor=pal["bg"],
                    border=ft.border.all(1, pal["accent"]+"60"),
                    content=ft.Row([
                        ft.Text("📝", size=14),
                        ft.Column([
                            ft.Text(v.get("materia"), size=11, color=TEXT_PRIMARY, weight="bold"),
                            ft.Text(f"{ds} · classe {v.get('classe','')} · {v.get('tipo','')}",
                                    size=9, color=TEXT_SECONDARY)
                        ], spacing=1, expand=True),
                        ft.IconButton(ft.Icons.DELETE_OUTLINE, icon_color=ACCENT_RED,
                                    icon_size=16, on_click=del_v)
                    ], spacing=10)))

            prof_scroll.controls.append(cal_section("Verifiche", "📝", ft.Column([
                ft.Row([mv], spacing=8), ai_vbox,
                ft.Row([
                    ft.Column([ft.Text("Data", size=10, color=TEXT_MUTED),
                            ft.Row([vg, vm], spacing=6)], spacing=4),
                    ft.Column([ft.Text("Classe / Tipo", size=10, color=TEXT_MUTED),
                            ft.Row([vc, vt], spacing=6)], spacing=4),
                ], spacing=16),
                pill(f"{ICON_PLUS} Aggiungi Verifica", add_v),
                ft.Divider(color=BORDER_COLOR, height=1), vlist
            ], spacing=10), accent=ACCENT_RED))

            # ── Interrogazioni ─────────────────────────────────────────────
            mi  = cal_drop("Materia", mats, width=170)
            ig_ = cal_tf("Gg inizio", width=75, kb=ft.KeyboardType.NUMBER)
            im_ = cal_drop("Mese inizio", MESI_OPTS, width=165)
            fg_ = cal_tf("Gg fine",   width=75, kb=ft.KeyboardType.NUMBER)
            fm_ = cal_drop("Mese fine",   MESI_OPTS, width=165)
            ai_ibox = ft.Container(visible=False)

            def imat_chg(e):
                if not mi.value: ai_ibox.visible = False; page.update(); return
                glist = giorni_mat(state, mi.value)
                if not glist: ai_ibox.visible = False; page.update(); return
                pesi = sorted([(g, peso(state, g)) for g in glist], key=lambda x: x[1])
                best = pesi[0][0]
                ai_ibox.content = ai_consiglio_box(
                    [f"✔ {best} — peso {pesi[0][1]}  ← GIORNO CONSIGLIATO"],
                    [f"  {g} — peso {p}" for g, p in pesi[1:]] + ["(Puoi impostare il periodo liberamente)"])
                ai_ibox.visible = True; page.update()
            mi.on_change = imat_chg

            def apri_i(e):
                if not mi.value: return
                try:
                    im = int(im_.value.split(" - ")[0]); ig = int(ig_.value)
                    fm = int(fm_.value.split(" - ")[0]); fg = int(fg_.value)
                    date(oggi.year, im, ig); date(oggi.year, fm, fg)
                except:
                    add_msg("⚠️ Date non valide", ai=True); return
                if any(i.get("materia") == mi.value for i in state["interrogazioni"]):
                    add_msg(f"⚠️ Periodo già attivo per {mi.value}", ai=True); return
                state["interrogazioni"].append({
                    "id": f"{mi.value}_{datetime.now().timestamp()}",
                    "materia": mi.value, "inizio_giorno": ig, "inizio_mese": im,
                    "fine_giorno": fg, "fine_mese": fm, "assegnazioni": {}})
                add_msg(f"✅ Periodo {mi.value}: {ig}/{im} → {fg}/{fm}", ai=True)
                mi.value = None; ig_.value = ""; im_.value = None
                fg_.value = ""; fm_.value = None
                ai_ibox.visible = False
                salva_orario(root); build_prof(); refresh_cal()

            ilist = ft.Column(spacing=5)
            for i in state["interrogazioni"]:
                try:
                    ps = f"{i['inizio_giorno']}/{i['inizio_mese']} → {i['fine_giorno']}/{i['fine_mese']}"
                except:
                    ps = "?"
                def del_i(e, _i=i):
                    state["interrogazioni"].remove(_i)
                    salva_orario(root); build_prof(); refresh_cal()
                ilist.controls.append(ft.Container(
                    padding=ft.padding.symmetric(horizontal=12, vertical=8),
                    border_radius=12, bgcolor=TERTIARY_BG,
                    border=ft.border.all(1, ACCENT_PURPLE+"60"),
                    content=ft.Row([
                        ft.Text("🎤", size=14),
                        ft.Column([
                            ft.Text(i.get("materia"), size=11, color=TEXT_PRIMARY, weight="bold"),
                            ft.Text(f"📆 {ps} · {len(i.get('assegnazioni',{}))} assegnati",
                                    size=9, color=TEXT_SECONDARY)
                        ], spacing=1, expand=True),
                        ft.IconButton(ft.Icons.DELETE_OUTLINE, icon_color=ACCENT_RED,
                                    icon_size=16, on_click=del_i)
                    ], spacing=10)))

            prof_scroll.controls.append(cal_section("Interrogazioni — Periodi", "🎤", ft.Column([
                ft.Row([mi], spacing=8), ai_ibox,
                ft.Row([
                    ft.Container(padding=10, border_radius=12, bgcolor=ACCENT_GREEN+"12",
                        border=ft.border.all(1, ACCENT_GREEN+"40"),
                        content=ft.Column([
                            ft.Text("Data inizio", size=9, color=ACCENT_GREEN, weight="bold"),
                            ft.Row([ig_, im_], spacing=6)], spacing=5)),
                    ft.Container(padding=10, border_radius=12, bgcolor=ACCENT_RED+"12",
                        border=ft.border.all(1, ACCENT_RED+"40"),
                        content=ft.Column([
                            ft.Text("Data fine", size=9, color=ACCENT_RED, weight="bold"),
                            ft.Row([fg_, fm_], spacing=6)], spacing=5)),
                ], spacing=12),
                pill("🎤 Apri Periodo", apri_i, color=ACCENT_PURPLE),
                ft.Divider(color=BORDER_COLOR, height=1), ilist
            ], spacing=10), accent=ACCENT_PURPLE))

            refresh_cal(); page.update()

        # ══════════════════════════════════════════════════════════════════
        # VISTA STUDENTE
        # ══════════════════════════════════════════════════════════════════

        student_scroll = ft.Column(spacing=14, scroll=ft.ScrollMode.AUTO, expand=True)

        def build_student():
            student_scroll.controls.clear()
            cl    = cur_cl[0]
            state = cls_data(root, cl) if cl else _empty()

            def on_cl(nuova):
                if not nuova: return
                cur_cl[0] = nuova; root["ultima_classe"] = nuova
                salva_orario(root); build_student()

            student_scroll.controls.append(
                classe_selector(cl, list(root["classi"].keys()), on_cl, page))

            # ── Nome studente (per presenza) ──────────────────────────────
            nome_s = state.get("nome_studente", "")
            tf_nome = cal_tf("Il mio nome (per le presenze)", width=260, value=nome_s)
            def salva_nome(e):
                state["nome_studente"] = tf_nome.value.strip()
                salva_orario(root)
            tf_nome.on_blur   = salva_nome
            tf_nome.on_submit = salva_nome
            student_scroll.controls.append(
                ft.Container(
                    padding=ft.padding.symmetric(horizontal=16, vertical=10),
                    border_radius=BORDER_RADIUS, bgcolor=SECONDARY_BG,
                    border=ft.border.all(1, ACCENT_PURPLE+"40"),
                    content=ft.Column([
                        ft.Row([ft.Text("👤", size=16),
                                ft.Text("Il mio profilo", size=12, weight="bold", color=TEXT_PRIMARY)],
                            spacing=8),
                        ft.Row([tf_nome,
                                ft.Text("← Invio per salvare", size=9, color=TEXT_MUTED)],
                            spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                    ], spacing=8, tight=True)))

            oggi_g  = g_nome(datetime.today())
            max_h   = max(MAX_ORE.values())
            mini    = [ft.Row(
                [ft.Container(width=32)] + [
                    ft.Container(expand=True, border_radius=6,
                        bgcolor=ACCENT_BLUE+"25" if g == oggi_g else None,
                        content=ft.Text(g[:3], size=8, weight="bold",
                                        color=ACCENT_BLUE if g == oggi_g else TEXT_MUTED,
                                        text_align=ft.TextAlign.CENTER))
                    for g in GIORNI
                ], spacing=2)]

            for h in range(1, max_h+1):
                row = [ft.Container(width=32,
                                    content=ft.Text(f"{h}ª", size=8, color=ACCENT_CYAN,
                                                    text_align=ft.TextAlign.CENTER))]
                for g in GIORNI:
                    if h > MAX_ORE[g]:
                        row.append(ft.Container(expand=True, height=26,
                                                bgcolor=CARD_BG+"22", border_radius=6))
                    else:
                        m   = state["orario"].get(g, {}).get(h, {}).get("materia", "").strip()
                        pal = SUBJECTS_PALETTE.get(m, SUBJECTS_PALETTE["default"]) if m else None
                        row.append(ft.Container(
                            expand=True, height=26, border_radius=6,
                            bgcolor=CARD_BG+"33" if not m else pal["bg"],
                            border=ft.border.all(1,
                                ACCENT_BLUE if g == oggi_g else
                                (BORDER_COLOR if not m else pal["accent"]+"50")),
                            padding=2,
                            content=ft.Text(
                                (m[:5]+"…" if len(m) > 5 else m), size=7,
                                color=TEXT_PRIMARY, text_align=ft.TextAlign.CENTER, max_lines=1)
                            if m else ft.Container()))
                mini.append(ft.Row(row, spacing=2))

            mini_widget = ft.Container(
                padding=ft.padding.symmetric(horizontal=12, vertical=10),
                border_radius=BORDER_RADIUS, bgcolor=SECONDARY_BG,
                border=ft.border.all(1, BORDER_COLOR_LIGHT),
                content=ft.Column([
                    ft.Text("Orario Settimanale", size=11, weight="bold", color=TEXT_MUTED),
                    ft.Column(mini, spacing=2)
                ], spacing=8))

            cal_widget.expand = True
            student_scroll.controls.append(
                ft.Row([
                    ft.Container(expand=True, content=cal_widget),
                    ft.Container(width=330, content=mini_widget)
                ], spacing=12, vertical_alignment=ft.CrossAxisAlignment.START))

            # ── Pannello registro (cliccabile) ────────────────────────────
            hint_registro = ft.Container(
                padding=ft.padding.symmetric(horizontal=14, vertical=12),
                border_radius=BORDER_RADIUS, bgcolor=TERTIARY_BG,
                border=ft.border.all(1, ACCENT_CYAN+"40"),
                content=ft.Column([
                    ft.Row([ft.Text("📖", size=18),
                            ft.Text("Registro Giornaliero", size=13, weight="bold", color=TEXT_PRIMARY)],
                        spacing=8),
                    ft.Text("Clicca su un giorno del calendario per vedere argomenti, compiti e presenza.",
                            size=11, color=TEXT_MUTED),
                    registro_panel_holder,
                ], spacing=10, tight=True))
            student_scroll.controls.append(hint_registro)

            # ── Prossime verifiche ─────────────────────────────────────────
            upcoming = sorted(
                [(date(oggi.year, v["mese"], v["giorno_num"]), v)
                for v in state.get("verifiche", [])
                if all([v.get("mese"), v.get("giorno_num")]) and
                    date(oggi.year, v["mese"], v["giorno_num"]) >= oggi],
                key=lambda x: x[0])
            if upcoming:
                vf = ft.Column(spacing=6)
                for vd, v in upcoming[:6]:
                    pal   = SUBJECTS_PALETTE.get(v.get("materia"), SUBJECTS_PALETTE["default"])
                    delta = (vd - oggi).days
                    bc    = ACCENT_RED if delta <= 2 else ACCENT_YELLOW if delta <= 7 else ACCENT_GREEN
                    vf.controls.append(ft.Container(
                        padding=ft.padding.symmetric(horizontal=12, vertical=8),
                        border_radius=12, bgcolor=pal["bg"],
                        border=ft.border.all(1, pal["accent"]+"60"),
                        content=ft.Row([
                            ft.Text("📝", size=16),
                            ft.Column([
                                ft.Text(v.get("materia"), size=11, color=TEXT_PRIMARY, weight="bold"),
                                ft.Text(f"{vd.strftime('%d %b')} ({v.get('giorno_settimana','')}) · {v.get('tipo','')}",
                                        size=9, color=TEXT_SECONDARY)
                            ], spacing=1, expand=True),
                            badge("OGGI!" if delta == 0 else f"tra {delta}gg", bc)
                        ], spacing=10)))
                student_scroll.controls.append(
                    cal_section("Prossime Verifiche", "📝", vf, accent=ACCENT_RED))

            # ── Riepilogo presenze mese corrente ──────────────────────────
            nome_studente = state.get("nome_studente", "")
            if nome_studente:
                assenze_mese = []
                for k, reg in state.get("registro", {}).items():
                    try:
                        rd = date.fromisoformat(k)
                        if rd.year == oggi.year and rd.month == oggi.month:
                            if nome_studente in reg.get("assenti", []):
                                assenze_mese.append(rd)
                    except:
                        pass
                assenze_mese.sort()
                if assenze_mese:
                    items = ft.Column(spacing=4)
                    for ad in assenze_mese:
                        items.controls.append(ft.Container(
                            padding=ft.padding.symmetric(horizontal=10, vertical=5),
                            border_radius=10, bgcolor=ACCENT_RED+"15",
                            border=ft.border.all(1, ACCENT_RED+"40"),
                            content=ft.Text(f"❌ {ad.strftime('%d %B %Y')} ({g_nome(ad)})",
                                            size=10, color=TEXT_PRIMARY)))
                    student_scroll.controls.append(
                        cal_section(f"Mie assenze — {MESI_NOMI[oggi.month]}", "📋",
                                    items, accent=ACCENT_RED))

            # ── Interrogazioni ─────────────────────────────────────────────
            nome_s2 = state.get("nome_studente", "Studente")
            pending = [i for i in state.get("interrogazioni", [])
                    if nome_s2 not in i.get("assegnazioni", {})]
            if pending:
                ic = ft.Column(spacing=12)
                for interr in pending:
                    mat = interr.get("materia", "?")
                    dd  = date_periodo(state, mat,
                                    interr.get("inizio_mese"), interr.get("inizio_giorno"),
                                    interr.get("fine_mese"),   interr.get("fine_giorno"))
                    if not dd:
                        ic.controls.append(
                            info_box(f"🎤 {mat}: nessun giorno disponibile — parla col prof.",
                                    ACCENT_YELLOW))
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
                        if not _d.value: return
                        try:
                            gs, ms = _d.value.split(" – ")[0].split("/")
                            chosen = date(oggi.year, int(ms), int(gs))
                            _i.setdefault("assegnazioni", {})[nome_s2] = g_nome(chosen)
                            salva_orario(root); build_student(); page.update()
                        except:
                            pass

                    ic.controls.append(ft.Container(
                        padding=12, border_radius=14, bgcolor=TERTIARY_BG,
                        border=ft.border.all(1, ACCENT_PURPLE+"70"),
                        content=ft.Column([
                            ft.Row([ft.Text("🎤", size=16),
                                    ft.Text(f"Interrogazione: {mat}", size=12,
                                            weight="bold", color=TEXT_PRIMARY)], spacing=8),
                            ai_box,
                            ft.Row([ddd, pill("Conferma", conferma, color=ACCENT_PURPLE)],
                                spacing=10, vertical_alignment=ft.CrossAxisAlignment.END),
                        ], spacing=8)))
                student_scroll.controls.append(
                    cal_section("Scegli Giorno Interrogazione", "🎤", ic, accent=ACCENT_PURPLE))

            confirmed = [(i, i["assegnazioni"][nome_s2])
                        for i in state.get("interrogazioni", [])
                        if nome_s2 in i.get("assegnazioni", {})]
            if confirmed:
                cc = ft.Column(spacing=6)
                for interr, giorno_sett in confirmed:
                    mat = interr.get("materia", "?")
                    cc.controls.append(ft.Container(
                        padding=ft.padding.symmetric(horizontal=12, vertical=8),
                        border_radius=12, bgcolor=ACCENT_PURPLE+"15",
                        border=ft.border.all(1, ACCENT_PURPLE+"60"),
                        content=ft.Row([
                            ft.Text("✅", size=14),
                            ft.Column([
                                ft.Text(mat, size=11, color=TEXT_PRIMARY, weight="bold"),
                                ft.Text(f"Giorno: {giorno_sett}", size=9, color=TEXT_SECONDARY)
                            ], spacing=1, expand=True)
                        ], spacing=10)))
                student_scroll.controls.append(
                    cal_section("Interrogazioni Confermate", "✅", cc, accent=ACCENT_GREEN))

            refresh_cal(large=True); page.update()

        # ── Layout finale ─────────────────────────────────────────────────
        if is_student:
            page.add(ft.Column([
                topbar,
                ft.Row([
                    ft.Container(expand=True,
                                padding=ft.padding.symmetric(horizontal=18, vertical=14),
                                content=student_scroll),
                    chat_panel
                ], expand=True, spacing=0, vertical_alignment=ft.CrossAxisAlignment.START)
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
                    ft.Divider(color=BORDER_COLOR, height=1), cal_widget
                ], spacing=10))
            page.add(ft.Column([
                topbar,
                ft.Row([
                    ft.Container(expand=True,
                                padding=ft.padding.symmetric(horizontal=18, vertical=14),
                                content=prof_scroll),
                    cal_side, chat_panel
                ], expand=True, spacing=0, vertical_alignment=ft.CrossAxisAlignment.START)
            ], spacing=0, expand=True))
            build_prof()

        page.update()


    # ══════════════════════════════════════════════════════════════════════
    # SEZIONE 4 — AI WORKSPACE (mappe concettuali)
    # ══════════════════════════════════════════════════════════════════════

    CARTELLA_MAPPE = "mappe_generate"
    CARTELLA_AUDIO = "audio_risposte"
    os.makedirs(CARTELLA_MAPPE, exist_ok=True)
    os.makedirs(CARTELLA_AUDIO, exist_ok=True)

    UTENTI = {
        "studente1": {"password": "prova1", "ruolo": "studente"},
        "docente1":  {"password": "prova1", "ruolo": "docente"},
    }

    def inizializza_ai():
        percorso_conoscenza = "conoscenza.txt"
        if not os.path.exists(percorso_conoscenza):
            with open(percorso_conoscenza, "w", encoding="utf-8") as f:
                f.write("AI Workspace: Sistema educativo per analisi PDF e mappe concettuali con Ollama.")
        try:
            loader  = TextLoader(percorso_conoscenza, encoding="utf-8")
            docs    = loader.load()
            splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
            chunks  = splitter.split_documents(docs)
            emb     = OllamaEmbeddings(model="llama3")
            vectorstore = Chroma.from_documents(documents=chunks, embedding=emb)
            return vectorstore.as_retriever()
        except Exception as e:
            print(f"Errore inizializzazione RAG: {e}")
            return None

    _retriever  = None
    _llm        = None
    _rag_chain  = None
    _ai_ready   = False

    def _assicura_ai():
        global _retriever, _llm, _rag_chain, _ai_ready
        if _ai_ready: return
        _retriever = inizializza_ai()
        _llm       = OllamaLLM(model="llama3")
        prompt_chat = ChatPromptTemplate.from_template(
            "Contesto: {context}\nDomanda: {question}\nRispondi in italiano in modo chiaro e conciso.")
        if _retriever:
            _rag_chain = (
                {"context": _retriever, "question": RunnablePassthrough()}
                | prompt_chat | _llm | StrOutputParser())
        _ai_ready = True

    def apri_dialogo_pdf() -> list:
        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        percorsi = filedialog.askopenfilenames(
            title="Seleziona uno o più PDF",
            filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")])
        root.destroy()
        return list(percorsi)

    recognizer = sr.Recognizer()

    def trascrivi_audio() -> str:
        try:
            with sr.Microphone() as source:
                recognizer.adjust_for_ambient_noise(source, duration=0.5)
                audio = recognizer.listen(source, timeout=10, phrase_time_limit=30)
            return recognizer.recognize_google(audio, language="it-IT")
        except sr.WaitTimeoutError:    return "__TIMEOUT__"
        except sr.UnknownValueError:   return "__NON_CAPITO__"
        except sr.RequestError as e:   return f"__ERRORE__:{e}"
        except Exception as e:         return f"__ERRORE__:{e}"

    _audio_counter = 0

    def genera_audio_risposta(testo: str) -> str | None:
        global _audio_counter
        if not TTS_DISPONIBILE: return None
        try:
            testo_tts = testo[:1200].strip()
            testo_tts = re.sub(r"\*{1,2}([^*]+)\*{1,2}", r"\1", testo_tts)
            testo_tts = re.sub(r"_{1,2}([^_]+)_{1,2}", r"\1", testo_tts)
            testo_tts = re.sub(r"#{1,6}\s*", "", testo_tts)
            testo_tts = re.sub(r"`([^`]+)`", r"\1", testo_tts)
            _audio_counter += 1
            nome_file = f"risposta_{_audio_counter:04d}.mp3"
            percorso  = os.path.join(CARTELLA_AUDIO, nome_file)
            gTTS(text=testo_tts, lang="it", slow=False).save(percorso)
            return os.path.abspath(percorso)
        except Exception as e:
            print(f"Errore TTS: {e}"); return None

    def riproduci_audio(percorso: str):
        if not PYGAME_DISPONIBILE or not percorso or not os.path.exists(percorso): return
        def _play():
            try:
                pygame.mixer.music.load(percorso)
                pygame.mixer.music.play()
            except Exception as e:
                print(f"Errore riproduzione: {e}")
        threading.Thread(target=_play, daemon=True).start()

    def estrai_relazioni(testo_llm: str) -> list:
        relazioni = []
        pattern   = re.compile(r"(.+?)\s*->\s*(.+?)(?:\s*\[(.+?)\])?$")
        for riga in testo_llm.splitlines():
            riga = riga.strip().strip('"').strip("'")
            m    = pattern.match(riga)
            if m:
                src   = m.group(1).strip()
                dst   = m.group(2).strip()
                label = m.group(3).strip() if m.group(3) else ""
                if src and dst:
                    relazioni.append((src, dst, label))
        return relazioni

    def crea_mappa_pyvis(relazioni: list, nome_file: str = "mappa.html") -> str:
        net = Network(height="700px", width="100%",
                    bgcolor="#0f172a", font_color="#f8fafc",
                    directed=True, notebook=False)
        net.set_options("""
        {
        "nodes": {"shape":"box","color":{"background":"#1e40af","border":"#3b82f6",
            "highlight":{"background":"#2563eb","border":"#60a5fa"}},
            "font":{"size":14,"color":"#f8fafc","face":"monospace"},"margin":10,"shadow":true},
        "edges": {"color":{"color":"#475569","highlight":"#60a5fa"},
            "arrows":{"to":{"enabled":true,"scaleFactor":1.2}},
            "font":{"size":11,"color":"#94a3b8","align":"middle"},
            "smooth":{"type":"curvedCW","roundness":0.2},"shadow":true},
        "physics": {"enabled":true,"barnesHut":{"gravitationalConstant":-8000,
            "centralGravity":0.3,"springLength":150,"springConstant":0.04,"damping":0.09}},
        "interaction":{"hover":true,"navigationButtons":true,"keyboard":true}
        }
        """)
        nodi = set()
        for src, dst, label in relazioni:
            if src not in nodi:
                net.add_node(src, label=src, title=f"<b>{src}</b>"); nodi.add(src)
            if dst not in nodi:
                net.add_node(dst, label=dst, title=f"<b>{dst}</b>"); nodi.add(dst)
            net.add_edge(src, dst, label=label, title=label)
        percorso = os.path.join(CARTELLA_MAPPE, nome_file)
        net.save_graph(percorso)
        return os.path.abspath(percorso)

    def avvia_workspace(page: ft.Page, on_back=None):
        page.controls.clear()
        page.title       = "AI Workspace — Mappe Concettuali"
        page.bgcolor     = "#0f172a"
        page.window_width  = 1200
        page.window_height = 850
        page.update()

        threading.Thread(target=_assicura_ai, daemon=True).start()

        def mostra_login():
            page.controls.clear()
            ruolo_selezionato = {"valore": None}
            campo_utente   = ft.TextField(
                label="Nome utente", width=340, border_radius=12,
                filled=True, fill_color="#1e293b", border_color="#334155",
                focused_border_color="#3b82f6", color="#f8fafc",
                label_style=ft.TextStyle(color="#64748b"), cursor_color="#3b82f6",
                on_submit=lambda e: campo_password.focus())
            campo_password = ft.TextField(
                label="Password", password=True, can_reveal_password=True,
                width=340, border_radius=12, filled=True, fill_color="#1e293b",
                border_color="#334155", focused_border_color="#3b82f6",
                color="#f8fafc", label_style=ft.TextStyle(color="#64748b"),
                cursor_color="#3b82f6", on_submit=lambda e: esegui_login(e))
            messaggio_errore = ft.Text("", color="#ef4444", size=13)
            titolo_form      = ft.Text("", size=15, color="#94a3b8", italic=True)
            form_login = ft.Column(
                [titolo_form, campo_utente, campo_password, messaggio_errore, ft.Container(height=2)],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=12, visible=False)
            btn_accedi   = ft.ElevatedButton("Accedi", bgcolor="#1e40af", color="#f8fafc",
                                            width=340, visible=False,
                                            on_click=lambda e: esegui_login(e))
            btn_indietro = ft.TextButton("← Cambia ruolo",
                                        style=ft.ButtonStyle(color={"": "#475569"}),
                                        visible=False, on_click=lambda e: torna_selezione())

            def esegui_login(e):
                utente = campo_utente.value.strip(); pwd = campo_password.value.strip()
                ruolo_atteso = ruolo_selezionato["valore"]
                if (utente in UTENTI and UTENTI[utente]["password"] == pwd
                        and UTENTI[utente]["ruolo"] == ruolo_atteso):
                    mostra_workspace_ui(utente, ruolo_atteso)
                else:
                    if utente in UTENTI and UTENTI[utente]["ruolo"] != ruolo_atteso:
                        messaggio_errore.value = (
                            f"❌ Credenziali di un {UTENTI[utente]['ruolo']}. "
                            f"Accedi come {ruolo_atteso} o cambia ruolo.")
                    else:
                        messaggio_errore.value = "❌ Credenziali non valide. Riprova."
                    campo_password.value = ""; page.update()

            def crea_card_ruolo(icona, etichetta, ruolo, colore_bg, colore_bordo, colore_hover, hint_account):
                card = ft.Container(
                    width=160, height=175, border_radius=18, bgcolor=colore_bg,
                    border=ft.border.all(2, colore_bordo),
                    content=ft.Column([
                        ft.Text(icona, size=48),
                        ft.Text(etichetta, size=18, weight=ft.FontWeight.BOLD, color="#f8fafc"),
                        ft.Text(hint_account, size=10, color="#94a3b8", italic=True),
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    alignment=ft.MainAxisAlignment.CENTER, spacing=6),
                    ink=True,
                    on_click=lambda e, r=ruolo, l=etichetta, icon=icona: scegli_ruolo(r, l, icon),
                    shadow=ft.BoxShadow(spread_radius=1, blur_radius=16,
                                        color=colore_bordo+"55", offset=ft.Offset(0, 4)))
                def _on_hover(e, c=card, ch=colore_hover, co=colore_bg):
                    c.bgcolor = ch if e.data == "true" else co; page.update()
                card.on_hover = _on_hover
                return card

            card_studenti = crea_card_ruolo("👨‍🎓","Studenti","studente","#064e3b","#10b981","#065f46","studente1 / prova1")
            card_docenti  = crea_card_ruolo("👨‍🏫","Docenti","docente","#1e1b4b","#818cf8","#2d2a6e","docente1 / prova1")
            riga_card = ft.Row([card_studenti, card_docenti], alignment=ft.MainAxisAlignment.CENTER, spacing=28)
            sottotitolo_selezione = ft.Text("Seleziona il tuo ruolo per accedere", size=13, color="#475569", italic=True)

            def scegli_ruolo(ruolo, etichetta, icona):
                ruolo_selezionato["valore"] = ruolo
                riga_card.visible = False; sottotitolo_selezione.visible = False
                form_login.visible = True; btn_accedi.visible = True; btn_indietro.visible = True
                titolo_form.value = f"{icona}  Accesso {etichetta} — inserisci le credenziali"
                messaggio_errore.value = ""; campo_utente.value = ""; campo_password.value = ""
                page.update(); campo_utente.focus()

            def torna_selezione():
                ruolo_selezionato["valore"] = None
                riga_card.visible = True; sottotitolo_selezione.visible = True
                form_login.visible = False; btn_accedi.visible = False; btn_indietro.visible = False
                messaggio_errore.value = ""; page.update()

            btn_home = ft.TextButton("🏠 Home",
                on_click=lambda e: on_back() if on_back else None,
                style=ft.ButtonStyle(color={"": ACCENT_CYAN}))
            page.add(ft.Container(
                content=ft.Column([
                    ft.Text("🗺️", size=52),
                    ft.Text("AI Workspace", size=30, weight=ft.FontWeight.BOLD, color="#f8fafc"),
                    ft.Text("Mappe Concettuali · Open Source · 100% Locale", size=13, color="#475569"),
                    ft.Container(height=24),
                    sottotitolo_selezione, riga_card,
                    form_login, btn_accedi, btn_indietro, btn_home,
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=16),
                alignment=ft.alignment.Alignment(0, 0), expand=True))
            page.update()

        def mostra_workspace_ui(utente: str, ruolo: str):
            page.controls.clear()
            pdf_caricati         = {}
            registrazione_attiva = {"valore": False}
            chat_container     = ft.ListView(expand=True, spacing=15, auto_scroll=True)
            pdf_list_container = ft.Column(scroll=ft.ScrollMode.AUTO, spacing=6)

            def _ferma_audio():
                if PYGAME_DISPONIBILE:
                    try: pygame.mixer.music.stop()
                    except: pass

            def messaggio_ai(testo: str, con_audio: bool = True):
                percorso_audio = None
                if con_audio and TTS_DISPONIBILE:
                    percorso_audio = genera_audio_risposta(testo)
                contenuto_msg = [ft.Markdown(testo, selectable=True)]
                if percorso_audio:
                    nome_audio = os.path.basename(percorso_audio)
                    riga_audio = ft.Container(
                        content=ft.Row([
                            ft.ElevatedButton("🔊  Ascolta risposta", bgcolor="#065f46", color="#f8fafc",
                                style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10)),
                                on_click=lambda e, p=percorso_audio: riproduci_audio(p)),
                            ft.ElevatedButton("⏹  Stop", bgcolor="#374151", color="#f8fafc",
                                style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10)),
                                on_click=lambda e: _ferma_audio()),
                            ft.TextButton(f"📁  {nome_audio}",
                                style=ft.ButtonStyle(color={"": "#6b7280"}),
                                on_click=lambda e, p=percorso_audio: webbrowser.open(f"file://{p}")),
                        ], spacing=8, wrap=True),
                        bgcolor="#052e16", padding=ft.padding.symmetric(horizontal=14, vertical=8),
                        border_radius=10, border=ft.border.all(1, "#065f46"))
                    contenuto_msg.append(riga_audio)
                chat_container.controls.append(ft.Container(
                    content=ft.Column(contenuto_msg, spacing=10),
                    bgcolor="#1e293b",
                    padding=ft.padding.symmetric(horizontal=18, vertical=14),
                    border_radius=15, width=700))
                page.update()
                if percorso_audio: riproduci_audio(percorso_audio)

            def messaggio_utente(testo: str):
                chat_container.controls.append(ft.Row([
                    ft.Container(content=ft.Text(testo, color="#f8fafc"),
                                bgcolor="#2563eb",
                                padding=ft.padding.symmetric(horizontal=16, vertical=12),
                                border_radius=15)
                ], alignment=ft.MainAxisAlignment.END))
                page.update()

            def aggiungi_spinner(msg="Elaborazione..."):
                spinner = ft.Container(
                    content=ft.Row([
                        ft.ProgressRing(width=18, height=18, stroke_width=2, color="#3b82f6"),
                        ft.Text(msg, color="#64748b", italic=True, size=13),
                    ], spacing=10),
                    bgcolor="#1e293b", padding=14, border_radius=12, width=280)
                chat_container.controls.append(spinner); page.update()
                return spinner

            def rimuovi_spinner(spinner):
                if spinner in chat_container.controls:
                    chat_container.controls.remove(spinner)
                page.update()

            def rinfresca_lista_pdf():
                pdf_list_container.controls.clear()
                if not pdf_caricati:
                    pdf_list_container.controls.append(
                        ft.Text("Nessun PDF caricato", color="#475569", italic=True, size=12))
                else:
                    for nome in pdf_caricati:
                        parole = len(pdf_caricati[nome].split())
                        nome_breve = nome if len(nome) < 22 else nome[:20]+"..."
                        def rimuovi_pdf(e, n=nome):
                            del pdf_caricati[n]; rinfresca_lista_pdf()
                            messaggio_ai(f"🗑️ PDF **{n}** rimosso.", con_audio=False)
                        pdf_list_container.controls.append(ft.Container(
                            content=ft.Column([
                                ft.Row([ft.Text("📄", size=16),
                                        ft.Text(nome_breve, expand=True, size=13, color="#f1f5f9"),
                                        ft.TextButton("✕", style=ft.ButtonStyle(color={"": "#ef4444"}),
                                                    on_click=rimuovi_pdf)], spacing=4),
                                ft.Text(f"{parole:,} parole", color="#64748b", size=11),
                            ], spacing=2),
                            bgcolor="#1e293b", padding=10, border_radius=10,
                            border=ft.border.all(1, "#334155")))
                page.update()

            def carica_pdf_thread():
                percorsi = apri_dialogo_pdf()
                if not percorsi: return
                nuovi = []
                for percorso in percorsi:
                    nome = os.path.basename(percorso)
                    try:
                        reader = PyPDF2.PdfReader(percorso)
                        testo  = "\n".join((p.extract_text() or "") for p in reader.pages).strip()
                        if not testo:
                            messaggio_ai(f"⚠️ **{nome}**: nessun testo estraibile.", con_audio=False)
                            continue
                        pdf_caricati[nome] = testo; nuovi.append(nome)
                    except Exception as ex:
                        messaggio_ai(f"❌ Errore **{nome}**: {ex}", con_audio=False)
                if nuovi:
                    elenco = "\n".join(f"- **{n}**" for n in nuovi)
                    messaggio_ai(
                        f"✅ Caricati {len(nuovi)} PDF:\n{elenco}\n\n"
                        "Ora puoi chiedere:\n- `crea mappa concettuale`\n"
                        "- `analizza nomefile.pdf`\n- Qualsiasi domanda sui contenuti")
                    rinfresca_lista_pdf()

            def carica_pdf(e):
                threading.Thread(target=carica_pdf_thread, daemon=True).start()

            def elaborazione_ai(input_utente: str):
                spinner   = aggiungi_spinner()
                testo_min = input_utente.lower()
                vuole_mappa   = any(p in testo_min for p in ["mappa","schema","grafo","concettual","visualizza"])
                match_singolo = re.search(r"analizza\s+(\S+\.pdf)", testo_min)
                try:
                    if vuole_mappa or match_singolo:
                        if not pdf_caricati:
                            rimuovi_spinner(spinner)
                            messaggio_ai("⚠️ Carica almeno un PDF prima di creare una mappa.")
                            return
                        if match_singolo:
                            nome_target = match_singolo.group(1)
                            if nome_target in pdf_caricati:
                                testi = {nome_target: pdf_caricati[nome_target]}
                            else:
                                rimuovi_spinner(spinner)
                                messaggio_ai(f"⚠️ PDF **{nome_target}** non trovato.")
                                return
                        else:
                            testi = pdf_caricati
                        testo_combinato = ""
                        for nome, contenuto in testi.items():
                            testo_combinato += f"\n\n=== {nome} ===\n{contenuto[:2000]}"
                        risposta_llm = _llm.invoke(
                            "Sei un assistente educativo esperto in mappe concettuali.\n"
                            "Analizza il testo seguente ed estrai i concetti principali e le loro relazioni.\n\n"
                            "Rispondi ESCLUSIVAMENTE con righe nel formato:\n"
                            "ConcettoA -> ConcettoB [tipo_relazione]\n\n"
                            "Non aggiungere spiegazioni o altro testo. Estrai almeno 15 relazioni.\n\n"
                            f"Testo:\n{testo_combinato}")
                        relazioni = estrai_relazioni(risposta_llm)
                        rimuovi_spinner(spinner)
                        if not relazioni:
                            messaggio_ai("⚠️ Nessuna relazione estratta. Verifica che il PDF abbia testo leggibile.")
                            return
                        nome_mappa    = "mappa_" + "_".join(list(testi.keys())[:2]).replace(" ", "_") + ".html"
                        percorso_html = crea_mappa_pyvis(relazioni, nome_mappa)
                        webbrowser.open(f"file://{percorso_html}")
                        testo_esito      = f"Mappa generata con {len(relazioni)} relazioni. Aperta nel browser."
                        percorso_audio_m = genera_audio_risposta(testo_esito) if TTS_DISPONIBILE else None
                        controlli_card = [
                            ft.Text(f"🗺️ Mappa generata — {len(relazioni)} relazioni",
                                    color="#10b981", weight=ft.FontWeight.BOLD, size=15),
                            ft.Text("La mappa si è aperta nel browser.\nTrascina i nodi, fai zoom.",
                                    color="#94a3b8", size=13),
                            ft.ElevatedButton("🌐  Riapri nel browser", bgcolor="#1e40af", color="#f8fafc",
                                            on_click=lambda e, p=percorso_html: webbrowser.open(f"file://{p}")),
                        ]
                        if percorso_audio_m:
                            controlli_card.append(ft.Row([
                                ft.ElevatedButton("🔊  Ascolta", bgcolor="#065f46", color="#f8fafc",
                                                on_click=lambda e, p=percorso_audio_m: riproduci_audio(p)),
                                ft.ElevatedButton("⏹  Stop", bgcolor="#374151", color="#f8fafc",
                                                on_click=lambda e: _ferma_audio()),
                            ], spacing=8))
                            riproduci_audio(percorso_audio_m)
                        chat_container.controls.append(ft.Container(
                            content=ft.Column(controlli_card, spacing=8),
                            bgcolor="#1e293b", padding=16, border_radius=14,
                            border=ft.border.all(1, "#10b981"), width=520))
                        page.update()
                        return
                    elif pdf_caricati and any(p in testo_min for p in
                            ["documento","pdf","testo","contenuto","parla","dice","riguarda"]):
                        contesto_pdf = "\n\n".join(
                            f"[{nome}]\n{contenuto[:1500]}" for nome, contenuto in pdf_caricati.items())
                        risposta = _llm.invoke(
                            f"Rispondi in italiano basandoti SOLO sui documenti seguenti.\n\n"
                            f"Documenti:\n{contesto_pdf}\n\nDomanda: {input_utente}")
                        rimuovi_spinner(spinner); messaggio_ai(risposta)
                    else:
                        risposta = _rag_chain.invoke(input_utente) if _rag_chain else _llm.invoke(input_utente)
                        rimuovi_spinner(spinner); messaggio_ai(risposta)
                except Exception as err:
                    rimuovi_spinner(spinner)
                    messaggio_ai(f"⚠️ Errore: {err}", con_audio=False)

            stato_mic = ft.Text("", color="#64748b", size=12, italic=True)

            def registra_vocale(e):
                if registrazione_attiva["valore"]: return
                registrazione_attiva["valore"] = True
                btn_mic.bgcolor = "#7f1d1d"; btn_mic.text = "⏺  Registrando..."
                stato_mic.value = "🎙️ In ascolto... parla ora"; page.update()
                def _ascolta():
                    testo = trascrivi_audio()
                    registrazione_attiva["valore"] = False
                    btn_mic.bgcolor = "#1e3a5f"; btn_mic.text = "🎤  Parla"
                    stato_mic.value = ""; page.update()
                    if   testo == "__TIMEOUT__":     messaggio_ai("⚠️ Nessun audio rilevato. Riprova.", con_audio=False)
                    elif testo == "__NON_CAPITO__":  messaggio_ai("⚠️ Non ho capito. Riprova.", con_audio=False)
                    elif testo.startswith("__ERRORE__"): messaggio_ai(f"⚠️ Errore: {testo.split(':',1)[-1]}", con_audio=False)
                    else:
                        chat_input.value = testo; page.update()
                        messaggio_utente(f"🎤 {testo}"); chat_input.value = ""; page.update()
                        threading.Thread(target=elaborazione_ai, args=(testo,), daemon=True).start()
                threading.Thread(target=_ascolta, daemon=True).start()

            def gestisci_invio(e):
                testo = chat_input.value.strip()
                if not testo: return
                messaggio_utente(testo); chat_input.value = ""; page.update()
                threading.Thread(target=elaborazione_ai, args=(testo,), daemon=True).start()

            chat_input = ft.TextField(
                hint_text="Carica PDF, poi chiedi 'crea mappa concettuale' o fai domande...",
                expand=True, on_submit=gestisci_invio, border_radius=14, filled=True,
                fill_color="#1e293b", border_color="#334155", focused_border_color="#3b82f6",
                color="#f8fafc", hint_style=ft.TextStyle(color="#475569"), cursor_color="#3b82f6")

            btn_upload = ft.ElevatedButton("📄  Carica PDF", bgcolor="#b91c1c", color="#f8fafc", on_click=carica_pdf)
            btn_mic    = ft.ElevatedButton("🎤  Parla", bgcolor="#1e3a5f", color="#f8fafc",
                                            style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=12)),
                                            tooltip="Premi per dettare il comando vocalmente",
                                            on_click=registra_vocale)
            btn_invia  = ft.ElevatedButton("➤", bgcolor="#1e40af", color="#f8fafc", on_click=gestisci_invio)
            btn_home   = ft.TextButton("🏠 Home",
                                        on_click=lambda e: on_back() if on_back else None,
                                        style=ft.ButtonStyle(color={"": ACCENT_CYAN}))

            badge_colore = "#6d28d9" if ruolo == "docente" else "#0f766e"
            badge_icona  = "👨‍🏫" if ruolo == "docente" else "👨‍🎓"
            badge_label  = f"{badge_icona}  {utente}  ({ruolo})"

            sidebar = ft.Container(
                content=ft.Column([
                    ft.Text("📁  PDF CARICATI", weight=ft.FontWeight.BOLD, color="#60a5fa", size=13),
                    ft.Divider(color="#1e293b", height=1),
                    pdf_list_container,
                    ft.Divider(color="#1e293b", height=1),
                ]),
                width=260, bgcolor="#070f1e",
                padding=ft.padding.symmetric(horizontal=16, vertical=20),
                border=ft.border.only(right=ft.border.BorderSide(1, "#1e293b")))

            header = ft.Container(
                content=ft.Row([
                    ft.Text("🗺️", size=22),
                    ft.Text("AI WORKSPACE", weight=ft.FontWeight.BOLD, size=18, color="#f8fafc"),
                    ft.Text("Mappe Concettuali · Open Source · 100% Locale", color="#475569", size=12),
                    ft.Container(expand=True),
                    ft.Container(content=ft.Text(badge_label, color="#f8fafc", size=12),
                                bgcolor=badge_colore,
                                padding=ft.padding.symmetric(horizontal=14, vertical=6),
                                border_radius=20),
                    btn_home,
                    ft.TextButton("🚪 Esci",
                                style=ft.ButtonStyle(color={"": "#94a3b8"}),
                                on_click=lambda e: mostra_login()),
                ], spacing=12, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                padding=ft.padding.symmetric(horizontal=24, vertical=14),
                bgcolor="#070f1e",
                border=ft.border.only(bottom=ft.border.BorderSide(1, "#1e293b")))

            barra_input = ft.Container(
                content=ft.Column([
                    ft.Row([btn_upload, chat_input, btn_mic, btn_invia],
                        spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                    stato_mic,
                ], spacing=4),
                bgcolor="#0f172a",
                padding=ft.padding.symmetric(horizontal=12, vertical=10),
                border=ft.border.only(top=ft.border.BorderSide(1, "#1e293b")))

            area_chat = ft.Container(
                content=ft.Column([chat_container, barra_input], expand=True, spacing=0),
                expand=True, padding=ft.padding.only(left=20, right=20, top=16))

            page.add(ft.Column([
                header,
                ft.Row([sidebar, area_chat], expand=True),
            ], expand=True, spacing=0))

            nome_ruolo = "Docente" if ruolo == "docente" else "Studente"
            messaggio_ai(
                f"👋 **Benvenuto, {utente}!** *({nome_ruolo})*\n\n"
                "Funziona **100% in locale** con Ollama (llama3).\n\n"
                "**Come iniziare:**\n"
                "1. Clicca **📄 Carica PDF** per selezionare i documenti\n"
                "2. Digita `crea mappa concettuale` oppure premi **🎤 Parla**\n"
                "3. La mappa si apre nel browser\n"
                "4. Ogni risposta include una **traccia audio 🔊**",
                con_audio=True)
            rinfresca_lista_pdf()

        mostra_login()


    # ══════════════════════════════════════════════════════════════════════
    # SEZIONE 5 — HOME
    # ══════════════════════════════════════════════════════════════════════

    def main(page: ft.Page):
        page.title       = "🏫 Piattaforma Scolastica AI"
        page.theme_mode  = ft.ThemeMode.DARK
        page.bgcolor     = PRIMARY_BG
        page.window_width  = 1400
        page.window_height = 900
        page.padding     = 0

        def mostra_home():
            page.controls.clear()
            page.bgcolor = PRIMARY_BG

            def apri_calendario(is_student: bool):
                avvia_calendario(page, is_student=is_student, on_back=mostra_home)

            def apri_workspace(_e=None):
                avvia_workspace(page, on_back=mostra_home)

            def crea_card_modulo(icona, titolo, sottotitolo, descrizione,
                                colore_bg, colore_bordo, colore_hover, on_click):
                card = ft.Container(
                    width=320, height=260, border_radius=BORDER_RADIUS,
                    bgcolor=colore_bg, border=ft.border.all(2, colore_bordo),
                    padding=ft.padding.all(28),
                    content=ft.Column([
                        ft.Text(icona, size=52),
                        ft.Text(titolo, size=20, weight=ft.FontWeight.BOLD, color=TEXT_PRIMARY),
                        ft.Text(sottotitolo, size=11, color=ACCENT_CYAN, italic=True),
                        ft.Container(height=8),
                        ft.Text(descrizione, size=12, color=TEXT_SECONDARY),
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    alignment=ft.MainAxisAlignment.CENTER, spacing=6),
                    ink=True, on_click=on_click,
                    shadow=ft.BoxShadow(spread_radius=1, blur_radius=20,
                                        color=colore_bordo+"44", offset=ft.Offset(0, 6)))
                def _hover(e, c=card, ch=colore_hover, co=colore_bg):
                    c.bgcolor = ch if e.data == "true" else co; page.update()
                card.on_hover = _hover
                return card

            card_cal_studente = crea_card_modulo(
                "👨‍🎓", "Calendario", "Vista Studente",
                "Orario · Verifiche · Registro · Presenze · AI chat",
                "#0a1e30", ACCENT_BLUE, "#0f2a45",
                lambda e: apri_calendario(is_student=True))

            card_cal_docente = crea_card_modulo(
                "👨‍🏫", "Calendario", "Vista Docente",
                "Orario · Registro giornaliero · Verifiche · Assenti",
                "#1a0a2e", ACCENT_PURPLE, "#240f3e",
                lambda e: apri_calendario(is_student=False))

            card_workspace = crea_card_modulo(
                "🗺️", "AI Workspace", "Mappe Concettuali",
                "Carica PDF · Genera mappe · Chat vocale · 100% locale",
                "#0a1e10", ACCENT_GREEN, "#0f2a18",
                apri_workspace)

            page.add(ft.Container(
                content=ft.Column([
                    ft.Container(height=30),
                    ft.Text("🏫", size=60),
                    ft.Text("Piattaforma Scolastica AI",
                            size=34, weight=ft.FontWeight.BOLD, color=TEXT_PRIMARY),
                    ft.Text("Calendario · Registro · Mappe Concettuali · Assistente AI · 100% Locale",
                            size=14, color=TEXT_SECONDARY),
                    ft.Container(height=40),
                    ft.Row(
                        [card_cal_studente, card_cal_docente, card_workspace],
                        alignment=ft.MainAxisAlignment.CENTER, spacing=32, wrap=True),
                    ft.Container(height=30),
                    ft.Text("Powered by Ollama (llama3) · Flet · LangChain · PyVis",
                            size=11, color=TEXT_MUTED, italic=True),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=10),
                alignment=ft.alignment.Alignment(0, 0),
                expand=True))
            page.update()

        mostra_home()


    if __name__ == "__main__":
        ft.app(target=main)