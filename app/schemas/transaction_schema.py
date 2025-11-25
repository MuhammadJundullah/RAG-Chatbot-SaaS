# app/schemas/transaction_schema.py
from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class Transaction(BaseModel):
    id: int
    company_id: int
    user_id: Optional[int] = None
    type: str
    plan_id: Optional[int] = None
    package_type: Optional[str] = None
    questions_delta: Optional[int] = None
    amount: int
    payment_url: Optional[str] = None
    payment_reference: Optional[str] = None
    status: str
    metadata_json: Optional[str] = None
    created_at: datetime
    paid_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class TransactionListResponse(BaseModel):
    items: list[Transaction]
    total: int


class TransactionReceiptResponse(BaseModel):
    transaction_id: int
    status: str
    payment_url: Optional[str] = None
    receipt: Optional[dict] = None
