from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app import crud
from app.database import schema
from app.database.connection import db_manager
from app.models import schemas
from app.utils.auth import get_current_company_admin

router = APIRouter()

# Dependency to get a division and verify it belongs to the admin's company
async def get_division_for_admin(division_id: int, current_user: schema.User = Depends(get_current_company_admin), db: AsyncSession = Depends(db_manager.get_db_session)) -> schema.Division:
    division = await crud.get_division_by_id(db, division_id=division_id)
    if not division or division.company_id != current_user.company_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Division with id {division_id} not found in your company."
        )
    return division

@router.post("/divisions", response_model=schemas.DivisionPublic, tags=["Divisions"], status_code=status.HTTP_201_CREATED)
async def create_division(
    division_data: schemas.DivisionCreate,
    current_user: schema.User = Depends(get_current_company_admin),
    db: AsyncSession = Depends(db_manager.get_db_session)
):
    """Create a new division within the admin's company."""
    new_division = await crud.create_division(
        db=db, 
        division_data=division_data, 
        company_id=current_user.company_id
    )
    return new_division

@router.get("/divisions", response_model=List[schemas.DivisionPublic], tags=["Divisions"])
async def get_company_divisions(
    current_user: schema.User = Depends(get_current_company_admin),
    db: AsyncSession = Depends(db_manager.get_db_session)
):
    """Get a list of all divisions within the admin's company."""
    divisions = await crud.get_divisions_by_company(db=db, company_id=current_user.company_id)
    return divisions

@router.get("/divisions/{division_id}", response_model=schemas.DivisionPublic, tags=["Divisions"])
async def get_single_division(
    division: schema.Division = Depends(get_division_for_admin)
):
    """Get details for a single division."""
    return division

@router.put("/divisions/{division_id}", response_model=schemas.DivisionPublic, tags=["Divisions"])
async def update_division(
    update_data: schemas.DivisionUpdate,
    division: schema.Division = Depends(get_division_for_admin),
    db: AsyncSession = Depends(db_manager.get_db_session)
):
    """Update a division's name."""
    return await crud.update_division(db=db, division=division, update_data=update_data)

@router.delete("/divisions/{division_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Divisions"])
async def delete_division(
    division: schema.Division = Depends(get_division_for_admin),
    db: AsyncSession = Depends(db_manager.get_db_session)
):
    """Delete a division."""
    await crud.delete_division(db=db, division=division)
    return