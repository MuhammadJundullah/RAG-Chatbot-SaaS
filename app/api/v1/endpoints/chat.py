from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sse_starlette.sse import EventSourceResponse
import json
import uuid

from app.schemas import chat_schema, chatlog_schema
from app.services.rag_service import rag_service
from app.services.gemini_service import gemini_service
from app.core.dependencies import get_current_user, get_db
from app.models.user_model import Users
from app.repository import chatlog_repository

router = APIRouter()

@router.post("/chat", tags=["Chat"])
async def chat_endpoint(
    request: chat_schema.ChatRequest,
    current_user: Users = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    async def event_generator():
        try:
            conversation_id = request.conversation_id or str(uuid.uuid4())
            user_message = request.message
            company_id = current_user.company_id

            # 1. Get context from RAG service
            rag_context = await rag_service.get_relevant_context(
                query=user_message,
                company_id=company_id
            )

            # 2. Generate chat response
            full_response = ""
            async for chunk in gemini_service.generate_chat_response(
                question=user_message,
                context=rag_context,
                query_results=None,
                db=db,
                current_user=current_user
            ):
                full_response += chunk
                yield {"event": "message", "data": chunk}

            # 3. Save chat to database
            chatlog_data = chatlog_schema.ChatlogCreate(
                question=user_message,
                answer=full_response,
                UsersId=current_user.id,
                company_id=company_id,
            )
            await chatlog_repository.create_chatlog(db=db, chatlog=chatlog_data)

            # 4. Send end event
            yield {
                "event": "end",
                "data": json.dumps({
                    "conversation_id": conversation_id
                })
            }

        except Exception as e:
            print(f"Unhandled error in chat endpoint: {e}")
            yield {"event": "error", "data": json.dumps({"detail": f"Chat error: {str(e)}", "status_code": 500})}

    return EventSourceResponse(event_generator())
