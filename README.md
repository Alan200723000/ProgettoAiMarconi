# 🏫 Piattaforma Scolastica AI — Guida Setup

## Installazione dipendenze

```bash
pip install flet flask flask-cors
```

---

## Avvio

### Modalità standalone (solo locale)
```bash
python main.py
```
Il server Flask si avvia automaticamente in background sulla porta 5000.

### Modalità server dedicato (consigliata per LAN)
Apri due terminali:

**Terminale 1 — Server API:**
```bash
python server.py
```

**Terminale 2 — App Flet:**
```bash
python main.py
```

---

## Comunicazione in rete locale (LAN)

Il server Flask si mette in ascolto su `0.0.0.0:5000`, rendendosi raggiungibile da **tutti i dispositivi sulla stessa rete Wi-Fi o cablata**.

### Come trovare l'IP del server
| Sistema | Comando |
|---------|---------|
| Windows | `ipconfig` → cerca "Indirizzo IPv4" |
| Linux   | `ip addr` oppure `ifconfig` |
| macOS   | `ifconfig en0` |

### Esempio
Se il PC server ha IP `192.168.1.50`, gli altri dispositivi potranno accedere alle API su:
```
http://192.168.1.50:5000/api/ping
```

L'IP viene mostrato anche nella Home dell'app (banner 📡).

---

## Sistema di registrazione

### Studenti
Devono inserire:
1. **Codice scuola** (fornito dalla segreteria)
2. **Nome e Cognome**
3. **Email personale**
4. **Classe** (opzionale, es. 5F)
5. **Password** (min. 6 caratteri)

### Docenti
Devono inserire:
1. **Codice scuola** (fornito dall'amministrazione)
2. **Username istituzionale** (fornito dalla scuola, es. `m.rossi`)
3. **Nome e Cognome**
4. **Materia principale** (opzionale)
5. **Password** (min. 6 caratteri)

---

## Codici scuola validi

I codici validi sono definiti in `auth.py` nella variabile `CODICI_SCUOLA_VALIDI`:

```python
CODICI_SCUOLA_VALIDI = {
    "SCUOLA2024",
    "ISTITUTO5F",
    "LICEO2024",
    "TECNICO01",
}
```

Aggiungine altri a piacere. In una versione produzione questi andrebbero in un database o file di configurazione separato.

---

## Credenziali di test (credenziali.json)

| Username   | Password    | Ruolo    |
|------------|-------------|----------|
| `studente` | `studente123` | Studente |
| `docente`  | `docente123`  | Docente  |
| `admin`    | `admin`       | Docente  |

> ⚠️ Le password nel file sono in chiaro solo per compatibilità legacy. Le nuove registrazioni usano hash SHA-256.

---

## Endpoint API REST

| Metodo | Endpoint | Auth | Descrizione |
|--------|----------|------|-------------|
| GET    | `/api/ping` | No | Stato server |
| POST   | `/api/login` | No | Login → token |
| POST   | `/api/logout` | Token | Logout |
| POST   | `/api/registra/studente` | No | Nuova registrazione studente |
| POST   | `/api/registra/docente` | No | Nuova registrazione docente |
| GET    | `/api/classi` | Token | Lista classi |
| GET    | `/api/orario/<classe>` | Token | Leggi orario |
| PUT    | `/api/orario/<classe>` | Docente | Aggiorna orario |
| GET    | `/api/registro/<classe>/<data>` | Token | Leggi registro |
| PUT    | `/api/registro/<classe>/<data>` | Docente | Salva registro |
| GET    | `/api/verifiche/<classe>` | Token | Lista verifiche |
| POST   | `/api/verifiche/<classe>` | Docente | Aggiungi verifica |
| DELETE | `/api/verifiche/<classe>/<idx>` | Docente | Elimina verifica |
| GET    | `/api/interrogazioni/<classe>` | Token | Lista interrogazioni |
| POST   | `/api/interrogazioni/<classe>` | Docente | Apri periodo |
| POST   | `/api/interrogazioni/<classe>/<idx>/assegna` | Token | Studente conferma |

### Autenticazione
Usa il token ricevuto dal login nell'header:
```
Authorization: Bearer <token>
```

### Esempio login con curl
```bash
curl -X POST http://192.168.1.50:5000/api/login \
     -H "Content-Type: application/json" \
     -d '{"username":"studente","password":"studente123","ruolo":"studente"}'
```

---

## File modificati

| File | Modifiche |
|------|-----------|
| `auth.py` | Registrazione studenti/docenti, validazioni, hash password |
| `server.py` | **Nuovo** — Server Flask per comunicazione LAN |
| `main.py` | Schermate registrazione, avvio server in background |
| `credenziali.json` | Aggiornato con nuovi campi (codice_scuola, email, ecc.) |
