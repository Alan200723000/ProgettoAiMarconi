import flet as ft
import os
import json
import requests
import shutil
import threading
import warnings
from pathlib import Path
from langchain_ollama import OllamaLLM, OllamaEmbeddings
from langchain_core.prompts import ChatPromptTemplate
from langchain_community.vectorstores import Chroma
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import TextLoader
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser

# --- CONFIGURAZIONE ---
warnings.filterwarnings("ignore")
CARTELLA_APP = "file_generati"
os.makedirs(CARTELLA_APP, exist_ok=True)

# --- MOTORE AI (RAG) ---
def inizializza_ai():
    percorso_conoscenza = "conoscenza.txt"
    if not os.path.exists(percorso_conoscenza):
        with open(percorso_conoscenza, "w", encoding="utf-8") as f:
            f.write("AI Workspace: Sistema di gestione documenti locale con Ollama.")
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
llm_json = OllamaLLM(model="llama3", format="json")
prompt_chat = ChatPromptTemplate.from_template("Contesto: {context}\nDomanda: {question}\nRispondi in italiano.")

if retriever:
    rag_chain = ({"context": retriever, "question": RunnablePassthrough()} | prompt_chat | llm | StrOutputParser())
else:
    rag_chain = None

# --- UI PRINCIPALE ---
def main(page: ft.Page):
    page.title = "AI Workspace Pro - Stabile"
    page.theme_mode = ft.ThemeMode.DARK
    page.bgcolor = "#0f172a"
    page.window_width = 1200
    page.window_height = 850

    def esporta_nei_download(nome_file):
        try:
            cartella_download = str(Path.home() / "Downloads")
            origine = os.path.join(CARTELLA_APP, nome_file)
            destinazione = os.path.join(cartella_download, nome_file)
            
            base, ext = os.path.splitext(nome_file)
            contatore = 1
            while os.path.exists(destinazione):
                destinazione = os.path.join(cartella_download, f"{base}_{contatore}{ext}")
                contatore += 1
            
            shutil.copy(origine, destinazione)
            page.snack_bar = ft.SnackBar(ft.Text(f"✅ Salvato in Download: {os.path.basename(destinazione)}"), bgcolor="#10b981")
            page.snack_bar.open = True
        except Exception as e:
            page.snack_bar = ft.SnackBar(ft.Text(f"❌ Errore: {str(e)}"), bgcolor="#ef4444")
            page.snack_bar.open = True
        page.update()

    chat_container = ft.ListView(expand=True, spacing=15, auto_scroll=True)
    file_list_container = ft.Column(scroll=ft.ScrollMode.AUTO)

    def rinfresca_lista_file():
        file_list_container.controls.clear()
        file_trovati = [f for f in os.listdir(CARTELLA_APP) if f.endswith(".txt")]
        for f in sorted(file_trovati):
            file_list_container.controls.append(
                ft.Container(
                    content=ft.Row([
                        ft.Icon(ft.Icons.ARTICLE, color="#3b82f6"),
                        ft.Text(f, expand=True, size=13),
                        ft.IconButton(
                            icon=ft.Icons.DOWNLOAD_FOR_OFFLINE,
                            icon_color="#10b981",
                            on_click=lambda e, n=f: esporta_nei_download(n)
                        )
                    ]),
                    bgcolor="#1e293b", padding=10, border_radius=8
                )
            )
        page.update()

    def elaborazione_ai(input_utente):
        risposta_testuale = ""
        try:
            testo_min = input_utente.lower()
            
            # 1. COMANDO CREAZIONE FILE
            if any(parola in testo_min for parola in ["crea", "salva", "scrivi", "file"]):
                prompt_estrazione = f"Estrai nome_file e contenuto da: '{input_utente}'. Rispondi solo in JSON con campi 'nome_file' e 'contenuto'."
                res = llm_json.invoke(prompt_estrazione)
                dati = json.loads(res)
                nome = dati.get("nome_file", "nota.txt").replace(" ", "_")
                if not nome.endswith(".txt"): nome += ".txt"
                
                with open(os.path.join(CARTELLA_APP, nome), "w", encoding="utf-8") as f:
                    f.write(dati.get("contenuto", ""))
                
                risposta_testuale = f"Ho creato il file **{nome}**. Puoi scaricarlo dalla barra laterale."
                rinfresca_lista_file()

            # 2. COMANDO IMMAGINI (CORRETTO)
            elif any(p in testo_min for p in ["disegna", "immagine", "genera foto"]):
                traduzione = llm.invoke(f"Translate only the prompt to English: {input_utente}")
                try:
                    r = requests.post("http://127.0.0.1:7860/sdapi/v1/txt2img", 
                                      json={"prompt": traduzione, "steps": 20}, timeout=30)
                    if r.status_code == 200:
                        img_data = r.json()['images'][0]
                        # Rimuoviamo la progress bar prima di mostrare l'immagine
                        if chat_container.controls and isinstance(chat_container.controls[-1], ft.ProgressBar):
                            chat_container.controls.pop()
                        
                        chat_container.controls.append(
                            ft.Container(
                                content=ft.Image(src=f"data:image/png;base64,{img_data}", width=400, border_radius=10),
                                bgcolor="#1e293b", padding=5, border_radius=10
                            )
                        )
                        risposta_testuale = "Ecco l'immagine generata!"
                    else:
                        risposta_testuale = "Errore: Stable Diffusion non risponde. Avvialo con `--api`."
                except:
                    risposta_testuale = "Impossibile connettersi a Stable Diffusion (127.0.0.1:7860)."

            # 3. CHAT GENERICA
            else:
                risposta_testuale = rag_chain.invoke(input_utente) if rag_chain else llm.invoke(input_utente)

        except Exception as err:
            risposta_testuale = f"⚠️ Errore di sistema: {str(err)}"

        # Rimuovi progress bar se ancora presente
        if chat_container.controls and isinstance(chat_container.controls[-1], ft.ProgressBar):
            chat_container.controls.pop()
            
        # Aggiungi risposta finale
        chat_container.controls.append(
            ft.Container(
                content=ft.Markdown(risposta_testuale, selectable=True),
                bgcolor="#334155", padding=15, border_radius=15, width=650
            )
        )
        page.update()

    def gestisci_invio(e):
        testo = chat_input.value.strip()
        if not testo: return
        
        chat_container.controls.append(
            ft.Row([
                ft.Container(content=ft.Text(testo), bgcolor="#2563eb", padding=12, border_radius=15)
            ], alignment=ft.MainAxisAlignment.END)
        )
        chat_container.controls.append(ft.ProgressBar(width=300, color="#2563eb"))
        chat_input.value = ""
        page.update()
        
        threading.Thread(target=elaborazione_ai, args=(testo,), daemon=True).start()

    chat_input = ft.TextField(
        hint_text="Chiedi qualcosa, crea un file o chiedi un disegno...",
        expand=True,
        on_submit=gestisci_invio,
        border_radius=15,
        fill_color="#1e293b",
        border_color="#334155"
    )

    # --- LAYOUT ---
    page.add(
        ft.Row([
            # Sidebar
            ft.Container(
                content=ft.Column([
                    ft.Text("DOCUMENTI GENERATI", weight="bold", color="#60a5fa", size=16),
                    ft.Divider(color="#334155"),
                    file_list_container
                ]),
                width=300, bgcolor="#0f172a", padding=20,
                border=ft.border.only(right=ft.border.BorderSide(1, "#334155"))
            ),
            # Chat
            ft.Container(
                content=ft.Column([
                    ft.Text("AI WORKSPACE", weight="bold", size=18, color="#f8fafc"),
                    chat_container,
                    ft.Row([
                        chat_input,
                        ft.IconButton(ft.Icons.SEND_ROUNDED, icon_color="#2563eb", on_click=gestisci_invio)
                    ])
                ]),
                expand=True, padding=20
            )
        ], expand=True)
    )
    
    rinfresca_lista_file()

if __name__ == "__main__":
    ft.app(target=main)