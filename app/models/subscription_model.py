# app/models/subscription_model.py
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from .base import Base

class Subscription(Base):
    __tablename__ = 'subscriptions'
    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey('Company.id'), nullable=False, unique=True)
    plan_id = Column(Integer, ForeignKey('plans.id'), nullable=False)
    
    # Status alur pembayaran: pending_payment -> active -> expired
    status = Column(String, default='pending_payment', nullable=False)
    
    start_date = Column(DateTime)
    end_date = Column(DateTime)
    current_question_usage = Column(Integer, default=0)
    top_up_quota = Column(Integer, default=0)
    payment_gateway_reference = Column(String, index=True) # Untuk menyimpan trx_id dari iPaymu

    company = relationship("Company", back_populates="subscription")
    plan = relationship("Plan")
