from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, distinct
from typing import List, Optional
from math import ceil
import io
from starlette.responses import StreamingResponse

from app.core.dependencies import get_current_super_admin, get_db
from app.schemas import company_schema, log_schema
from app.services import admin_service
from app.models.user_model import Users
from app.models.log_model import ActivityLog

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

@router.get("/activity-logs", response_model=log_schema.PaginatedActivityLogResponse)
async def get_activity_logs(
    page: int = 1,
    limit: int = 100,
    company_id: Optional[int] = None,
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
    company_id: Optional[int] = None,
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

