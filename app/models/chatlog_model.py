from sqlalchemy import (
    Column,
    Integer,
    String,
    ForeignKey,
    Text,
    DateTime,
    func,
    JSON,
    Index,
    Float,
)
from sqlalchemy.dialects.postgresql import UUID
from app.models.guid import GUID

from sqlalchemy.orm import relationship
from app.models.base import Base

class Chatlogs(Base):
    __tablename__ = "Chatlogs"
    __table_args__ = (
        Index("ix_chatlogs_company_created", "company_id", "created_at"),
        Index("ix_chatlogs_company_user", "company_id", "UsersId"),
    )
    id = Column(Integer, primary_key=True)
    question = Column(Text)
    answer = Column(Text)
    UsersId = Column(Integer, ForeignKey("Users.id"), nullable=False)
    company_id = Column(Integer, ForeignKey("Company.id"), nullable=False)
    conversation_id = Column(GUID, ForeignKey('Conversation.id'), nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    referenced_document_ids = Column(JSON, nullable=True)
    match_score = Column(Float, nullable=True)  # Stored as percentage (0-100)
    response_time_ms = Column(Integer, nullable=True)

    user = relationship("Users", back_populates="chatlogs")
    company = relationship("Company", back_populates="chatlogs")
