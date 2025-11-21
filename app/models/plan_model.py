# app/models/plan_model.py
from sqlalchemy import Column, Integer, String, Boolean
from .base import Base

class Plan(Base):
    __tablename__ = 'plans'
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False) 
    price = Column(Integer, nullable=False)
    question_quota = Column(Integer, nullable=False) 
    max_users = Column(Integer, nullable=False)
    allow_custom_prompts = Column(Boolean, default=False)
    api_access = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
