from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app import crud
from app.database.connection import db_manager
from app.models import schemas
from app.database.schema import Users
from app.utils.auth import get_current_company_admin, get_current_user

router = APIRouter(
    prefix="/divisions",
    tags=["Divisions"],
)

class DivisionCreateRequest(schemas.BaseModel):
    name: str

@router.post("/", response_model=schemas.Division)
async def create_division(
    division_request: DivisionCreateRequest,
    db: AsyncSession = Depends(db_manager.get_db_session),
    current_user: Users = Depends(get_current_company_admin) # Only company admins can create divisions
):
    """Create a new division within the admin's company."""
    # Create the full DivisionCreate schema including the company_id from the logged-in admin
    division_data = schemas.DivisionCreate(
        name=division_request.name,
        company_id=current_user.company_id
    )
    
    return await crud.create_division(db=db, division=division_data)

@router.get("/", response_model=List[schemas.Division])
async def read_divisions(
    db: AsyncSession = Depends(db_manager.get_db_session),
    current_user: Users = Depends(get_current_user)
):
    divisions = await crud.get_divisions_by_company(db, company_id=current_user.company_id)
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
