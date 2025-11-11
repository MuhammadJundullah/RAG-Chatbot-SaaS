from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func
from typing import List, Tuple
from sqlalchemy.orm import joinedload

from app.models import log_model
from app.repository.base_repository import BaseRepository

class LogRepository(BaseRepository[log_model.ActivityLog]):
    def __init__(self):
        super().__init__(log_model.ActivityLog)

    async def get_activity_logs(self, db: AsyncSession, skip: int, limit: int) -> Tuple[List[log_model.ActivityLog], int]:
        """Gets all activity logs with pagination."""
        result = await db.execute(
            select(self.model)
            .options(joinedload(self.model.user), joinedload(self.model.company))
            .order_by(self.model.id.desc())
            .offset(skip)
            .limit(limit)
        )
        logs = result.scalars().all()
        
        total_result = await db.execute(select(func.count(self.model.id)))
        total_count = total_result.scalar_one()
        
        return logs, total_count

log_repository = LogRepository()
