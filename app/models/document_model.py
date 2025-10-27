import enum
from sqlalchemy import Column, Integer, String, ForeignKey, Text, Enum as SQLAlchemyEnum
from sqlalchemy.orm import relationship
from app.models.base import Base
from app.models.embedding_model import Embeddings

class DocumentStatus(enum.Enum):
    UPLOADED = "UPLOADED"
    OCR_PROCESSING = "OCR_PROCESSING"
    PENDING_VALIDATION = "PENDING_VALIDATION"
    EMBEDDING = "EMBEDDING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED" # General failure, might be deprecated
    PROCESSING_FAILED = "PROCESSING_FAILED" # New specific status

class Documents(Base):
    __tablename__ = "Documents"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    storage_path = Column(String, unique=True)
    company_id = Column(Integer, ForeignKey("Company.id"))
    status = Column(SQLAlchemyEnum(DocumentStatus), nullable=False, default=DocumentStatus.UPLOADED)
    content_type = Column(String)
    extracted_text = Column(Text, nullable=True)
    failed_reason = Column(Text, nullable=True) # New column for error details

    company = relationship("Company", back_populates="documents")
    embeddings = relationship("Embeddings", back_populates="document", cascade="all, delete-orphan")
