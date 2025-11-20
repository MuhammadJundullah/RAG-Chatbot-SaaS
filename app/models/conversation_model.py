from sqlalchemy import (
    Column,
    String,
    DateTime,
    func,
    Boolean,
    ForeignKey,
    Integer
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import expression
from app.models.guid import GUID
import uuid

from app.models.base import Base

class Conversation(Base):
    __tablename__ = "Conversation"

    id = Column(GUID, primary_key=True, index=True, default=uuid.uuid4)
    title = Column(String(255), nullable=False, default="New Conversation")
    company_id = Column(Integer, ForeignKey("Company.id"), nullable=False)
    is_archived = Column(Boolean, default=False, server_default=expression.false())
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())

    company = relationship("Company", back_populates="conversations")

    def __repr__(self):
        return f"<Conversation(id='{self.id}', title='{self.title}', summary='{self.summary}')>"
