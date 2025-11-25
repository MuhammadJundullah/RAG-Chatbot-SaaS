from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Tuple, Optional
from fastapi import HTTPException, status
import csv # Import csv
import io # Import io

from app.repository.company_repository import company_repository
from app.schemas import company_schema
from app.repository.log_repository import log_repository
from app.models.log_model import ActivityLog
from app.utils.email_sender import send_brevo_email

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
    result = await company_repository.approve_company(db, company_id=company_id)

    if result == "already_active":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Company with id {company_id} is already active."
        )

    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Company with id {company_id} not found."
        )

    company = result

    # Non-blocking email notification to company admin(s)
    try:
        # Ambil admin perusahaan
        from app.repository.user_repository import user_repository

        admins = await user_repository.get_admins_by_company(db, company_id=company_id)
        emails = [admin.email for admin in admins if admin.email]
        if emails:
            subject = "Perusahaan Anda telah disetujui"
            body = (
                f"<p>Perusahaan '{company.name}' telah disetujui.</p>"
                f"<p>Silakan login ke platform untuk mulai menggunakan layanan.</p>"
            )
            for email in emails:
                await send_brevo_email(to_email=email, subject=subject, html_content=body)
    except Exception as e:
        import logging
        logging.error("Failed to send approval email for company %s: %s", company_id, e)

    return {"message": f"Company with id {company_id} has been approved."}

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
    company_id: Optional[str] = None,
    activity_type_category: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
) -> Tuple[List[ActivityLog], int]:
    """
    Service to get all activity logs with pagination and filtering.
    Handles empty string parameters by converting them to None.
    """
    # Convert empty strings to None and handle company_id conversion
    company_id_int = None
    if company_id and company_id.strip():
        try:
            company_id_int = int(company_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid company_id format. Must be an integer.")

    if not activity_type_category or not activity_type_category.strip():
        activity_type_category = None
    if not start_date or not start_date.strip():
        start_date = None
    if not end_date or not end_date.strip():
        end_date = None

    logs, total_count = await log_repository.get_activity_logs(
        db=db,
        skip=skip,
        limit=limit,
        company_id=company_id_int,
        activity_type_category=activity_type_category,
        start_date=start_date,
        end_date=end_date
    )
    return logs, total_count

async def export_activity_logs_service(
    db: AsyncSession,
    company_id: Optional[str] = None,
    activity_type_category: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
) -> str:
    """
    Fetches activity logs with filters and formats them into a CSV string.
    Handles empty string parameters by converting them to None.
    """
    # Convert empty strings to None and handle company_id conversion
    company_id_int = None
    if company_id and company_id.strip():
        try:
            company_id_int = int(company_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid company_id format. Must be an integer.")

    if not activity_type_category or not activity_type_category.strip():
        activity_type_category = None
    if not start_date or not start_date.strip():
        start_date = None
    if not end_date or not end_date.strip():
        end_date = None
        
    # Fetch all logs matching the criteria for export.
    logs, _ = await log_repository.get_activity_logs(
        db=db,
        skip=0,
        limit=None,
        company_id=company_id_int,
        activity_type_category=activity_type_category,
        start_date=start_date,
        end_date=end_date
    )

    # Use io.StringIO to write CSV data in memory
    output = io.StringIO()
    writer = csv.writer(output)

    # Write header row
    header = [
        "ID", "Timestamp", "User ID", "Company ID", 
        "Activity Type Category", "Activity Description",
        "User Email", "Company Name"
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
