from sqlalchemy import (
    Column,
    Integer,
    String,
    ForeignKey
)
from sqlalchemy.orm import relationship
from app.models.base import Base
from sqlalchemy import Boolean


class Users(Base):
    __tablename__ = "Users"
    id = Column(Integer, primary_key=True)
    name = Column(String(255))
    username = Column(String(255), unique=True, index=True, nullable=True)
    email = Column(String(255), unique=True, index=True, nullable=True)
    password = Column(String(255))
    pic_phone_number = Column(String(20), nullable=True)
    role = Column(String(50), nullable=False)
    company_id = Column(Integer, ForeignKey("Company.id"), nullable=True)
    division_id = Column(Integer, ForeignKey("Division.id"), nullable=True)
    is_active = Column(Boolean, default=True)


    company = relationship("Company", back_populates="users")
    division = relationship("Division", back_populates="users")
    chatlogs = relationship("Chatlogs", back_populates="user")