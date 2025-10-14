from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app import crud
from app.database.connection import db_manager
from app.models import schemas
from app.utils.auth import get_current_user
from app.database.schema import Users

router = APIRouter(
    prefix="/divisions",
    tags=["Divisions"],
)

@router.post("/", response_model=schemas.Division)
async def create_division(
    division: schemas.DivisionCreate,
    db: AsyncSession = Depends(db_manager.get_db_session),
    current_user: Users = Depends(get_current_user)
):
    if division.Companyid != current_user.Companyid:
        raise HTTPException(status_code=403, detail="You can only create divisions for your own company.")
    
    return await crud.create_division(db=db, division=division)

@router.get("/", response_model=List[schemas.Division])
async def read_divisions(
    db: AsyncSession = Depends(db_manager.get_db_session),
    current_user: Users = Depends(get_current_user)
):
    divisions = await crud.get_divisions_by_company(db, company_id=current_user.Companyid)
    return divisions

@router.get("/public/{company_id}", response_model=List[schemas.Division])
async def read_public_divisions(
    company_id: int,
    db: AsyncSession = Depends(db_manager.get_db_session)
):
    divisions = await crud.get_divisions_by_company(db, company_id=company_id)
    if not divisions:
        raise HTTPException(status_code=404, detail="No divisions found for this company.")
    return divisions
