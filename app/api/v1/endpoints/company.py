from fastapi import APIRouter, Depends, Form, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional

from app.core.dependencies import get_current_user, get_db, get_current_company_admin
from app.models.user_model import Users
from app.schemas import company_schema, user_schema # Import user_schema
from app.services import company_service

# Changed prefix from "/company" to "/companies" to match the desired API path structure
router = APIRouter(
    prefix="/companies",
    tags=["Company"],
)

# --- NEW ENDPOINT FOR UPDATING COMPANY DETAILS ---
@router.put("/me", response_model=company_schema.Company)
async def update_company_by_admin(
    name: Optional[str] = Form(None),
    code: Optional[str] = Form(None),
    address: Optional[str] = Form(None),
    logo_file: Optional[UploadFile] = None,
    pic_phone_number: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db),
    current_user: Users = Depends(get_current_company_admin)
):
    """
    Updates the company's name and code.
    Requires the user to be a company administrator.
    """
    # The 'db' and 'current_user' parameters are correctly injected by FastAPI's dependency injection system.
    # They are available for use within this function.
    return await company_service.update_company_by_admin_service(
        db=db,
        current_user=current_user,
        name=name,
        code=code,
        address=address,
        logo_file=logo_file,
        pic_phone_number=pic_phone_number,
    )

# --- NEW ENDPOINT FOR REGISTERING EMPLOYEES ---
@router.post("/employees/register", response_model=user_schema.User)
async def register_employee_by_admin(
    employee_data: user_schema.EmployeeRegistrationByAdmin, # Using the correct schema for employee registration
    db: AsyncSession = Depends(get_db),
    current_user: Users = Depends(get_current_company_admin) # Ensure only company admins can register employees
):
    """
    Registers a new employee within the company.
    Requires the user to be a company administrator.
    """
    # The company_id will be derived from the current_user
    return await company_service.register_employee_by_admin_service(
        db=db,
        company_id=current_user.company_id,
        employee_data=employee_data
    )

# --- Existing endpoints ---

@router.get("/", response_model=company_schema.Company)
async def read_company_by_user(
    db: AsyncSession = Depends(get_db),
    current_user: Users = Depends(get_current_user) # Changed to get_current_user for broader access
):
    return await company_service.get_company_by_user_service(
        db=db,
        current_user=current_user
    )

@router.get("/me", response_model=company_schema.Company)
async def read_company_by_admin(
    db: AsyncSession = Depends(get_db),
    current_user: Users = Depends(get_current_company_admin)
):
    """
    Gets the current user's company details via /companies/me.
    Accessible by company admin.
    """
    return await company_service.get_company_by_user_service(
        db=db,
        current_user=current_user
    )

@router.get("/users", response_model=List[user_schema.User]) # Changed response_model to List[user_schema.User]
async def get_company_users_by_admin(
    db: AsyncSession = Depends(get_db),
    current_user: Users = Depends(get_current_company_admin)
):
    """
    Gets a list of all users within the company.
    Accessible only by company administrators.
    """
    return await company_service.get_company_users_by_admin_service(
        db=db,
        current_user=current_user
    )

@router.get("/active", response_model=List[company_schema.Company])
async def get_active_companies(
    page: int = 1,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
):
    """Gets a list of active companies, supporting pagination."""
    skip_calculated = (page - 1) * limit
    return await company_service.get_active_companies_service(
        db=db,
        skip=skip_calculated,
        limit=limit
    )

@router.get("/pending-approval", response_model=List[company_schema.Company])
async def get_pending_approval_companies(
    page: int = 1,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
):
    """Gets a list of companies that are pending approval."""
    skip_calculated = (page - 1) * limit
    return await company_service.get_pending_approval_companies_service(
        db=db,
        skip=skip_calculated,
        limit=limit
    )
