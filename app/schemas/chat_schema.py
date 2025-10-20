from pydantic import BaseModel
from typing import List, Optional, Dict, Any

class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None

class ChatResponse(BaseModel):
    reply: str
    conversation_id: str
