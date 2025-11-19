from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import date
from typing import Optional

from app.core.dependencies import get_db, get_current_company_admin
from app.models.user_model import Users
from app.schemas import dashboard_schema
from app.services import dashboard_service

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
    """
    Provides a summary of company data for the dashboard, including:
    - Document counts by status
    - Daily chat activity (can be filtered by date)
    - Total chat count (can be filtered by date)
    - Recently updated documents
    
    The response is wrapped in a 'dashboard_breakdown' object.
    """
    if not current_user.company_id:
        # This case should ideally not be hit due to the dependency, but as a safeguard:
        raise HTTPException(status_code=404, detail="Admin user is not associated with a company.")

    summary_data = await dashboard_service.get_dashboard_summary(
        db=db, 
        company_id=current_user.company_id,
    )
    
    return {"dashboard_breakdown": summary_data}
