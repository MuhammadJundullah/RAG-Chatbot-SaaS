from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models import division_model
from app.schemas import division_schema

async def create_division(db: AsyncSession, division: division_schema.DivisionCreate):
    db_division = division_model.Division(**division.model_dump())
    db.add(db_division)
    await db.commit()
    await db.refresh(db_division)
    return db_division

async def get_division(db: AsyncSession, division_id: int):
    result = await db.execute(select(division_model.Division).filter(division_model.Division.id == division_id))
    return result.scalar_one_or_none()

async def get_divisions_by_company(db: AsyncSession, company_id: int, skip: int = 0, limit: int = 100):
    result = await db.execute(
        select(division_model.Division)
        .filter(division_model.Division.company_id == company_id)
        .offset(skip)
        .limit(limit)
    )
    return result.scalars().all()
