from pydantic import BaseModel
from typing import List, Optional, Dict
from datetime import date, datetime
from app.models.document_model import DocumentStatus

class DocumentSummarySchema(BaseModel):
    total_documents: int
    processing_documents: int
    completed_documents: int
    failed_documents: int

class ChatActivityPointSchema(BaseModel):
    date: date
    chat_count: int

class RecentDocumentSchema(BaseModel):
    id: int
    title: str
    status: DocumentStatus
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class DashboardResponseSchema(BaseModel):
    document_summary: DocumentSummarySchema
    chat_activity_30d: dict
    chat_activity_7d: dict
    document_uploads_this_month: int

    total_chats: int
    recent_documents: List[RecentDocumentSchema]

class DashboardBreakdownResponseSchema(BaseModel):
    dashboard_breakdown: DashboardResponseSchema


class SuperAdminDashboardData(BaseModel):
    active_company_admins: int
    active_companies_this_month: int
    total_users: int
    user_wow_change_pct: float
    user_wow_change_pct_status: str

    document_distribution: dict

    chats_this_month: int
    chat_mom_change_pct: float
    chat_mom_change_pct_status: str
    total_questions_this_month: int

    daily_chat_counts: dict

    top_user_logs: List[dict]
    daily_company_registrations_7d: dict


class SuperAdminDashboardResponse(BaseModel):
    dashboard_summary: SuperAdminDashboardData
