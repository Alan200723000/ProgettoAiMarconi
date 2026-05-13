# Piattaforma Scolastica AI

Applicazione desktop con **Flet** e **Ollama (llama3)** per la gestione del calendario scolastico.

## Struttura file

```
piattaforma_scolastica/
│
├── main.py                 ← Entry point — avvia l'app con:  python main.py
│
├── styles.py               ← Palette colori, costanti UI, icone
├── auth.py                 ← Autenticazione utenti (legge credenziali.json)
├── credenziali.json        ← Utenti, password e ruoli  ← MODIFICA QUI
│
├── utils_calendario.py     ← Persistenza orario.json, logica calcoli, Ollama
├── ui_helpers.py           ← Widget riutilizzabili (cal_tf, badge, pill…)
├── chatbot.py              ← Pannello chat AI laterale
├── registro.py             ← Pannelli registro docente e studente
└── calendario.py           ← Vista calendario completa (docente + studente)
```

## Dipendenze

```bash
pip install flet langchain-ollama langchain-community langchain chromadb
pip install SpeechRecognition gTTS pygame PyPDF2
```

Ollama deve essere in esecuzione:
```bash
ollama serve
ollama pull llama3
```

## Credenziali

Modifica `credenziali.json` per aggiungere o modificare utenti:

```json
{
  "utenti": {
    "mario": {
      "password": "secret",
      "ruolo": "studente",
      "nome_display": "Mario Rossi"
    },
    "prof_bianchi": {
      "password": "secret2",
      "ruolo": "docente",
      "nome_display": "Prof. Bianchi"
    }
  }
}
```

I ruoli validi sono `"studente"` e `"docente"`.

## Gestione credenziali via codice

```python
from auth import aggiungi_utente, rimuovi_utente, verifica_login

# Aggiunge un utente
aggiungi_utente("nuovostudente", "password123", "studente", "Luca Verdi")

# Verifica login
ok, errore = verifica_login("mario", "secret", "studente")

# Rimuove un utente
rimuovi_utente("nuovostudente")
```

## Dati salvati

- `orario.json` — orario, verifiche, interrogazioni e registro (creato automaticamente)
- `credenziali.json` — utenti (da creare/modificare manualmente o via `auth.py`)
