# app/schemas/plan_schema.py
from pydantic import BaseModel
from typing import Optional

class PlanBase(BaseModel):
    name: str
    price: int
    question_quota: int
    max_users: int
    document_quota: int = -1
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
    allow_custom_prompts: Optional[bool] = None
    api_access: Optional[bool] = None
    is_active: Optional[bool] = None

class Plan(PlanBase):
    id: int

    class Config:
        from_attributes = True
