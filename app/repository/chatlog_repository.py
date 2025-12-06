from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import Optional, List
from datetime import date
from sqlalchemy import func, or_, cast, String
from app.models import chatlog_model
from app.schemas import chatlog_schema
from app.repository.base_repository import BaseRepository
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
        search: Optional[str] = None,
    ) -> (List[dict], int):
        from app.models.user_model import Users

        base_query = select(self.model).join(Users, self.model.UsersId == Users.id).filter(self.model.company_id == company_id)

        if user_id:
            base_query = base_query.filter(self.model.UsersId == user_id)

        if division_id:
            base_query = base_query.filter(Users.division_id == division_id)

        if start_date:
            base_query = base_query.filter(self.model.created_at >= start_date)
        if end_date:
            base_query = base_query.filter(self.model.created_at <= end_date)

        if search and search.strip():
            pattern = f"%{search.strip()}%"
            base_query = base_query.filter(
                or_(
                    self.model.question.ilike(pattern),
                    self.model.answer.ilike(pattern),
                    Users.username.ilike(pattern),
                    cast(self.model.conversation_id, String).ilike(pattern),
                )
            )

        count_query = base_query.with_only_columns(func.count(self.model.id))
        total_count_result = await db.execute(count_query)
        total_count = total_count_result.scalar_one()

        data_query = base_query.with_only_columns(
            self.model.id,
            self.model.question,
            self.model.answer,
            self.model.created_at,
            self.model.conversation_id,
            self.model.UsersId,
            self.model.company_id,
            Users.username
        ).order_by(self.model.created_at.desc()).offset(skip)

        if limit >= 0:
            data_query = data_query.limit(limit)
        
        result = await db.execute(data_query)
        data = [
            {
                "id": i,
                "question": q,
                "answer": a,
                "created_at": ca,
                "conversation_id": conv_id,
                "UsersId": user_id,
                "company_id": comp_id,
                "username": u,
            }
            for i, q, a, ca, conv_id, user_id, comp_id, u in result.all()
        ]
        
        return data, total_count

    async def get_unique_conversation_ids_for_user(
        self, db: AsyncSession,
        user_id: int,
        skip: int = 0,
        limit: int = 100,
    ) -> List[tuple[str, str, bool]]: # Changed return type hint
        from app.models.conversation_model import Conversation # Import Conversation model

        # Subquery to find the latest created_at for each conversation_id
        # We also select the conversation_id from the Chatlogs model
        latest_chat_per_conversation = select(
            self.model.conversation_id,
            self.model.created_at.label("latest_created_at")
        ).filter(
            self.model.UsersId == user_id
        ).order_by(
            self.model.conversation_id,
            self.model.created_at.desc()
        ).distinct(self.model.conversation_id).subquery()

        # Main query to select distinct conversation_id and its title, ordered by their latest message
        # Join Chatlogs with Conversation
        query = select(
            latest_chat_per_conversation.c.conversation_id,
            Conversation.title,
            Conversation.is_archived
        ).join(
            Conversation,
            latest_chat_per_conversation.c.conversation_id == Conversation.id
        ).order_by(
            latest_chat_per_conversation.c.latest_created_at.desc()
        )
        result = await db.execute(query.offset(skip).limit(limit))
        return result.all() # Changed from scalars().all() to all()

    async def delete_chatlogs_by_conversation_id(self, db: AsyncSession, conversation_id: str, user_id: int) -> int:
        """Deletes all chatlog entries for a specific conversation ID and user ID."""
        stmt = delete(self.model).filter(
            self.model.conversation_id == conversation_id,
            self.model.UsersId == user_id
        )
        result = await db.execute(stmt)
        await db.commit()
        return result.rowcount

    async def get_chatlogs_by_conversation_id(
        self, db: AsyncSession,
        conversation_id: str,
    ) -> List[chatlog_model.Chatlogs]:
        query = select(self.model).filter(
            self.model.conversation_id == conversation_id
        ).order_by(self.model.created_at)
        result = await db.execute(query)
        return result.scalars().all()

    async def get_total_chat_count(self, db: AsyncSession, company_id: int, start_date: Optional[date] = None, end_date: Optional[date] = None) -> int:
        """Gets the total number of chatlogs for a company, with optional date filtering."""
        query = select(func.count(self.model.id)).filter(self.model.company_id == company_id)
        if start_date:
            query = query.filter(self.model.created_at >= start_date)
        if end_date:
            query = query.filter(self.model.created_at <= end_date)
        result = await db.execute(query)
        return result.scalar_one_or_none() or 0

    async def get_daily_chat_activity(self, db: AsyncSession, company_id: int, start_date: Optional[date] = None, end_date: Optional[date] = None) -> List[tuple[date, int]]:
        """Gets the daily chat count for a company, with optional date filtering."""
        query = select(
            func.date(self.model.created_at).label("chat_date"),
            func.count(self.model.id).label("chat_count")
        ).filter(
            self.model.company_id == company_id
        )
        if start_date:
            query = query.filter(func.date(self.model.created_at) >= start_date)
        if end_date:
            query = query.filter(func.date(self.model.created_at) <= end_date)
        
        query = query.group_by("chat_date").order_by("chat_date")
        
        result = await db.execute(query)
        return result.all()

chatlog_repository = ChatlogRepository()
