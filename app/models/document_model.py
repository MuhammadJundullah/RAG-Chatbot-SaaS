import enum
from sqlalchemy import Column, Integer, String, ForeignKey, Text, Enum as SQLAlchemyEnum
from sqlalchemy.orm import relationship
from app.models.base import Base

class DocumentStatus(enum.Enum):
    UPLOADING = "UPLOADING"
    UPLOAD_FAILED = "UPLOAD_FAILED"
    UPLOADED = "UPLOADED"
    OCR_PROCESSING = "OCR_PROCESSING"
    PENDING_VALIDATION = "PENDING_VALIDATION"
    EMBEDDING = "EMBEDDING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    PROCESSING_FAILED = "PROCESSING_FAILED"

class Documents(Base):
    __tablename__ = "Documents"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    s3_path = Column(String, unique=True, nullable=True)
    temp_storage_path = Column(String, unique=True, nullable=True)
    company_id = Column(Integer, ForeignKey("Company.id"))
    status = Column(SQLAlchemyEnum(DocumentStatus), nullable=False, default=DocumentStatus.UPLOADING)
    content_type = Column(String)
    extracted_text = Column(Text, nullable=True)
    failed_reason = Column(Text, nullable=True)

    company = relationship("Company", back_populates="documents")
    embeddings = relationship("Embeddings", back_populates="document", cascade="all, delete-orphan")
