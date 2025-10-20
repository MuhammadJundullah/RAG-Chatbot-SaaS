from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import Optional
from datetime import date
from app.models import chatlog_model
from app.schemas import chatlog_schema

async def create_chatlog(db: AsyncSession, chatlog: chatlog_schema.ChatlogCreate):
    db_chatlog = chatlog_model.Chatlogs(**chatlog.model_dump())
    db.add(db_chatlog)
    await db.commit()
    await db.refresh(db_chatlog)
    return db_chatlog

async def get_chatlogs(
    db: AsyncSession,
    company_id: Optional[int] = None,
    user_id: Optional[int] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    skip: int = 0,
    limit: int = 100,
):
    query = select(chatlog_model.Chatlogs)
    if company_id:
        query = query.filter(chatlog_model.Chatlogs.company_id == company_id)
    if user_id:
        query = query.filter(chatlog_model.Chatlogs.UsersId == user_id)
    if start_date:
        query = query.filter(chatlog_model.Chatlogs.created_at >= start_date)
    if end_date:
        query = query.filter(chatlog_model.Chatlogs.created_at <= end_date)
    
    result = await db.execute(query.offset(skip).limit(limit))
    return result.scalars().all()
