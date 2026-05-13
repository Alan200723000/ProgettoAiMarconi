# ══════════════════════════════════════════════════════════════════════
# utils_calendario.py — Persistenza, logica orario e funzioni helper
# ══════════════════════════════════════════════════════════════════════

import os
import json
import urllib.request
import urllib.error
from datetime import date, timedelta

SAVE_FILE = "orario.json"

GIORNI   = ["Lunedì", "Martedì", "Mercoledì", "Giovedì", "Venerdì"]
MAX_ORE  = {"Lunedì": 7, "Martedì": 6, "Mercoledì": 6, "Giovedì": 6, "Venerdì": 7}
MESI_NOMI = ["", "Gennaio", "Febbraio", "Marzo", "Aprile", "Maggio", "Giugno",
             "Luglio", "Agosto", "Settembre", "Ottobre", "Novembre", "Dicembre"]
MESI_OPTS = [f"{i} - {MESI_NOMI[i]}" for i in range(1, 13)]

LIGHT = {"Educazione Fisica", "Religione", "Arte", "Musica"}
LAB   = {"Sistemi e Reti", "Informatica", "Telecomunicazioni", "Fisica", "Chimica", "Scienze"}


# ── Struttura dati vuota ──────────────────────────────────────────────

def _empty() -> dict:
    return {
        "orario": {},
        "verifiche": [],
        "interrogazioni": [],
        "registro": {}   # chiave "YYYY-MM-DD" → {argomenti, compiti, assenti:[]}
    }


# ── Persistenza ───────────────────────────────────────────────────────

def carica_orario() -> dict:
    if os.path.exists(SAVE_FILE):
        try:
            d = json.load(open(SAVE_FILE, encoding="utf-8"))
            # Migrazione formato vecchio → nuovo multi-classe
            if "classi" not in d:
                cl = d.get("classe", "4G")
                d  = {
                    "classi": {
                        cl: {
                            "orario": d.get("orario", {}),
                            "verifiche": d.get("verifiche", []),
                            "interrogazioni": d.get("interrogazioni", []),
                            "registro": d.get("registro", {}),
                        }
                    },
                    "ultima_classe": cl,
                }
            for data in d["classi"].values():
                # Normalizza ore: int key + dict value
                data["orario"] = {
                    g: {
                        int(h): (
                            v if isinstance(v, dict)
                            else {"materia": str(v), "prof": ""}
                        )
                        for h, v in ore.items()
                    }
                    for g, ore in data.get("orario", {}).items()
                }
                data.setdefault("verifiche", [])
                data.setdefault("interrogazioni", [])
                data.setdefault("registro", {})
            return d
        except Exception:
            pass
    return {"classi": {}, "ultima_classe": ""}


def salva_orario(root: dict) -> None:
    json.dump(root, open(SAVE_FILE, "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)


def cls_data(root: dict, classe: str) -> dict:
    """Ritorna (e crea se assente) il dict dati della classe."""
    root["classi"].setdefault(classe, _empty())
    d = root["classi"][classe]
    d.setdefault("registro", {})
    return d


# ── Registro giornaliero ──────────────────────────────────────────────

def chiave_data(dt: date) -> str:
    return dt.strftime("%Y-%m-%d")


def get_registro_giorno(state: dict, dt: date) -> dict:
    k = chiave_data(dt)
    state["registro"].setdefault(k, {"argomenti": "", "compiti": "", "assenti": []})
    return state["registro"][k]


# ── Calcolo "peso" giornata (per suggerimenti AI) ─────────────────────

def peso(state: dict, g: str) -> float:
    day = state["orario"].get(g, {})
    n   = MAX_ORE[g]
    mat = [day.get(h, {}).get("materia", "").strip() for h in range(1, n + 1)]

    edge_pen = sum(
        1.2 for idx in [0, n - 1]
        if idx < len(mat) and mat[idx] and mat[idx] not in LIGHT
    )
    filled = [m for m in mat if m]
    n_l = sum(1 for m in filled if m in LIGHT)
    n_b = sum(1 for m in filled if m in LAB)

    mx, cu, cm = 0, 0, ""
    for m in filled:
        if m not in LIGHT and m not in LAB:
            cu = cu + 1 if m == cm else 1
            cm = m
            mx = max(mx, cu)
        else:
            cu, cm = 0, ""

    p = n - n_l - n_b * 0.5 + mx * 0.8 + edge_pen

    for v in state.get("verifiche", []):
        if v.get("giorno_settimana") == g:
            p += 2
    for i in state.get("interrogazioni", []):
        for gg in i.get("assegnazioni", {}).values():
            if gg == g:
                p += 1

    return round(p, 2)


# ── Utilità date ──────────────────────────────────────────────────────

def giorni_mat(state: dict, mat: str) -> list[str]:
    """Restituisce i giorni della settimana in cui è presente la materia."""
    return [
        g for g in GIORNI
        if any(
            state["orario"].get(g, {}).get(h, {}).get("materia") == mat
            for h in range(1, MAX_ORE[g] + 1)
        )
    ]


def g_nome(dt: date) -> str:
    return ["Lunedì", "Martedì", "Mercoledì", "Giovedì", "Venerdì", "Sabato", "Domenica"][dt.weekday()]


def date_periodo(state: dict, mat: str, im, ig, fm, fg) -> list[tuple[date, str]]:
    """Restituisce lista di (date, giorno_settimana) per il periodo dato."""
    oggi = date.today()
    try:
        ini = date(oggi.year, im, ig)
        fin = date(oggi.year, fm, fg)
        if fin < ini:
            fin = date(oggi.year + 1, fm, fg)
    except Exception:
        return []
    gm  = set(giorni_mat(state, mat))
    res, cur = [], ini
    while cur <= fin:
        gn = g_nome(cur)
        if gn in gm:
            res.append((cur, gn))
        cur += timedelta(days=1)
    return res


def parse_data(testo: str, oggi: date) -> date | None:
    """Interpreta espressioni come 'domani', 'oggi', '3 maggio' ecc."""
    t = testo.lower()
    if "domani"     in t: return oggi + timedelta(1)
    if "dopodomani" in t: return oggi + timedelta(2)
    if "oggi"       in t: return oggi
    mesi = {
        "gennaio": 1, "febbraio": 2, "marzo": 3, "aprile": 4,
        "maggio": 5, "giugno": 6, "luglio": 7, "agosto": 8,
        "settembre": 9, "ottobre": 10, "novembre": 11, "dicembre": 12,
    }
    for nome, num in mesi.items():
        if nome in t:
            for p in t.split():
                if p.isdigit():
                    a = oggi.year if num >= oggi.month else oggi.year + 1
                    try:
                        return date(a, num, int(p))
                    except Exception:
                        pass
    return None


# ── Comunicazione con Ollama ──────────────────────────────────────────

def call_ollama(
    prompt: str,
    system: str = "Sei un assistente scolastico. Rispondi brevemente in italiano.",
) -> str:
    import json as j
    try:
        payload = j.dumps({
            "model": "llama3",
            "messages": [
                {"role": "system", "content": system},
                {"role": "user",   "content": prompt},
            ],
            "stream": False,
        }).encode()
        req = urllib.request.Request(
            "http://localhost:11434/api/chat",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        return j.loads(urllib.request.urlopen(req, timeout=30).read())["message"]["content"]
    except urllib.error.URLError:
        return "⚠️ Ollama non raggiungibile — avvia con: ollama serve"
    except Exception as ex:
        return f"⚠️ {ex.__class__.__name__}: {str(ex)[:100]}"
