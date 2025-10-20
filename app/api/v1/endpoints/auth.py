from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.services import user_service
from app.services.user_service import UserRegistrationError
from app.core.dependencies import get_db, get_current_user
from app.schemas import user_schema, token_schema
from app.models.user_model import Users
from app.utils import auth

router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
)

@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(
    user_data: user_schema.UserRegistration, 
    db: AsyncSession = Depends(get_db)
):
    """
    Handles unified registration for both new companies and new employees.

    - **To register a new company:** Provide `name`, `email`, `password`, `company_name`, and `company_code`.
    - **To register as an employee for an existing company:** Provide `name`, `email`, `password`, and `company_id`.
    """
    try:
        user = await user_service.register_user(db, user_data=user_data)
        
        if user.role == 'admin':
            return {"message": f"Company '{user_data.company_name}' and admin user '{user.email}' registered successfully. Pending approval from a super admin."}
        else:
            return {"message": f"User '{user.email}' registered for company ID {user_data.company_id}. Pending approval from the company admin."}

    except UserRegistrationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.detail,
        )

@router.post("/token", response_model=token_schema.Token)
async def login_for_access_token(
    data: user_schema.UserLogin,
    db: AsyncSession = Depends(get_db),
):
    user = await user_service.authenticate_user(db, email=data.email, password=data.password)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password, or user is inactive.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = auth.create_access_token(
        data={
            "sub": user.email,
            "role": user.role,
            "company_id": user.company_id,
        }
    )
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me", response_model=user_schema.User)
async def read_users_me(current_user: user_schema.User = Depends(get_current_user)):
    """
    Get the current logged in user.
    """
    return current_user
