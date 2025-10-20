from pydantic import BaseModel
from typing import List, Optional, Dict, Any

class ChatlogBase(BaseModel):
    question: str
    answer: str
    UsersId: int
    company_id: int

class ChatlogCreate(ChatlogBase):
    pass

class Chatlog(ChatlogBase):
    id: int

    class Config:
        from_attributes = True
