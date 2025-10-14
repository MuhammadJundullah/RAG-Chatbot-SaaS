from fastapi import APIRouter, Depends, HTTPException, status
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



@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(
    user_data: schemas.UserRegistration, 
    db: AsyncSession = Depends(db_manager.get_db_session)
):
    """
    Handles unified registration for both new companies and new employees.

    - **To register a new company:** Provide `name`, `email`, `password`, `company_name`, and `company_code`.
    - **To register as an employee for an existing company:** Provide `name`, `email`, `password`, and `company_id`.
    """
    user = await crud.register_user(db, user_data=user_data)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email or company name may already be registered, or company ID not found.",
        )
    
    if user.role == 'admin':
        return {"message": f"Company '{user_data.company_name}' and admin user '{user.email}' registered successfully. Pending approval from a super admin."}
    else:
        return {"message": f"User '{user.email}' registered for company ID {user_data.company_id}. Pending approval from the company admin."}



@router.post("/token", response_model=schemas.Token)
async def login_for_access_token(
    data: schemas.UserLogin,
    db: AsyncSession = Depends(db_manager.get_db_session),
):
    user = await crud.get_user_by_email(db, email=data.email)
    if not user or not security.verify_password(data.password, user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active_in_company and not user.is_super_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"User account is not active. Please contact your company admin for approval."
        )

    access_token = auth.create_access_token(
        data={
            "sub": user.email,
            "role": user.role,
            "company_id": user.company_id,
        }
    )
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me", response_model=schemas.User)
async def read_users_me(current_user: schemas.User = Depends(auth.get_current_user)):
    """
    Get the current logged in user.
    """
    return current_user