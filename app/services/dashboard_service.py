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
    Gathers all data required for the dashboard summary for the last 30 days.
    """
    # Calculate date range for the last 30 days
    end_date = date.today()
    start_date = end_date - timedelta(days=29) # 30 days inclusive

    # 1. Get document summary (not affected by date filter)
    doc_summary_data = await document_repository.get_document_summary(db, company_id=company_id)
    document_summary = dashboard_schema.DocumentSummarySchema(**doc_summary_data)

    # 2. Get chat activity (for the last 30 days)
    daily_activity_data_list = await chatlog_repository.get_daily_chat_activity(
        db, company_id=company_id, start_date=start_date, end_date=end_date
    )
    # Transform list of ChatActivityPointSchema into a dictionary {date_str: chat_count}
    chat_activity_dict: Dict[str, int] = {}
    for row in daily_activity_data_list:
        chat_activity_dict[row.chat_date.strftime('%Y-%m-%d')] = row.chat_count
    
    # Fill in missing dates within the 30-day range with 0 chats
    current_date = start_date
    while current_date <= end_date:
        date_str = current_date.strftime('%Y-%m-%d')
        if date_str not in chat_activity_dict:
            chat_activity_dict[date_str] = 0
        current_date += timedelta(days=1)

    # Sort the dictionary by date
    sorted_chat_activity = dict(sorted(chat_activity_dict.items()))


    # 3. Get total chats (for the last 30 days)
    total_chats = await chatlog_repository.get_total_chat_count(
        db, company_id=company_id, start_date=start_date, end_date=end_date
    )

    # 4. Get recent documents (not affected by date filter)
    recent_docs_data = await document_repository.get_recent_documents(db, company_id=company_id, limit=3)
    recent_documents = [dashboard_schema.RecentDocumentSchema.from_orm(doc) for doc in recent_docs_data]

    # 5. Assemble the final response
    dashboard_response = dashboard_schema.DashboardResponseSchema(
        document_summary=document_summary,
        chat_activity=sorted_chat_activity, # Use the dictionary here
        total_chats=total_chats,
        recent_documents=recent_documents,
    )

    return dashboard_response
