from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
import uuid
from app.schemas import chatlog_schema, document_schema

class ConversationUpdateTitle(BaseModel):
    title: str

class ConversationBase(BaseModel):
    title: str
    created_at: Optional[datetime] = None
    # Assuming Conversation model has id, title, created_at, updated_at
    # id is handled by the model's default UUID generation

class ConversationCreate(ConversationBase):
    id: str # Expecting a UUID string to be passed in

class ConversationListResponse(ConversationBase):
    id: uuid.UUID
    title: str
    is_archived: bool
    created_at: datetime

    class Config:
        from_attributes = True # For SQLAlchemy ORM mapping

class CompanyConversationResponse(BaseModel):
    conversation_id: uuid.UUID = Field(..., alias='id')
    title: str
    is_archived: bool
    created_at: datetime

    class Config:
        from_attributes = True
        populate_by_name = True

class PaginatedCompanyConversationResponse(BaseModel):
    conversations: List[CompanyConversationResponse]
    total_pages: int
    current_page: int
    total_conversations: int

class ConversationDetailResponse(BaseModel):
    conversation_id: uuid.UUID
    conversation_title: str
    is_archived: bool
    conversation_created_at: datetime
    username: str
    division_name: Optional[str]
    chat_history: List[chatlog_schema.ChatMessage]
    referenced_documents: List[document_schema.ReferencedDocument]
    company_id: int
