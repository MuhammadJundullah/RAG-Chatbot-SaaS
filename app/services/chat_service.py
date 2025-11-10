from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
import uuid

from app.schemas import chat_schema, chatlog_schema
from app.services.rag_service import rag_service
from app.services.gemini_service import gemini_service
from app.models.user_model import Users
from app.repository.chatlog_repository import chatlog_repository
from app.schemas.conversation_schema import ConversationCreate, ConversationListResponse # Import ConversationCreate and ListResponse schemas
from app.repository.conversation_repository import conversation_repository # Import conversation repository
from fastapi import HTTPException, status # Import HTTPException and status

# Placeholder for LLM-based title generation
async def generate_conversation_title(user_message: str, conversation_history: list) -> str:
    """
    Placeholder function to simulate LLM-based conversation title generation.
    In a real implementation, this would call an LLM service.
    """
    # Simple logic: use the first user message as a basis for the title, or a default.
    if user_message:
        # Truncate message for title if it's too long
        title = user_message[:50] + "..." if len(user_message) > 50 else user_message
        return f"{title}"
    elif conversation_history:
        # If no user message, try to infer from history (more complex LLM task)
        # For now, a default title if history exists but no new message.
        return "Conversation History"
    else:
        return "New Conversation"

async def process_chat_message(
    db: AsyncSession,
    current_user: Users,
    request: chat_schema.ChatRequest
):
    conversation_id_str = request.conversation_id
    user_message = request.message
    company_id = current_user.company_id

    # If no conversation_id is provided, create a new conversation
    if not conversation_id_str:
        new_uuid = str(uuid.uuid4())
        # Generate title using LLM placeholder
        conversation_title = await generate_conversation_title(user_message=user_message, conversation_history=[])
        
        # Create Conversation object using the schema
        conversation_create_schema = ConversationCreate(
            id=new_uuid,
            title=conversation_title,
        )
        
        # Save new conversation to the database
        await conversation_repository.create_conversation(db=db, conversation=conversation_create_schema)
        
        conversation_id_str = new_uuid

    # 1. Get chat history for context
    conversation_history = []
    if request.conversation_id: # Use the original request.conversation_id if provided
        # Validate the provided conversation_id
        try:
            valid_conversation_id = uuid.UUID(request.conversation_id)
            conversation_id_str = str(valid_conversation_id) # Ensure conversation_id_str is the validated UUID string
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid conversation ID format. Please provide a valid UUID."
            )
        
        # Check if the conversation exists. If not, create it.
        existing_conversation = await conversation_repository.get_conversation(db=db, conversation_id=conversation_id_str)
        if not existing_conversation:
            # Create a new conversation with the provided ID from the frontend
            # Generate title using LLM placeholder, considering user message and history
            # For simplicity, using user_message here. A real LLM would use history too.
            conversation_title = await generate_conversation_title(user_message=user_message, conversation_history=[])
            conversation_create_schema = ConversationCreate(
                id=conversation_id_str, # Use the ID provided by the frontend
                title=conversation_title
            )
            await conversation_repository.create_conversation(db=db, conversation=conversation_create_schema)
            # conversation_id_str is already set to the validated UUID from request.conversation_id

        # Fetch history for the conversation (either existing or newly created)
        history_records = await chatlog_repository.get_chat_history(
            db=db,
            conversation_id=conversation_id_str, # Use the validated and existing/newly created conversation_id
            user_id=current_user.id
        )
        conversation_history = [{"question": record.question, "answer": record.answer} for record in history_records]
    else: # If a new conversation was just created (no conversation_id in request), history is empty initially
        # Fetch history for the newly created conversation_id_str to ensure consistency
        history_records = await chatlog_repository.get_chat_history(
            db=db,
            conversation_id=conversation_id_str, # Use the newly created conversation_id
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
        conversation_id=conversation_id_str, # Use the conversation_id (either provided or newly created)
        referenced_document_ids=document_ids
    )
    await chatlog_repository.create_chatlog(db=db, chatlog=chatlog_data)

    return {"response": full_response, "conversation_id": conversation_id_str}

async def get_conversations_with_titles(
    db: AsyncSession,
    current_user: Users,
    skip: int = 0,
    limit: int = 100,
) -> List[ConversationListResponse]:
    """
    Fetches a list of conversations for the current user, including their titles.
    """
    # Use the repository to get conversations, filtering by user_id
    conversations = await conversation_repository.get_conversations_for_user(
        db=db,
        user_id=current_user.id,
        skip=skip,
        limit=limit,
    )
    return conversations
