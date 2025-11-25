# app/models/plan_model.py
from sqlalchemy import Column, Integer, String, Boolean, Index
from .base import Base

class Plan(Base):
    __tablename__ = 'plans'
    __table_args__ = (
        Index("ix_plans_is_active", "is_active"),
        Index("ix_plans_price", "price"),
    )
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False) 
    price = Column(Integer, nullable=False)
    question_quota = Column(Integer, nullable=False) 
    max_users = Column(Integer, nullable=False)
    document_quota = Column(Integer, nullable=True, default=-1)
    allow_custom_prompts = Column(Boolean, default=False)
    api_access = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
