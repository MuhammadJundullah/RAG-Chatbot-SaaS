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
    document_quota: int
    current_documents: int
    remaining_documents: int
    remaining_documents_percentage: float
    max_users: int
    current_users: int
    remaining_users: int
    remaining_users_percentage: float
    days_until_renewal: Optional[int] = None

class SubscriptionUpgradeRequest(BaseModel):
    plan_id: int

class SubscriptionTopUpRequest(BaseModel):
    quota: int

class TopUpPackageOption(BaseModel):
    package_type: str
    questions: int
    price: int

class TopUpPackageRequest(BaseModel):
    package_type: str  # e.g. "large" or "small"

class TopUpPackageResponse(BaseModel):
    package_type: str
    questions_added: int
    price: int
    transaction_id: int
    payment_url: str

class CustomPlanRequest(BaseModel):
    estimated_employees: Optional[int] = None
    need_internal_integration: Optional[str] = None
    special_requests: Optional[str] = None

class CustomPlanResponse(BaseModel):
    request_id: int
    status: str
    special_requests: Optional[str] = None


class CustomPlanApprovalRequest(BaseModel):
    price: int
    product_name: Optional[str] = "Custom Plan"


class CustomPlanApprovalResponse(BaseModel):
    transaction_id: int
    status: str
    payment_url: str

class PlansWithSubscription(BaseModel):
    plans: List[Plan]
    current_subscription: Optional[SubscriptionStatus] = None
    top_up_packages: List[TopUpPackageOption]

class Config:
    arbitrary_types_allowed = True
