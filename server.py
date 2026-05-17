# ══════════════════════════════════════════════════════════════════════
# server.py — Server Flask per comunicazione in rete locale (LAN)
#
# Avvio: python server.py
# Gli altri dispositivi sulla stessa rete potranno accedere a:
#   http://<IP-del-server>:5000
#
# Per trovare l'IP del server:
#   Windows: ipconfig
#   Linux/Mac: ifconfig o ip addr
# ══════════════════════════════════════════════════════════════════════

import json
import os
import socket
import threading
from datetime import datetime
from functools import wraps

try:
    from flask import Flask, request, jsonify, send_from_directory
    from flask_cors import CORS
except ImportError:
    print("Installa le dipendenze: pip install flask flask-cors")
    raise

import auth
from utils_calendario import carica_orario, salva_orario, cls_data, _empty

app = Flask(__name__, static_folder="static")
CORS(app)  # Permette richieste cross-origin dalla LAN

# ── Lock per accesso concorrente al file ──────────────────────────────
_file_lock = threading.Lock()


# ══════════════════════════════════════════════════════════════════════
# HELPER: IP locale
# ══════════════════════════════════════════════════════════════════════

def get_local_ip() -> str:
    """Rileva l'IP locale del server sulla LAN."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


# ══════════════════════════════════════════════════════════════════════
# MIDDLEWARE: autenticazione sessione semplice (token)
# ══════════════════════════════════════════════════════════════════════

# Sessioni attive: { token: { username, ruolo, nome_display, scadenza } }
_sessioni: dict = {}
_sessioni_lock  = threading.Lock()


def genera_token() -> str:
    import secrets
    return secrets.token_hex(32)


def richiedi_auth(f):
    """Decorator: verifica il token Bearer nell'header Authorization."""
    @wraps(f)
    def wrapped(*args, **kwargs):
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return jsonify({"errore": "Non autenticato"}), 401
        token = auth_header[7:]
        with _sessioni_lock:
            sessione = _sessioni.get(token)
        if not sessione:
            return jsonify({"errore": "Sessione scaduta o non valida"}), 401
        request.utente = sessione
        return f(*args, **kwargs)
    return wrapped


def richiedi_docente(f):
    """Decorator: verifica che l'utente sia un docente."""
    @wraps(f)
    def wrapped(*args, **kwargs):
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return jsonify({"errore": "Non autenticato"}), 401
        token = auth_header[7:]
        with _sessioni_lock:
            sessione = _sessioni.get(token)
        if not sessione:
            return jsonify({"errore": "Sessione scaduta"}), 401
        if sessione.get("ruolo") != "docente":
            return jsonify({"errore": "Accesso riservato ai docenti"}), 403
        request.utente = sessione
        return f(*args, **kwargs)
    return wrapped


# ══════════════════════════════════════════════════════════════════════
# ENDPOINT: AUTH
# ══════════════════════════════════════════════════════════════════════

@app.route("/api/login", methods=["POST"])
def api_login():
    """Login utente → ritorna token di sessione."""
    dati = request.get_json() or {}
    username = dati.get("username", "").strip()
    password = dati.get("password", "").strip()
    ruolo    = dati.get("ruolo", "").strip()

    if not all([username, password, ruolo]):
        return jsonify({"errore": "Campi mancanti"}), 400

    ok, msg = auth.verifica_login(username, password, ruolo)
    if not ok:
        return jsonify({"errore": msg}), 401

    nome_display = auth.get_nome_display(username)
    token        = genera_token()

    with _sessioni_lock:
        _sessioni[token] = {
            "username":     username,
            "ruolo":        ruolo,
            "nome_display": nome_display,
        }

    return jsonify({
        "token":       token,
        "nome_display": nome_display,
        "ruolo":        ruolo,
    })


@app.route("/api/logout", methods=["POST"])
@richiedi_auth
def api_logout():
    auth_header = request.headers.get("Authorization", "")
    token = auth_header[7:]
    with _sessioni_lock:
        _sessioni.pop(token, None)
    return jsonify({"ok": True})


@app.route("/api/registra/studente", methods=["POST"])
def api_registra_studente():
    """Registrazione nuovo studente."""
    dati = request.get_json() or {}
    ok, msg = auth.registra_studente(
        codice_scuola = dati.get("codice_scuola", ""),
        email         = dati.get("email", ""),
        nome_display  = dati.get("nome_display", ""),
        password      = dati.get("password", ""),
        classe        = dati.get("classe", ""),
    )
    status = 200 if ok else 400
    return jsonify({"ok": ok, "messaggio": msg}), status


