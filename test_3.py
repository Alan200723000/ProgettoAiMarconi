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

warnings.filterwarnings("ignore")
CARTELLA_MAPPE = "mappe_generate"
os.makedirs(CARTELLA_MAPPE, exist_ok=True)

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
        docs = loader.load()
        splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
        chunks = splitter.split_documents(docs)
        emb = OllamaEmbeddings(model="llama3")
        vectorstore = Chroma.from_documents(documents=chunks, embedding=emb)
        return vectorstore.as_retriever()
    except Exception as e:
        print(f"Errore inizializzazione RAG: {e}")
        return None

retriever = inizializza_ai()
llm = OllamaLLM(model="llama3")
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
# FILE DIALOG
# ─────────────────────────────────────────────
def apri_dialogo_pdf() -> list:
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    percorsi = filedialog.askopenfilenames(
        title="Seleziona uno o piu PDF",
        filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")]
    )
    root.destroy()
    return list(percorsi)

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
            src = m.group(1).strip()
            dst = m.group(2).strip()
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
# APP FLET 0.84
# ─────────────────────────────────────────────
def main(page: ft.Page):
    page.title = "AI Workspace — Mappe Concettuali"
    page.theme_mode = ft.ThemeMode.DARK
    page.bgcolor = "#0f172a"
    page.window_width = 1200
    page.window_height = 850

    pdf_caricati = {}

    chat_container = ft.ListView(expand=True, spacing=15, auto_scroll=True)
    pdf_list_container = ft.Column(scroll=ft.ScrollMode.AUTO, spacing=6)

    # ── Messaggi ──────────────────────────────
    def messaggio_ai(testo: str):
        chat_container.controls.append(
            ft.Container(
                content=ft.Markdown(testo, selectable=True),
                bgcolor="#1e293b",
                padding=ft.padding.symmetric(horizontal=18, vertical=14),
                border_radius=15,
                width=680,
            )
        )
        page.update()

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

    def aggiungi_spinner():
        spinner = ft.Container(
            content=ft.Row(
                [
                    ft.ProgressRing(width=18, height=18, stroke_width=2, color="#3b82f6"),
                    ft.Text("Elaborazione...", color="#64748b", italic=True, size=13),
                ],
                spacing=10,
            ),
            bgcolor="#1e293b", padding=14, border_radius=12, width=240,
        )
        chat_container.controls.append(spinner)
        page.update()
        return spinner

    def rimuovi_spinner(spinner):
        if spinner in chat_container.controls:
            chat_container.controls.remove(spinner)
        page.update()

    # ── Lista PDF ─────────────────────────────
    def rinfresca_lista_pdf():
        pdf_list_container.controls.clear()
        if not pdf_caricati:
            pdf_list_container.controls.append(
                ft.Text("Nessun PDF caricato", color="#475569", italic=True, size=12)
            )
        else:
            for nome in pdf_caricati:
                parole = len(pdf_caricati[nome].split())
                nome_breve = nome if len(nome) < 22 else nome[:20] + "..."
                pdf_list_container.controls.append(
                    ft.Container(
                        content=ft.Column(
                            [
                                ft.Row(
                                    [
                                        ft.Text("📄", size=16),
                                        ft.Text(nome_breve, expand=True, size=13, color="#f1f5f9"),
                                        # FIX: In Flet 0.84 TextButton non accetta 'text' come keyword
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
            messaggio_ai(f"🗑️ PDF **{nome}** rimosso.")

    # ── Carica PDF ────────────────────────────
    def carica_pdf_thread():
        percorsi = apri_dialogo_pdf()
        if not percorsi:
            return
        nuovi = []
        for percorso in percorsi:
            nome = os.path.basename(percorso)
            try:
                reader = PyPDF2.PdfReader(percorso)
                testo = "\n".join(
                    (pagina.extract_text() or "") for pagina in reader.pages
                ).strip()
                if not testo:
                    messaggio_ai(f"⚠️ **{nome}**: nessun testo estraibile.")
                    continue
                pdf_caricati[nome] = testo
                nuovi.append(nome)
            except Exception as ex:
                messaggio_ai(f"❌ Errore **{nome}**: {ex}")
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

    # ── Logica AI ─────────────────────────────
    def elaborazione_ai(input_utente: str):
        spinner = aggiungi_spinner()
        try:
            testo_min = input_utente.lower()
            vuole_mappa = any(p in testo_min for p in ["mappa", "schema", "grafo", "concettual", "visualizza"])
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
                relazioni = estrai_relazioni(risposta_llm)
                rimuovi_spinner(spinner)

                if not relazioni:
                    messaggio_ai("⚠️ Nessuna relazione estratta. Verifica che il PDF abbia testo leggibile.")
                    return

                nome_mappa = "mappa_" + "_".join(list(testi.keys())[:2]).replace(" ", "_") + ".html"
                percorso_html = crea_mappa_pyvis(relazioni, nome_mappa)
                webbrowser.open(f"file://{percorso_html}")

                def riapri(_):
                    webbrowser.open(f"file://{percorso_html}")

                chat_container.controls.append(
                    ft.Container(
                        content=ft.Column(
                            [
                                ft.Text(
                                    f"🗺️ Mappa generata — {len(relazioni)} relazioni",
                                    color="#10b981",
                                    weight=ft.FontWeight.BOLD,
                                    size=15,
                                ),
                                ft.Text(
                                    "La mappa si e' aperta nel browser.\n"
                                    "Trascina i nodi, fai zoom, clicca per esplorare.",
                                    color="#94a3b8", size=13,
                                ),
                                # FIX: ElevatedButton con primo argomento posizionale
                                ft.ElevatedButton(
                                    "🌐  Riapri nel browser",
                                    bgcolor="#1e40af",
                                    color="#f8fafc",
                                    on_click=riapri,
                                ),
                            ],
                            spacing=8,
                        ),
                        bgcolor="#1e293b", padding=16, border_radius=14,
                        border=ft.border.all(1, "#10b981"), width=500,
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
                prompt = (
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
            messaggio_ai(f"⚠️ Errore: {err}")

    # ── Invio ─────────────────────────────────
    def gestisci_invio(e):
        testo = chat_input.value.strip()
        if not testo:
            return
        messaggio_utente(testo)
        chat_input.value = ""
        page.update()
        threading.Thread(target=elaborazione_ai, args=(testo,), daemon=True).start()

    # ── Controlli ─────────────────────────────
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

    # FIX: ElevatedButton — 'text' come primo argomento posizionale (non keyword)
    btn_upload = ft.ElevatedButton(
        "📄  Carica PDF",
        bgcolor="#b91c1c",
        color="#f8fafc",
        on_click=carica_pdf,
    )

    btn_invia = ft.ElevatedButton(
        "➤",
        bgcolor="#1e40af",
        color="#f8fafc",
        on_click=gestisci_invio,
    )

    # ── Sidebar ───────────────────────────────
    sidebar = ft.Container(
        content=ft.Column(
            [
                ft.Text("📁  PDF CARICATI", weight=ft.FontWeight.BOLD, color="#60a5fa", size=13),
                ft.Divider(color="#1e293b", height=1),
                pdf_list_container,
                ft.Divider(color="#1e293b", height=1),
                ft.Text("COMANDI RAPIDI", color="#475569", size=11, weight=ft.FontWeight.BOLD),
                ft.Column(
                    [
                        ft.Container(
                            content=ft.Text(cmd, size=11, color="#94a3b8"),
                            bgcolor="#1e293b",
                            padding=ft.padding.symmetric(horizontal=10, vertical=5),
                            border_radius=20,
                            border=ft.border.all(1, "#334155"),
                        )
                        for cmd in [
                            "crea mappa concettuale",
                            "analizza [nome.pdf]",
                            "riassumi i documenti",
                            "confronta i PDF",
                        ]
                    ],
                    spacing=4,
                ),
            ],
            spacing=12,
        ),
        width=260,
        bgcolor="#070f1e",
        padding=ft.padding.symmetric(horizontal=16, vertical=20),
        border=ft.border.only(right=ft.border.BorderSide(1, "#1e293b")),
    )

    # ── Header ────────────────────────────────
    header = ft.Container(
        content=ft.Row(
            [
                ft.Text("🗺️", size=22),
                ft.Text("AI WORKSPACE", weight=ft.FontWeight.BOLD, size=18, color="#f8fafc"),
                ft.Text("Mappe Concettuali · Open Source · 100% Locale", color="#475569", size=12),
            ],
            spacing=12,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        padding=ft.padding.symmetric(horizontal=24, vertical=14),
        bgcolor="#070f1e",
        border=ft.border.only(bottom=ft.border.BorderSide(1, "#1e293b")),
    )

    # ── Area chat ─────────────────────────────
    area_chat = ft.Container(
        content=ft.Column(
            [
                chat_container,
                ft.Container(
                    content=ft.Row(
                        [btn_upload, chat_input, btn_invia],
                        spacing=10,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    bgcolor="#0f172a",
                    padding=ft.padding.symmetric(horizontal=12, vertical=10),
                    border=ft.border.only(top=ft.border.BorderSide(1, "#1e293b")),
                ),
            ],
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

    messaggio_ai(
        "👋 **Benvenuto in AI Workspace!**\n\n"
        "Funziona **100% in locale** con Ollama (llama3).\n\n"
        "**Come iniziare:**\n"
        "1. Clicca **📄 Carica PDF** per selezionare i documenti\n"
        "2. Digita `crea mappa concettuale` per il grafo interattivo\n"
        "3. La mappa si apre nel browser — trascina i nodi e fai zoom\n\n"
        "Puoi anche fare domande libere sui contenuti dei PDF!"
    )
    rinfresca_lista_pdf()


if __name__ == "__main__":
    ft.app(target=main)
