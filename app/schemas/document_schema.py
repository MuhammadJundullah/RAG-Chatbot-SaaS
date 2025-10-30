from pydantic import BaseModel
from typing import Optional

class DocumentBase(BaseModel):
    """Base schema for a document, containing common fields."""
    title: str
    company_id: int
    s3_path: Optional[str] = None # Changed back to s3_path
    content_type: Optional[str] = None
    status: str

class DocumentCreate(BaseModel):
    """Schema used for creating a new document record in the database."""
    title: str
    company_id: int
    temp_storage_path: str # Will be provided by the endpoint internally
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