# app/schemas/subscription_schema.py
from pydantic import BaseModel, model_validator
from typing import List, Optional, Literal
from datetime import datetime
from .plan_schema import Plan, PlanPublic

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
    transaction_type: Literal["subscription", "topup"] = "subscription"
    plan_id: Optional[int] = None
    package_type: Optional[str] = None
    success_return_url: Optional[str] = None
    failed_return_url: Optional[str] = None

    @model_validator(mode="after")
    def validate_fields(self):
        if self.transaction_type == "subscription":
            if not self.plan_id:
                raise ValueError("plan_id is required for subscription upgrade")
        if self.transaction_type == "topup":
            if not self.package_type:
                raise ValueError("package_type is required for top-up")
        return self

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

class PlansWithSubscription(BaseModel):
    plans: List[PlanPublic]
    current_subscription: Optional[SubscriptionStatus] = None
    top_up_packages: List[TopUpPackageOption]

class Config:
    arbitrary_types_allowed = True
