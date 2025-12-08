from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from pydantic import BaseModel
from starlette.responses import StreamingResponse
import uuid
import re
import time

from app.schemas import chat_schema, chatlog_schema
from app.modules.chat.service import chat_service
from app.modules.documents import service as document_service
from app.core.dependencies import get_current_user, get_db, get_current_employee, check_quota_and_subscription
from app.models.user_model import Users
from app.schemas.conversation_schema import (
    ConversationArchiveStatusUpdate,
    ConversationListResponse,
    ConversationUpdateTitle,
)
from app.repository.chatlog_repository import chatlog_repository
from app.modules.documents.rag_service import rag_service
from app.modules.chat.together_service import together_service
from app.repository.conversation_repository import conversation_repository
from app.schemas.conversation_schema import ConversationCreate
from app.utils.activity_logger import log_activity

router = APIRouter()


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

    company_id_to_log = current_user.company_id if current_user.company else None
    await log_activity(
        db=db,
        user_id=current_user.id,
        activity_type_category="Data/CRUD",
        company_id=company_id_to_log,
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
        BUFFER_CHAR_LIMIT = 180
        END_MARKERS = ["[ENDFINALRESPONSE]", "<|end|>", "</s>"]
        def clean_text(text: str) -> str:
            text = text.strip()
            text = re.sub(r"\s+([,!.?])", r"\1", text)  # remove space before punctuation
            text = re.sub(r"([,!.?]){2,}", r"\1", text)  # collapse repeated punctuation
            text = re.sub(r"\s{2,}", " ", text)  # collapse double spaces
            text = re.sub(r"([.!?])\s+[A-Za-z]{1,2}\.$", r"\1", text)  # drop trailing orphan tokens like 'an.'
            return text

        def should_flush(buf: str) -> bool:
            if len(buf) >= BUFFER_CHAR_LIMIT:
                return True
            return any(buf.endswith(p) for p in [".", "!", "?", "?!", "!?"])

        conversation_id_str = request.conversation_id
        user_message = request.message
        company_id = current_user.company_id
        full_response = ""
        buffer = ""
        final_response = ""
        start_time = time.monotonic()

        if not conversation_id_str:
            new_uuid = str(uuid.uuid4())
            conversation_title = await chat_service.generate_conversation_title(user_message=user_message, conversation_history=[])
            conversation_create_schema = ConversationCreate(
                id=new_uuid,
                title=conversation_title,
                company_id=company_id,
            )
            await conversation_repository.create_conversation(db=db, conversation=conversation_create_schema)
            conversation_id_str = new_uuid
        else:
            try:
                valid_conversation_id = uuid.UUID(request.conversation_id)
                conversation_id_str = str(valid_conversation_id)
            except ValueError:
                yield "data: {\"error\": \"Invalid conversation ID format.\"}\n\n"
                return

            existing_conversation = await conversation_repository.get_conversation(db=db, conversation_id=conversation_id_str)
            if not existing_conversation:
                conversation_title = await chat_service.generate_conversation_title(user_message=user_message, conversation_history=[])
                conversation_create_schema = ConversationCreate(
                    id=conversation_id_str,
                    title=conversation_title,
                    company_id=company_id,
                )
                await conversation_repository.create_conversation(db=db, conversation=conversation_create_schema)

        history_records = await chatlog_repository.get_chat_history(
            db=db,
            conversation_id=conversation_id_str,
            user_id=current_user.id
        )
        conversation_history = [{"question": record.question, "answer": record.answer} for record in history_records]

        rag_response = await rag_service.get_relevant_context(
            query=user_message,
            company_id=company_id
        )
        rag_context = rag_response["context"]
        document_ids = rag_response["document_ids"]
        match_score = rag_response.get("match_score")

        try:
            async for chunk in together_service.generate_chat_response(
                question=user_message,
                context=rag_context,
                db=db,
                current_user=current_user,
                conversation_history=conversation_history,
                model_name=request.model,
            ):
                # Sanitize model end markers
                for marker in END_MARKERS:
                    chunk = chunk.replace(marker, "")
                if not chunk:
                    continue

                full_response += chunk
                buffer += chunk

                if should_flush(buffer):
                    cleaned = clean_text(buffer)
                    if cleaned:
                        final_response += cleaned
                        yield f"data: {cleaned}\n\n"
                    buffer = ""
        except Exception as e:
            if buffer:
                cleaned = clean_text(buffer)
                if cleaned:
                    final_response += cleaned
                    yield f"data: {cleaned}\n\n"
            yield f"data: {{\"error\": \"An error occurred during AI response generation: {str(e)}\"}}\n\n"
            return

        if buffer:
            cleaned = clean_text(buffer)
            if cleaned:
                final_response += cleaned
                yield f"data: {cleaned}\n\n"

        if not final_response:
            final_response = clean_text(full_response)
        else:
            # If we already streamed cleaned parts, ensure any trailing uncleaned part is included
            remaining = clean_text(full_response[len(final_response):])
            final_response += remaining

        chatlog_data = chatlog_schema.ChatlogCreate(
            question=user_message,
            answer=final_response,
            UsersId=current_user.id,
            company_id=company_id,
            conversation_id=conversation_id_str,
            referenced_document_ids=document_ids,
            match_score=match_score,
            response_time_ms=int((time.monotonic() - start_time) * 1000),
        )
        await chatlog_repository.create_chatlog(db=db, chatlog=chatlog_data)

        company_id_to_log = current_user.company_id if current_user.company else None
        await log_activity(
            db=db,
            user_id=current_user.id,
            activity_type_category="Data/CRUD",
            company_id=company_id_to_log,
            activity_description=f"User '{current_user.email}' sent a chat message in conversation {conversation_id_str}.",
        )

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
    await log_activity(
        db=db,
        user_id=current_user.id,
        activity_type_category="Data/CRUD",
        company_id=current_user.company_id,
        activity_description=f"User '{current_user.email}' archived conversation {conversation_id}.",
    )
    return updated_conversation


@router.patch("/chat/conversations/{conversation_id}/archive-status", response_model=ConversationListResponse, tags=["Chat"])
async def set_archive_status_endpoint(
    conversation_id: str,
    request: ConversationArchiveStatusUpdate,
    current_user: Users = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Sets the archive status of a specific conversation (archive or unarchive).
    """
    updated_conversation = await chat_service.set_archive_status(
        db=db,
        conversation_id=conversation_id,
        is_archived=request.is_archived,
        current_user=current_user
    )
    status_label = "archived" if request.is_archived else "unarchived"
    await log_activity(
        db=db,
        user_id=current_user.id,
        activity_type_category="Data/CRUD",
        company_id=current_user.company_id,
        activity_description=f"User '{current_user.email}' {status_label} conversation {conversation_id}.",
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
    await log_activity(
        db=db,
        user_id=current_user.id,
        activity_type_category="Data/CRUD",
        company_id=current_user.company_id,
        activity_description=f"User '{current_user.email}' edited title of conversation {conversation_id}.",
    )
    return updated_conversation


@router.get("/chat/document", response_model=List[ChatDocumentResponse], tags=["Chat"])
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

    company_id_to_log = current_user.company_id if current_user.company else None
    await log_activity(
        db=db,
        user_id=current_user.id,
        activity_type_category="Data/CRUD",
        company_id=company_id_to_log,
        activity_description=f"User '{current_user.email}' retrieved list of company documents for chat. Found {len(documents_list)} documents.",
    )

    return [
        {
            "id": doc.id,
            "title": doc.title,
            "extracted_text": doc.extracted_text,
        }
        for doc in documents_list
    ]