@app.route("/api/registra/docente", methods=["POST"])
def api_registra_docente():
    """Registrazione nuovo docente."""
    dati = request.get_json() or {}
    ok, msg = auth.registra_docente(
        codice_scuola   = dati.get("codice_scuola", ""),
        username_scuola = dati.get("username_scuola", ""),
        nome_display    = dati.get("nome_display", ""),
        password        = dati.get("password", ""),
        materia         = dati.get("materia", ""),
    )
    status = 200 if ok else 400
    return jsonify({"ok": ok, "messaggio": msg}), status


# ══════════════════════════════════════════════════════════════════════
# ENDPOINT: ORARIO
# ══════════════════════════════════════════════════════════════════════

@app.route("/api/orario/<classe>", methods=["GET"])
@richiedi_auth
def api_get_orario(classe):
    """Legge l'orario di una classe."""
    with _file_lock:
        root  = carica_orario()
        state = cls_data(root, classe.upper())
    return jsonify(state.get("orario", {}))


@app.route("/api/orario/<classe>", methods=["PUT"])
@richiedi_docente
def api_set_orario(classe):
    """Aggiorna l'orario di una classe (solo docenti)."""
    nuovo_orario = request.get_json() or {}
    with _file_lock:
        root  = carica_orario()
        state = cls_data(root, classe.upper())
        # Normalizza chiavi int
        state["orario"] = {
            g: {int(h): v for h, v in ore.items()}
            for g, ore in nuovo_orario.items()
        }
        salva_orario(root)
    return jsonify({"ok": True})


# ══════════════════════════════════════════════════════════════════════
# ENDPOINT: REGISTRO
# ══════════════════════════════════════════════════════════════════════

@app.route("/api/registro/<classe>/<data_str>", methods=["GET"])
@richiedi_auth
def api_get_registro(classe, data_str):
    """Legge il registro di un giorno (formato: YYYY-MM-DD)."""
    with _file_lock:
        root  = carica_orario()
        state = cls_data(root, classe.upper())
        reg   = state.get("registro", {}).get(data_str, {
            "argomenti": "", "compiti": "", "assenti": []
        })
    return jsonify(reg)


@app.route("/api/registro/<classe>/<data_str>", methods=["PUT"])
@richiedi_docente
def api_set_registro(classe, data_str):
    """Aggiorna il registro di un giorno (solo docenti)."""
    dati = request.get_json() or {}
    with _file_lock:
        root  = carica_orario()
        state = cls_data(root, classe.upper())
        state["registro"].setdefault(data_str, {"argomenti": "", "compiti": "", "assenti": []})
        reg = state["registro"][data_str]
        if "argomenti" in dati: reg["argomenti"] = dati["argomenti"]
        if "compiti"   in dati: reg["compiti"]   = dati["compiti"]
        if "assenti"   in dati: reg["assenti"]   = dati["assenti"]
        salva_orario(root)
    return jsonify({"ok": True})


# ══════════════════════════════════════════════════════════════════════
# ENDPOINT: VERIFICHE
# ══════════════════════════════════════════════════════════════════════

@app.route("/api/verifiche/<classe>", methods=["GET"])
@richiedi_auth
def api_get_verifiche(classe):
    with _file_lock:
        root  = carica_orario()
        state = cls_data(root, classe.upper())
    return jsonify(state.get("verifiche", []))


@app.route("/api/verifiche/<classe>", methods=["POST"])
@richiedi_docente
def api_add_verifica(classe):
    dati = request.get_json() or {}
    with _file_lock:
        root  = carica_orario()
        state = cls_data(root, classe.upper())
        state["verifiche"].append(dati)
        salva_orario(root)
    return jsonify({"ok": True})


@app.route("/api/verifiche/<classe>/<int:idx>", methods=["DELETE"])
@richiedi_docente
def api_del_verifica(classe, idx):
    with _file_lock:
        root  = carica_orario()
        state = cls_data(root, classe.upper())
        if 0 <= idx < len(state["verifiche"]):
            state["verifiche"].pop(idx)
            salva_orario(root)
    return jsonify({"ok": True})


