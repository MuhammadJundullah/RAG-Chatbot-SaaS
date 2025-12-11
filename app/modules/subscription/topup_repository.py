# app/modules/subscription/topup_repository.py
from typing import List, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models import TopUpPackage


class TopUpPackageRepository:
    async def list_active(self, db: AsyncSession) -> List[TopUpPackage]:
        stmt = select(TopUpPackage).where(TopUpPackage.is_active.is_(True)).order_by(TopUpPackage.questions.asc())
        result = await db.execute(stmt)
        return result.scalars().all()

    async def list_all(self, db: AsyncSession) -> List[TopUpPackage]:
        stmt = select(TopUpPackage).order_by(TopUpPackage.questions.asc())
        result = await db.execute(stmt)
        return result.scalars().all()

    async def get_by_type(self, db: AsyncSession, package_type: str) -> TopUpPackage | None:
        stmt = select(TopUpPackage).where(TopUpPackage.package_type == package_type)
        result = await db.execute(stmt)
        return result.scalars().first()

    async def update_by_type(
        self,
        db: AsyncSession,
        package_type: str,
        *,
        price: Optional[int] = None,
        questions: Optional[int] = None,
        is_active: Optional[bool] = None,
    ) -> TopUpPackage:
        package = await self.get_by_type(db, package_type)
        if not package:
            return None

        if price is not None:
            package.price = price
        if questions is not None:
            package.questions = questions
        if is_active is not None:
            package.is_active = is_active

        await db.commit()
        await db.refresh(package)
        return package


topup_package_repository = TopUpPackageRepository()
