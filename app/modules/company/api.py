from fastapi import APIRouter, Depends, Form, UploadFile, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from datetime import datetime, timezone

from app.core.dependencies import get_db, get_current_company_admin, get_current_employee
from app.models.user_model import Users
from app.schemas import company_schema, user_schema
from app.schemas.user_schema import User, PaginatedUserResponse
from app.modules.company import service as company_service
from app.modules.auth import service as user_service
from app.modules.auth.service import EmployeeDeletionError, EmployeeUpdateError
from app.utils.activity_logger import log_activity

router = APIRouter(
    prefix="/companies",
    tags=["Company"],
)


@router.get("/", response_model=company_schema.Company)
async def read_company_by_user(
    db: AsyncSession = Depends(get_db),
    current_user: Users = Depends(get_current_employee)
):
    return await company_service.get_company_by_user_service(
        db=db,
        current_user=current_user
    )


@router.put("/me", response_model=company_schema.CompanyMeResponse)
async def update_company_by_admin(
    name: Optional[str] = Form(None),
    company_email: Optional[str] = Form(None),
    admin_name: Optional[str] = Form(None),
    admin_email: Optional[str] = Form(None),
    admin_password: Optional[str] = Form(None),
    code: Optional[str] = Form(None),
    address: Optional[str] = Form(None),
    logo_file: Optional[UploadFile] = None,
    pic_phone_number: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db),
    current_user: Users = Depends(get_current_company_admin)
):
    updated_company, updated_admin = await company_service.update_company_by_admin_service(
        db=db,
        current_user=current_user,
        name=name,
        company_email=company_email,
        admin_name=admin_name,
        admin_email=admin_email,
        admin_password=admin_password,
        code=code,
        address=address,
        logo_file=logo_file,
        pic_phone_number=pic_phone_number,
    )

    company_id_to_log = current_user.company_id if current_user.company else None
    log_activity(
        db=db,
        user_id=current_user.id,
        activity_type_category="Data/CRUD",
        company_id=company_id_to_log,
        activity_description=f"Company '{updated_company.name}' updated by admin '{current_user.email}'.",
        timestamp=datetime.now(timezone.utc)
    )

    company_data = company_schema.Company.from_orm(updated_company)

    response = company_schema.CompanyMeResponse(
        **company_data.model_dump(),
        admin_name=updated_admin.name,
        admin_email=updated_admin.email
    )
    return response


@router.post("/employees/register", response_model=user_schema.User)
async def register_employee_by_admin(
    name: str = Form(...),
    email: str = Form(...),
    username: str = Form(...),
    password: str = Form(...),
    division: Optional[str] = Form(None),
    profile_picture_file: UploadFile = None,
    db: AsyncSession = Depends(get_db),
    current_user: Users = Depends(get_current_company_admin)
):
    employee_data = user_schema.EmployeeRegistrationByAdmin(
        name=name,
        email=email,
        username=username,
        password=password,
        division=division
    )

    registered_employee = await user_service.register_employee_by_admin(
        db=db,
        company_id=current_user.company_id,
        employee_data=employee_data,
        current_user=current_user,
        profile_picture_file=profile_picture_file
    )

    company_id_to_log = current_user.company_id if current_user.company else None
    log_activity(
        db=db,
        user_id=current_user.id,
        activity_type_category="Data/CRUD",
        company_id=company_id_to_log,
        activity_description=f"Employee '{registered_employee.email}' registered by admin '{current_user.email}'.",
        timestamp=datetime.now(timezone.utc)
    )
    return registered_employee


