from sqlalchemy.ext.asyncio import AsyncSession
import uuid

from app.schemas import chat_schema, chatlog_schema
from app.services.rag_service import rag_service
from app.services.gemini_service import gemini_service
from app.models.user_model import Users
from app.repository.chatlog_repository import chatlog_repository

async def process_chat_message(
    db: AsyncSession,
    current_user: Users,
    request: chat_schema.ChatRequest
):
    conversation_id = request.conversation_id or str(uuid.uuid4())
    user_message = request.message
    company_id = current_user.company_id

    # 1. Get chat history for context
    conversation_history = []
    if request.conversation_id:
        history_records = await chatlog_repository.get_chat_history(
            db=db,
            conversation_id=request.conversation_id,
            user_id=current_user.id
        )
        conversation_history = [{"question": record.question, "answer": record.answer} for record in history_records]

    # 2. Get context from RAG service
    rag_context = await rag_service.get_relevant_context(
        query=user_message,
        company_id=company_id
    )

    # 3. Generate chat response
    full_response = ""
    async for chunk in gemini_service.generate_chat_response(
        question=user_message,
        context=rag_context,
        query_results=None,
        db=db,
        current_user=current_user,
        conversation_history=conversation_history
    ):
        full_response += chunk

    # 4. Save chat to database
    chatlog_data = chatlog_schema.ChatlogCreate(
        question=user_message,
        answer=full_response,
        UsersId=current_user.id,
        company_id=company_id,
        conversation_id=conversation_id
    )
    await chatlog_repository.create_chatlog(db=db, chatlog=chatlog_data)

    return {"response": full_response, "conversation_id": conversation_id}
