from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func, and_
from sqlalchemy.orm import joinedload
from datetime import datetime
from typing import Tuple, List, Optional 

from app.models import log_model
from app.repository.base_repository import BaseRepository
from urllib.parse import unquote

class LogRepository(BaseRepository[log_model.ActivityLog]):
    def __init__(self):
        super().__init__(log_model.ActivityLog)

    async def get_activity_logs(
        self,
        db: AsyncSession,
        skip: int,
        limit: int,
        company_id: Optional[int] = None,
        activity_type_category: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Tuple[List[log_model.ActivityLog], int]:
        """
        Gets activity logs with pagination and filtering.
        """

        stmt = select(self.model).options(
            joinedload(self.model.user), joinedload(self.model.company)
        ).order_by(self.model.id.desc())

        filters = []
        if company_id is not None:
            filters.append(self.model.company_id == company_id)
        if activity_type_category is not None:
            filters.append(self.model.activity_type_category == activity_type_category)
        
        parsed_start_date = None
        if start_date:
            try:
                parsed_start_date = datetime.strptime(start_date, '%Y-%m-%d')
                filters.append(self.model.timestamp >= parsed_start_date)
            except ValueError:
                pass 
        
        parsed_end_date = None
        if end_date:
            try:
                parsed_end_date = datetime.strptime(end_date, '%Y-%m-%d')
                filters.append(self.model.timestamp <= parsed_end_date)
            except ValueError:
                pass

        if filters:
            stmt = stmt.where(and_(*filters))

        stmt = stmt.offset(skip).limit(limit)

        result = await db.execute(stmt)
        logs = result.scalars().all()
        
        count_stmt = select(func.count(self.model.id))
        if filters:
            count_stmt = count_stmt.where(and_(*filters))

        total_result = await db.execute(count_stmt)
        total_count = total_result.scalar_one()
        
        return logs, total_count

log_repository = LogRepository()
