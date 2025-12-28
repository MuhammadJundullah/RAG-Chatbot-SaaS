from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import joinedload
from typing import List, Tuple, Optional
from math import ceil
from fastapi import HTTPException, status, UploadFile
import csv # Import csv
import io # Import io
import os
import uuid

from app.repository.company_repository import company_repository
from app.schemas import company_schema
from app.repository.log_repository import log_repository
from app.models.log_model import ActivityLog
from app.utils.email_sender import send_brevo_email
from app.repository.user_repository import user_repository
from app.utils.security import get_password_hash
from app.utils.file_manager import save_uploaded_file, delete_static_file
from app.schemas import user_schema
from app.models.company_model import Company
from app.models.subscription_model import Subscription
from app.utils.generators import generate_company_code
from app.models import user_model
from app.utils.user_identifier import get_user_identifier

async def get_companies_service(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None,
    page: int = 1,
    search: Optional[str] = None,
) -> company_schema.PaginatedCompanyUserListResponse:
    normalized_search = search.strip() if search and search.strip() else None
    companies, total_companies = await company_repository.get_companies(
        db,
        skip=skip,
        limit=limit,
        status=status,
        search=normalized_search,
    )
    company_ids = [company.id for company in companies]
    subscription_map = {}
    if company_ids:
        result = await db.execute(
            select(Subscription)
            .options(joinedload(Subscription.plan))
            .filter(Subscription.company_id.in_(company_ids))
        )
        subscriptions = result.scalars().all()
        subscription_map = {sub.company_id: sub for sub in subscriptions}
    users = await user_repository.get_users_by_company_ids(db, company_ids)
    users_by_company = {}
    for user in users:
        users_by_company.setdefault(user.company_id, []).append(user)
    items: List[company_schema.CompanyUserListItem] = []
    for company in companies:
        company_users = users_by_company.get(company.id, [])
        if company_users:
            for user in company_users:
                items.append(
                    company_schema.CompanyUserListItem(
                        company_id=company.id,
                        company_name=company.name,
                        company_email=company.company_email,
                        company_code=company.code,
                        company_logo_s3_path=company.logo_s3_path,
                        company_is_active=company.is_active,
                        company_address=company.address,
                        company_pic_phone_number=company.pic_phone_number,
                        company_created_at=company.created_at,
                        subscription_plan=(
                            subscription_map.get(company.id).plan.name
                            if subscription_map.get(company.id) and subscription_map.get(company.id).plan
                            else None
                        ),
                        admin_name=user.name,
                        admin_profile_picture_url=user.profile_picture_url,
                    )
                )
        else:
            items.append(
                company_schema.CompanyUserListItem(
                    company_id=company.id,
                    company_name=company.name,
                    company_email=company.company_email,
                    company_code=company.code,
                    company_logo_s3_path=company.logo_s3_path,
                    company_is_active=company.is_active,
                    company_address=company.address,
                    company_pic_phone_number=company.pic_phone_number,
                    company_created_at=company.created_at,
                    subscription_plan=(
                        subscription_map.get(company.id).plan.name
                        if subscription_map.get(company.id) and subscription_map.get(company.id).plan
                        else None
                    ),
                )
            )
    total_page = ceil(total_companies / limit) if total_companies else 0
    return company_schema.PaginatedCompanyUserListResponse(
        companies=items,
        total_company=total_companies,
        current_page=page,
        total_page=total_page,
    )

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

    # Non-blocking email notification to company
    try:
        if company.company_email:
            subject = "Perusahaan Anda telah disetujui"
            body = (
                f"<p>Perusahaan '{company.name}' telah disetujui.</p>"
                f"<p>Silakan login ke platform untuk mulai menggunakan layanan.</p>"
            )
            await send_brevo_email(to_email=company.company_email, subject=subject, html_content=body)
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
        "User Identifier", "Company Name"
    ]
    writer.writerow(header)

    # Write data rows
    for log in logs:
        user_email = get_user_identifier(log.user, company=log.company)
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


async def get_company_detail_with_admins(
    db: AsyncSession,
    company_id: int
) -> company_schema.CompanyUserListItem:
    company = await company_repository.get_company(db, company_id=company_id)
    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Company with id {company_id} not found."
        )
    admin = None
    admins = await user_repository.get_admins_by_company(db, company_id=company_id)
    if admins:
        admin = admins[0]

    subscription_result = await db.execute(
        select(Subscription)
        .options(joinedload(Subscription.plan))
        .filter(Subscription.company_id == company_id)
    )
    subscription = subscription_result.scalar_one_or_none()

    return company_schema.CompanyUserListItem(
        company_id=company.id,
        company_name=company.name,
        company_email=company.company_email,
        company_code=company.code,
        company_logo_s3_path=company.logo_s3_path,
        company_is_active=company.is_active,
        company_address=company.address,
        company_pic_phone_number=company.pic_phone_number,
        company_created_at=company.created_at,
        subscription_plan=subscription.plan.name if subscription and subscription.plan else None,
        admin_name=admin.name if admin else None,
        admin_profile_picture_url=admin.profile_picture_url if admin else None,
    )


