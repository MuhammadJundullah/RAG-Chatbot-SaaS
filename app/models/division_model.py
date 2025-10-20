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


class Division(Base):
    __tablename__ = "Division"
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    company_id = Column(Integer, ForeignKey("Company.id"), nullable=False)

    company = relationship("Company", back_populates="divisions")
    users = relationship("Users", back_populates="division")
