import flet as ft
import os
import re
import threading
import warnings
import webbrowser
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

# ── Dipendenze audio ──────────────────────────────────────
# pip install SpeechRecognition pyaudio gTTS pygame
import speech_recognition as sr
import tempfile
import base64

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
CARTELLA_MAPPE  = "mappe_generate"
CARTELLA_AUDIO  = "audio_risposte"
os.makedirs(CARTELLA_MAPPE,  exist_ok=True)
os.makedirs(CARTELLA_AUDIO,  exist_ok=True)

# ─────────────────────────────────────────────
# CREDENZIALI
# ─────────────────────────────────────────────
UTENTI = {
    "studente1": {"password": "prova1", "ruolo": "studente"},
    "docente1":  {"password": "prova1", "ruolo": "docente"},
}

# ─────────────────────────────────────────────
# MOTORE AI
# ─────────────────────────────────────────────
def inizializza_ai():
    percorso_conoscenza = "conoscenza.txt"
    if not os.path.exists(percorso_conoscenza):
        with open(percorso_conoscenza, "w", encoding="utf-8") as f:
            f.write("AI Workspace: Sistema educativo per analisi PDF e mappe concettuali con Ollama.")
    try:
        loader = TextLoader(percorso_conoscenza, encoding="utf-8")
        docs   = loader.load()
        splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
        chunks = splitter.split_documents(docs)
        emb    = OllamaEmbeddings(model="llama3")
        vectorstore = Chroma.from_documents(documents=chunks, embedding=emb)
        return vectorstore.as_retriever()
    except Exception as e:
        print(f"Errore inizializzazione RAG: {e}")
        return None

retriever  = inizializza_ai()
llm        = OllamaLLM(model="llama3")
prompt_chat = ChatPromptTemplate.from_template(
    "Contesto: {context}\nDomanda: {question}\nRispondi in italiano in modo chiaro e conciso."
)

if retriever:
    rag_chain = (
        {"context": retriever, "question": RunnablePassthrough()}
        | prompt_chat
        | llm
        | StrOutputParser()
    )
else:
    rag_chain = None

# ─────────────────────────────────────────────
# FILE DIALOG PDF
# ─────────────────────────────────────────────
def apri_dialogo_pdf() -> list:
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    percorsi = filedialog.askopenfilenames(
        title="Seleziona uno o più PDF",
        filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")]
    )
    root.destroy()
    return list(percorsi)

# ─────────────────────────────────────────────
# RICONOSCIMENTO VOCALE
# ─────────────────────────────────────────────
recognizer = sr.Recognizer()

def trascrivi_audio() -> str:
    """Registra dal microfono e restituisce il testo trascritto."""
    try:
        with sr.Microphone() as source:
            recognizer.adjust_for_ambient_noise(source, duration=0.5)
            audio = recognizer.listen(source, timeout=10, phrase_time_limit=30)
        testo = recognizer.recognize_google(audio, language="it-IT")
        return testo
    except sr.WaitTimeoutError:
        return "__TIMEOUT__"
    except sr.UnknownValueError:
        return "__NON_CAPITO__"
    except sr.RequestError as e:
        return f"__ERRORE__:{e}"
    except Exception as e:
        return f"__ERRORE__:{e}"

# ─────────────────────────────────────────────
# TEXT-TO-SPEECH
# ─────────────────────────────────────────────
_audio_counter = 0

def genera_audio_risposta(testo: str) -> str | None:
    """Genera un file MP3 dal testo e ne restituisce il percorso assoluto."""
    global _audio_counter
    if not TTS_DISPONIBILE:
        return None
    try:
        # Accorcia il testo se troppo lungo per TTS
        testo_tts = testo[:1200].strip()
        # Rimuovi eventuale markdown grossolano
        testo_tts = re.sub(r"\*{1,2}([^*]+)\*{1,2}", r"\1", testo_tts)
        testo_tts = re.sub(r"_{1,2}([^_]+)_{1,2}", r"\1", testo_tts)
        testo_tts = re.sub(r"#{1,6}\s*", "", testo_tts)
        testo_tts = re.sub(r"`([^`]+)`", r"\1", testo_tts)

        _audio_counter += 1
        nome_file = f"risposta_{_audio_counter:04d}.mp3"
        percorso  = os.path.join(CARTELLA_AUDIO, nome_file)
        tts = gTTS(text=testo_tts, lang="it", slow=False)
        tts.save(percorso)
        return os.path.abspath(percorso)
    except Exception as e:
        print(f"Errore TTS: {e}")
        return None