@router.put("/employees/{employee_id}", response_model=user_schema.User)
async def update_employee_by_admin(
    employee_id: int,
    name: Optional[str] = Form(None),
    email: Optional[str] = Form(None),
    username: Optional[str] = Form(None),
    password: Optional[str] = Form(None),
    division: Optional[str] = Form(None),
    profile_picture_file: Optional[UploadFile] = None,
    db: AsyncSession = Depends(get_db),
    current_user: Users = Depends(get_current_company_admin)
):
    employee_data = user_schema.EmployeeUpdate(
        name=name,
        email=email,
        username=username,
        password=password,
        division=division
    )

    try:
        updated_employee = await user_service.update_employee_by_admin(
            db=db,
            company_id=current_user.company_id,
            employee_id=employee_id,
            employee_data=employee_data,
            profile_picture_file=profile_picture_file
        )

        company_id_to_log = current_user.company_id if current_user.company else None
        log_activity(
            db=db,
            user_id=current_user.id,
            activity_type_category="Data/CRUD",
            company_id=company_id_to_log,
            activity_description=f"Employee '{updated_employee.email}' updated by admin '{current_user.email}'.",
            timestamp=datetime.now(timezone.utc)
        )
        return updated_employee
    except EmployeeUpdateError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)


@router.delete("/employees/{employee_id}", status_code=204)
async def delete_employee_by_admin(
    employee_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Users = Depends(get_current_company_admin)
):
    try:
        await user_service.delete_employee_by_admin(
            db=db,
            company_id=current_user.company_id,
            employee_id=employee_id
        )

        company_id_to_log = current_user.company_id if current_user.company else None
        log_activity(
            db=db,
            user_id=current_user.id,
            activity_type_category="Data/CRUD",
            company_id=company_id_to_log,
            activity_description=f"Employee with ID {employee_id} deleted by admin '{current_user.email}'.",
            timestamp=datetime.now(timezone.utc)
        )
        return {"message": "Employee deleted successfully"}
    except EmployeeDeletionError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)


@router.get("/me", response_model=company_schema.CompanyMeResponse)
async def read_company_by_admin(
    db: AsyncSession = Depends(get_db),
    current_user: Users = Depends(get_current_company_admin)
):
    company_details = await company_service.get_company_by_user_service(
        db=db,
        current_user=current_user
    )

    response = company_schema.CompanyMeResponse(
        id=company_details.id,
        name=company_details.name,
        code=company_details.code,
        logo_s3_path=company_details.logo_s3_path,
        address=company_details.address,
        is_active=company_details.is_active,
        pic_phone_number=company_details.pic_phone_number,
        company_email=company_details.company_email,
        created_at=str(company_details.created_at) if company_details.created_at else None,
        admin_name=current_user.name,
        admin_email=current_user.email
    )

    return response


@router.get(
    "/users",
    response_model=PaginatedUserResponse,
    summary="List company employees with pagination",
    description="Retrieves a list of employees within the company, excluding admins, with pagination and optional filters.",
)
async def get_company_users_by_admin(
    db: AsyncSession = Depends(get_db),
    current_user: Users = Depends(get_current_company_admin),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(100, ge=1, le=1000, description="Items per page"),
    search: Optional[str] = Query(
        None,
        max_length=100,
        description=(
            "Cari username, nama, atau email. Kosongkan untuk menampilkan semua pengguna; "
            "pencarian diterapkan jika panjang kata kunci minimal 2 karakter."
        ),
    ),
):
    try:
        skip = (page - 1) * limit
        normalized_search = search.strip() if search else None
        if normalized_search == "" or (normalized_search and len(normalized_search) < 2):
            normalized_search = None
        paginated_users = await company_service.get_company_users_paginated(
            db=db,
            company_id=current_user.company_id,
            skip=skip,
            limit=limit,
            page=page,
            search=normalized_search
        )
        return paginated_users

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred while fetching users: {str(e)}")


@router.get("/active", response_model=List[company_schema.Company])
async def get_active_companies(
    page: int = 1,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
):
    skip_calculated = (page - 1) * limit
    companies = await company_service.get_active_companies_service(
        db=db,
        skip=skip_calculated,
        limit=limit
    )

    company_id_to_log = None
    log_activity(
        db=db,
        user_id=None,
        activity_type_category="Data/CRUD",
        company_id=company_id_to_log,
        activity_description=f"Retrieved list of active companies. Found {len(companies)} companies.",
        timestamp=datetime.now(timezone.utc)
    )
    return companies


@router.get("/pending-approval", response_model=List[company_schema.Company])
async def get_pending_approval_companies(
    page: int = 1,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
):
    skip_calculated = (page - 1) * limit
    return await company_service.get_pending_approval_companies_service(
        db=db,
        skip=skip_calculated,
        limit=limit
    )
