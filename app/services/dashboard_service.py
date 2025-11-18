from sqlalchemy.ext.asyncio import AsyncSession
from datetime import date
from typing import Optional

from app.repository.document_repository import document_repository
from app.repository.chatlog_repository import chatlog_repository
from app.schemas import dashboard_schema

async def get_dashboard_summary(
    db: AsyncSession, 
    company_id: int, 
    start_date: Optional[date] = None, 
    end_date: Optional[date] = None
) -> dashboard_schema.DashboardResponseSchema:
    """
    Gathers all data required for the dashboard summary.
    """
    # 1. Get document summary (not affected by date filter)
    doc_summary_data = await document_repository.get_document_summary(db, company_id=company_id)
    document_summary = dashboard_schema.DocumentSummarySchema(**doc_summary_data)

    # 2. Get chat activity (with date filter)
    daily_activity_data = await chatlog_repository.get_daily_chat_activity(
        db, company_id=company_id, start_date=start_date, end_date=end_date
    )
    chat_activity = [
        dashboard_schema.ChatActivityPointSchema(date=row.chat_date, chat_count=row.chat_count)
        for row in daily_activity_data
    ]

    # 3. Get total chats (with date filter)
    total_chats = await chatlog_repository.get_total_chat_count(
        db, company_id=company_id, start_date=start_date, end_date=end_date
    )

    # 4. Get recent documents (not affected by date filter)
    recent_docs_data = await document_repository.get_recent_documents(db, company_id=company_id, limit=3)
    recent_documents = [dashboard_schema.RecentDocumentSchema.from_orm(doc) for doc in recent_docs_data]

    # 5. Assemble the final response
    dashboard_response = dashboard_schema.DashboardResponseSchema(
        document_summary=document_summary,
        chat_activity=chat_activity,
        total_chats=total_chats,
        recent_documents=recent_documents,
    )

    return dashboard_response
