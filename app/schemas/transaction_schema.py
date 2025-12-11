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
    created_at: datetime
    paid_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class AdminTransaction(BaseModel):
    id: int
    company_name: str
    user_id: Optional[int] = None
    type: str
    plan_id: Optional[int] = None
    package_type: Optional[str] = None
    questions_delta: Optional[int] = None
    amount: int
    payment_url: Optional[str] = None
    payment_reference: Optional[str] = None
    status: str
    created_at: datetime
    paid_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class TransactionListResponse(BaseModel):
    items: list[Transaction]
    total: int
    current_page: int
    total_pages: int


class AdminTransactionListResponse(BaseModel):
    items: list[AdminTransaction]
    total_transaction: int
    current_page: int
    total_pages: int


class TransactionReceiptResponse(BaseModel):
    transaction_id: int
    status: str
    payment_url: Optional[str] = None
    receipt: Optional[dict] = None
    plan_name: Optional[str] = None


class PaymentSuccessResponse(BaseModel):
    transaction_id: int
    transaction_type: str
    transaction_status: str
    plan_name: Optional[str] = None
    active_start: Optional[datetime] = None
    active_end: Optional[datetime] = None
    subscription_status: Optional[str] = None
    
