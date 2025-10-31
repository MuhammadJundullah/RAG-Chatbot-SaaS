from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import Optional, List
from datetime import date
from app.models import chatlog_model
from app.schemas import chatlog_schema
from app.repository.base_repository import BaseRepository, ModelType, CreateSchemaType, UpdateSchemaType
from sqlalchemy import delete

class ChatlogRepository(BaseRepository[chatlog_model.Chatlogs]):
    def __init__(self):
        super().__init__(chatlog_model.Chatlogs)

    async def create_chatlog(self, db: AsyncSession, chatlog: chatlog_schema.ChatlogCreate) -> chatlog_model.Chatlogs:
        return await self.create(db, chatlog)

    async def get_chatlogs(
        self, db: AsyncSession,
        company_id: Optional[int] = None,
        user_id: Optional[int] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[chatlog_model.Chatlogs]:
        query = select(self.model)
        if company_id:
            query = query.filter(self.model.company_id == company_id)
        if user_id:
            query = query.filter(self.model.UsersId == user_id)
        if start_date:
            query = query.filter(self.model.created_at >= start_date)
        if end_date:
            query = query.filter(self.model.created_at <= end_date)
        
        result = await db.execute(query.offset(skip).limit(limit))
        return result.scalars().all()

    async def get_chat_history(
        self, db: AsyncSession,
        conversation_id: str,
        user_id: int,
        skip: int = 0,
        limit: int = 100,
    ) -> List[chatlog_model.Chatlogs]:
        query = select(self.model).filter(
            self.model.conversation_id == conversation_id,
            self.model.UsersId == user_id
        ).order_by(self.model.created_at)
        result = await db.execute(query.offset(skip).limit(limit))
        return result.scalars().all()

    async def get_all_chatlogs_for_admin(
        self, db: AsyncSession,
        company_id: Optional[int] = None,
        division_id: Optional[int] = None,
        user_id: Optional[int] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[chatlog_model.Chatlogs]:
        from app.models.user_model import Users

        query = select(self.model)

        if company_id:
            query = query.filter(self.model.company_id == company_id)
        if user_id:
            query = query.filter(self.model.UsersId == user_id)
        
        if division_id:
            query = query.join(Users, self.model.UsersId == Users.id).filter(Users.division_id == division_id)

        if start_date:
            query = query.filter(self.model.created_at >= start_date)
        if end_date:
            query = query.filter(self.model.created_at <= end_date)
        
        result = await db.execute(query.offset(skip).limit(limit))
        return result.scalars().all()

    async def get_chatlogs_for_company_admin(
        self, db: AsyncSession,
        company_id: int,
        division_id: Optional[int] = None,
        user_id: Optional[int] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[chatlog_model.Chatlogs]:
        from app.models.user_model import Users

        query = select(self.model).filter(self.model.company_id == company_id)

        if user_id:
            query = query.filter(self.model.UsersId == user_id)

        if division_id:
            query = query.join(Users, self.model.UsersId == Users.id).filter(Users.division_id == division_id)

        if start_date:
            query = query.filter(self.model.created_at >= start_date)
        if end_date:
            query = query.filter(self.model.created_at <= end_date)
        
        result = await db.execute(query.offset(skip).limit(limit))
        return result.scalars().all()

    async def get_unique_conversation_ids_for_user(
        self, db: AsyncSession,
        user_id: int,
        skip: int = 0,
        limit: int = 100,
    ) -> List[str]:
        from sqlalchemy import distinct
        # Subquery to find the latest created_at for each conversation_id
        latest_chat_per_conversation = select(
            self.model.conversation_id,
            self.model.created_at
        ).filter(
            self.model.UsersId == user_id
        ).distinct(self.model.conversation_id).order_by(
            self.model.conversation_id,
            self.model.created_at.desc()
        ).subquery()

        # Main query to select distinct conversation_id ordered by their latest message
        query = select(latest_chat_per_conversation.c.conversation_id).order_by(
            latest_chat_per_conversation.c.created_at.desc()
        )
        result = await db.execute(query.offset(skip).limit(limit))
        return result.scalars().all()

    async def delete_chatlogs_by_conversation_id(self, db: AsyncSession, conversation_id: str, user_id: int) -> int:
        """Deletes all chatlog entries for a specific conversation ID and user ID."""
        stmt = delete(self.model).filter(
            self.model.conversation_id == conversation_id,
            self.model.UsersId == user_id
        )
        result = await db.execute(stmt)
        await db.commit()
        return result.rowcount

chatlog_repository = ChatlogRepository()