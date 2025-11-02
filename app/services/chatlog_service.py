from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from datetime import date
from fastapi import HTTPException

from app.repository.chatlog_repository import chatlog_repository
from app.schemas import chatlog_schema
from app.models.user_model import Users

async def get_all_chatlogs_as_admin_service(
    db: AsyncSession,
    company_id: Optional[int],
    division_id: Optional[int],
    user_id: Optional[int],
    start_date: Optional[date],
    end_date: Optional[date],
    skip: int,
    limit: int,
) -> List[chatlog_schema.Chatlog]:
    chatlogs = await chatlog_repository.get_all_chatlogs_for_admin(
        db=db,
        company_id=company_id,
        division_id=division_id,
        user_id=user_id,
        start_date=start_date,
        end_date=end_date,
        skip=skip,
        limit=limit,
    )
    return chatlogs

async def get_chatlogs_as_company_admin_service(
    db: AsyncSession,
    current_user: Users,
    division_id: Optional[int],
    user_id: Optional[int],
    start_date: Optional[date],
    end_date: Optional[date],
    skip: int,
    limit: int,
) -> List[chatlog_schema.Chatlog]:
    chatlogs = await chatlog_repository.get_chatlogs_for_company_admin(
        db=db,
        company_id=current_user.company_id,
        division_id=division_id,
        user_id=user_id,
        start_date=start_date,
        end_date=end_date,
        skip=skip,
        limit=limit,
    )
    return chatlogs

async def get_user_chatlogs_service(
    db: AsyncSession,
    current_user: Users,
    start_date: Optional[date],
    end_date: Optional[date],
    skip: int,
    limit: int,
) -> List[chatlog_schema.Chatlog]:
    chatlogs = await chatlog_repository.get_chatlogs(
        db,
        company_id=current_user.company_id,
        user_id=current_user.id,
        start_date=start_date,
        end_date=end_date,
        skip=skip,
        limit=limit,
    )
    return chatlogs

async def get_user_conversation_ids_service(
    db: AsyncSession,
    current_user: Users,
    skip: int,
    limit: int,
) -> List[str]:
    conversation_ids = await chatlog_repository.get_unique_conversation_ids_for_user(
        db=db,
        user_id=current_user.id,
        skip=skip,
        limit=limit,
    )
    return conversation_ids

async def get_conversation_history_service(
    db: AsyncSession,
    current_user: Users,
    conversation_id: str,
    skip: int,
    limit: int,
) -> List[chatlog_schema.Chatlog]:
    chat_history = await chatlog_repository.get_chat_history(
        db=db,
        conversation_id=conversation_id,
        user_id=current_user.id,
        skip=skip,
        limit=limit,
    )
    return chat_history

async def delete_conversation_service(
    db: AsyncSession,
    current_user: Users,
    conversation_id: str,
):
    deleted_count = await chatlog_repository.delete_chatlogs_by_conversation_id(
        db=db,
        conversation_id=conversation_id,
        user_id=current_user.id,
    )
    if deleted_count == 0:
        raise HTTPException(status_code=404, detail="Conversation not found or user does not have permission.")
    return {"message": f"Successfully deleted {deleted_count} chatlogs for conversation ID {conversation_id}."}