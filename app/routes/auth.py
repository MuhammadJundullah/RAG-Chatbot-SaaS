from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app import crud
from app.database.connection import db_manager
from app.models import schemas
from app.utils import auth, security
from app.database.schema import Users

from app.database.schema import Users

router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
)


@router.post("/company-signup", status_code=status.HTTP_201_CREATED)
async def company_signup(
    data: schemas.CompanyAdminCreate, db: AsyncSession = Depends(db_manager.get_db_session)
):
    """
    Handles the registration of a new company and its first admin user.
    """
    # Check if company or admin email already exists
    db_company = await crud.get_company_by_name(db, name=data.company_name)
    if db_company:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Company name already registered.",
        )
    
    db_user = await crud.get_user_by_email(db, email=data.admin_email)
    if db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered.",
        )

    company, admin = await crud.create_company_and_admin(db, data=data)
    
    # Create access token for the new admin
    access_token = auth.create_access_token(
        data={
            "sub": admin.email,
            "role": admin.role,
            "company_id": company.id,
        }
    )
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/register", response_model=schemas.User, status_code=status.HTTP_201_CREATED)
async def register_user(
    user: schemas.UserCreate, 
    db: AsyncSession = Depends(db_manager.get_db_session)
):
    """
    Handles self-registration for a user to a specific company.
    The user's status will be 'pending_approval' until an admin approves them.
    """
    db_user = await crud.get_user_by_email(db, email=user.email)
    if db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered.",
        )

    db_company = await crud.get_company(db, company_id=user.Companyid)
    if not db_company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Company with id {user.Companyid} not found."
        )

    # Override status to pending_approval
    user_data = user.model_dump()
    user_data["status"] = "pending_approval"
    
    # Create a new UserCreate schema with the modified data
    pending_user = schemas.UserCreate(**user_data)

    return await crud.create_user(db=db, user=pending_user)


@router.post("/token", response_model=schemas.Token)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(db_manager.get_db_session),
):
    user = await crud.get_user_by_email(db, email=form_data.username) # Using email as username
    if not user or not security.verify_password(form_data.password, user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if user.status != "active":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"User account is not active. Current status: {user.status}"
        )

    access_token = auth.create_access_token(
        data={
            "sub": user.email,
            "role": user.role,
            "company_id": user.Companyid,
        }
    )
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me", response_model=schemas.User)
async def read_users_me(current_user: schemas.User = Depends(auth.get_current_user)):
    """
    Get the current logged in user.
    """
    return current_user