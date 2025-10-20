from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from pydantic import BaseModel

from app.repository import division_repository
from app.core.dependencies import get_current_company_admin, get_current_user, get_db
from app.schemas import division_schema
from app.models.user_model import Users

router = APIRouter(
    prefix="/divisions",
    tags=["Divisions"],
)

class DivisionCreateRequest(BaseModel):
    name: str

@router.post("/", response_model=division_schema.Division)
async def create_division(
    division_request: DivisionCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: Users = Depends(get_current_company_admin)
):
    """Create a new division within the admin's company."""
    # Create the full DivisionCreate schema including the company_id from the logged-in admin
    division_data = division_schema.DivisionCreate(
        name=division_request.name,
        company_id=current_user.company_id
    )
    
    return await division_repository.create_division(db=db, division=division_data)

@router.get("/", response_model=List[division_schema.Division])
async def read_divisions(
    db: AsyncSession = Depends(get_db),
    current_user: Users = Depends(get_current_user)
):
    divisions = await division_repository.get_divisions_by_company(db, company_id=current_user.company_id)
    return divisions

@router.get("/public/{company_id}", response_model=List[division_schema.Division])
async def read_public_divisions(
    company_id: int,
    db: AsyncSession = Depends(get_db)
):
    divisions = await division_repository.get_divisions_by_company(db, company_id=company_id)
    if not divisions:
        raise HTTPException(status_code=404, detail="No divisions found for this company.")
    return divisions