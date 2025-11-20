from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from pydantic import BaseModel
from starlette.responses import StreamingResponse
import uuid

from app.schemas import chat_schema, chatlog_schema
from app.services import chat_service, document_service
from app.core.dependencies import get_current_user, get_db, get_current_employee, check_quota_and_subscription
from app.models.user_model import Users
from app.schemas.conversation_schema import ConversationListResponse, ConversationUpdateTitle
from app.repository.chatlog_repository import chatlog_repository
from app.services.rag_service import rag_service
from app.services.gemini_service import gemini_service
from app.repository.conversation_repository import conversation_repository
from app.schemas.conversation_schema import ConversationCreate
from app.utils.activity_logger import log_activity

router = APIRouter()

# --- NEW Pydantic model for chat document response ---
class ChatDocumentResponse(BaseModel):
    id: int
    title: str
    extracted_text: Optional[str] = None

@router.post("/chat", tags=["Chat"])
async def chat_endpoint(
    request: chat_schema.ChatRequest,
    current_user: Users = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _quota_check: None = Depends(check_quota_and_subscription)
):
    response_data = await chat_service.process_chat_message(
        db=db,
        current_user=current_user,
        request=request
    )

    # Log chat message
    company_id_to_log = current_user.company_id if current_user.company else None
    await log_activity(
        db=db, # Pass the database session
        user_id=current_user.id, # Use integer user ID
        activity_type_category="Data/CRUD", # Or a new category like "CHAT_MESSAGE"
        company_id=company_id_to_log, # Use integer company ID
        activity_description=f"User '{current_user.email}' sent a chat message.",
    )
    return response_data

@router.post("/sse/chat", tags=["Chat"])
async def sse_chat_endpoint(
    request: chat_schema.ChatRequest,
    current_user: Users = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _quota_check: None = Depends(check_quota_and_subscription)
):
    """
    Streams AI chat responses using Server-Sent Events (SSE).
    """
    async def event_generator():
        conversation_id_str = request.conversation_id
        user_message = request.message
        company_id = current_user.company_id
        full_response = ""

        # If no conversation_id is provided, create a new conversation
        if not conversation_id_str:
            new_uuid = str(uuid.uuid4())
            conversation_title = await chat_service.generate_conversation_title(user_message=user_message, conversation_history=[])
            conversation_create_schema = ConversationCreate(
                id=new_uuid,
                title=conversation_title,
            )
            await conversation_repository.create_conversation(db=db, conversation=conversation_create_schema)
            conversation_id_str = new_uuid
        else:
            # Validate the provided conversation_id
            try:
                valid_conversation_id = uuid.UUID(request.conversation_id)
                conversation_id_str = str(valid_conversation_id)
            except ValueError:
                yield "data: {\"error\": \"Invalid conversation ID format.\"}\n\n"
                return

            # Check if the conversation exists. If not, create it.
            existing_conversation = await conversation_repository.get_conversation(db=db, conversation_id=conversation_id_str)
            if not existing_conversation:
                conversation_title = await chat_service.generate_conversation_title(user_message=user_message, conversation_history=[])
                conversation_create_schema = ConversationCreate(
                    id=conversation_id_str,
                    title=conversation_title
                )
                await conversation_repository.create_conversation(db=db, conversation=conversation_create_schema)

        # 1. Get chat history for context
        history_records = await chatlog_repository.get_chat_history(
            db=db,
            conversation_id=conversation_id_str,
            user_id=current_user.id
        )
        conversation_history = [{"question": record.question, "answer": record.answer} for record in history_records]

        # 2. Get context from RAG service
        rag_response = await rag_service.get_relevant_context(
            query=user_message,
            company_id=company_id
        )
        rag_context = rag_response["context"]
        document_ids = rag_response["document_ids"]

        # 3. Generate chat response in streaming fashion
        try:
            async for chunk in gemini_service.generate_chat_response(
                question=user_message,
                context=rag_context,
                query_results=None, 
                db=db,
                current_user=current_user,
                conversation_history=conversation_history
            ):
                full_response += chunk
                yield f"data: {chunk}\n\n" 
        except Exception as e: 
            yield f"data: {{\"error\": \"An error occurred during AI response generation: {str(e)}\"}}\n\n"
            return
        
        # 4. Save chat to database after full response is received
        chatlog_data = chatlog_schema.ChatlogCreate(
            question=user_message,
            answer=full_response,
            UsersId=current_user.id,
            company_id=company_id,
            conversation_id=conversation_id_str,
            referenced_document_ids=document_ids
        )
        await chatlog_repository.create_chatlog(db=db, chatlog=chatlog_data)

        # Log chat message (after saving to chatlog)
        company_id_to_log = current_user.company_id if current_user.company else None
        await log_activity(
            db=db, 
            user_id=current_user.id, 
            activity_type_category="Data/CRUD", 
            company_id=company_id_to_log, 
            activity_description=f"User '{current_user.email}' sent a chat message in conversation {conversation_id_str}.",
        )

        # Signal end of stream
        yield "event: end\ndata: {}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")

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

    # Log conversation list retrieval
    company_id_to_log = current_user.company_id if current_user.company else None
    await log_activity(
        db=db, 
        user_id=current_user.id, 
        activity_type_category="Data/CRUD",
        company_id=company_id_to_log, 
        activity_description=f"User '{current_user.email}' retrieved list of conversations. Found {len(conversations)} conversations.",
    )
    return conversations

