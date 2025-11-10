from fastapi import APIRouter, Depends, Form, UploadFile, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional

from app.core.dependencies import get_current_user, get_db, get_current_company_admin
from app.models.user_model import Users
from app.schemas import company_schema, user_schema
from app.services import company_service, user_service
from app.services.user_service import EmployeeDeletionError, UserRegistrationError, EmployeeUpdateError

router = APIRouter(
    prefix="/companies",
    tags=["Company"],
)

@router.get("/", response_model=company_schema.Company)
async def read_company_by_user(
    db: AsyncSession = Depends(get_db),
    current_user: Users = Depends(get_current_user)
):
    return await company_service.get_company_by_user_service(
        db=db,
        current_user=current_user
    )

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

@router.post("/employees/register", response_model=user_schema.User)
async def register_employee_by_admin(
    # Define each field as a Form parameter instead of a single JSON string
    name: str = Form(...),
    email: str = Form(...),
    username: str = Form(...),
    password: str = Form(...),
    division: Optional[str] = Form(None), 
    profile_picture_file: UploadFile = None,
    db: AsyncSession = Depends(get_db),
    current_user: Users = Depends(get_current_company_admin) 
):
    """
    Registers a new employee within the company, including uploading a profile picture.
    Requires the user to be a company administrator.
    If a division name is provided and the division does not exist, it will be created.
    """
    try:
        # Manually construct the Pydantic model from form parameters
        employee_data = user_schema.EmployeeRegistrationByAdmin(
            name=name,
            email=email,
            username=username,
            password=password,
            division=division 
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid employee data format: {e}")

    try:
        # The company_id will be derived from the current_user
        # Call the user_service function and pass the profile picture file and current_user
        return await user_service.register_employee_by_admin(
            db=db,
            company_id=current_user.company_id,
            employee_data=employee_data,
            current_user=current_user,
            profile_picture_file=profile_picture_file
        )
    except UserRegistrationError as e:
        raise HTTPException(status_code=400, detail=e.detail)

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
    """
    Updates an employee's information, including their profile picture.
    Requires the user to be a company administrator.
    """
    employee_data = user_schema.EmployeeUpdate(
        name=name,
        email=email,
        username=username,
        password=password,
        division=division
    )

    try:
        return await user_service.update_employee_by_admin(
            db=db,
            company_id=current_user.company_id,
            employee_id=employee_id,
            employee_data=employee_data,
            profile_picture_file=profile_picture_file
        )
    except EmployeeUpdateError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)


@router.delete("/employees/{employee_id}", status_code=204)
async def delete_employee_by_admin(
    employee_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Users = Depends(get_current_company_admin)
):
    """
    Deletes an employee within the company.
    Requires the user to be a company administrator.
    """
    try:
        await user_service.delete_employee_by_admin(
            db=db,
            company_id=current_user.company_id,
            employee_id=employee_id
        )
        return {"message": "Employee deleted successfully"}
    except EmployeeDeletionError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)

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

@router.get("/users", response_model=List[user_schema.User])
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

