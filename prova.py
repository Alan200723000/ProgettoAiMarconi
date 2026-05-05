import streamlit as st
import requests
import speech_recognition as sr
import os
import base64
from io import BytesIO
from pydub import AudioSegment
from streamlit_mic_recorder import mic_recorder

# --- COMPONENTI AI (LangChain & RAG) ---
from langchain_ollama import OllamaLLM, OllamaEmbeddings
from langchain_core.prompts import ChatPromptTemplate
from langchain_community.vectorstores import Chroma
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import TextLoader
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser 

# --- CONFIGURAZIONE AMBIENTE ---
# Assicurati che ffmpeg sia nella cartella o nel PATH di sistema
st.set_page_config(page_title="AI Multi-Tool Dashboard", layout="wide")

# Inizializzazione sessione
if "messages" not in st.session_state:
    st.session_state.messages = []
if "history" not in st.session_state:
    st.session_state.history = []

# --- 1. MOTORE RAG ---
@st.cache_resource
def setup_rag():
    filepath = "conoscenza_app.txt"
    if not os.path.exists(filepath):
        with open(filepath, "w", encoding="utf-8") as f:
            f.write("L'app To-Do usa Flet. Il RAG migliora la precisione. L'operatore pipe collega i moduli.")
    
    loader = TextLoader(filepath, encoding="utf-8")
    docs = loader.load()
    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    chunks = splitter.split_documents(docs)
    
    # Nota: Assicurati che Ollama sia attivo con llama3
    emb = OllamaEmbeddings(model="llama3")
    vectorstore = Chroma.from_documents(documents=chunks, embedding=emb)
    return vectorstore.as_retriever()

retriever = setup_rag()

# --- 2. DEFINIZIONE CHAIN ---
llm = OllamaLLM(model="llama3")
prompt_template = ChatPromptTemplate.from_template(
    "Usa il contesto: {context}\n\nDomanda: {question}\nRispondi in italiano."
)

rag_chain = (
    {"context": retriever, "question": RunnablePassthrough()}
    | prompt_template 
    | llm 
    | StrOutputParser()
)

# --- 3. FUNZIONI UTILITY ---
def trascrivi_audio(audio_bytes):
    try:
        audio = AudioSegment.from_file(BytesIO(audio_bytes))
        wav_io = BytesIO()
        audio.set_frame_rate(16000).set_channels(1).export(wav_io, format="wav")
        wav_io.seek(0)
        rec = sr.Recognizer()
        with sr.AudioFile(wav_io) as source:
            return rec.recognize_google(rec.record(source), language="it-IT")
    except Exception as e:
        return f"⚠️ Errore trascrizione: {e}"

def genera_immagine(prompt_testo):
    # Endpoint standard di Automatic1111 (Stable Diffusion WebUI)
    url = "http://127.0.0.1:7860/sdapi/v1/txt2img"
    
    # Chiediamo a Ollama di estrarre solo i tag visivi in inglese
    clean_prompt_query = f"Convert this request into a concise descriptive image prompt in English, only keywords, no sentences: {prompt_testo}"
    prompt_en = llm.invoke(clean_prompt_query)
    
    payload = {
        "prompt": prompt_en,
        "steps": 25,
        "width": 512,
        "height": 512,
        "cfg_scale": 7
    }
    
    try:
        response = requests.post(url, json=payload, timeout=60)
        if response.status_code == 200:
            r = response.json()
            return base64.b64decode(r['images'][0])
    except Exception as e:
        st.error(f"Errore di connessione a Stable Diffusion: {e}")
        return None

# --- 4. INTERFACCIA ---
with st.sidebar:
    st.header("📊 Dashboard")
    if st.button("🗑️ Svuota Tutto"):
        st.session_state.messages = []
        st.session_state.history = []
        st.rerun()
    
    st.subheader("📜 Cronologia")
    for h in reversed(st.session_state.history):
        st.text(f"• {h[:30]}...")

st.title("🎙️ AI Assistant Pro")

# Visualizzazione Chat con supporto immagini
for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.write(m["content"])
        if "image" in m and m["image"]:
            st.image(m["image"])

# Input
col1, col2 = st.columns([1, 4])
with col1:
    audio_data = mic_recorder(start_prompt="🎤", stop_prompt="🛑", key='mic')
with col2:
    user_input = st.chat_input("Chiedi qualcosa o chiedi di 'disegnare'...")

comando = None
if audio_data:
    comando = trascrivi_audio(audio_data['bytes'])
elif user_input:
    comando = user_input

# --- 5. LOGICA DI ESECUZIONE ---
if comando:
    st.session_state.history.append(comando)
    st.session_state.messages.append({"role": "user", "content": comando})
    
    # Mostra immediatamente il messaggio dell'utente
    with st.chat_message("user"):
        st.write(comando)

    # Logica di distinzione: Immagine vs Testo
    img_keywords = ["disegna", "genera immagine", "mostrami", "crea un'immagine", "fai un disegno"]
    
    if any(k in comando.lower() for k in img_keywords):
        with st.chat_message("assistant"):
            with st.spinner("🎨 Stable Diffusion sta lavorando..."):
                img_data = genera_immagine(comando)
                if img_data:
                    st.image(img_data)
                    st.session_state.messages.append({
                        "role": "assistant", 
                        "content": "Ecco l'immagine che ho generato per te:", 
                        "image": img_data
                    })
                else:
                    msg = "Non sono riuscito a generare l'immagine. Verifica che Stable Diffusion sia attivo con --api."
                    st.error(msg)
                    st.session_state.messages.append({"role": "assistant", "content": msg})
    else:
        with st.chat_message("assistant"):
            with st.spinner("🤖 Consulto i documenti..."):
                risposta = rag_chain.invoke(comando)
                st.write(risposta)
                st.session_state.messages.append({"role": "assistant", "content": risposta})
                
                
                