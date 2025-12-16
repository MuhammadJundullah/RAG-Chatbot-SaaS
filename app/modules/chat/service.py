from typing import List, Optional
import uuid
import time
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from app.schemas import chat_schema, chatlog_schema
from app.schemas.conversation_schema import ConversationCreate, ConversationListResponse
from app.models.user_model import Users
from app.repository.conversation_repository import conversation_repository
from app.repository.chatlog_repository import chatlog_repository
from app.modules.documents.rag_service import rag_service
from app.modules.chat.together_service import together_service


class ChatService:
    """
    Thin service wrapper to encapsulate chat flows using injected dependencies.
    This keeps API handlers lean and makes the flow easier to test.
    """

    def __init__(
        self,
        rag_client=rag_service,
        llm_client=together_service,
        conversation_repo=conversation_repository,
        chatlog_repo=chatlog_repository,
    ):
        self.rag_client = rag_client
        self.llm_client = llm_client
        self.conversation_repo = conversation_repo
        self.chatlog_repo = chatlog_repo

    async def generate_conversation_title(self, user_message: str, conversation_history: list) -> str:
        if user_message:
            title = user_message[:50] + "..." if len(user_message) > 50 else user_message
            return f"{title}"
        if conversation_history:
            return "Conversation History"
        return "New Conversation"

    async def _ensure_conversation_exists(
        self,
        db: AsyncSession,
        conversation_id: Optional[str],
        user_message: str,
        company_id: int,
    ) -> str:
        """
        Validate or create conversation; returns conversation_id string.
        """
        if not conversation_id:
            new_uuid = str(uuid.uuid4())
            conversation_title = await self.generate_conversation_title(user_message=user_message, conversation_history=[])
            conversation_create_schema = ConversationCreate(
                id=new_uuid,
                title=conversation_title,
                company_id=company_id,
            )
            await self.conversation_repo.create_conversation(db=db, conversation=conversation_create_schema)
            return new_uuid

        try:
            valid_conversation_id = uuid.UUID(conversation_id)
            conversation_id_str = str(valid_conversation_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid conversation ID format. Please provide a valid UUID.",
            )

        existing_conversation = await self.conversation_repo.get_conversation(db=db, conversation_id=conversation_id_str)
        if not existing_conversation:
            conversation_title = await self.generate_conversation_title(user_message=user_message, conversation_history=[])
            conversation_create_schema = ConversationCreate(
                id=conversation_id_str,
                title=conversation_title,
                company_id=company_id,
            )
            await self.conversation_repo.create_conversation(db=db, conversation=conversation_create_schema)

        return conversation_id_str

    async def _get_history(self, db: AsyncSession, conversation_id: str, user_id: int) -> list[dict]:
        history_records = await self.chatlog_repo.get_chat_history(
            db=db,
            conversation_id=conversation_id,
            user_id=user_id,
        )
        return [{"question": record.question, "answer": record.answer} for record in history_records]

    async def process_chat_message(
        self,
        db: AsyncSession,
        current_user: Users,
        request: chat_schema.ChatRequest,
        chatlog_extra: Optional[dict] = None,
    ):
        END_MARKERS = ["[ENDFINALRESPONSE]", "[END FINAL RESPONSE]", "<|end|>", "</s>"]

        def strip_end_markers(text: str) -> str:
            for marker in END_MARKERS:
                text = text.replace(marker, "")
            return text

        conversation_id_str = await self._ensure_conversation_exists(
            db=db,
            conversation_id=request.conversation_id,
            user_message=request.message,
            company_id=current_user.company_id,
        )

        conversation_history = await self._get_history(
            db=db,
            conversation_id=conversation_id_str,
            user_id=current_user.id,
        )

        start_time = time.monotonic()
        rag_response = await self.rag_client.get_relevant_context(
            query=request.message,
            company_id=current_user.company_id,
        )
        rag_context = rag_response["context"]
        document_ids = rag_response["document_ids"]
        match_score = rag_response.get("match_score")

        full_response = ""
        async for chunk in self.llm_client.generate_chat_response(
            question=request.message,
            context=rag_context,
            db=db,
            current_user=current_user,
            conversation_history=conversation_history,
            model_name=request.model,
        ):
            cleaned_chunk = strip_end_markers(chunk)
            if not cleaned_chunk:
                continue
            full_response += cleaned_chunk

        full_response = strip_end_markers(full_response).strip()

        extra = chatlog_extra or {}
        input_type = extra.pop("input_type", "text")
        chatlog_data = chatlog_schema.ChatlogCreate(
            question=request.message,
            answer=full_response,
            UsersId=current_user.id,
            company_id=current_user.company_id,
            conversation_id=conversation_id_str,
            referenced_document_ids=document_ids,
            match_score=match_score,
            response_time_ms=int((time.monotonic() - start_time) * 1000),
            input_type=input_type,
            **extra,
        )
        created_chatlog = await self.chatlog_repo.create_chatlog(db=db, chatlog=chatlog_data)

        return {
            "response": full_response,
            "conversation_id": conversation_id_str,
            "chatlog_id": created_chatlog.id if created_chatlog else None,
        }

    async def get_conversations_with_titles(
        self,
        db: AsyncSession,
        current_user: Users,
        skip: int = 0,
        limit: int = 100,
    ) -> List[ConversationListResponse]:
        return await self.conversation_repo.get_conversations_for_user(
            db=db,
            user_id=current_user.id,
            skip=skip,
            limit=limit,
        )

    async def set_archive_status(
        self,
        db: AsyncSession,
        conversation_id: str,
        is_archived: bool,
        current_user: Users,
    ):
        conversation = await self.conversation_repo.get_conversation(db=db, conversation_id=conversation_id)
        if not conversation:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")

        user_chatlogs = await self.chatlog_repo.get_chat_history(
            db=db,
            conversation_id=conversation_id,
            user_id=current_user.id,
            limit=1,
        )
        if not user_chatlogs:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not have permission to change this conversation")

        updated_conversation = await self.conversation_repo.set_archive_status(db=db, conversation_id=conversation_id, is_archived=is_archived)
        return updated_conversation

    async def archive_chat(
        self,
        db: AsyncSession,
        conversation_id: str,
        current_user: Users,
    ):
        return await self.set_archive_status(
            db=db,
            conversation_id=conversation_id,
            is_archived=True,
            current_user=current_user,
        )

    async def edit_chat_title(
        self,
        db: AsyncSession,
        conversation_id: str,
        new_title: str,
        current_user: Users,
    ):
        conversation = await self.conversation_repo.get_conversation(db=db, conversation_id=conversation_id)
        if not conversation:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")

        user_chatlogs = await self.chatlog_repo.get_chat_history(
            db=db,
            conversation_id=conversation_id,
            user_id=current_user.id,
            limit=1,
        )
        if not user_chatlogs:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not have permission to edit this conversation")

        updated_conversation = await self.conversation_repo.update_title(db=db, conversation_id=conversation_id, title=new_title)
        return updated_conversation


chat_service = ChatService()