async def get_company_admins_service(
    db: AsyncSession,
    company_id: int
):
    company = await company_repository.get_company(db, company_id=company_id)
    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Company with id {company_id} not found."
        )
    return await user_repository.get_admins_by_company(db, company_id=company_id)


async def get_all_company_admins_service(
    db: AsyncSession,
    skip: int,
    limit: int,
    page: int
) -> user_schema.PaginatedAdminResponse:
    admins, total_admins = await user_repository.get_all_admins_paginated(
        db=db,
        skip=skip,
        limit=limit,
    )
    total_pages = (total_admins + limit - 1) // limit if limit > 0 else 0
    return user_schema.PaginatedAdminResponse(
        admins=admins,
        total_admin=total_admins,
        current_page=page,
        total_page=total_pages,
    )


async def get_company_admin_by_id_service(
    db: AsyncSession,
    user_id: int
):
    admin = await user_repository.get_user(db, user_id)
    if not admin or admin.role != "admin" or not admin.company_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Admin not found."
        )
    return admin


async def _read_logo_file(logo_file: UploadFile, max_size_mb: int = 2) -> bytes:
    content = await logo_file.read()
    if not content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Logo file is empty."
        )
    if len(content) > max_size_mb * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Logo file exceeds {max_size_mb} MB."
        )
    allowed_types = {"image/png", "image/jpeg", "image/jpg"}
    if logo_file.content_type and logo_file.content_type.lower() not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Logo file type must be PNG or JPEG."
        )
    return content


async def update_company_by_superadmin_service(
    db: AsyncSession,
    company_id: int,
    payload: company_schema.CompanySuperadminUpdate,
    logo_file: Optional[UploadFile],
    target_admin_id: Optional[int] = None,
    admin_profile_picture_file: Optional[UploadFile] = None,
):
    company = await company_repository.get_company(db, company_id=company_id)
    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Company with id {company_id} not found."
        )

    admins = await user_repository.get_admins_by_company(db, company_id=company_id)
    target_admin = None
    if target_admin_id:
        target_admin = next((a for a in admins if a.id == target_admin_id), None)
        if not target_admin:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Admin with id {target_admin_id} not found for this company."
            )
    else:
        target_admin = admins[0] if admins else None

    logo_path_to_update = company.logo_s3_path
    if payload.logo_s3_path is not None:
        logo_path_to_update = payload.logo_s3_path
    if logo_file and logo_file.filename:
        UPLOAD_DIR = "static/company_logos"
        os.makedirs(UPLOAD_DIR, exist_ok=True)
        content = await _read_logo_file(logo_file)
        file_extension = os.path.splitext(logo_file.filename)[1] or ".png"
        filename = f"{uuid.uuid4()}{file_extension}"
        file_path = os.path.join(UPLOAD_DIR, filename)
        with open(file_path, "wb") as f:
            f.write(content)
        logo_path_to_update = f"/{file_path}"
        if company.logo_s3_path:
            old_file_path = company.logo_s3_path.lstrip('/')
            if os.path.exists(old_file_path) and old_file_path != file_path:
                try:
                    os.remove(old_file_path)
                except OSError:
                    pass

    update_data = {
        "name": payload.name,
        "code": payload.code,
        "address": payload.address,
        "company_email": payload.company_email,
        "pic_phone_number": payload.pic_phone_number,
        "is_active": payload.is_active,
        "logo_s3_path": logo_path_to_update,
    }
    update_data_filtered = {k: v for k, v in update_data.items() if v is not None}
    for key, value in update_data_filtered.items():
        setattr(company, key, value)

    if target_admin and any([payload.admin_name, payload.admin_password, admin_profile_picture_file]):
        if payload.admin_name:
            target_admin.name = payload.admin_name
        if payload.admin_password:
            target_admin.hashed_password = get_password_hash(payload.admin_password)
        if admin_profile_picture_file and admin_profile_picture_file.filename:
            UPLOAD_DIR = "static/admin_profiles"
            new_profile_picture_url = await save_uploaded_file(admin_profile_picture_file, UPLOAD_DIR)
            if target_admin.profile_picture_url:
                delete_static_file(target_admin.profile_picture_url)
            target_admin.profile_picture_url = new_profile_picture_url
        db.add(target_admin)

    db.add(company)
    await db.commit()
    await db.refresh(company)
    if target_admin:
        await db.refresh(target_admin)

    admins_refreshed = await user_repository.get_admins_by_company(db, company_id=company_id)
    return company_schema.CompanyDetailWithAdmins(
        **company_schema.Company.from_orm(company).model_dump(),
        admins=[company_schema.CompanyAdminSummary.from_orm(admin) for admin in admins_refreshed],
    )


