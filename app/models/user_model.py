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
from sqlalchemy import Boolean


class Users(Base):
    __tablename__ = "Users"
    id = Column(Integer, primary_key=True)
    name = Column(String(255))
    email = Column(String(255), unique=True, index=True)
    password = Column(String(255))
    is_super_admin = Column(Boolean, default=False)
    is_active_in_company = Column(Boolean, default=False)
    role = Column(String(50), nullable=False)
    company_id = Column(Integer, ForeignKey("Company.id"), nullable=True)
    Divisionid = Column(Integer, ForeignKey("Division.id"), nullable=True)

    company = relationship("Company", back_populates="users")
    division = relationship("Division", back_populates="users")
    chatlogs = relationship("Chatlogs", back_populates="user")
