from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app import crud
from app.database import schema
from app.database.connection import db_manager
from app.models import schemas
from app.utils.auth import get_current_company_admin

router = APIRouter()

@router.post(
    "/divisions", 
    response_model=schemas.DivisionPublic, 
    status_code=status.HTTP_201_CREATED,
    tags=["Divisions"]
)
async def create_division(
    division_data: schemas.DivisionCreate,
    current_user: schema.User = Depends(get_current_company_admin),
    db: AsyncSession = Depends(db_manager.get_db_session)
):
    """
    Create a new division within the admin's company.
    Requires COMPANY_ADMIN authentication.
    """
    new_division = await crud.create_division(
        db=db, 
        division_data=division_data, 
        company_id=current_user.company_id
    )
    return new_division

@router.get(
    "/divisions", 
    response_model=List[schemas.DivisionPublic],
    tags=["Divisions"]
)
async def get_company_divisions(
    current_user: schema.User = Depends(get_current_company_admin),
    db: AsyncSession = Depends(db_manager.get_db_session)
):
    """
    Get a list of all divisions within the admin's company.
    Requires COMPANY_ADMIN authentication.
    """
    divisions = await crud.get_divisions_by_company(db=db, company_id=current_user.company_id)
    return divisions
