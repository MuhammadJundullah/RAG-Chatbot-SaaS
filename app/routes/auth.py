from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app import crud
from app.database import schema
from app.database.connection import db_manager
from app.models import schemas
from app.utils import auth, security

router = APIRouter()

@router.post("/companies/register", response_model=schemas.CompanyRegistrationResponse, status_code=status.HTTP_201_CREATED)
async def register_company(
    company_data: schemas.CompanyCreate, 
    db: AsyncSession = Depends(db_manager.get_db_session)
):
    """
    Register a new company and its first admin user.
    Returns the company details along with a one-time secret for employee registration.
    """
    db_company = await crud.get_company_by_name(db, name=company_data.name)
    if db_company:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A company with this name already exists.",
        )
    
    db_user = await crud.get_user_by_username(db, username=company_data.admin_username)
    if db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This username is already taken.",
        )

    new_company = await crud.create_company_and_admin(db=db, company_data=company_data)
    
    # The unhashed secret is temporarily attached in crud for this one-time response
    return schemas.CompanyRegistrationResponse(
        id=new_company.id,
        name=new_company.name,
        company_code=new_company.company_code,
        company_secret_one_time=new_company.unhashed_secret
    )


@router.post("/employees/register", response_model=schemas.UserPublic, status_code=status.HTTP_201_CREATED)
async def register_employee(
    employee_data: schemas.EmployeeCreate,
    db: AsyncSession = Depends(db_manager.get_db_session)
):
    """
    Register a new employee for a company.
    Requires a valid company_code and company_secret.
    """
    # 1. Validate company code
    company = await crud.get_company_by_code(db, code=employee_data.company_code)
    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invalid company code.",
        )

    # 2. Validate company secret (plaintext comparison)
    if employee_data.company_secret != company.company_secret:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid company secret credential.",
        )
        
    # 3. Validate division_id if provided
    if employee_data.division_id:
        division = await crud.get_division_by_id(db, division_id=employee_data.division_id)
        if not division or division.company_id != company.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Division with id {employee_data.division_id} is not valid for this company.",
            )

    # 4. Check if username is taken
    db_user = await crud.get_user_by_username(db, username=employee_data.username)
    if db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered.",
        )

    # 4. Create employee
    new_employee = await crud.create_employee(db=db, employee_data=employee_data, company=company)
    return new_employee


@router.post("/token", response_model=schemas.Token)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(db_manager.get_db_session)
):
    """
    Login for any user (admin or employee) to get an access token.
    """
    user = await crud.get_user_by_username(db, username=form_data.username)
    if not user or not security.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = auth.create_access_token(
        data={
            "sub": user.username,
            "role": user.role.value,
            "company_id": user.company_id,
            "division_id": user.division_id
        }
    )
    return {"access_token": access_token, "token_type": "bearer"}
