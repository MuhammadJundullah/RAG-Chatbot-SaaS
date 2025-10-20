from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.repository import company_repository, user_repository
from app.core.dependencies import get_current_super_admin, get_db
from app.schemas import company_schema

router = APIRouter(
    prefix="/admin",
    tags=["Super Admin"],
    dependencies=[Depends(get_current_super_admin)],
)


@router.get("/companies/pending", response_model=List[company_schema.Company])
async def get_pending_companies(
    db: AsyncSession = Depends(get_db),
    skip: int = 0,
    limit: int = 100
):
    """
    Get a list of companies awaiting approval.
    Accessible only by super admins.
    """
    companies = await user_repository.get_pending_companies(db, skip=skip, limit=limit)
    return companies


@router.patch("/companies/{company_id}/approve", response_model=company_schema.Company)
async def approve_company(
    company_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Approve a company registration.
    Accessible only by super admins.
    """
    approved_company = await company_repository.approve_company(db, company_id=company_id)
    if not approved_company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Company with id {company_id} not found."
        )
    return approved_company