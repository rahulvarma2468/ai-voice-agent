from typing import List, Dict
from pydantic import BaseModel

class AgentChatResponse(BaseModel):
    audioUrls: List[str]
    transcript: str
    llmText: str
    history: List[Dict]
    fallback: bool
