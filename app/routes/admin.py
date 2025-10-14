from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app import crud
from app.database.connection import db_manager
from app.models import schemas
from app.utils.auth import get_current_super_admin

router = APIRouter(
    prefix="/admin",
    tags=["Super Admin"],
    dependencies=[Depends(get_current_super_admin)],
)


@router.get("/companies/pending", response_model=List[schemas.Company])
async def get_pending_companies(
    db: AsyncSession = Depends(db_manager.get_db_session),
    skip: int = 0,
    limit: int = 100
):
    """
    Get a list of companies awaiting approval.
    Accessible only by super admins.
    """
    companies = await crud.get_pending_companies(db, skip=skip, limit=limit)
    return companies


@router.post("/companies/{company_id}/approve", response_model=schemas.Company)
async def approve_company(
    company_id: int,
    db: AsyncSession = Depends(db_manager.get_db_session)
):
    """
    Approve a company registration.
    Accessible only by super admins.
    """
    approved_company = await crud.approve_company(db, company_id=company_id)
    if not approved_company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Company with id {company_id} not found."
        )
    return approved_company
