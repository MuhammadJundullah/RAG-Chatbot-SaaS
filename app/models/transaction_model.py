from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from sqlalchemy import func

from .base import Base


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("Company.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("Users.id"), nullable=True, index=True)

    type = Column(String, nullable=False)  # subscription, topup, custom_plan
    plan_id = Column(Integer, ForeignKey("plans.id"), nullable=True)
    package_type = Column(String, nullable=True)
    questions_delta = Column(Integer, nullable=True)

    amount = Column(Integer, nullable=False, default=0)
    payment_reference = Column(String, nullable=True, index=True)

    status = Column(String, nullable=False, default="pending_payment")  # pending_payment|paid|failed|cancelled|pending_review
    metadata_json = Column(Text, nullable=True)

    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    paid_at = Column(DateTime, nullable=True)

    company = relationship("Company")
    user = relationship("Users")
