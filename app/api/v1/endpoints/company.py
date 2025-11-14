from fastapi import APIRouter, Depends, Form, UploadFile, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from datetime import datetime, timezone
from app.core.dependencies import get_db, get_current_company_admin, get_current_employee
from app.models.user_model import Users
from app.schemas import company_schema, user_schema
from app.services import company_service, user_service
from app.services.user_service import EmployeeDeletionError, UserRegistrationError, EmployeeUpdateError
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
    updated_company = await company_service.update_company_by_admin_service(
        db=db,
        current_user=current_user,
        name=name,
        code=code,
        address=address,
        logo_file=logo_file,
        pic_phone_number=pic_phone_number,
    )
    
    # Log company update
    company_id_to_log = current_user.company_id if current_user.company else None
    log_activity(
        db=db, # Pass the database session
        user_id=current_user.id, # Use integer user ID
        activity_type_category="Data/CRUD",
        company_id=company_id_to_log, # Use integer company ID
        activity_description=f"Company '{updated_company.name}' updated by admin '{current_user.email}'.",
        timestamp=datetime.now(timezone.utc)
    )
    return updated_company

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
        registered_employee = await user_service.register_employee_by_admin(
            db=db,
            company_id=current_user.company_id,
            employee_data=employee_data,
            current_user=current_user,
            profile_picture_file=profile_picture_file
        )
        
        # Log employee registration
        company_id_to_log = current_user.company_id if current_user.company else None
        log_activity(
            db=db, # Pass the database session
            user_id=current_user.id, # Use integer user ID
            activity_type_category="Data/CRUD",
            company_id=company_id_to_log, # Use integer company ID
            activity_description=f"Employee '{registered_employee.email}' registered by admin '{current_user.email}'.",
            timestamp=datetime.now(timezone.utc)
        )
        return registered_employee
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
        updated_employee = await user_service.update_employee_by_admin(
            db=db,
            company_id=current_user.company_id,
            employee_id=employee_id,
            employee_data=employee_data,
            profile_picture_file=profile_picture_file
        )
        
        # Log employee update
        company_id_to_log = current_user.company_id if current_user.company else None
        log_activity(
            db=db, # Pass the database session
            user_id=current_user.id, # Use integer user ID
            activity_type_category="Data/CRUD",
            company_id=company_id_to_log, # Use integer company ID
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
        
        # Log employee deletion
        company_id_to_log = current_user.company_id if current_user.company else None
        log_activity(
            db=db, # Pass the database session
            user_id=current_user.id, # Use integer user ID
            activity_type_category="Data/CRUD",
            company_id=company_id_to_log, # Use integer company ID
            activity_description=f"Employee with ID {employee_id} deleted by admin '{current_user.email}'.",
            timestamp=datetime.now(datetime.timezone.utc)
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
    users = await company_service.get_company_users_by_admin_service(
        db=db,
        current_user=current_user
    )
    
    # Log feature access
    company_id_to_log = current_user.company_id if current_user.company else None
    log_activity(
        db=db, # Pass the database session
        user_id=current_user.id, # Use integer user ID
        activity_type_category="Data/CRUD", # Or "Login/Akses" if preferred for feature access
        company_id=company_id_to_log, # Use integer company ID
        activity_description=f"Admin '{current_user.email}' accessed list of company users. Found {len(users)} users.",
        timestamp=datetime.now(timezone.utc)
    )
    return users

@router.get("/active", response_model=List[company_schema.Company])
async def get_active_companies(
    page: int = 1,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
):
    """Gets a list of active companies, supporting pagination."""
    skip_calculated = (page - 1) * limit
    companies = await company_service.get_active_companies_service(
        db=db,
        skip=skip_calculated,
        limit=limit
    )
    
    # Log data read
    # For public endpoints, user_id and company might be unknown or N/A
    log_activity(
        db=db, # Pass the database session
        user_id=None, # User ID is not known for public access
        activity_type_category="Data/CRUD",
        company_id=None, # Company ID is not known for public access
        activity_description=f"Retrieved list of active companies. Found {len(companies)} companies.",
        timestamp=datetime.now(datetime.timezone.utc)
    )
    return companies

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

