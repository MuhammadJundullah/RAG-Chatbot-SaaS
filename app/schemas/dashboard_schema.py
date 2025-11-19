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

