from pydantic import BaseModel, field_validator
from typing import Optional, List
from datetime import datetime
from app.models.document_model import DocumentStatus

class DocumentBase(BaseModel):
    """Base schema for a document, containing common fields."""
    title: str
    company_id: int
    s3_path: Optional[str] = None 
    content_type: Optional[str] = None
    status: DocumentStatus
    tags: Optional[List[str]] = None 
    uploaded_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

class DocumentCreate(BaseModel):
    """Schema used for creating a new document record in the database."""
    title: str
    company_id: int
    temp_storage_path: str
    content_type: Optional[str] = None
    tags: List[str] = [] 
    # uploaded_at is set by the system, not provided in create request

class Document(DocumentBase):
    """Main schema for a document, used for API responses."""
    id: int
    extracted_text: Optional[str] = None

    class Config:
        from_attributes = True

    @field_validator('tags', mode='after')
    def ensure_tags_is_list(cls, v):
        """Ensures that tags is always a list, defaulting to empty list if None."""
        if v is None:
            return []
        return v

class DocumentUpdateContentRequest(BaseModel):
    new_content: str
    # Reverted to strictly accept 'title'
    title: Optional[str] = None
    tags: Optional[List[str]] = None

class ReferencedDocument(BaseModel):
    id: int
    title: str