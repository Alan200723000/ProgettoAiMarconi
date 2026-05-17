# ══════════════════════════════════════════════════════════════════════
# auth.py — Autenticazione e registrazione utenti
# Studenti: codice scuola + email + password
# Docenti:  codice scuola + username (fornito dalla scuola) + password
# ══════════════════════════════════════════════════════════════════════

import json
import os
import hashlib
import re
import secrets
from datetime import datetime

CREDENZIALI_FILE = "credenziali.json"

# Codici scuola validi (puoi aggiungerne altri o caricarli da un file)
CODICI_SCUOLA_VALIDI = {
    "SCUOLA2024",
    "ISTITUTO5F",
    "LICEO2024",
    "TECNICO01",
}


# ── Hashing password ──────────────────────────────────────────────────

def _hash_password(password: str) -> str:
    """Hash SHA-256 della password."""
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def _verifica_password(password: str, hashed: str) -> bool:
    """Verifica password contro hash. Supporta anche password in chiaro (legacy)."""
    # Supporto legacy: password in chiaro (per credenziali.json pre-esistente)
    if len(hashed) != 64:
        return password == hashed
    return hashlib.sha256(password.encode("utf-8")).hexdigest() == hashed


# ── Caricamento credenziali ───────────────────────────────────────────

def _carica_credenziali() -> dict:
    """Carica il dizionario utenti da credenziali.json."""
    if not os.path.exists(CREDENZIALI_FILE):
        data = {"utenti": {}, "scuole": {}}
        with open(CREDENZIALI_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return {}
    with open(CREDENZIALI_FILE, encoding="utf-8") as f:
        data = json.load(f)
    return data.get("utenti", {})


def _carica_tutto() -> dict:
    """Carica l'intero file credenziali."""
    if not os.path.exists(CREDENZIALI_FILE):
        return {"utenti": {}, "scuole": {}}
    with open(CREDENZIALI_FILE, encoding="utf-8") as f:
        return json.load(f)


def _salva_tutto(data: dict) -> None:
    with open(CREDENZIALI_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ── Validazione ───────────────────────────────────────────────────────

def valida_email(email: str) -> bool:
    """Validazione base formato email."""
    pattern = r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$"
    return bool(re.match(pattern, email.strip()))


def valida_password(password: str) -> tuple[bool, str]:
    """
    Verifica che la password rispetti i requisiti minimi.
    Ritorna (valida, messaggio_errore).
    """
    if len(password) < 6:
        return False, "⚠️ La password deve avere almeno 6 caratteri."
    if len(password) > 128:
        return False, "⚠️ La password è troppo lunga."
    return True, ""


def valida_codice_scuola(codice: str) -> bool:
    """Verifica che il codice scuola sia tra quelli validi."""
    return codice.strip().upper() in CODICI_SCUOLA_VALIDI


# ── Login ─────────────────────────────────────────────────────────────

def verifica_login(username: str, password: str, ruolo_atteso: str) -> tuple[bool, str]:
    """
    Verifica le credenziali.
    Per studenti, username può essere l'email.
    Ritorna (successo: bool, messaggio_errore: str).
    """
    try:
        utenti = _carica_credenziali()
    except Exception as e:
        return False, f"❌ Errore caricamento credenziali: {e}"

    # Cerca per username diretto o per email (studenti)
    utente = None
    chiave = None

    username_lower = username.strip().lower()

    if username_lower in utenti:
        utente = utenti[username_lower]
        chiave = username_lower
    else:
        # Cerca per email
        for k, u in utenti.items():
            if u.get("email", "").lower() == username_lower:
                utente = u
                chiave = k
                break

    if utente is None:
        return False, "❌ Utente non trovato."

    if not _verifica_password(password, utente.get("password", "")):
        return False, "❌ Password errata."

    ruolo_reale = utente.get("ruolo", "")
    if ruolo_reale != ruolo_atteso:
        return False, (
            f"❌ Questo account è registrato come {ruolo_reale}. "
            f"Seleziona '{ruolo_reale}' per accedere."
        )

    return True, ""


# ── Registrazione Studente ────────────────────────────────────────────

def registra_studente(
    codice_scuola: str,
    email: str,
    nome_display: str,
    password: str,
    classe: str = "",
) -> tuple[bool, str]:
    """
    Registra un nuovo studente.
    Ritorna (successo, messaggio).
    """
    codice_scuola = codice_scuola.strip().upper()
    email         = email.strip().lower()
    nome_display  = nome_display.strip()
    password      = password.strip()
    classe        = classe.strip().upper()

    # Validazioni
    if not valida_codice_scuola(codice_scuola):
        return False, "❌ Codice scuola non valido. Contatta la tua scuola."

    if not valida_email(email):
        return False, "❌ Formato email non valido."

    if not nome_display:
        return False, "❌ Inserisci il tuo nome completo."

    ok, msg = valida_password(password)
    if not ok:
        return False, msg

    data = _carica_tutto()
    utenti = data.get("utenti", {})

    # Controlla email duplicata
    for u in utenti.values():
        if u.get("email", "").lower() == email:
            return False, "❌ Questa email è già registrata."

    # Username = parte locale dell'email (univoca)
    username = email.split("@")[0] + "_" + secrets.token_hex(3)

    utenti[username] = {
        "password":      _hash_password(password),
        "ruolo":         "studente",
        "nome_display":  nome_display,
        "email":         email,
        "codice_scuola": codice_scuola,
        "classe":        classe,
        "registrato_il": datetime.now().isoformat(),
    }

    data["utenti"] = utenti
    _salva_tutto(data)
    return True, f"✅ Registrazione completata! Benvenuto, {nome_display}."


# ── Registrazione Docente ─────────────────────────────────────────────

def registra_docente(
    codice_scuola: str,
    username_scuola: str,
    nome_display: str,
    password: str,
    materia: str = "",
) -> tuple[bool, str]:
    """
    Registra un nuovo docente con username fornito dalla scuola.
    Ritorna (successo, messaggio).
    """
    codice_scuola   = codice_scuola.strip().upper()
    username_scuola = username_scuola.strip().lower()
    nome_display    = nome_display.strip()
    password        = password.strip()
    materia         = materia.strip()

    # Validazioni
    if not valida_codice_scuola(codice_scuola):
        return False, "❌ Codice scuola non valido. Contatta l'amministrazione."

    if len(username_scuola) < 3:
        return False, "❌ Username deve avere almeno 3 caratteri."

    if not re.match(r"^[a-z0-9._\-]+$", username_scuola):
        return False, "❌ Username può contenere solo lettere, numeri, punti e trattini."

    if not nome_display:
        return False, "❌ Inserisci il tuo nome completo."

    ok, msg = valida_password(password)
    if not ok:
        return False, msg

    data = _carica_tutto()
    utenti = data.get("utenti", {})

    if username_scuola in utenti:
        return False, "❌ Questo username è già in uso. Contatta l'amministrazione."

    utenti[username_scuola] = {
        "password":        _hash_password(password),
        "ruolo":           "docente",
        "nome_display":    nome_display,
        "email":           "",
        "codice_scuola":   codice_scuola,
        "materia":         materia,
        "registrato_il":   datetime.now().isoformat(),
    }

    data["utenti"] = utenti
    _salva_tutto(data)
    return True, f"✅ Account docente creato! Benvenuto, {nome_display}."


# ── Helpers ───────────────────────────────────────────────────────────

def get_nome_display(username: str) -> str:
    """Ritorna il nome leggibile dell'utente."""
    try:
        utenti = _carica_credenziali()
        # Cerca per username o email
        if username in utenti:
            return utenti[username].get("nome_display", username)
        for u in utenti.values():
            if u.get("email", "").lower() == username.lower():
                return u.get("nome_display", username)
        return username
    except Exception:
        return username


def get_username_da_login(login: str) -> str:
    """Dato un login (username o email) ritorna la chiave interna."""
    try:
        utenti = _carica_credenziali()
        login_lower = login.strip().lower()
        if login_lower in utenti:
            return login_lower
        for k, u in utenti.items():
            if u.get("email", "").lower() == login_lower:
                return k
        return login_lower
    except Exception:
        return login.lower()


def get_tutti_utenti() -> dict:
    """Ritorna l'intero dizionario utenti."""
    try:
        return _carica_credenziali()
    except Exception:
        return {}


def aggiungi_utente(username: str, password: str, ruolo: str, nome_display: str = "") -> bool:
    """Aggiunge manualmente un utente (admin/debug)."""
    try:
        data = _carica_tutto()
        data.setdefault("utenti", {})[username] = {
            "password":     _hash_password(password),
            "ruolo":        ruolo,
            "nome_display": nome_display or username,
        }
        _salva_tutto(data)
        return True
    except Exception as e:
        print(f"Errore salvataggio: {e}")
        return False


def rimuovi_utente(username: str) -> bool:
    """Rimuove un utente."""
    try:
        data = _carica_tutto()
        if username in data.get("utenti", {}):
            del data["utenti"][username]
            _salva_tutto(data)
        return True
    except Exception as e:
        print(f"Errore rimozione: {e}")
        return False
