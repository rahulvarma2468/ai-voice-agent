import os
from typing import List
from fastapi import FastAPI, UploadFile, File
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv
import logging


from models import AgentChatResponse
from services.stt import transcribe_audio
from services.llm import generate_llm_response
from services.tts import synthesize_speech, synthesize_fallback_speech

# Load env vars and configure logger
load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)



UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)
chat_histories = {}

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def root():
    return FileResponse("static/index.html")

def add_message(session_id: str, role: str, content: str):
    if session_id not in chat_histories:
        chat_histories[session_id] = []
    chat_histories[session_id].append({
        "role": role,
        "content": content or ""
    })

def get_history(session_id: str):
    return chat_histories.get(session_id, [])

def generate_fallback_response(session_id, transcript_hint, error_stage, error):
    logger.error(f"[{error_stage}] {error}")
    audio_url = synthesize_fallback_speech()
    if transcript_hint:
        add_message(session_id, "user", transcript_hint)
    add_message(session_id, "assistant", "I'm having trouble connecting right now.")
    return AgentChatResponse(
        audioUrls=[audio_url] if audio_url else [],
        transcript=transcript_hint or "",
        llmText="I'm having trouble connecting right now.",
        history=get_history(session_id),
        fallback=True
    )

@app.post("/agent/chat/{session_id}", response_model=AgentChatResponse)
async def agent_chat(session_id: str, file: UploadFile = File(...)):
    transcript = ""
    llm_text = ""
    audio_urls: List[str] = []

    # STT
    try:
        audio_bytes = await file.read()
        transcript = transcribe_audio(audio_bytes)
        if not transcript:
            raise RuntimeError("No speech recognized")
    except Exception as e:
        return generate_fallback_response(session_id, "", "STT", str(e))

    # LLM
    try:
        add_message(session_id, "user", transcript)
        history = get_history(session_id)
        llm_text = generate_llm_response(history)
        if not llm_text:
            raise RuntimeError("Empty LLM response")
    except Exception as e:
        return generate_fallback_response(session_id, transcript, "LLM", str(e))

    # TTS
    try:
        add_message(session_id, "assistant", llm_text)
        audio_urls = synthesize_speech(llm_text)
    except Exception as e:
        return generate_fallback_response(session_id, transcript, "TTS", str(e))

    return AgentChatResponse(
        audioUrls=audio_urls,
        transcript=transcript,
        llmText=llm_text,
        history=history,
        fallback=False
    )