# ══════════════════════════════════════════════════════════════════════
# ENDPOINT: INTERROGAZIONI
# ══════════════════════════════════════════════════════════════════════

@app.route("/api/interrogazioni/<classe>", methods=["GET"])
@richiedi_auth
def api_get_interrogazioni(classe):
    with _file_lock:
        root  = carica_orario()
        state = cls_data(root, classe.upper())
    return jsonify(state.get("interrogazioni", []))


@app.route("/api/interrogazioni/<classe>", methods=["POST"])
@richiedi_docente
def api_add_interrogazione(classe):
    dati = request.get_json() or {}
    with _file_lock:
        root  = carica_orario()
        state = cls_data(root, classe.upper())
        state["interrogazioni"].append(dati)
        salva_orario(root)
    return jsonify({"ok": True})


@app.route("/api/interrogazioni/<classe>/<int:idx>", methods=["DELETE"])
@richiedi_docente
def api_del_interrogazione(classe, idx):
    with _file_lock:
        root  = carica_orario()
        state = cls_data(root, classe.upper())
        if 0 <= idx < len(state["interrogazioni"]):
            state["interrogazioni"].pop(idx)
            salva_orario(root)
    return jsonify({"ok": True})


@app.route("/api/interrogazioni/<classe>/<int:idx>/assegna", methods=["POST"])
@richiedi_auth
def api_assegna_interrogazione(classe, idx):
    """Lo studente conferma la sua data di interrogazione."""
    dati      = request.get_json() or {}
    nome_s    = dati.get("nome_studente", "")
    giorno_s  = dati.get("giorno_settimana", "")
    if not nome_s or not giorno_s:
        return jsonify({"errore": "Dati mancanti"}), 400
    with _file_lock:
        root  = carica_orario()
        state = cls_data(root, classe.upper())
        interr = state["interrogazioni"]
        if 0 <= idx < len(interr):
            interr[idx].setdefault("assegnazioni", {})[nome_s] = giorno_s
            salva_orario(root)
    return jsonify({"ok": True})


# ══════════════════════════════════════════════════════════════════════
# ENDPOINT: STATO SERVER / PING
# ══════════════════════════════════════════════════════════════════════

@app.route("/api/ping", methods=["GET"])
def api_ping():
    """Ping per verificare la raggiungibilità del server."""
    return jsonify({
        "ok":        True,
        "server":    "Piattaforma Scolastica AI",
        "versione":  "1.0",
        "timestamp": datetime.now().isoformat(),
        "ip":        get_local_ip(),
    })


@app.route("/api/classi", methods=["GET"])
@richiedi_auth
def api_get_classi():
    """Lista di tutte le classi disponibili."""
    with _file_lock:
        root = carica_orario()
    return jsonify(list(root.get("classi", {}).keys()))


# ══════════════════════════════════════════════════════════════════════
# AVVIO SERVER
# ══════════════════════════════════════════════════════════════════════

def avvia_server(host: str = "0.0.0.0", port: int = 5000, debug: bool = False):
    """
    Avvia il server Flask sulla LAN.
    host="0.0.0.0" → raggiungibile da tutti i dispositivi sulla rete.
    """
    local_ip = get_local_ip()
    print("=" * 60)
    print("  🏫  PIATTAFORMA SCOLASTICA AI — SERVER LAN")
    print("=" * 60)
    print(f"  📡  IP del server:   {local_ip}")
    print(f"  🌐  URL locale:      http://{local_ip}:{port}")
    print(f"  💻  URL sul server:  http://localhost:{port}")
    print()
    print("  Gli altri dispositivi sulla stessa rete Wi-Fi/LAN")
    print(f"  possono connettersi a: http://{local_ip}:{port}")
    print()
    print("  📋  Endpoint disponibili:")
    print("       POST  /api/login")
    print("       POST  /api/registra/studente")
    print("       POST  /api/registra/docente")
    print("       GET   /api/orario/<classe>")
    print("       GET   /api/registro/<classe>/<data>")
    print("       GET   /api/verifiche/<classe>")
    print("       GET   /api/interrogazioni/<classe>")
    print("       GET   /api/ping")
    print("=" * 60)
    app.run(host=host, port=port, debug=debug, threaded=True)


if __name__ == "__main__":
    avvia_server(debug=True)
