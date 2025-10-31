from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas import chat_schema
from app.services import chat_service
from app.core.dependencies import get_current_user, get_db
from app.models.user_model import Users

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
