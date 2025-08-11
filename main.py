import os
from typing import List
from fastapi import FastAPI, HTTPException, UploadFile, File, Path
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import requests
from dotenv import load_dotenv

import assemblyai as aai  # pip install assemblyai
import google.generativeai as genai  # pip install google-generativeai

# Load environment variables
load_dotenv()

MURF_API_KEY = os.getenv("MURF_API_KEY")
MURF_API_URL = "https://api.murf.ai/v1/speech/generate-with-key"
ASSEMBLYAI_API_KEY = os.getenv("ASSEMBLYAI_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# In-memory chat history store
chat_histories = {}  # { session_id: [ {"role": "user"/"assistant", "content": "..."} ] }

def add_message(session_id: str, role: str, content: str):
    if session_id not in chat_histories:
        chat_histories[session_id] = []
    chat_histories[session_id].append({"role": role, "content": content})

def get_history(session_id: str):
    return chat_histories.get(session_id, [])

# FastAPI app
app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def root():
    return FileResponse("static/index.html")

# ---------- MODELS ----------
class TextRequest(BaseModel):
    text: str

# ---------- ENDPOINTS ----------

@app.post("/generate-audio")
def generate_audio(body: TextRequest):
    payload = {
        "voiceId": "en-US-natalie",
        "text": body.text,
        "style": "Promo",  # Optional
        "format": "MP3"
    }
    headers = {
        "api-key": MURF_API_KEY,
        "Content-Type": "application/json"
    }
    try:
        response = requests.post(MURF_API_URL, headers=headers, json=payload)
        if response.status_code == 200:
            result = response.json()
            audio_url = (
                result.get("audioUrl") or
                result.get("audioFile") or
                result.get("audio_url")
            )
            if not audio_url:
                raise HTTPException(status_code=500, detail="Audio URL missing in Murf response")
            return {"audioUrl": audio_url}
        else:
            raise HTTPException(status_code=response.status_code, detail=f"Murf API error: {response.text}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")

@app.post("/upload-audio")
async def upload_audio(file: UploadFile = File(...)):
    file_location = os.path.join(UPLOAD_DIR, file.filename)
    content = await file.read()
    with open(file_location, "wb") as f:
        f.write(content)
    return {
        "filename": file.filename,
        "content_type": file.content_type,
        "size": len(content)
    }

@app.post("/transcribe/file")
async def transcribe_file(file: UploadFile = File(...)):
    if not ASSEMBLYAI_API_KEY:
        raise HTTPException(status_code=500, detail="AssemblyAI API key not set in environment.")
    audio_bytes = await file.read()
    try:
        aai.settings.api_key = ASSEMBLYAI_API_KEY
        transcriber = aai.Transcriber()
        transcript = transcriber.transcribe(audio_bytes)
        text = transcript.text if transcript.text else ""
        return {"transcript": text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Transcription failed: {e}")

@app.post("/tts/echo")
async def echo_tts(file: UploadFile = File(...)):
    if not ASSEMBLYAI_API_KEY:
        raise HTTPException(status_code=500, detail="AssemblyAI API key not set in environment.")
    try:
        audio_bytes = await file.read()
        aai.settings.api_key = ASSEMBLYAI_API_KEY
        transcriber = aai.Transcriber()
        transcript = transcriber.transcribe(audio_bytes)
        text = transcript.text.strip() if transcript.text else ""
        if not text:
            raise HTTPException(status_code=400, detail="No speech recognized to echo.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Transcription failed: {e}")
    if not MURF_API_KEY:
        raise HTTPException(status_code=500, detail="Murf API key not set in environment.")
    try:
        payload = {
            "voiceId": "en-US-natalie",
            "text": text,
            "format": "MP3"
        }
        headers = {
            "api-key": MURF_API_KEY,
            "Content-Type": "application/json"
        }
        response = requests.post(MURF_API_URL, headers=headers, json=payload)
        if response.status_code == 200:
            result = response.json()
            audio_url = (
                result.get("audioUrl") or
                result.get("audioFile") or
                result.get("audio_url")
            )
            if not audio_url:
                raise HTTPException(status_code=500, detail="Murf audio URL missing in response.")
            return {"audioUrl": audio_url, "transcript": text}
        else:
            raise HTTPException(status_code=response.status_code, detail=f"Murf API error: {response.text}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Murf synthesis failed: {e}")

# ----------- DAY 9: LLM Full Pipeline endpoint -----------
@app.post("/llm/query")
async def llm_audio_query(file: UploadFile = File(...)):
    # 1. Transcribe the uploaded audio
    if not ASSEMBLYAI_API_KEY:
        raise HTTPException(status_code=500, detail="AssemblyAI API key not set in environment.")
    try:
        audio_bytes = await file.read()
        aai.settings.api_key = ASSEMBLYAI_API_KEY
        transcriber = aai.Transcriber()
        transcript = transcriber.transcribe(audio_bytes)
        prompt = transcript.text.strip() if transcript.text else ""
        if not prompt:
            raise HTTPException(status_code=400, detail="No speech recognized in audio.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Transcription failed: {e}")

    # 2. LLM response from Gemini
    if not GEMINI_API_KEY:
        raise HTTPException(status_code=500, detail="Gemini API key not set in environment.")
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel("gemini-1.5-flash")
        llm_response = model.generate_content(prompt)
        llm_text = llm_response.text.strip() if hasattr(llm_response, 'text') else str(llm_response)
        if not llm_text:
            raise HTTPException(status_code=500, detail="No response from LLM.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM query failed: {e}")

    # 3. Murf TTS for LLM response (<=3,000 chars per call)
    if not MURF_API_KEY:
        raise HTTPException(status_code=500, detail="Murf API key not set in environment.")
    limit = 3000
    chunks: List[str] = [llm_text[i:i+limit] for i in range(0, len(llm_text), limit)]
    audio_urls = []
    try:
        for chunk in chunks:
            payload = {
                "voiceId": "en-US-natalie",
                "text": chunk,
                "format": "MP3"
            }
            headers = {
                "api-key": MURF_API_KEY,
                "Content-Type": "application/json"
            }
            response = requests.post(MURF_API_URL, headers=headers, json=payload)
            if response.status_code == 200:
                result = response.json()
                audio_url = (
                    result.get("audioUrl") or
                    result.get("audioFile") or
                    result.get("audio_url")
                )
                if not audio_url:
                    raise HTTPException(status_code=500, detail="Murf audio URL missing in response.")
                audio_urls.append(audio_url)
            else:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Murf API error: {response.text}"
                )
        return {
            "audioUrls": audio_urls,
            "transcript": prompt,
            "llmText": llm_text
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Murf synthesis failed: {e}")

# ----------- DAY 10: Agent chat with session memory -----------
@app.post("/agent/chat/{session_id}")
async def agent_chat(session_id: str, file: UploadFile = File(...)):
    # 1. Transcribe audio
    if not ASSEMBLYAI_API_KEY:
        raise HTTPException(status_code=500, detail="AssemblyAI API key not set.")
    try:
        audio_bytes = await file.read()
        aai.settings.api_key = ASSEMBLYAI_API_KEY
        transcriber = aai.Transcriber()
        transcript_obj = transcriber.transcribe(audio_bytes)
        transcript = transcript_obj.text.strip() if transcript_obj.text else ""
        if not transcript:
            raise HTTPException(status_code=400, detail="No speech recognized.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Transcription failed: {e}")

    # 2. Add user message to history
    add_message(session_id, "user", transcript)
    history = get_history(session_id)

    # 3. Build conversation prompt
    messages = []
    for m in history:
        if m["role"] == "user":
            messages.append(f"User: {m['content']}")
        else:
            messages.append(f"Assistant: {m['content']}")
    chat_prompt = "\n".join(messages) + "\nAssistant:"

    # 4. Get response from Gemini
    if not GEMINI_API_KEY:
        raise HTTPException(status_code=500, detail="Gemini API key not set.")
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel("gemini-1.5-flash")
        llm_res = model.generate_content(chat_prompt)
        llm_text = llm_res.text.strip() if hasattr(llm_res, 'text') else str(llm_res)
        if not llm_text:
            raise HTTPException(status_code=500, detail="No response from LLM.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM query failed: {e}")

    # 5. Add assistant message to history
    add_message(session_id, "assistant", llm_text)

    # 6. Murf TTS for LLM response
    if not MURF_API_KEY:
        raise HTTPException(status_code=500, detail="Murf API key not set.")
    limit = 3000
    chunks = [llm_text[i:i+limit] for i in range(0, len(llm_text), limit)]
    audio_urls = []
    for chunk in chunks:
        payload = {
            "voiceId": "en-US-natalie",
            "text": chunk,
            "format": "MP3"
        }
        headers = {
            "api-key": MURF_API_KEY,
            "Content-Type": "application/json"
        }
        response = requests.post(MURF_API_URL, headers=headers, json=payload)
        if response.status_code == 200:
            result = response.json()
            audio_url = result.get("audioUrl") or result.get("audioFile") or result.get("audio_url")
            if not audio_url:
                raise HTTPException(status_code=500, detail="Murf audio URL missing.")
            audio_urls.append(audio_url)
        else:
            raise HTTPException(status_code=response.status_code, detail=f"Murf API error: {response.text}")

    # 7. Return
    return {
        "audioUrls": audio_urls,
        "transcript": transcript,
        "llmText": llm_text,
        "history": history
    }