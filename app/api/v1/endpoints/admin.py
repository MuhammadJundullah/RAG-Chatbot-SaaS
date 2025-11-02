from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.core.dependencies import get_current_super_admin, get_db
from app.schemas import company_schema
from app.services import admin_service

router = APIRouter(
    prefix="/admin",
    tags=["Super Admin"],
    dependencies=[Depends(get_current_super_admin)],
)

# get all active companyes
@router.get("/companies", response_model=List[company_schema.Company])
async def read_companies(
    skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db),
):
    companies = await admin_service.get_all_active_companies_service(db, skip=skip, limit=limit)
    return companies

# get pending company
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
    companies = await admin_service.get_pending_companies_service(db, skip=skip, limit=limit)
    return companies

@router.patch("/companies/{company_id}/approve")
async def approve_company(
    company_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Approve a company registration.
    Accessible only by super admins.
    """
    return await admin_service.approve_company_service(db, company_id=company_id)

@router.patch("/companies/{company_id}/reject")

async def reject_company(

    company_id: int,

    db: AsyncSession = Depends(get_db)

):

    """

    Reject a company registration.

    Accessible only by super admins.

    """

    return await admin_service.reject_company_service(db, company_id=company_id)