@router.patch("/chat/conversations/{conversation_id}/archive", response_model=ConversationListResponse, tags=["Chat"])
async def archive_conversation_endpoint(
    conversation_id: str,
    current_user: Users = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Archives a specific conversation.
    """
    updated_conversation = await chat_service.archive_chat(
        db=db,
        conversation_id=conversation_id,
        current_user=current_user
    )
    # Log activity
    await log_activity(
        db=db,
        user_id=current_user.id,
        activity_type_category="Data/CRUD",
        company_id=current_user.company_id,
        activity_description=f"User '{current_user.email}' archived conversation {conversation_id}.",
    )
    return updated_conversation

@router.patch("/chat/conversations/{conversation_id}/title", response_model=ConversationListResponse, tags=["Chat"])
async def edit_conversation_title_endpoint(
    conversation_id: str,
    request: ConversationUpdateTitle,
    current_user: Users = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Edits the title of a specific conversation.
    """
    updated_conversation = await chat_service.edit_chat_title(
        db=db,
        conversation_id=conversation_id,
        new_title=request.title,
        current_user=current_user
    )
    # Log activity
    await log_activity(
        db=db,
        user_id=current_user.id,
        activity_type_category="Data/CRUD",
        company_id=current_user.company_id,
        activity_description=f"User '{current_user.email}' edited title of conversation {conversation_id}.",
    )
    return updated_conversation

@router.get("/chat/document", response_model=List[ChatDocumentResponse], tags=["Chat"]) # Changed response_model
async def get_company_documents(
    current_user: Users = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Retrieve a list of documents for the current user's company, including their extracted text.
    """
    documents_list, total_count = await document_service.get_all_company_documents_service(
        db=db,
        current_user=current_user,
        skip=0,
        limit=1000000
    )

    # Log document list retrieval
    company_id_to_log = current_user.company_id if current_user.company else None
    await log_activity(
        db=db, 
        user_id=current_user.id,
        activity_type_category="Data/CRUD",
        company_id=company_id_to_log, 
        activity_description=f"User '{current_user.email}' retrieved list of company documents for chat. Found {len(documents_list)} documents.",
    )

    # Map documents to the new response model including extracted_text
    return [
        {
            "id": doc.id,
            "title": doc.title,
            "extracted_text": doc.extracted_text,
        }
        for doc in documents_list
    ]