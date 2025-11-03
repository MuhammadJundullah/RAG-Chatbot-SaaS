from pydantic import BaseModel
import uuid
from datetime import datetime
from typing import List

class ChatlogBase(BaseModel):
    question: str
    answer: str
    UsersId: int
    company_id: int
    conversation_id: uuid.UUID
    created_at: datetime

class ChatlogCreate(ChatlogBase):
    pass

class Chatlog(ChatlogBase):
    id: int

    class Config:
        from_attributes = True

class ChatlogResponse(BaseModel):
    username: str
    created_at: datetime
    question: str
    answer: str

class PaginatedChatlogResponse(BaseModel):
    chatlogs: List[ChatlogResponse]
    total_pages: int
    current_page: int
    total_chat: int

class ConversationInfoSchema(BaseModel):
    id: uuid.UUID
    title: str