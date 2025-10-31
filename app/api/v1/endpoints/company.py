from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional

from app.core.dependencies import get_current_company_admin, get_db
from app.schemas import user_schema, company_schema
from app.models import user_model
from app.services import company_service

router = APIRouter(
    prefix="/companies",
    tags=["Companies"],
)

# mendapatkan data users dari satu company 
@router.get("/users", response_model=List[user_schema.User])
async def read_company_users(
    db: AsyncSession = Depends(get_db),
    current_user: user_model.Users = Depends(get_current_company_admin)
):
    """
    Get a list of all users in the admin's company.
    Accessible only by the company's admin.
    """
    return await company_service.get_company_users_service(
        db=db,
        current_user=current_user
    )

@router.get("/me", response_model=company_schema.Company)
async def read_my_company(
    db: AsyncSession = Depends(get_db),
    current_user: user_model.Users = Depends(get_current_company_admin)
):
    """
    Get the current admin's company data.
    Accessible only by the company's admin.
    """
    return await company_service.get_my_company_service(
        db=db,
        current_user=current_user
    )

# register employee
@router.post("/employees/register", response_model=user_schema.User, status_code=status.HTTP_201_CREATED)
async def register_employee_by_company_admin(
    employee_data: user_schema.EmployeeRegistrationByAdmin,
    current_admin: user_model.Users = Depends(get_current_company_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Register a new employee for the admin's company.
    Accessible only by the company's admin.
    """
    return await company_service.register_employee_by_company_admin_service(
        db=db,
        employee_data=employee_data,
        current_admin=current_admin
    )

@router.put("/me", response_model=company_schema.Company)
async def update_my_company(
    name: Optional[str] = Form(None),
    code: Optional[str] = Form(None),
    address: Optional[str] = Form(None),
    logo_file: UploadFile = File(None),
    current_user: user_model.Users = Depends(get_current_company_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Update the current admin's company data, including logo upload to S3.
    Accessible only by the company's admin.
    """
    return await company_service.update_my_company_service(
        db=db,
        current_user=current_user,
        name=name,
        code=code,
        address=address,
        logo_file=logo_file
    )