from sqlalchemy import (
    Column,
    Integer,
    String,
    ForeignKey,
    Text,
    DateTime,
    func
)
from sqlalchemy.orm import relationship
from app.models.base import Base
from app.models.embedding_model import Embeddings

class Documents(Base):
    __tablename__ = "Documents"
    id = Column(Integer, primary_key=True)
    title = Column(String(255), nullable=False) # Original filename
    content_type = Column(String(100), nullable=True) # MIME type of the file
    storage_path = Column(String(255), nullable=False) # Path/key in S3
    status = Column(String(50), default="UPLOADED", nullable=False)
    extracted_text = Column(Text, nullable=True)
    company_id = Column(Integer, ForeignKey("Company.id"), nullable=False)

    company = relationship("Company", back_populates="documents")
    embeddings = relationship("Embeddings", back_populates="document")
