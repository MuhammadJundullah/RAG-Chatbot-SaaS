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


class Embeddings(Base):
    __tablename__ = "Embeddings"
    id = Column(Integer, primary_key=True)
    vector_id = Column(String)
    DocumentsId = Column(Integer, ForeignKey("Documents.id"), nullable=False)

    document = relationship("Documents", back_populates="embeddings")
