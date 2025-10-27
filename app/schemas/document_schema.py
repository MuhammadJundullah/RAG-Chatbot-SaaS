from pydantic import BaseModel
from typing import Optional

class DocumentBase(BaseModel):
    """Base schema for a document, containing common fields."""
    title: str
    company_id: int
    storage_path: str
    content_type: Optional[str] = None
    status: str

class DocumentCreate(BaseModel):
    """Schema used for creating a new document record in the database."""
    title: str
    company_id: int
    storage_path: str
    content_type: Optional[str] = None

class Document(DocumentBase):
    """Main schema for a document, used for API responses."""
    id: int
    extracted_text: Optional[str] = None

    class Config:
        from_attributes = True

class DocumentUpdateContentRequest(BaseModel):
    new_content: str
    filename: str