import os
from fastapi import FastAPI, HTTPException, UploadFile, File, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import requests
from dotenv import load_dotenv

load_dotenv()

MURF_API_KEY = os.getenv("MURF_API_KEY")
MURF_API_URL = "https://api.murf.ai/v1/speech/generate-with-key"

# Ensure uploads directory exists
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
        "style": "Promo",  # Optional: Only if supported for the voice
        "format": "MP3"
    }
    headers = {
        "api-key": MURF_API_KEY,
        "Content-Type": "application/json"
    }

    try:
        response = requests.post(MURF_API_URL, headers=headers, json=payload)
        print("Murf API Response:", response.status_code, response.text)  # Debug Info

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
