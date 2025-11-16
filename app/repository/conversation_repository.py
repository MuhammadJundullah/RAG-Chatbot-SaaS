from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import Optional, List
from app.models.conversation_model import Conversation
from app.schemas.conversation_schema import ConversationCreate, ConversationListResponse
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
    ) -> List[ConversationListResponse]:
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
            Chatlogs.created_at.desc().label('latest_created_at')
        ).filter(
            Chatlogs.UsersId == user_id
        ).distinct(Chatlogs.conversation_id).subquery()

        # Main query to join Conversation with the subquery and order by latest chat
        query = select(
            Conversation.id,
            Conversation.title,
            Conversation.created_at,
            latest_chat_subquery.c.latest_created_at
        ).join(
            latest_chat_subquery, Conversation.id == latest_chat_subquery.c.conversation_id
        ).order_by(
            latest_chat_subquery.c.latest_created_at.desc()
        )

        result = await db.execute(query.offset(skip).limit(limit))
        
        # Convert results to ConversationListResponse schema
        conversations = [
            ConversationListResponse(
                id=str(row.id), # Convert UUID to string
                title=row.title,
                created_at=row.created_at,
                # latest_message_at=row.latest_created_at # Optional: include latest message time
            ) for row in result.all()
        ]
        return conversations

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

conversation_repository = ConversationRepository()