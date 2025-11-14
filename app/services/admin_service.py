from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Tuple, Optional
from fastapi import HTTPException, status
import csv # Import csv
import io # Import io

from app.repository.company_repository import company_repository
from app.schemas import company_schema
from app.repository.log_repository import log_repository
from app.models.log_model import ActivityLog

async def get_companies_service(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None
) -> List[company_schema.Company]:
    companies = await company_repository.get_companies(db, skip=skip, limit=limit, status=status)
    return companies

async def approve_company_service(
    db: AsyncSession,
    company_id: int
):
    approval_status = await company_repository.approve_company(db, company_id=company_id)
    
    if approval_status == "approved":
        return {"message": f"Company with id {company_id} has been approved."}
    elif approval_status == "already_active":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Company with id {company_id} is already active."
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Company with id {company_id} not found."
        )

async def reject_company_service(
    db: AsyncSession,
    company_id: int
):
    company_to_reject = await company_repository.get_company(db, company_id=company_id)
    if not company_to_reject:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Company with id {company_id} not found."
        )

    if company_to_reject.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot reject an active company."
        )

    await company_repository.reject_company(db, company_id=company_id)
    return {"message": f"Company with id {company_id} has been rejected and deleted."}

async def get_activity_logs_service(
    db: AsyncSession,
    skip: int,
    limit: int,
    company_id: Optional[int] = None,
    activity_type_category: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
) -> Tuple[List[ActivityLog], int]:
    """
    Service to get all activity logs with pagination and filtering.
    """
    logs, total_count = await log_repository.get_activity_logs(
        db=db,
        skip=skip,
        limit=limit,
        company_id=company_id,
        activity_type_category=activity_type_category,
        start_date=start_date,
        end_date=end_date
    )
    return logs, total_count

async def export_activity_logs_service(
    db: AsyncSession,
    company_id: Optional[int] = None,
    activity_type_category: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
) -> str:
    """
    Fetches activity logs with filters and formats them into a CSV string.
    """
    # Fetch all logs matching the criteria for export.
    # We pass limit=None to indicate fetching all records.
    # The repository's get_activity_logs should handle limit=None to fetch all.
    logs, _ = await log_repository.get_activity_logs(
        db=db,
        skip=0, # No skip for export, fetch all from the beginning
        limit=None, # Fetch all records
        company_id=company_id,
        activity_type_category=activity_type_category,
        start_date=start_date,
        end_date=end_date
    )

    # Use io.StringIO to write CSV data in memory
    output = io.StringIO()
    writer = csv.writer(output)

    # Write header row
    # Ensure these field names match the ActivityLog model attributes or desired output
    header = [
        "ID", "Timestamp", "User ID", "Company ID", 
        "Activity Type Category", "Activity Description",
        "User Email", "Company Name" # Assuming these are available via joinedload
    ]
    writer.writerow(header)

    # Write data rows
    for log in logs:
        user_email = log.user.email if log.user else ""
        company_name = log.company.name if log.company else ""
        
        writer.writerow([
            log.id,
            log.timestamp.isoformat() if log.timestamp else "",
            log.user_id,
            log.company_id,
            log.activity_type_category,
            log.activity_description,
            user_email,
            company_name
        ])

    return output.getvalue()
