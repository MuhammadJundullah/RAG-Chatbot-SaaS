from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List

from app import crud
from app.database import schema
from app.database.connection import db_manager
from app.models import schemas
from app.utils.auth import get_current_user
from app.database.schema import Users

router = APIRouter(
    prefix="/companies",
    tags=["Companies"],
)


@router.get("/", response_model=List[schemas.Company])
async def read_companies(
    skip: int = 0, limit: int = 100, db: AsyncSession = Depends(db_manager.get_db_session)
):
    companies = await crud.get_companies(db, skip=skip, limit=limit)
    return companies


@router.get("/{company_id}", response_model=schemas.Company)
async def read_company(company_id: int, db: AsyncSession = Depends(db_manager.get_db_session)):
    db_company = await crud.get_company(db, company_id=company_id)
    if db_company is None:
        raise HTTPException(status_code=404, detail="Company not found")
    return db_company

@router.get("/{company_id}/users/", response_model=List[schemas.User])
async def read_company_users(
    company_id: int, 
    db: AsyncSession = Depends(db_manager.get_db_session),
    current_user: schema.Users = Depends(get_current_user)
):
    db_company = await crud.get_company(db, company_id=company_id)
    if db_company is None:
        raise HTTPException(status_code=404, detail="Company not found")
    
    result = await db.execute(
        select(schema.Users).filter(schema.Users.Companyid == company_id)
    )
    users = result.scalars().all()
    return users