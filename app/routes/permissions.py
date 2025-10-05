from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app import crud
from app.database import schema
from app.database.connection import db_manager
from app.models import schemas
from app.utils.auth import get_current_company_admin

router = APIRouter()

async def get_division_for_admin(division_id: int, current_user: schema.User = Depends(get_current_company_admin), db: AsyncSession = Depends(db_manager.get_db_session)) -> schema.Division:
    """Dependency to get a division and verify it belongs to the admin's company."""
    division = await crud.get_division_by_id(db, division_id=division_id)
    if not division or division.company_id != current_user.company_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Division with id {division_id} not found in your company."
        )
    return division

@router.post("/divisions/{division_id}/permissions", response_model=schemas.Permission, tags=["Permissions"])
async def create_permission_for_division(
    permission_data: schemas.PermissionCreate,
    division: schema.Division = Depends(get_division_for_admin),
    db: AsyncSession = Depends(db_manager.get_db_session)
):
    """
    Adds a new data access permission to a specific division.
    Requires COMPANY_ADMIN authentication.
    """
    new_permission = await crud.add_permission_for_division(
        db=db, 
        permission=permission_data, 
        division_id=division.id
    )
    return new_permission

@router.get("/divisions/{division_id}/permissions", response_model=List[schemas.Permission], tags=["Permissions"])
async def get_permissions_for_division(
    division: schema.Division = Depends(get_division_for_admin),
    db: AsyncSession = Depends(db_manager.get_db_session)
):
    """
    Gets all data access permissions for a specific division.
    Requires COMPANY_ADMIN authentication.
    """
    permissions = await crud.get_permissions_for_division(db=db, division_id=division.id)
    return permissions
