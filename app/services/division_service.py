from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from fastapi import HTTPException

from app.repository.division_repository import division_repository
from app.schemas import division_schema
from app.models.user_model import Users

async def create_division_service(
    db: AsyncSession,
    division_name: str,
    current_user: Users
) -> division_schema.Division:
    division_data = division_schema.DivisionCreate(
        name=division_name,
        company_id=current_user.company_id
    )
    return await division_repository.create_division(db=db, division=division_data)

async def read_divisions_service(
    db: AsyncSession,
    current_user: Users
) -> List[division_schema.Division]:
    divisions = await division_repository.get_divisions_by_company(db, company_id=current_user.company_id)
    return divisions

async def read_public_divisions_service(
    db: AsyncSession,
    company_id: int
) -> List[division_schema.Division]:
    divisions = await division_repository.get_divisions_by_company(db, company_id=company_id)
    if not divisions:
        raise HTTPException(status_code=404, detail="No divisions found for this company.")
    return divisions