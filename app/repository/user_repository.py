from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import joinedload
from app.models import user_model
from app.repository.base_repository import BaseRepository
from typing import Optional, List

class UserRepository(BaseRepository[user_model.Users]):
    def __init__(self):
        super().__init__(user_model.Users)

    async def create_user(self, db: AsyncSession, user: user_model.Users) -> user_model.Users:
        # This method is kept for now as user_service.py directly passes user_model.Users object
        # rather than a schema. If user_service is updated to pass a schema, this can be replaced
        # by super().create(db, user_schema.UserCreate.model_validate(user))
        db.add(user)
        await db.commit()
        await db.refresh(user)
        return user

    async def get_user(self, db: AsyncSession, user_id: int) -> Optional[user_model.Users]:
        result = await db.execute(
            select(self.model)
            .options(joinedload(self.model.company))
            .filter(self.model.id == user_id)
        )
        return result.scalar_one_or_none()

    async def get_user_by_username(self, db: AsyncSession, username: str) -> Optional[user_model.Users]:
        result = await db.execute(
            select(self.model)
            .options(joinedload(self.model.company))
            .filter(self.model.username == username)
        )
        return result.scalar_one_or_none()

    async def get_users(self, db: AsyncSession, skip: int = 0, limit: int = 100) -> List[user_model.Users]:
        return await self.get_multi(db, skip=skip, limit=limit)

    async def update_user_status(self, db: AsyncSession, user: user_model.Users, status: str) -> user_model.Users:
        user.is_active = status 
        db.add(user)
        await db.commit()
        await db.refresh(user)
        return user

    async def delete_user(self, db: AsyncSession, user_id: int):
        user = await self.get_user(db, user_id)
        if user:
            await db.delete(user)
            await db.commit()

    async def get_admins_by_company(self, db: AsyncSession, company_id: int) -> List[user_model.Users]:
        result = await db.execute(
            select(self.model)
            .filter(
                self.model.company_id == company_id,
                self.model.role == "admin",
            )
        )
        return result.scalars().all()

    async def get_all_admins(self, db: AsyncSession) -> List[user_model.Users]:
        result = await db.execute(
            select(self.model).filter(self.model.role == "admin")
        )
        return result.scalars().all()

    async def get_first_admin_by_company(self, db: AsyncSession, company_id: int) -> Optional[user_model.Users]:
        result = await db.execute(
            select(self.model)
            .filter(
                self.model.company_id == company_id,
                self.model.role == "admin",
            )
            .limit(1)
        )
        return result.scalar_one_or_none()

user_repository = UserRepository()
