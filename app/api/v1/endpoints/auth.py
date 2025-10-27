from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.services import user_service
from app.services.user_service import UserRegistrationError
from app.core.dependencies import get_db, get_current_user
from app.schemas import user_schema, token_schema
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
    Handles registration for new companies.

    - **To register a new company:** Provide `name`, `email`, `password`, `company_name`, and optionally `pic_phone_number` and `username`.
    """
    try:
        user = await user_service.register_user(db, user_data=user_data)
        
        if user.role == 'admin':
            return {"message": f"Company '{user_data.company_name}' and admin user '{user.email}' registered successfully. Pending approval from a super admin."}
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Employee self-registration is not allowed. Please contact your company administrator to be registered."
            )

    except UserRegistrationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.detail,
        )

@router.post("/user/token", response_model=token_schema.Token)
async def login_for_access_token(
    data: user_schema.UserLoginCombined,
    db: AsyncSession = Depends(get_db),
):
    user = await user_service.authenticate_user(db, email=data.email, username=data.username, password=data.password)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect credentials or user is inactive/unauthorized.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token_data_payload = {
        "sub": str(user.id),
        "role": user.role,
    }
    if user.company_id:
        token_data_payload["company_id"] = user.company_id

    token_data = auth.create_access_token(data=token_data_payload)
    return {
        "access_token": token_data["access_token"],
        "token_type": "bearer",
        "expires_in": token_data["expires_in"],
        "user": user,
    }

@router.get("/me", response_model=user_schema.User)
async def read_users_me(current_user: user_schema.User = Depends(get_current_user)):
    """
    Get the current logged in user.
    """
    return current_user
