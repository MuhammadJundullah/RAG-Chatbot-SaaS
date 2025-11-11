from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from math import ceil

from app.core.dependencies import get_current_super_admin, get_db
from app.schemas import company_schema, log_schema
from app.services import admin_service
from app.models.user_model import Users

router = APIRouter(
    prefix="/admin",
    tags=["Super Admin"],
    dependencies=[Depends(get_current_super_admin)],
)

from typing import List, Optional

# get all companies with optional status filter
@router.get("/companies", response_model=List[company_schema.Company])
async def read_companies(
    skip: int = 0, 
    limit: int = 100, 
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    companies = await admin_service.get_companies_service(db, skip=skip, limit=limit, status=status)
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

@router.get("/activity-logs", response_model=log_schema.PaginatedActivityLogResponse)
async def get_activity_logs(
    page: int = 1,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user: Users = Depends(get_current_super_admin)
):
    """
    Gets all activity logs.
    Supports pagination via 'page' (page number) and 'limit' (number of items per page) query parameters.
    Returns a list of logs and pagination details.
    Example: /api/admin/activity-logs/?page=1&limit=20
    """
    skip_calculated = (page - 1) * limit

    logs, total_count = await admin_service.get_activity_logs_service(
        db=db,
        skip=skip_calculated,
        limit=limit
    )

    total_pages = ceil(total_count / limit) if limit > 0 else 0

    return log_schema.PaginatedActivityLogResponse(
        logs=logs,
        total_pages=total_pages,
        current_page=page,
        total_logs=total_count
    )
