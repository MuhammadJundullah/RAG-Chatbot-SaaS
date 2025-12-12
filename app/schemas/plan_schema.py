# app/schemas/plan_schema.py
from datetime import datetime
from pydantic import BaseModel
from typing import Optional

class PlanBase(BaseModel):
    name: str
    price: int
    question_quota: int
    max_users: int
    document_quota: int = -1
    recomended_for: Optional[str] = None
    allow_custom_prompts: bool
    api_access: bool
    is_active: bool

class PlanCreate(PlanBase):
    pass

class PlanUpdate(BaseModel):
    name: Optional[str] = None
    price: Optional[int] = None
    question_quota: Optional[int] = None
    max_users: Optional[int] = None
    document_quota: Optional[int] = None
    recomended_for: Optional[str] = None
    allow_custom_prompts: Optional[bool] = None
    api_access: Optional[bool] = None
    is_active: Optional[bool] = None

class Plan(PlanBase):
    id: int
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class PlanPriceUpdate(BaseModel):
    name: str
    price: int


class PlanPublic(BaseModel):
    id: int
    name: str
    price: str
    question_quota: str
    max_users: str
    document_quota: str
    recomended_for: Optional[str] = None
    allow_custom_prompts: str
    api_access: str
    is_active: str
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
