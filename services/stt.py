import os
import assemblyai as aai
import logging

logger = logging.getLogger(__name__)

def transcribe_audio(audio_bytes) -> str:
    ASSEMBLYAI_API_KEY = os.getenv("ASSEMBLYAI_API_KEY")
    if not ASSEMBLYAI_API_KEY:
        logger.error("AssemblyAI key missing")
        raise RuntimeError("AssemblyAI key missing")
    aai.settings.api_key = ASSEMBLYAI_API_KEY
    transcript_obj = aai.Transcriber().transcribe(audio_bytes)
    text = transcript_obj.text.strip() if transcript_obj.text else ""
    logger.info(f"Transcript: {text}")
    return text
