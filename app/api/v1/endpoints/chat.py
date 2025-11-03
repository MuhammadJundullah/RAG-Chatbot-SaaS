from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.schemas import chat_schema
from app.services import chat_service
from app.core.dependencies import get_current_user, get_db
from app.models.user_model import Users
from app.schemas.conversation_schema import ConversationListResponse # Import the response schema

router = APIRouter()

@router.post("/chat", tags=["Chat"])
async def chat_endpoint(
    request: chat_schema.ChatRequest,
    current_user: Users = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    response_data = await chat_service.process_chat_message(
        db=db,
        current_user=current_user,
        request=request
    )
    return response_data

@router.get("/conversations", response_model=List[ConversationListResponse], tags=["Chat"])
async def list_conversations_endpoint(
    current_user: Users = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
):
    """
    Retrieve a list of conversations for the current user.
    """
    conversations = await chat_service.get_conversations_with_titles(
        db=db,
        current_user=current_user,
        skip=skip,
        limit=limit,
    )
    return conversations