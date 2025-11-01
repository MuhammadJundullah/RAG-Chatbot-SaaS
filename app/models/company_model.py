from sqlalchemy import (
    Column,
    Integer,
    String,
    Boolean # Added Boolean import
)
from sqlalchemy.orm import relationship
from app.models.base import Base


class Company(Base):
    __tablename__ = "Company"
    id = Column(Integer, primary_key=True)
    name = Column(String(100))
    code = Column(String(10))
    logo_s3_path = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=False) # New column for company active status
    users = relationship("Users", back_populates="company")
    documents = relationship("Documents", back_populates="company")
    chatlogs = relationship("Chatlogs", back_populates="company")
    divisions = relationship("Division", back_populates="company")
    address = Column(String(255), nullable=True)
    pic_phone_number = Column(String(50), nullable=True) # Added pic_phone_number
