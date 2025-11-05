from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.schemas import chat_schema
from app.services import chat_service, document_service
from app.core.dependencies import get_current_user, get_db, get_current_employee
from app.models.user_model import Users
from app.schemas.conversation_schema import ConversationListResponse # Import the response schema
from app.schemas.document_schema import ReferencedDocument

router = APIRouter()

@router.post("/chat", tags=["Chat"])
async def chat_endpoint(
    request: chat_schema.ChatRequest,
    current_user: Users = Depends(get_current_employee),
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

@router.get("/chat/document", response_model=List[ReferencedDocument], tags=["Chat"])
async def get_company_documents(
    current_user: Users = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Retrieve a list of documents for the current user's company.
    Only returns document ID and title.
    """
    documents = await document_service.get_all_company_documents_service(
        db=db,
        current_user=current_user,
        skip=0,
        limit=1000000  # A large limit to get all documents
    )
    return [ReferencedDocument(id=doc.id, title=doc.title) for doc in documents]