from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import or_, exists, cast, String, func
from typing import Optional, List, Tuple, Any
from app.models.conversation_model import Conversation
from app.schemas.conversation_schema import ConversationCreate
from app.repository.base_repository import BaseRepository

class ConversationRepository(BaseRepository[Conversation]):
    def __init__(self):
        super().__init__(Conversation)

    async def create_conversation(self, db: AsyncSession, conversation: ConversationCreate) -> Conversation:
        return await self.create(db, conversation)

    # Add the get_conversation method
    async def get_conversation(self, db: AsyncSession, conversation_id: str) -> Optional[Conversation]:
        # Assuming BaseRepository has a 'get' method that takes db and id
        # If not, this would need to be implemented here using select statement.
        # For now, let's assume BaseRepository.get(db, id) exists.
        return await self.get(db, conversation_id)

    async def get_conversations_for_user(
        self, db: AsyncSession,
        user_id: int,
        skip: int = 0,
        limit: int = 100,
        search: Optional[str] = None,
    ) -> Tuple[List[Any], int]:
        # Fetch conversations associated with the user.
        # This assumes a relationship or a way to link conversations to users.
        # For now, let's assume we can fetch all conversations and filter by user_id if needed,
        # or that the conversation model has a user_id field.
        
        # Based on chatlog_model, UsersId is linked to Chatlogs.
        # To get conversations for a user, we might need to join Chatlogs and Conversation.
        
        # Let's try to fetch conversations directly, assuming a direct link or filtering capability.
        # If Conversation model has UsersId:
        # query = select(self.model).filter(self.model.UsersId == user_id)
        
        # If Conversation model does NOT have UsersId, we need to join with Chatlogs
        # to filter by user_id.
        from app.models.chatlog_model import Chatlogs
        
        # Subquery to get the latest chatlog's created_at for each conversation_id for the user
        latest_chat_subquery = select(
            Chatlogs.conversation_id,
            Chatlogs.created_at.label('latest_created_at')
        ).filter(
            Chatlogs.UsersId == user_id
        ).order_by(
            Chatlogs.conversation_id,
            Chatlogs.created_at.desc()
        ).distinct(Chatlogs.conversation_id).subquery()

        # Main query to join Conversation with the subquery and order by latest chat
        query = select(
            Conversation.id,
            Conversation.title,
            Conversation.created_at,
            Conversation.is_archived,
            latest_chat_subquery.c.latest_created_at
        ).join(
            latest_chat_subquery, Conversation.id == latest_chat_subquery.c.conversation_id
        ).order_by(
            latest_chat_subquery.c.latest_created_at.desc(),
            Conversation.id.desc(),
        )

        if search:
            like_term = f"%{search}%"
            matching_chatlog_exists = exists().where(
                Chatlogs.UsersId == user_id,
                Chatlogs.conversation_id == Conversation.id,
                or_(
                    Chatlogs.question.ilike(like_term),
                    Chatlogs.answer.ilike(like_term),
                    cast(Chatlogs.conversation_id, String).ilike(like_term),
                ),
            )
            query = query.where(
                or_(
                    Conversation.title.ilike(like_term),
                    cast(Conversation.id, String).ilike(like_term),
                    matching_chatlog_exists,
                )
            )

        count_query = select(func.count()).select_from(Conversation).join(
            latest_chat_subquery, Conversation.id == latest_chat_subquery.c.conversation_id
        )
        if search:
            count_query = count_query.where(
                or_(
                    Conversation.title.ilike(like_term),
                    cast(Conversation.id, String).ilike(like_term),
                    matching_chatlog_exists,
                )
            )

        total_conversations = await db.scalar(count_query)
        result = await db.execute(query.offset(skip).limit(limit))
        
        rows = result.all()
        return rows, total_conversations or 0

    async def update_title(self, db: AsyncSession, conversation_id: str, title: str) -> Optional[Conversation]:
        conversation = await self.get(db, conversation_id)
        if conversation:
            conversation.title = title
            await db.commit()
            await db.refresh(conversation)
        return conversation

    async def archive_conversation(self, db: AsyncSession, conversation_id: str) -> Optional[Conversation]:
        conversation = await self.get(db, conversation_id)
        if conversation:
            conversation.is_archived = True
            await db.commit()
            await db.refresh(conversation)
        return conversation

    async def set_archive_status(self, db: AsyncSession, conversation_id: str, is_archived: bool) -> Optional[Conversation]:
        conversation = await self.get(db, conversation_id)
        if conversation:
            conversation.is_archived = is_archived
            await db.commit()
            await db.refresh(conversation)
        return conversation

conversation_repository = ConversationRepository()
