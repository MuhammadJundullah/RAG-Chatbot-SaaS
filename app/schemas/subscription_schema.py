# app/schemas/subscription_schema.py
from pydantic import BaseModel, UUID4
from typing import Optional
from datetime import datetime
from .plan_schema import Plan

class SubscriptionBase(BaseModel):
    company_id: int
    plan_id: int
    status: str
    current_question_usage: int
    top_up_quota: int

class SubscriptionCreate(BaseModel):
    plan_id: int

class Subscription(SubscriptionBase):
    id: int
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    plan: Plan

    class Config:
        from_attributes = True

class SubscriptionStatus(BaseModel):
    plan_name: str
    status: str
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    question_quota: int
    questions_used: int
    top_up_quota: int
    remaining_questions: int
    max_users: int

class SubscriptionUpgradeRequest(BaseModel):
    plan_id: int

class SubscriptionTopUpRequest(BaseModel):
    quota: int

class Config:
    arbitrary_types_allowed = True
