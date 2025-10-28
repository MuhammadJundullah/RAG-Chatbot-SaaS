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
    if start_date:
        query = query.filter(chatlog_model.Chatlogs.created_at >= start_date)
    if end_date:
        query = query.filter(chatlog_model.Chatlogs.created_at <= end_date)
    
    result = await db.execute(query.offset(skip).limit(limit))
    return result.scalars().all()

async def get_chat_history(
    db: AsyncSession,
    conversation_id: str,
    user_id: int,
    skip: int = 0,
    limit: int = 100,
):
    query = select(chatlog_model.Chatlogs).filter(
        chatlog_model.Chatlogs.conversation_id == conversation_id,
        chatlog_model.Chatlogs.UsersId == user_id
    ).order_by(chatlog_model.Chatlogs.created_at)
    result = await db.execute(query.offset(skip).limit(limit))
    return result.scalars().all()


async def get_all_chatlogs_for_admin(
    db: AsyncSession,
    company_id: Optional[int] = None,
    division_id: Optional[int] = None,
    user_id: Optional[int] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    skip: int = 0,
    limit: int = 100,
):
    from app.models.user_model import Users

    query = select(chatlog_model.Chatlogs)

    if user_id:
        query = query.filter(chatlog_model.Chatlogs.UsersId == user_id)
    
    if division_id:
        query = query.join(Users, chatlog_model.Chatlogs.UsersId == Users.id).filter(Users.Divisionid == division_id)

    
    result = await db.execute(query.offset(skip).limit(limit))
    return result.scalars().all()

async def get_chatlogs_for_company_admin(
    db: AsyncSession,
    company_id: int,
    division_id: Optional[int] = None,
    user_id: Optional[int] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    skip: int = 0,
    limit: int = 100,
):
    from app.models.user_model import Users

    query = select(chatlog_model.Chatlogs).filter(chatlog_model.Chatlogs.company_id == company_id)

    if user_id:
        query = query.filter(chatlog_model.Chatlogs.UsersId == user_id)

    if division_id:
        query = query.join(Users, chatlog_model.Chatlogs.UsersId == Users.id).filter(Users.Divisionid == division_id)

    if start_date:
        query = query.filter(chatlog_model.Chatlogs.created_at >= start_date)
    if end_date:
        query = query.filter(chatlog_model.Chatlogs.created_at <= end_date)
    
    result = await db.execute(query.offset(skip).limit(limit))
    return result.scalars().all()

async def get_unique_conversation_ids_for_user(
    db: AsyncSession,
    user_id: int,
    skip: int = 0,
    limit: int = 100,
):
    # Subquery to find the latest created_at for each conversation_id
    latest_chat_per_conversation = select(
        chatlog_model.Chatlogs.conversation_id,
        chatlog_model.Chatlogs.created_at
    ).filter(
        chatlog_model.Chatlogs.UsersId == user_id
    ).distinct(chatlog_model.Chatlogs.conversation_id).order_by(
        chatlog_model.Chatlogs.conversation_id,
        chatlog_model.Chatlogs.created_at.desc()
    ).subquery()

    # Main query to select distinct conversation_id ordered by their latest message
    query = select(latest_chat_per_conversation.c.conversation_id).order_by(
        latest_chat_per_conversation.c.created_at.desc()
    )
    result = await db.execute(query.offset(skip).limit(limit))
    return result.scalars().all()
