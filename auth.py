# ══════════════════════════════════════════════════════════════════════
# auth.py — Autenticazione utenti da credenziali.json
# ══════════════════════════════════════════════════════════════════════

import json
import os

CREDENZIALI_FILE = "credenziali.json"


def _carica_credenziali() -> dict:
    """Carica il dizionario utenti da credenziali.json."""
    if not os.path.exists(CREDENZIALI_FILE):
        raise FileNotFoundError(
            f"File '{CREDENZIALI_FILE}' non trovato. "
            "Crea il file con la struttura: {\"utenti\": {\"nome\": {\"password\": ..., \"ruolo\": ...}}}"
        )
    with open(CREDENZIALI_FILE, encoding="utf-8") as f:
        data = json.load(f)
    return data.get("utenti", {})


def verifica_login(username: str, password: str, ruolo_atteso: str) -> tuple[bool, str]:
    """
    Verifica le credenziali.
    Ritorna (successo: bool, messaggio_errore: str).
    Se successo è True il messaggio è vuoto.
    """
    try:
        utenti = _carica_credenziali()
    except FileNotFoundError as e:
        return False, f"❌ {e}"

    if username not in utenti:
        return False, "❌ Utente non trovato."

    utente = utenti[username]

    if utente["password"] != password:
        return False, "❌ Password errata."

    if utente["ruolo"] != ruolo_atteso:
        ruolo_reale = utente["ruolo"]
        return False, (
            f"❌ Credenziali di un {ruolo_reale}. "
            f"Accedi come {ruolo_atteso} o cambia ruolo."
        )

    return True, ""


def get_nome_display(username: str) -> str:
    """Ritorna il nome leggibile dell'utente, o il solo username se assente."""
    try:
        utenti = _carica_credenziali()
        return utenti.get(username, {}).get("nome_display", username)
    except Exception:
        return username


def get_tutti_utenti() -> dict:
    """Ritorna l'intero dizionario utenti (per uso admin/debug)."""
    try:
        return _carica_credenziali()
    except Exception:
        return {}


def aggiungi_utente(username: str, password: str, ruolo: str, nome_display: str = "") -> bool:
    """
    Aggiunge un nuovo utente a credenziali.json.
    Ritorna True se salvato con successo, False altrimenti.
    """
    try:
        if os.path.exists(CREDENZIALI_FILE):
            with open(CREDENZIALI_FILE, encoding="utf-8") as f:
                data = json.load(f)
        else:
            data = {"utenti": {}}

        data["utenti"][username] = {
            "password": password,
            "ruolo": ruolo,
            "nome_display": nome_display or username
        }

        with open(CREDENZIALI_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"Errore salvataggio credenziali: {e}")
        return False


def rimuovi_utente(username: str) -> bool:
    """Rimuove un utente da credenziali.json."""
    try:
        with open(CREDENZIALI_FILE, encoding="utf-8") as f:
            data = json.load(f)
        if username in data["utenti"]:
            del data["utenti"][username]
            with open(CREDENZIALI_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"Errore rimozione utente: {e}")
        return False
