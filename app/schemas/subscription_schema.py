# app/schemas/subscription_schema.py
from pydantic import BaseModel, UUID4
from typing import List, Optional
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
    end_date: Optional[datetime] = None
    monthly_quota: int
    top_up_quota: int
    total_quota: int
    remaining_quota: int
    remaining_quota_percentage: float
    days_until_renewal: Optional[int] = None

class SubscriptionUpgradeRequest(BaseModel):
    plan_id: int

class SubscriptionTopUpRequest(BaseModel):
    quota: int

class TopUpPackageRequest(BaseModel):
    package_type: str  # e.g. "large" or "small"

class TopUpPackageResponse(BaseModel):
    package_type: str
    questions_added: int
    price: int
    subscription: SubscriptionStatus

class PlansWithSubscription(BaseModel):
    plans: List[Plan]
    current_subscription: Optional[SubscriptionStatus] = None

class Config:
    arbitrary_types_allowed = True
