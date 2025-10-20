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


class Company(Base):
    __tablename__ = "Company"
    id = Column(Integer, primary_key=True)
    name = Column(String(100))
    code = Column(String(10))
    logo = Column(String(255), nullable=True)
    users = relationship("Users", back_populates="company")
    documents = relationship("Documents", back_populates="company")
    chatlogs = relationship("Chatlogs", back_populates="company")
    divisions = relationship("Division", back_populates="company")
