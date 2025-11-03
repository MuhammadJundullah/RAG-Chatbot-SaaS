from pydantic import BaseModel
from typing import Optional
from datetime import datetime
import uuid

class ConversationBase(BaseModel):
    title: str
    created_at: Optional[datetime] = None
    # Assuming Conversation model has id, title, created_at, updated_at
    # id is handled by the model's default UUID generation

class ConversationCreate(ConversationBase):
    id: str # Expecting a UUID string to be passed in

class ConversationListResponse(ConversationBase):
    id: str
    title: str
    created_at: datetime

    class Config:
        from_attributes = True # For SQLAlchemy ORM mapping
