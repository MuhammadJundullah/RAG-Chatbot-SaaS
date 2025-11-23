from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import date
from typing import Optional

from app.core.dependencies import get_db, get_current_company_admin, get_current_super_admin
from app.models.user_model import Users
from app.schemas import dashboard_schema
from app.modules.dashboard import service as dashboard_service
from app.modules.dashboard.superadmin_service import superadmin_dashboard_service

router = APIRouter(
    prefix="/dashboard",
    tags=["Dashboard"],
)


@router.get(
    "/summary",
    response_model=dashboard_schema.DashboardBreakdownResponseSchema,
    summary="Get Dashboard Summary Data",
    description="Retrieves a comprehensive summary of data for the company's dashboard, wrapped in a dashboard_breakdown object.",
)
async def get_dashboard_summary(
    db: AsyncSession = Depends(get_db),
    current_user: Users = Depends(get_current_company_admin),
):
    if not current_user.company_id:
        raise HTTPException(status_code=404, detail="Admin user is not associated with a company.")

    summary_data = await dashboard_service.get_dashboard_summary(
        db=db,
        company_id=current_user.company_id,
    )

    return {"dashboard_breakdown": summary_data}


@router.get(
    "/admin/summary",
    response_model=dashboard_schema.SuperAdminDashboardResponse,
    summary="Super admin dashboard overview",
    dependencies=[Depends(get_current_super_admin)],
)
async def get_superadmin_overview(db: AsyncSession = Depends(get_db)):
    return await superadmin_dashboard_service.get_overview(db)