def riproduci_audio(percorso: str):
    """Riproduce un file MP3 tramite pygame (non blocca il thread principale)."""
    if not PYGAME_DISPONIBILE or not percorso or not os.path.exists(percorso):
        return
    def _play():
        try:
            pygame.mixer.music.load(percorso)
            pygame.mixer.music.play()
        except Exception as e:
            print(f"Errore riproduzione: {e}")
    threading.Thread(target=_play, daemon=True).start()

# ─────────────────────────────────────────────
# PARSING RELAZIONI
# ─────────────────────────────────────────────
def estrai_relazioni(testo_llm: str) -> list:
    relazioni = []
    pattern = re.compile(r"(.+?)\s*->\s*(.+?)(?:\s*\[(.+?)\])?$")
    for riga in testo_llm.splitlines():
        riga = riga.strip().strip('"').strip("'")
        m = pattern.match(riga)
        if m:
            src   = m.group(1).strip()
            dst   = m.group(2).strip()
            label = m.group(3).strip() if m.group(3) else ""
            if src and dst:
                relazioni.append((src, dst, label))
    return relazioni

# ─────────────────────────────────────────────
# MAPPA PYVIS
# ─────────────────────────────────────────────
def crea_mappa_pyvis(relazioni: list, nome_file: str = "mappa.html") -> str:
    net = Network(
        height="700px", width="100%",
        bgcolor="#0f172a", font_color="#f8fafc",
        directed=True, notebook=False,
    )
    net.set_options("""
    {
      "nodes": {
        "shape": "box",
        "color": {
          "background": "#1e40af", "border": "#3b82f6",
          "highlight": {"background": "#2563eb", "border": "#60a5fa"}
        },
        "font": {"size": 14, "color": "#f8fafc", "face": "monospace"},
        "margin": 10, "shadow": true
      },
      "edges": {
        "color": {"color": "#475569", "highlight": "#60a5fa"},
        "arrows": {"to": {"enabled": true, "scaleFactor": 1.2}},
        "font": {"size": 11, "color": "#94a3b8", "align": "middle"},
        "smooth": {"type": "curvedCW", "roundness": 0.2}, "shadow": true
      },
      "physics": {
        "enabled": true,
        "barnesHut": {
          "gravitationalConstant": -8000, "centralGravity": 0.3,
          "springLength": 150, "springConstant": 0.04, "damping": 0.09
        }
      },
      "interaction": {"hover": true, "navigationButtons": true, "keyboard": true}
    }
    """)
    nodi = set()
    for src, dst, label in relazioni:
        if src not in nodi:
            net.add_node(src, label=src, title=f"<b>{src}</b>")
            nodi.add(src)
        if dst not in nodi:
            net.add_node(dst, label=dst, title=f"<b>{dst}</b>")
            nodi.add(dst)
        net.add_edge(src, dst, label=label, title=label)
    percorso = os.path.join(CARTELLA_MAPPE, nome_file)
    net.save_graph(percorso)
    return os.path.abspath(percorso)

