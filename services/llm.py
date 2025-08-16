import os
import google.generativeai as genai
import logging

logger = logging.getLogger(__name__)

def generate_llm_response(history: list) -> str:
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    if not GEMINI_API_KEY:
        logger.error("Gemini API key missing")
        raise RuntimeError("Gemini API key missing")
    genai.configure(api_key=GEMINI_API_KEY)
    chat_prompt = "\n".join(
        [f"{'User' if m['role']=='user' else 'Assistant'}: {m['content']}" for m in history]
    ) + "\nAssistant:"
    model = genai.GenerativeModel("gemini-1.5-flash")
    llm_res = model.generate_content(chat_prompt)
    text = llm_res.text.strip() if hasattr(llm_res, "text") else str(llm_res)
    logger.info(f"LLM Response: {text}")
    return text



