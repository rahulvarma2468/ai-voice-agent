import os
import requests
import logging





import os
import requests
import logging

logger = logging.getLogger(__name__)

MURF_API_URL = "https://api.murf.ai/v1/speech/generate-with-key"

def synthesize_speech(text: str) -> list:
    MURF_API_KEY = os.getenv("MURF_API_KEY")
    if not MURF_API_KEY:
        logger.error("Murf API key missing")
        raise RuntimeError("Murf API key missing")

    limit = 3000
    chunks = [text[i:i+limit] for i in range(0, len(text), limit)]
    audio_urls = []
    for chunk in chunks:
        payload = {"voiceId": "en-US-natalie", "text": chunk, "format": "MP3"}
        headers = {"api-key": MURF_API_KEY, "Content-Type": "application/json"}
        r = requests.post(MURF_API_URL, headers=headers, json=payload)
        if r.status_code == 200:
            result = r.json()
            audio_url = result.get("audioUrl") or result.get("audioFile") or result.get("audio_url")
            if not audio_url:
                logger.error("Audio URL missing in Murf response")
                raise RuntimeError("Audio URL missing")
            audio_urls.append(audio_url)
        else:
            logger.error(f"Murf API failed: {r.text}")
            raise RuntimeError(r.text)
    logger.info(f"TTS Audio URLs: {audio_urls}")
    return audio_urls

def synthesize_fallback_speech() -> str:
    MURF_API_KEY = os.getenv("MURF_API_KEY")
    if not MURF_API_KEY:
        logger.error("Murf API key missing for fallback")
        return None
    payload = {"voiceId": "en-US-natalie", "text": "I'm having trouble connecting right now.", "format": "MP3"}
    headers = {"api-key": MURF_API_KEY, "Content-Type": "application/json"}
    r = requests.post(MURF_API_URL, headers=headers, json=payload)
    if r.status_code == 200:
        result = r.json()
        return result.get("audioUrl") or result.get("audioFile") or result.get("audio_url")
    logger.warning("Fallback speech synthesis failed")
    return None
