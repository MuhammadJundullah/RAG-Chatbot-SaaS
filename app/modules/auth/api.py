from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from app.core.dependencies import get_db, get_current_user
from app.models import user_model
from app.modules.auth import service as user_service
from app.modules.auth.service import UserRegistrationError
from app.schemas import user_schema, token_schema
from app.utils import auth
from app.utils.activity_logger import log_activity
from app.utils.user_identifier import get_user_identifier

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
    """
    try:
        user = await user_service.register_user(db, user_data=user_data)

        company_email_to_use = user_data.company_email or user_data.email
        company_id_to_log = user.company_id
        await log_activity(
            db=db,
            user_id=user.id,
            activity_type_category="Data/CRUD",
            company_id=company_id_to_log,
            activity_description=(
                f"Admin registered for company '{user_data.company_name}' with company email '{company_email_to_use}'."
            ),
        )

        if user.role == 'admin':
            return {"message": f"Company '{user_data.company_name}' and admin user '{company_email_to_use}' registered successfully. Pending approval from a super admin."}
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
    except IntegrityError as e:
        if "duplicate key value violates unique constraint" in str(e):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Username or company email already registered. Please use a different username or company email."
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="An unexpected error occurred during registration. Please try again later."
            )


@router.post("/user/token", response_model=token_schema.Token)
async def login_for_access_token(
    data: user_schema.UserLoginCombined,
    db: AsyncSession = Depends(get_db),
):
    """
    Authenticates any user (super admin, admin, or employee) and returns a JWT token.
    """
    try:
        user = await user_service.authenticate_user(
            db,
            email=data.email,
            username=data.username,
            password=data.password,
        )
    except HTTPException as e:
        await log_activity(
            db=db,
            user_id=None,
            activity_type_category="Login/Akses",
            company_id=None,
            activity_description=f"User login blocked: {e.detail}",
        )
        raise e

    if not user:
        await log_activity(
            db=db,
            user_id=None,
            activity_type_category="Login/Akses",
            company_id=None,
            activity_description="User login failed.",
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect credentials or user is inactive/unauthorized.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token_data_payload = {
        "sub": str(user.id),
        "role": user.role,
        "name": user.name,
    }
    if user.company_id:
        token_data_payload["company_id"] = user.company_id
    if user.company and user.company.name:
        token_data_payload["company_name"] = user.company.name
    if user.company and user.company.logo_s3_path:
        token_data_payload["logo_s3_path"] = user.company.logo_s3_path
    token_data_payload["login_at"] = datetime.utcnow().isoformat() + "Z"

    user_identifier = get_user_identifier(user)
    await log_activity(
        db=db,
        user_id=user.id,
        activity_type_category="Login/Akses",
        company_id=user.company_id if user.company else None,
        activity_description=f"User '{user_identifier}' login successfully for company '{user.company.company_email if user.company else ''}'.",
    )

    token_data = auth.create_access_token(data=token_data_payload)
    return {
        "access_token": token_data["access_token"],
        "token_type": "bearer",
        "expires_in": token_data["expires_in"],
        "user": user,
    }


@router.get("/me", response_model=user_schema.User)
async def read_users_me(current_user: user_model.Users = Depends(get_current_user)):
    """
    Retrieves the current user's profile.
    """
    return current_user


@router.post("/request-password-reset")
async def request_password_reset(
    email: str = Query(..., description="Company email yang akan di-reset"),
    db: AsyncSession = Depends(get_db),
):
    """
    Mengirimkan tautan/token reset password via email.
    """
    return await user_service.request_password_reset(db, email=email)


@router.post("/reset-password")
async def reset_password(
    payload: user_schema.PasswordResetRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Mengganti password menggunakan token reset yang valid.
    """
    return await user_service.reset_password(
        db,
        email=payload.email,
        token=payload.token,
        new_password=payload.new_password,
    )