# ─────────────────────────────────────────────
# APP FLET
# ─────────────────────────────────────────────
def main(page: ft.Page):
    page.title        = "AI Workspace — Mappe Concettuali"
    page.theme_mode   = ft.ThemeMode.DARK
    page.bgcolor      = "#0f172a"
    page.window_width  = 1200
    page.window_height = 850

    # ─────────────────────────────────────────
    # SCHERMATA DI LOGIN
    # ─────────────────────────────────────────
    def mostra_login():
        page.controls.clear()

        # Stato selezione ruolo: None = nessuno scelto ancora
        ruolo_selezionato = {"valore": None}

        # ── Form credenziali (nascosto finché non si sceglie il ruolo) ──
        campo_utente = ft.TextField(
            label="Nome utente", width=340, border_radius=12,
            filled=True, fill_color="#1e293b", border_color="#334155",
            focused_border_color="#3b82f6", color="#f8fafc",
            label_style=ft.TextStyle(color="#64748b"), cursor_color="#3b82f6",
            on_submit=lambda e: campo_password.focus(),
        )
        campo_password = ft.TextField(
            label="Password", password=True, can_reveal_password=True,
            width=340, border_radius=12, filled=True, fill_color="#1e293b",
            border_color="#334155", focused_border_color="#3b82f6",
            color="#f8fafc", label_style=ft.TextStyle(color="#64748b"),
            cursor_color="#3b82f6", on_submit=lambda e: esegui_login(e),
        )
        messaggio_errore = ft.Text("", color="#ef4444", size=13)

        # Titolo dinamico del form (mostra quale ruolo è stato scelto)
        titolo_form = ft.Text("", size=15, color="#94a3b8", italic=True)

        # Contenitore form — visibile solo dopo la scelta del ruolo
        form_login = ft.Column(
            [
                titolo_form,
                campo_utente,
                campo_password,
                messaggio_errore,
                ft.Container(height=2),
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=12,
            visible=False,
        )

        btn_accedi = ft.ElevatedButton(
            "Accedi", bgcolor="#1e40af", color="#f8fafc", width=340,
            visible=False,
            on_click=lambda e: esegui_login(e),
        )

        btn_indietro = ft.TextButton(
            "← Cambia ruolo",
            style=ft.ButtonStyle(color={"": "#475569"}),
            visible=False,
            on_click=lambda e: torna_selezione(),
        )

        def esegui_login(e):
            utente = campo_utente.value.strip()
            pwd    = campo_password.value.strip()
            ruolo_atteso = ruolo_selezionato["valore"]

            if (
                utente in UTENTI
                and UTENTI[utente]["password"] == pwd
                and UTENTI[utente]["ruolo"] == ruolo_atteso
            ):
                mostra_workspace(utente, ruolo_atteso)
            else:
                # Messaggio specifico se le credenziali sono dell'altro ruolo
                if utente in UTENTI and UTENTI[utente]["ruolo"] != ruolo_atteso:
                    messaggio_errore.value = (
                        f"❌ Queste credenziali appartengono a un {UTENTI[utente]['ruolo']}. "
                        f"Accedi come {ruolo_atteso} o cambia ruolo."
                    )
                else:
                    messaggio_errore.value = "❌ Credenziali non valide. Riprova."
                campo_password.value = ""
                page.update()

        # ── Card ruolo ────────────────────────────────────────────────
        def crea_card_ruolo(
            icona: str,
            etichetta: str,
            ruolo: str,
            colore_bg: str,
            colore_bordo: str,
            colore_hover: str,
            hint_account: str,
        ) -> ft.Container:
            """Restituisce una card cliccabile per la scelta del ruolo."""

            card = ft.Container(
                width=160,
                height=175,
                border_radius=18,
                bgcolor=colore_bg,
                border=ft.border.all(2, colore_bordo),
                content=ft.Column(
                    [
                        ft.Text(icona, size=48),
                        ft.Text(
                            etichetta,
                            size=18,
                            weight=ft.FontWeight.BOLD,
                            color="#f8fafc",
                        ),
                        ft.Text(hint_account, size=10, color="#94a3b8", italic=True),
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    alignment=ft.MainAxisAlignment.CENTER,
                    spacing=6,
                ),
                ink=True,
                on_click=lambda e, r=ruolo, l=etichetta, icon=icona: scegli_ruolo(r, l, icon),
                shadow=ft.BoxShadow(
                    spread_radius=1, blur_radius=16,
                    color=colore_bordo + "55",
                    offset=ft.Offset(0, 4),
                ),
            )
            # Hover: cambia bgcolor (compatibile con tutte le versioni di Flet)
            def _on_hover(e, c=card, ch=colore_hover, co=colore_bg):
                c.bgcolor = ch if e.data == "true" else co
                page.update()
            card.on_hover = _on_hover
            return card

        card_studenti = crea_card_ruolo(
            icona="👨‍🎓",
            etichetta="Studenti",
            ruolo="studente",
            colore_bg="#064e3b",
            colore_bordo="#10b981",
            colore_hover="#065f46",
            hint_account="studente1 / prova1",
        )
        card_docenti = crea_card_ruolo(
            icona="👨‍🏫",
            etichetta="Docenti",
            ruolo="docente",
            colore_bg="#1e1b4b",
            colore_bordo="#818cf8",
            colore_hover="#2d2a6e",
            hint_account="docente1 / prova1",
        )

        riga_card = ft.Row(
            [card_studenti, card_docenti],
            alignment=ft.MainAxisAlignment.CENTER,
            spacing=28,
        )

        sottotitolo_selezione = ft.Text(
            "Seleziona il tuo ruolo per accedere",
            size=13,
            color="#475569",
            italic=True,
        )

        def scegli_ruolo(ruolo: str, etichetta: str, icona: str):
            ruolo_selezionato["valore"] = ruolo
            # Nascondi le card e mostra il form
            riga_card.visible              = False
            sottotitolo_selezione.visible  = False
            form_login.visible             = True
            btn_accedi.visible             = True
            btn_indietro.visible           = True
            titolo_form.value = f"{icona}  Accesso {etichetta} — inserisci le credenziali"
            messaggio_errore.value         = ""
            campo_utente.value             = ""
            campo_password.value           = ""
            page.update()
            campo_utente.focus()

        def torna_selezione():
            ruolo_selezionato["valore"]   = None
            riga_card.visible             = True
            sottotitolo_selezione.visible = True
            form_login.visible            = False
            btn_accedi.visible            = False
            btn_indietro.visible          = False
            messaggio_errore.value        = ""
            page.update()

        page.add(
            ft.Container(
                content=ft.Column(
                    [
                        ft.Text("🗺️", size=52),
                        ft.Text(
                            "AI Workspace",
                            size=30,
                            weight=ft.FontWeight.BOLD,
                            color="#f8fafc",
                        ),
                        ft.Text(
                            "Mappe Concettuali · Open Source · 100% Locale",
                            size=13,
                            color="#475569",
                        ),
                        ft.Container(height=24),
                        # ── Selezione ruolo ──
                        sottotitolo_selezione,
                        riga_card,
                        # ── Form (appare dopo la scelta) ──
                        form_login,
                        btn_accedi,
                        btn_indietro,
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=16,
                ),
                alignment=ft.alignment.Alignment(0, 0),
                expand=True,
            )
        )
        page.update()

    # ─────────────────────────────────────────
    # WORKSPACE PRINCIPALE
    # ─────────────────────────────────────────
    def mostra_workspace(utente: str, ruolo: str):
        page.controls.clear()

        pdf_caricati    = {}
        registrazione_attiva = {"valore": False}

        chat_container    = ft.ListView(expand=True, spacing=15, auto_scroll=True)
        pdf_list_container = ft.Column(scroll=ft.ScrollMode.AUTO, spacing=6)

        # ── Messaggi ──────────────────────────────────────────────────
        def messaggio_ai(testo: str, con_audio: bool = True):
            """Mostra la risposta testuale e, se richiesto, genera e mostra l'audio."""

            # Genera traccia audio in background
            percorso_audio = None
            if con_audio and TTS_DISPONIBILE:
                percorso_audio = genera_audio_risposta(testo)

            # Costruisci i controlli del messaggio
            contenuto_msg = [ft.Markdown(testo, selectable=True)]

            # Aggiungi lettore audio se disponibile
            if percorso_audio:
                nome_audio = os.path.basename(percorso_audio)
                btn_ascolta = ft.ElevatedButton(
                    "🔊  Ascolta risposta",
                    bgcolor="#065f46",
                    color="#f8fafc",
                    style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10)),
                    on_click=lambda e, p=percorso_audio: riproduci_audio(p),
                )
                btn_ferma = ft.ElevatedButton(
                    "⏹  Stop",
                    bgcolor="#374151",
                    color="#f8fafc",
                    style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10)),
                    on_click=lambda e: _ferma_audio(),
                )
                btn_apri = ft.TextButton(
                    f"📁  {nome_audio}",
                    style=ft.ButtonStyle(color={"": "#6b7280"}),
                    on_click=lambda e, p=percorso_audio: webbrowser.open(f"file://{p}"),
                )
                riga_audio = ft.Container(
                    content=ft.Row(
                        [btn_ascolta, btn_ferma, btn_apri],
                        spacing=8,
                        wrap=True,
                    ),
                    bgcolor="#052e16",
                    padding=ft.padding.symmetric(horizontal=14, vertical=8),
                    border_radius=10,
                    border=ft.border.all(1, "#065f46"),
                )
                contenuto_msg.append(riga_audio)

            chat_container.controls.append(
                ft.Container(
                    content=ft.Column(contenuto_msg, spacing=10),
                    bgcolor="#1e293b",
                    padding=ft.padding.symmetric(horizontal=18, vertical=14),
                    border_radius=15,
                    width=700,
                )
            )
            page.update()

            # Riproduci automaticamente
            if percorso_audio:
                riproduci_audio(percorso_audio)

        def _ferma_audio():
            if PYGAME_DISPONIBILE:
                try:
                    pygame.mixer.music.stop()
                except Exception:
                    pass

        def messaggio_utente(testo: str):
            chat_container.controls.append(
                ft.Row(
                    [
                        ft.Container(
                            content=ft.Text(testo, color="#f8fafc"),
                            bgcolor="#2563eb",
                            padding=ft.padding.symmetric(horizontal=16, vertical=12),
                            border_radius=15,
                        )
                    ],
                    alignment=ft.MainAxisAlignment.END,
                )
            )
            page.update()

        def aggiungi_spinner(messaggio: str = "Elaborazione..."):
            spinner = ft.Container(
                content=ft.Row(
                    [
                        ft.ProgressRing(width=18, height=18, stroke_width=2, color="#3b82f6"),
                        ft.Text(messaggio, color="#64748b", italic=True, size=13),
                    ],
                    spacing=10,
                ),
                bgcolor="#1e293b", padding=14, border_radius=12, width=280,
            )
            chat_container.controls.append(spinner)
            page.update()
            return spinner

        def rimuovi_spinner(spinner):
            if spinner in chat_container.controls:
                chat_container.controls.remove(spinner)
            page.update()

        # ── Lista PDF ─────────────────────────────────────────────────
        def rinfresca_lista_pdf():
            pdf_list_container.controls.clear()
            if not pdf_caricati:
                pdf_list_container.controls.append(
                    ft.Text("Nessun PDF caricato", color="#475569", italic=True, size=12)
                )
            else:
                for nome in pdf_caricati:
                    parole    = len(pdf_caricati[nome].split())
                    nome_breve = nome if len(nome) < 22 else nome[:20] + "..."
                    pdf_list_container.controls.append(
                        ft.Container(
                            content=ft.Column(
                                [
                                    ft.Row(
                                        [
                                            ft.Text("📄", size=16),
                                            ft.Text(nome_breve, expand=True, size=13, color="#f1f5f9"),
                                            ft.TextButton(
                                                "✕",
                                                style=ft.ButtonStyle(color={"": "#ef4444"}),
                                                on_click=lambda e, n=nome: rimuovi_pdf(n),
                                            ),
                                        ],
                                        spacing=4,
                                    ),
                                    ft.Text(f"{parole:,} parole", color="#64748b", size=11),
                                ],
                                spacing=2,
                            ),
                            bgcolor="#1e293b", padding=10, border_radius=10,
                            border=ft.border.all(1, "#334155"),
                        )
                    )
            page.update()

        def rimuovi_pdf(nome: str):
            if nome in pdf_caricati:
                del pdf_caricati[nome]
                rinfresca_lista_pdf()
                messaggio_ai(f"🗑️ PDF **{nome}** rimosso.", con_audio=False)

        # ── Carica PDF ────────────────────────────────────────────────
        def carica_pdf_thread():
            percorsi = apri_dialogo_pdf()
            if not percorsi:
                return
            nuovi = []
            for percorso in percorsi:
                nome = os.path.basename(percorso)
                try:
                    reader = PyPDF2.PdfReader(percorso)
                    testo  = "\n".join(
                        (pagina.extract_text() or "") for pagina in reader.pages
                    ).strip()
                    if not testo:
                        messaggio_ai(f"⚠️ **{nome}**: nessun testo estraibile.", con_audio=False)
                        continue
                    pdf_caricati[nome] = testo
                    nuovi.append(nome)
                except Exception as ex:
                    messaggio_ai(f"❌ Errore **{nome}**: {ex}", con_audio=False)
            if nuovi:
                elenco = "\n".join(f"- **{n}**" for n in nuovi)
                messaggio_ai(
                    f"✅ Caricati {len(nuovi)} PDF:\n{elenco}\n\n"
                    "Ora puoi chiedere:\n"
                    "- `crea mappa concettuale`\n"
                    "- `analizza nomefile.pdf`\n"
                    "- Qualsiasi domanda sui contenuti"
                )
                rinfresca_lista_pdf()

        def carica_pdf(e):
            threading.Thread(target=carica_pdf_thread, daemon=True).start()

        # ── Logica AI ─────────────────────────────────────────────────
        def elaborazione_ai(input_utente: str):
            spinner = aggiungi_spinner()
            try:
                testo_min    = input_utente.lower()
                vuole_mappa  = any(p in testo_min for p in ["mappa", "schema", "grafo", "concettual", "visualizza"])
                match_singolo = re.search(r"analizza\s+(\S+\.pdf)", testo_min)

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

                    prompt_mappa = (
                        "Sei un assistente educativo esperto in mappe concettuali.\n"
                        "Analizza il testo seguente ed estrai i concetti principali e le loro relazioni.\n\n"
                        "Rispondi ESCLUSIVAMENTE con righe nel formato:\n"
                        "ConcettoA -> ConcettoB [tipo_relazione]\n\n"
                        "Non aggiungere spiegazioni o altro testo. Estrai almeno 15 relazioni.\n\n"
                        f"Testo:\n{testo_combinato}"
                    )

                    risposta_llm = llm.invoke(prompt_mappa)
                    relazioni    = estrai_relazioni(risposta_llm)
                    rimuovi_spinner(spinner)

                    if not relazioni:
                        messaggio_ai("⚠️ Nessuna relazione estratta. Verifica che il PDF abbia testo leggibile.")
                        return

                    nome_mappa   = "mappa_" + "_".join(list(testi.keys())[:2]).replace(" ", "_") + ".html"
                    percorso_html = crea_mappa_pyvis(relazioni, nome_mappa)
                    webbrowser.open(f"file://{percorso_html}")

                    def riapri(_):
                        webbrowser.open(f"file://{percorso_html}")

                    testo_esito = f"Mappa generata con {len(relazioni)} relazioni. Aperta nel browser. Trascina i nodi, fai zoom e clicca per esplorare."
                    percorso_audio_mappa = genera_audio_risposta(testo_esito) if TTS_DISPONIBILE else None

                    controlli_card = [
                        ft.Text(
                            f"🗺️ Mappa generata — {len(relazioni)} relazioni",
                            color="#10b981", weight=ft.FontWeight.BOLD, size=15,
                        ),
                        ft.Text(
                            "La mappa si è aperta nel browser.\nTrascina i nodi, fai zoom, clicca per esplorare.",
                            color="#94a3b8", size=13,
                        ),
                        ft.ElevatedButton(
                            "🌐  Riapri nel browser",
                            bgcolor="#1e40af", color="#f8fafc",
                            on_click=riapri,
                        ),
                    ]

                    if percorso_audio_mappa:
                        controlli_card.append(
                            ft.Row(
                                [
                                    ft.ElevatedButton(
                                        "🔊  Ascolta",
                                        bgcolor="#065f46", color="#f8fafc",
                                        on_click=lambda e, p=percorso_audio_mappa: riproduci_audio(p),
                                    ),
                                    ft.ElevatedButton(
                                        "⏹  Stop",
                                        bgcolor="#374151", color="#f8fafc",
                                        on_click=lambda e: _ferma_audio(),
                                    ),
                                ],
                                spacing=8,
                            )
                        )
                        riproduci_audio(percorso_audio_mappa)

                    chat_container.controls.append(
                        ft.Container(
                            content=ft.Column(controlli_card, spacing=8),
                            bgcolor="#1e293b", padding=16, border_radius=14,
                            border=ft.border.all(1, "#10b981"), width=520,
                        )
                    )
                    page.update()
                    return

                elif pdf_caricati and any(
                    p in testo_min for p in ["documento", "pdf", "testo", "contenuto", "parla", "dice", "riguarda"]
                ):
                    contesto_pdf = "\n\n".join(
                        f"[{nome}]\n{contenuto[:1500]}" for nome, contenuto in pdf_caricati.items()
                    )
                    prompt   = (
                        f"Rispondi in italiano basandoti SOLO sui documenti seguenti.\n\n"
                        f"Documenti:\n{contesto_pdf}\n\nDomanda: {input_utente}"
                    )
                    risposta = llm.invoke(prompt)
                    rimuovi_spinner(spinner)
                    messaggio_ai(risposta)

                else:
                    risposta = rag_chain.invoke(input_utente) if rag_chain else llm.invoke(input_utente)
                    rimuovi_spinner(spinner)
                    messaggio_ai(risposta)

            except Exception as err:
                rimuovi_spinner(spinner)
                messaggio_ai(f"⚠️ Errore: {err}", con_audio=False)

        # ── Input vocale ──────────────────────────────────────────────
        stato_mic = ft.Text("", color="#64748b", size=12, italic=True)

        def registra_vocale(e):
            if registrazione_attiva["valore"]:
                return  # già in ascolto

            registrazione_attiva["valore"] = True
            btn_mic.bgcolor = "#7f1d1d"
            btn_mic.text    = "⏺  Registrando..."
            stato_mic.value = "🎙️ In ascolto... parla ora"
            page.update()

            def _ascolta():
                testo = trascrivi_audio()
                registrazione_attiva["valore"] = False
                btn_mic.bgcolor = "#1e3a5f"
                btn_mic.text    = "🎤  Parla"
                stato_mic.value = ""
                page.update()

                if testo == "__TIMEOUT__":
                    messaggio_ai("⚠️ Nessun audio rilevato. Riprova.", con_audio=False)
                elif testo == "__NON_CAPITO__":
                    messaggio_ai("⚠️ Non ho capito. Parla più chiaramente e riprova.", con_audio=False)
                elif testo.startswith("__ERRORE__"):
                    messaggio_ai(f"⚠️ Errore microfono: {testo.split(':', 1)[-1]}", con_audio=False)
                else:
                    # Mostra il testo trascritto come se lo avesse scritto l'utente
                    chat_input.value = testo
                    page.update()
                    messaggio_utente(f"🎤 {testo}")
                    chat_input.value = ""
                    page.update()
                    threading.Thread(target=elaborazione_ai, args=(testo,), daemon=True).start()

            threading.Thread(target=_ascolta, daemon=True).start()

        # ── Invio testo ───────────────────────────────────────────────
        def gestisci_invio(e):
            testo = chat_input.value.strip()
            if not testo:
                return
            messaggio_utente(testo)
            chat_input.value = ""
            page.update()
            threading.Thread(target=elaborazione_ai, args=(testo,), daemon=True).start()

        # ── Controlli UI ──────────────────────────────────────────────
        chat_input = ft.TextField(
            hint_text="Carica PDF, poi chiedi 'crea mappa concettuale' o fai domande...",
            expand=True,
            on_submit=gestisci_invio,
            border_radius=14,
            filled=True,
            fill_color="#1e293b",
            border_color="#334155",
            focused_border_color="#3b82f6",
            color="#f8fafc",
            hint_style=ft.TextStyle(color="#475569"),
            cursor_color="#3b82f6",
        )

        btn_upload = ft.ElevatedButton(
            "📄  Carica PDF",
            bgcolor="#b91c1c", color="#f8fafc",
            on_click=carica_pdf,
        )

        btn_mic = ft.ElevatedButton(
            "🎤  Parla",
            bgcolor="#1e3a5f", color="#f8fafc",
            style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=12)),
            tooltip="Premi per dettare il comando vocalmente",
            on_click=registra_vocale,
        )

        btn_invia = ft.ElevatedButton(
            "➤",
            bgcolor="#1e40af", color="#f8fafc",
            on_click=gestisci_invio,
        )

        # ── Badge ruolo ───────────────────────────────────────────────
        badge_colore = "#6d28d9" if ruolo == "docente" else "#0f766e"
        badge_icona  = "👨‍🏫" if ruolo == "docente" else "👨‍🎓"
        badge_label  = f"{badge_icona}  {utente}  ({ruolo})"

        # ── Sidebar ───────────────────────────────────────────────────
        sidebar = ft.Container(
            content=ft.Column(
                [
                    ft.Text("📁  PDF CARICATI", weight=ft.FontWeight.BOLD, color="#60a5fa", size=13),
                    ft.Divider(color="#1e293b", height=1),
                    pdf_list_container,
                    ft.Divider(color="#1e293b", height=1),
                ]
            ),
            width=260,
            bgcolor="#070f1e",
            padding=ft.padding.symmetric(horizontal=16, vertical=20),
            border=ft.border.only(right=ft.border.BorderSide(1, "#1e293b")),
        )

        # ── Header ────────────────────────────────────────────────────
        header = ft.Container(
            content=ft.Row(
                [
                    ft.Text("🗺️", size=22),
                    ft.Text("AI WORKSPACE", weight=ft.FontWeight.BOLD, size=18, color="#f8fafc"),
                    ft.Text("Mappe Concettuali · Open Source · 100% Locale", color="#475569", size=12),
                    ft.Container(expand=True),
                    ft.Container(
                        content=ft.Text(badge_label, color="#f8fafc", size=12),
                        bgcolor=badge_colore,
                        padding=ft.padding.symmetric(horizontal=14, vertical=6),
                        border_radius=20,
                    ),
                    ft.TextButton(
                        "🚪 Esci",
                        style=ft.ButtonStyle(color={"": "#94a3b8"}),
                        on_click=lambda e: mostra_login(),
                    ),
                ],
                spacing=12,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            padding=ft.padding.symmetric(horizontal=24, vertical=14),
            bgcolor="#070f1e",
            border=ft.border.only(bottom=ft.border.BorderSide(1, "#1e293b")),
        )

        # ── Area chat ─────────────────────────────────────────────────
        barra_input = ft.Container(
            content=ft.Column(
                [
                    ft.Row(
                        [btn_upload, chat_input, btn_mic, btn_invia],
                        spacing=10,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    stato_mic,           # riga stato microfono (vuota quando non in uso)
                ],
                spacing=4,
            ),
            bgcolor="#0f172a",
            padding=ft.padding.symmetric(horizontal=12, vertical=10),
            border=ft.border.only(top=ft.border.BorderSide(1, "#1e293b")),
        )

        area_chat = ft.Container(
            content=ft.Column(
                [chat_container, barra_input],
                expand=True,
                spacing=0,
            ),
            expand=True,
            padding=ft.padding.only(left=20, right=20, top=16),
        )

        page.add(
            ft.Column(
                [
                    header,
                    ft.Row([sidebar, area_chat], expand=True),
                ],
                expand=True,
                spacing=0,
            )
        )

        # ── Messaggio di benvenuto ────────────────────────────────────
        nome_ruolo = "Docente" if ruolo == "docente" else "Studente"
        messaggio_ai(
            f"👋 **Benvenuto, {utente}!** *({nome_ruolo})*\n\n"
            "Funziona **100% in locale** con Ollama (llama3).\n\n"
            "**Come iniziare:**\n"
            "1. Clicca **📄 Carica PDF** per selezionare i documenti\n"
            "2. Digita `crea mappa concettuale` oppure premi **🎤 Parla** per dettarlo\n"
            "3. La mappa si apre nel browser — trascina i nodi e fai zoom\n"
            "4. Ogni risposta include una **traccia audio 🔊** che parte automaticamente\n\n"
            "Puoi anche fare domande libere sui contenuti dei PDF!",
            con_audio=True,
        )
        rinfresca_lista_pdf()

    # ── Avvia dalla login ─────────────────────────────────────────────
    mostra_login()


if __name__ == "__main__":
    ft.app(target=main)