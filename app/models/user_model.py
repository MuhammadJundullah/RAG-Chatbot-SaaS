from sqlalchemy import (
    Column,
    Integer,
    String,
    ForeignKey,
    DateTime 
)
from sqlalchemy.orm import relationship
from app.models.base import Base
from sqlalchemy import Boolean
from datetime import datetime


class Users(Base):
    __tablename__ = "Users"
    id = Column(Integer, primary_key=True)
    name = Column(String(255))
    username = Column(String(255), unique=True, index=True, nullable=True)
    email = Column(String(255), unique=True, index=True, nullable=True)
    password = Column(String(255))
    role = Column(String(50), nullable=False)
    company_id = Column(Integer, ForeignKey("Company.id"), nullable=True)
    division = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True)
    profile_picture_url = Column(String, nullable=True)

    # Added fields for password reset
    reset_token = Column(String(255), nullable=True)
    reset_token_expiry = Column(DateTime, nullable=True)

    company = relationship("Company", back_populates="users")
    chatlogs = relationship("Chatlogs", back_populates="user")

    # Add relationship for activity logs
    activity_logs = relationship("ActivityLog", back_populates="user")

    