from pydantic import BaseModel
import uuid
from datetime import datetime
from typing import List, Optional

class ChatlogBase(BaseModel):
    question: str
    answer: str
    UsersId: int
    company_id: int
    conversation_id: uuid.UUID
    match_score: Optional[float] = None  # percentage 0-100
    response_time_ms: Optional[int] = None
    input_type: Optional[str] = None
    input_audio_path: Optional[str] = None
    output_audio_path: Optional[str] = None
    stt_request_id: Optional[str] = None
    tts_request_id: Optional[str] = None
    input_duration_ms: Optional[int] = None

class ChatlogCreate(ChatlogBase):
    referenced_document_ids: Optional[List[int]] = None

class Chatlog(ChatlogBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True

class ChatlogResponse(BaseModel):
    id: int
    username: str
    created_at: datetime
    question: str
    answer: str
    conversation_id: uuid.UUID
    match_score: Optional[float] = None
    response_time_ms: Optional[int] = None
    input_type: Optional[str] = None
    input_audio_path: Optional[str] = None
    output_audio_path: Optional[str] = None
    stt_request_id: Optional[str] = None
    tts_request_id: Optional[str] = None
    input_duration_ms: Optional[int] = None

class PaginatedChatlogResponse(BaseModel):
    chatlogs: List[ChatlogResponse]
    total_pages: int
    current_page: int
    total_chat: int

class ChatMessage(BaseModel):
    question: str
    answer: str
    created_at: datetime
    match_score: Optional[float] = None
    response_time_ms: Optional[int] = None

class ConversationInfoSchema(BaseModel):
    id: str
    title: str
    is_archived: bool


class TopicRecommendations(BaseModel):
    topics: List[str]
