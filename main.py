import os
from typing import List
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import requests
from dotenv import load_dotenv

import assemblyai as aai
import google.generativeai as genai

# Load environment variables
load_dotenv()

MURF_API_KEY = os.getenv("MURF_API_KEY")
MURF_API_URL = "https://api.murf.ai/v1/speech/generate-with-key"
ASSEMBLYAI_API_KEY = os.getenv("ASSEMBLYAI_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# In-memory chat history store
chat_histories = {}  # {session_id: [ {"role": "...", "content": "..."} ]}

FALLBACK_MESSAGE = "I'm having trouble connecting right now."

def add_message(session_id: str, role: str, content: str):
    """Always store 'content' as a string to avoid None issues."""
    if session_id not in chat_histories:
        chat_histories[session_id] = []
    chat_histories[session_id].append({
        "role": role,
        "content": content or ""
    })

def get_history(session_id: str):
    return chat_histories.get(session_id, [])

def generate_fallback_response(session_id, transcript_hint, error_stage, error):
    print(f"[ERROR] Stage {error_stage}: {error}")
    audio_url = None
    try:
        if MURF_API_KEY:
            payload = {"voiceId": "en-US-natalie", "text": FALLBACK_MESSAGE, "format": "MP3"}
            headers = {"api-key": MURF_API_KEY, "Content-Type": "application/json"}
            r = requests.post(MURF_API_URL, headers=headers, json=payload)
            if r.status_code == 200:
                result = r.json()
                audio_url = result.get("audioUrl") or result.get("audioFile") or result.get("audio_url")
    except Exception as e:
        print(f"[ERROR] Fallback TTS failed: {e}")

    # Ensure fallback messages are in history
    if transcript_hint:
        add_message(session_id, "user", transcript_hint)
    add_message(session_id, "assistant", FALLBACK_MESSAGE)

    return {
        "audioUrls": [audio_url] if audio_url else [],
        "transcript": transcript_hint or "",
        "llmText": FALLBACK_MESSAGE,
        "history": get_history(session_id),
        "fallback": True,
        "errorStage": error_stage
    }

# FastAPI app
app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def root():
    return FileResponse("static/index.html")

class TextRequest(BaseModel):
    text: str

@app.post("/generate-audio")
def generate_audio(body: TextRequest):
    try:
        payload = {"voiceId": "en-US-natalie", "text": body.text, "style": "Promo", "format": "MP3"}
        headers = {"api-key": MURF_API_KEY, "Content-Type": "application/json"}
        r = requests.post(MURF_API_URL, headers=headers, json=payload)
        if r.status_code == 200:
            result = r.json()
            audio_url = result.get("audioUrl") or result.get("audioFile") or result.get("audio_url")
            if not audio_url:
                raise RuntimeError("Audio URL missing in Murf response")
            return {"audioUrl": audio_url}
        else:
            raise RuntimeError(f"Murf API error: {r.text}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/agent/chat/{session_id}")
async def agent_chat(session_id: str, file: UploadFile = File(...)):
    transcript = ""
    llm_text = ""
    audio_urls = []

    # Step 1 – STT
    try:
        if not ASSEMBLYAI_API_KEY:
            raise RuntimeError("AssemblyAI key missing")
        audio_bytes = await file.read()
        aai.settings.api_key = ASSEMBLYAI_API_KEY
        transcript_obj = aai.Transcriber().transcribe(audio_bytes)
        transcript = transcript_obj.text.strip() if transcript_obj.text else ""
        if not transcript:
            raise RuntimeError("No speech recognized")
    except Exception as e:
        return generate_fallback_response(session_id, "", "STT", str(e))

    # Step 2 – LLM
    try:
        add_message(session_id, "user", transcript)
        history = get_history(session_id)
        chat_prompt = "\n".join(
            [f"{'User' if m['role']=='user' else 'Assistant'}: {m['content']}" for m in history]
        ) + "\nAssistant:"
        if not GEMINI_API_KEY:
            raise RuntimeError("Gemini API key missing")
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel("gemini-1.5-flash")
        llm_res = model.generate_content(chat_prompt)
        llm_text = llm_res.text.strip() if hasattr(llm_res, 'text') else str(llm_res)
        if not llm_text:
            raise RuntimeError("Empty LLM response")
    except Exception as e:
        return generate_fallback_response(session_id, transcript, "LLM", str(e))

    # Step 3 – TTS
    try:
        add_message(session_id, "assistant", llm_text)
        if not MURF_API_KEY:
            raise RuntimeError("Murf API key missing")
        limit = 3000
        chunks = [llm_text[i:i+limit] for i in range(0, len(llm_text), limit)]
        for chunk in chunks:
            payload = {"voiceId": "en-US-natalie", "text": chunk, "format": "MP3"}
            headers = {"api-key": MURF_API_KEY, "Content-Type": "application/json"}
            r = requests.post(MURF_API_URL, headers=headers, json=payload)
            if r.status_code == 200:
                result = r.json()
                audio_url = result.get("audioUrl") or result.get("audioFile") or result.get("audio_url")
                if not audio_url:
                    raise RuntimeError("Murf audio URL missing")
                audio_urls.append(audio_url)
            else:
                raise RuntimeError(f"Murf API failed with code {r.status_code}")
    except Exception as e:
        return generate_fallback_response(session_id, transcript, "TTS", str(e))

    return {
        "audioUrls": audio_urls,
        "transcript": transcript,
        "llmText": llm_text,
        "history": history,
        "fallback": False
    }