async def update_company_admin_by_superadmin_service(
    db: AsyncSession,
    admin_id: int,
    payload: user_schema.AdminSuperadminUpdate,
):
    admin = await user_repository.get_user(db, admin_id)
    if not admin or admin.role != "admin" or not admin.company_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Admin not found."
        )

    if payload.name:
        admin.name = payload.name
    if payload.username:
        admin.username = payload.username
    if payload.password:
        admin.hashed_password = get_password_hash(payload.password)

    db.add(admin)
    await db.commit()
    await db.refresh(admin)
    return admin


async def update_superadmin_profile_service(
    db: AsyncSession,
    superadmin: user_model.Users,
    payload: user_schema.SuperAdminUpdate,
) -> user_model.Users:
    if payload.name:
        superadmin.name = payload.name

    if payload.username:
        existing_user = await user_repository.get_user_by_username(db, username=payload.username)
        if existing_user and existing_user.id != superadmin.id:
            raise HTTPException(status_code=400, detail="Username is already registered.")
        superadmin.username = payload.username

    if payload.email:
        existing_email = await user_repository.get_user_by_email(db, email=payload.email)
        if existing_email and existing_email.id != superadmin.id:
            raise HTTPException(status_code=400, detail="Email is already registered.")
        superadmin.email = payload.email

    if payload.password:
        superadmin.password = get_password_hash(payload.password)

    db.add(superadmin)
    await db.commit()
    await db.refresh(superadmin)
    return superadmin


async def create_company_by_superadmin_service(
    db: AsyncSession,
    payload: company_schema.CompanySuperadminCreate,
    company_logo_file: Optional[UploadFile] = None,
    admin_profile_picture_file: Optional[UploadFile] = None,
):
    existing_company = await company_repository.get_company_by_name(db, name=payload.name)
    if existing_company:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Company name already exists."
        )
    existing_company_email = await company_repository.get_company_by_email(db, company_email=payload.company_email)
    if existing_company_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Company email already exists."
        )
    if payload.code:
        existing_code = await company_repository.get_company_by_code(db, code=payload.code)
        if existing_code:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Company code already exists."
            )

    existing_admin_username = await user_repository.get_user_by_username(db, username=payload.company_email)
    if existing_admin_username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Admin username already exists."
        )

    code_to_use = payload.code or generate_company_code()
    company = Company(
        name=payload.name,
        code=code_to_use,
        address=payload.address,
        company_email=payload.company_email,
        pic_phone_number=payload.pic_phone_number,
        is_active=payload.is_active,
        activation_email_sent=payload.is_active,
    )
    if company_logo_file and company_logo_file.filename:
        UPLOAD_DIR = "static/company_logos"
        os.makedirs(UPLOAD_DIR, exist_ok=True)
        content = await _read_logo_file(company_logo_file)
        file_extension = os.path.splitext(company_logo_file.filename)[1] or ".png"
        filename = f"{uuid.uuid4()}{file_extension}"
        file_path = os.path.join(UPLOAD_DIR, filename)
        with open(file_path, "wb") as f:
            f.write(content)
        company.logo_s3_path = f"/{file_path}"
    db.add(company)
    await db.flush()

    admin_user = user_model.Users(
        name=payload.admin_name,
        username=payload.company_email,
        password=get_password_hash(payload.password),
        role="admin",
        company_id=company.id,
    )
    if admin_profile_picture_file and admin_profile_picture_file.filename:
        UPLOAD_DIR = "static/admin_profiles"
        admin_user.profile_picture_url = await save_uploaded_file(
            admin_profile_picture_file,
            UPLOAD_DIR,
        )
    db.add(admin_user)
    await db.commit()
    await db.refresh(company)
    await db.refresh(admin_user)

    return company_schema.CompanyDetailWithAdmins(
        **company_schema.Company.from_orm(company).model_dump(),
        admins=[company_schema.CompanyAdminSummary.from_orm(admin_user)],
    )

async def update_company_status_service(
    db: AsyncSession,
    company_id: int,
    is_active: bool,
):
    company: Company = await company_repository.get_company(db, company_id=company_id)
    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Company with id {company_id} not found."
        )

    previous_status = company.is_active
    if previous_status == is_active:
        return company

    company.is_active = is_active
    db.add(company)
    await db.commit()
    await db.refresh(company)

    # Kirim email hanya pada aktivasi pertama (False -> True dan belum pernah dikirim)
    if (not previous_status) and is_active and not company.activation_email_sent:
        try:
            if company.company_email:
                subject = "Perusahaan Anda telah disetujui"
                body = (
                    f"<p>Perusahaan '{company.name}' telah disetujui.</p>"
                    f"<p>Silakan login ke platform untuk mulai menggunakan layanan.</p>"
                )
                await send_brevo_email(to_email=company.company_email, subject=subject, html_content=body)
                company.activation_email_sent = True
                db.add(company)
                await db.commit()
        except Exception as e:
            import logging
            logging.error("Failed to send activation email for company %s: %s", company_id, e)

    return company
