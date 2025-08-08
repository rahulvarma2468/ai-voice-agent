import os
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import requests
from dotenv import load_dotenv

import assemblyai as aai  # pip install assemblyai

load_dotenv()

MURF_API_KEY = os.getenv("MURF_API_KEY")
MURF_API_URL = "https://api.murf.ai/v1/speech/generate-with-key"
ASSEMBLYAI_API_KEY = os.getenv("ASSEMBLYAI_API_KEY")

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def root():
    return FileResponse("static/index.html")

class TextRequest(BaseModel):
    text: str

@app.post("/generate-audio")
def generate_audio(body: TextRequest):
    payload = {
        "voiceId": "en-US-natalie",
        "text": body.text,
        "style": "Promo",  # Optional: Only if supported
        "format": "MP3"
    }
    headers = {
        "api-key": MURF_API_KEY,
        "Content-Type": "application/json"
    }
    try:
        response = requests.post(MURF_API_URL, headers=headers, json=payload)
        print("Murf API Response:", response.status_code, response.text)
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

# ----------- DAY 7: Echo Bot v2 endpoint -----------
@app.post("/tts/echo")
async def echo_tts(file: UploadFile = File(...)):
    # 1. Transcribe the uploaded audio (no saving to disk)
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

    # 2. Send transcript to Murf for TTS
    if not MURF_API_KEY:
        raise HTTPException(status_code=500, detail="Murf API key not set in environment.")
    try:
        payload = {
            "voiceId": "en-US-natalie",  # Or set your favorite Murf voice here
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
            raise HTTPException(
                status_code=response.status_code,
                detail=f"Murf API error: {response.text}"
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Murf synthesis failed: {e}")
