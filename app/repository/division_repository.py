from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models import division_model
from app.schemas import division_schema
from app.repository.base_repository import BaseRepository
from typing import Optional, List

class DivisionRepository(BaseRepository[division_model.Division]):
    def __init__(self):
        super().__init__(division_model.Division)

    async def create_division(self, db: AsyncSession, division: division_schema.DivisionCreate) -> division_model.Division:
        return await self.create(db, division)

    async def get_division(self, db: AsyncSession, division_id: int) -> Optional[division_model.Division]:
        return await self.get(db, division_id)

    async def get_divisions_by_company(self, db: AsyncSession, company_id: int, skip: int = 0, limit: int = 100) -> List[division_model.Division]:
        result = await db.execute(
            select(self.model)
            .filter(self.model.company_id == company_id)
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()

division_repository = DivisionRepository()