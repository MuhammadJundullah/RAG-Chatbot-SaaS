from sqlalchemy.ext.asyncio import AsyncSession
from datetime import date, timedelta, datetime
from typing import Optional, Dict, List

from app.repository.document_repository import document_repository
from app.repository.chatlog_repository import chatlog_repository
from app.schemas import dashboard_schema

async def get_dashboard_summary(
    db: AsyncSession, 
    company_id: int, 
) -> dashboard_schema.DashboardResponseSchema:
    """
    Gathers all data required for the dashboard summary.
    """
    today = date.today()
    end_date = today # Use today as the end date for all calculations
    
    # Date range for the last 30 days
    start_date_30d = end_date - timedelta(days=29) # 30 days inclusive

    # Date range for the last 7 days
    start_date_7d = end_date - timedelta(days=6) # 7 days inclusive
    
    # Date range for the current month
    start_of_month = today.replace(day=1)

    # 1. Get document summary (this might need adjustment if it should be month-specific)
    # For now, assume it remains a general summary as per existing code.
    doc_summary_data = await document_repository.get_document_summary(db, company_id=company_id)
    document_summary = dashboard_schema.DocumentSummarySchema(**doc_summary_data)

    # 2. Get chat activity for the last 30 days
    daily_activity_data_list_30d = await chatlog_repository.get_daily_chat_activity(
        db, company_id=company_id, start_date=start_date_30d, end_date=end_date
    )
    chat_activity_dict_30d: Dict[str, int] = {}
    for row in daily_activity_data_list_30d:
        chat_activity_dict_30d[row.chat_date.strftime('%Y-%m-%d')] = row.chat_count
    
    # Fill missing dates for 30-day range
    current_date = start_date_30d
    while current_date <= end_date:
        date_str = current_date.strftime('%Y-%m-%d')
        if date_str not in chat_activity_dict_30d:
            chat_activity_dict_30d[date_str] = 0
        current_date += timedelta(days=1)
    sorted_chat_activity_30d = dict(sorted(chat_activity_dict_30d.items()))

    # 3. Get chat activity for the last 7 days
    daily_activity_data_list_7d = await chatlog_repository.get_daily_chat_activity(
        db, company_id=company_id, start_date=start_date_7d, end_date=end_date
    )
    chat_activity_dict_7d: Dict[str, int] = {}
    for row in daily_activity_data_list_7d:
        chat_activity_dict_7d[row.chat_date.strftime('%Y-%m-%d')] = row.chat_count
    
    # Fill missing dates for 7-day range
    current_date = start_date_7d
    while current_date <= end_date:
        date_str = current_date.strftime('%Y-%m-%d')
        if date_str not in chat_activity_dict_7d:
            chat_activity_dict_7d[date_str] = 0
        current_date += timedelta(days=1)
    sorted_chat_activity_7d = dict(sorted(chat_activity_dict_7d.items()))

    # 4. Get total chats (for the last 30 days) - assuming total is for the longer period
    total_chats = await chatlog_repository.get_total_chat_count(
        db, company_id=company_id, start_date=start_date_30d, end_date=end_date
    )
    
    # 5. Get document uploads for the current month
    # Assumes document_repository has a method to count uploads within a date range.
    # If this method does not exist, it will need to be added to the repository.
    document_uploads_this_month = await document_repository.get_document_uploads_count_in_range(
        db, company_id=company_id, start_date=start_of_month, end_date=end_date
    )

    # 6. Get recent documents (not affected by date filter)
    recent_docs_data = await document_repository.get_recent_documents(db, company_id=company_id, limit=3)
    recent_documents = [dashboard_schema.RecentDocumentSchema.from_orm(doc) for doc in recent_docs_data]

    # 7. Assemble the final response using the updated schema fields
    dashboard_response = dashboard_schema.DashboardResponseSchema(
        document_summary=document_summary,
        chat_activity_30d=sorted_chat_activity_30d,
        chat_activity_7d=sorted_chat_activity_7d,
        document_uploads_this_month=document_uploads_this_month, # Add the new field
        total_chats=total_chats,
        recent_documents=recent_documents,
    )

    return dashboard_response
