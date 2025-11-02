from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from pydantic import BaseModel

from app.core.dependencies import get_current_company_admin, get_current_user, get_db
from app.schemas import division_schema
from app.models.user_model import Users
from app.services import division_service

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
    return await division_service.create_division_service(
        db=db,
        division_name=division_request.name,
        current_user=current_user
    )

@router.get("/", response_model=List[division_schema.Division])
async def read_divisions(
    db: AsyncSession = Depends(get_db),
    current_user: Users = Depends(get_current_user)
):
    divisions = await division_service.read_divisions_service(
        db=db,
        current_user=current_user
    )
    return divisions

@router.get("/public/{company_id}", response_model=List[division_schema.Division])
async def read_public_divisions(
    company_id: int,
    db: AsyncSession = Depends(get_db)
):
    divisions = await division_service.read_public_divisions_service(
        db=db,
        company_id=company_id
    )
    return divisions