from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, distinct
from typing import List, Optional
from math import ceil
import io
from starlette.responses import StreamingResponse

from app.core.dependencies import get_current_super_admin, get_db
from app.schemas import company_schema, log_schema, subscription_schema, plan_schema
from app.services import admin_service, subscription_service
from app.services.plan_service import plan_service
from app.models.user_model import Users
from app.models.log_model import ActivityLog
from app.models.subscription_model import Subscription
from app.models.plan_model import Plan as PlanModel
from sqlalchemy.orm import joinedload



router = APIRouter(
    prefix="/admin",
    tags=["Super Admin"],
    dependencies=[Depends(get_current_super_admin)],
)

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

# --- Subscription Management Endpoints for Superadmin ---

@router.get("/subscriptions", response_model=List[subscription_schema.Subscription])
async def get_all_subscriptions(db: AsyncSession = Depends(get_db)):
    """
    Get a list of all company subscriptions.
    """
    result = await db.execute(select(Subscription).options(joinedload(Subscription.plan)))
    subscriptions = result.scalars().all()
    return subscriptions

@router.post("/subscriptions/{subscription_id}/activate-manual", response_model=subscription_schema.Subscription)
async def manual_activate_subscription(
    subscription_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Manually activates a subscription. Use this for offline payments or special cases.
    """
    return await subscription_service.activate_subscription(db, subscription_id=subscription_id)

@router.post("/companies/{company_id}/add-topup", response_model=subscription_schema.Subscription)
async def add_topup_quota(
    company_id: str,
    topup_data: subscription_schema.SubscriptionTopUpRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Adds top-up question quota to a company's subscription.
    """
    sub = await subscription_service.get_subscription_by_company(db, company_id=company_id)
    sub.top_up_quota += topup_data.quota
    await db.commit()
    await db.refresh(sub)
    return sub

# --- Plan Management Endpoints for Superadmin ---

@router.post("/plans", response_model=plan_schema.Plan)
async def create_new_plan(
    plan_data: plan_schema.PlanCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new subscription plan.
    """
    return await plan_service.create_plan(db, plan_data)

@router.put("/plans/{plan_id}", response_model=plan_schema.Plan)
async def update_existing_plan(
    plan_id: int,
    plan_data: plan_schema.PlanUpdate,
    db: AsyncSession = Depends(get_db)
):
    """
    Update an existing subscription plan.
    """
    return await plan_service.update_plan(db, plan_id, plan_data)

@router.delete("/plans/{plan_id}", response_model=plan_schema.Plan)
async def deactivate_existing_plan(
    plan_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Deactivate a subscription plan (sets is_active to False).
    """
    return await plan_service.deactivate_plan(db, plan_id)

@router.get("/activity-logs", response_model=log_schema.PaginatedActivityLogResponse)
async def get_activity_logs(
    page: int = 1,
    limit: int = 100,
    company_id: Optional[str] = None,
    activity_type_category: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: Users = Depends(get_current_super_admin)
):
    """
    Gets all activity logs.
    Supports pagination via 'page' (page number) and 'limit' (number of items per page) query parameters.
    Supports filtering by 'company_id', 'activity_type_category', 'start_date', and 'end_date'.
    Returns a list of logs and pagination details.
    Example: /api/admin/activity-logs/?page=1&limit=20&company_id=1&activity_type_category=Data/CRUD&start_date=2023-01-01&end_date=2023-12-31
    """
    skip_calculated = (page - 1) * limit

    logs, total_count = await admin_service.get_activity_logs_service(
        db=db,
        skip=skip_calculated,
        limit=limit,
        company_id=company_id,
        activity_type_category=activity_type_category,
        start_date=start_date,
        end_date=end_date
    )

    total_pages = ceil(total_count / limit) if limit > 0 else 0

    return log_schema.PaginatedActivityLogResponse(
        logs=logs,
        total_pages=total_pages,
        current_page=page,
        total_logs=total_count
    )

# --- NEW ENDPOINT FOR EXPORTING ACTIVITY LOGS ---
@router.get("/export-logs")
async def export_activity_logs(
    company_id: Optional[str] = None,
    activity_type_category: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: Users = Depends(get_current_super_admin)
):
    """
    Exports activity logs as a CSV file.
    Supports filtering by 'company_id', 'activity_type_category', 'start_date', and 'end_date'.
    """
    # Fetch logs using the service, potentially without pagination for export
    # We'll assume the service function can handle fetching all relevant logs
    csv_data = await admin_service.export_activity_logs_service(
        db=db,
        company_id=company_id,
        activity_type_category=activity_type_category,
        start_date=start_date,
        end_date=end_date
    )

    # Prepare the response for CSV download
    return StreamingResponse(
        io.StringIO(csv_data),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=activity_logs.csv"}
    )

# --- ENDPOINT BARU DITAMBAHKAN DI SINI ---
@router.get(
    "/activity-logs/type",
    response_model=log_schema.CategoryListResponse,
    summary="Dapatkan kategori tipe aktivitas yang unik",
    description="Mengambil daftar nilai unik dari kolom 'activity_type_category' pada log aktivitas."
)
async def get_distinct_activity_categories(
    db: AsyncSession = Depends(get_db),
    company_id: Optional[int] = Query(None, description="Opsional: Filter berdasarkan ID perusahaan"),
):
    """
    Mengambil nilai distinct untuk kolom 'activity_type_category'.
    Opsional dapat difilter berdasarkan company_id.
    """
    try:
        # Buat statement query SQL menggunakan SQLAlchemy
        stmt = select(distinct(ActivityLog.activity_type_category))

        # Terapkan filter company_id jika diberikan
        if company_id is not None:
            stmt = stmt.where(ActivityLog.company_id == company_id)
        
        # Eksekusi query
        result = await db.execute(stmt)
        
        # Ambil semua kategori distinct
        distinct_categories = result.scalars().all()
        
        # Kembalikan daftar kategori
        return log_schema.CategoryListResponse(categories=distinct_categories)

    except Exception as e:
        # Log the exception for debugging
        # logger.error(f"Error fetching distinct activity categories: {e}") 
        
        # Raise an HTTPException for the client
        raise HTTPException(
            status_code=500, 
            detail=f"Terjadi kesalahan saat mengambil kategori distinct: {str(e)}"
        )

