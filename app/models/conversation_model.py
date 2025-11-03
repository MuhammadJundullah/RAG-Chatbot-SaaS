from sqlalchemy import (
    Column,
    Integer,
    String,
    ForeignKey,
    DateTime,
    func,
    Text
)
from sqlalchemy.dialects.postgresql import UUID
import uuid

from sqlalchemy.orm import relationship
from app.models.base import Base

class Conversation(Base):
    __tablename__ = "Conversation"

    id = Column(UUID(as_uuid=True), primary_key=True, index=True, default=uuid.uuid4)
    title = Column(String(255), nullable=False, default="New Conversation")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())

    def __repr__(self):
        return f"<Conversation(id='{self.id}', title='{self.title}', summary='{self.summary}')>"
