from sqlalchemy import (
    Column,
    Integer,
    String,
    Boolean,
    DateTime,
    func,
)
from sqlalchemy.orm import relationship
from app.models.base import Base


class Company(Base):
    __tablename__ = "Company"
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    company_email = Column(String(100), nullable=True, unique=True)
    code = Column(String(10), unique=True)
    logo_s3_path = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=False)
    address = Column(String(255), nullable=True)
    pic_phone_number = Column(String(50), nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    users = relationship("Users", back_populates="company")
    documents = relationship("Documents", back_populates="company")
    conversations = relationship("Conversation", back_populates="company")
    chatlogs = relationship("Chatlogs", back_populates="company")
    
    # Relationship to Subscription
    subscription = relationship("Subscription", back_populates="company", uselist=False, cascade="all, delete-orphan")
    
    activity_logs = relationship("ActivityLog", back_populates="company")
