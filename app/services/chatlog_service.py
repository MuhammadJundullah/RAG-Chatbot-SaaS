from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from datetime import date
from fastapi import HTTPException
import math
import csv
import io

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
    page: int,
) -> chatlog_schema.PaginatedChatlogResponse:
    chatlogs_data, total_chat = await chatlog_repository.get_chatlogs_for_company_admin(
        db=db,
        company_id=current_user.company_id,
        division_id=division_id,
        user_id=user_id,
        start_date=start_date,
        end_date=end_date,
        skip=skip,
        limit=limit,
    )
    
    total_pages = math.ceil(total_chat / limit) if limit > 0 else 0
    
    return chatlog_schema.PaginatedChatlogResponse(
        chatlogs=[chatlog_schema.ChatlogResponse(**data) for data in chatlogs_data],
        total_pages=total_pages,
        current_page=page,
        total_chat=total_chat,
    )

async def export_chatlogs_as_company_admin_service(
    db: AsyncSession,
    current_user: Users,
    division_id: Optional[int],
    user_id: Optional[int],
    start_date: Optional[date],
    end_date: Optional[date],
) -> str:
    chatlogs_data, _ = await chatlog_repository.get_chatlogs_for_company_admin(
        db=db,
        company_id=current_user.company_id,
        division_id=division_id,
        user_id=user_id,
        start_date=start_date,
        end_date=end_date,
        skip=0,
        limit=-1,
    )

    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow(["id", "username", "created_at", "question", "answer"])

    for chatlog in chatlogs_data:
        writer.writerow([chatlog["id"], chatlog["username"], chatlog["created_at"], chatlog["question"], chatlog["answer"]])

    return output.getvalue()

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
) -> List[chatlog_schema.ConversationInfoSchema]: # Changed return type hint
    # The repository now returns a list of tuples: (UUID_object, title_str)
    conversation_data = await chatlog_repository.get_unique_conversation_ids_for_user(
        db=db,
        user_id=current_user.id,
        skip=skip,
        limit=limit,
    )
    # Format the data into ConversationInfoSchema objects, converting UUID to string
    return [
        chatlog_schema.ConversationInfoSchema(id=str(conv_id), title=title) # Convert UUID to string
        for conv_id, title in conversation_data
    ]

async def get_conversation_history_service(
    db: AsyncSession,
    current_user: Users,
    conversation_id: str,
    skip: int,
    limit: int,
) -> List[chatlog_schema.Chatlog]:
    chat_history_models = await chatlog_repository.get_chat_history(
        db=db,
        conversation_id=conversation_id,
        user_id=current_user.id,
        skip=skip,
        limit=limit,
    )
    # Convert Chatlog models to Pydantic schemas, ensuring conversation_id is a string
    return [
        chatlog_schema.Chatlog(
            id=chatlog.id,
            question=chatlog.question,
            answer=chatlog.answer,
            UsersId=chatlog.UsersId,
            company_id=chatlog.company_id,
            conversation_id=str(chatlog.conversation_id) 
        )
        for chatlog in chat_history_models
    ]

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