from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.services import user_service
from app.services.user_service import UserRegistrationError, UserRegistrationError # Ensure custom exceptions are imported
from app.core.dependencies import get_db, get_current_user
from app.schemas import user_schema, token_schema
from app.utils import auth
from app.models import user_model, company_model # Ensure company_model is imported if needed
from datetime import datetime, timedelta # Import datetime and timedelta
import secrets
import string
import os
import uuid
import io
from sqlalchemy.exc import IntegrityError
import logging
from botocore.exceptions import ClientError
from app.core.config import settings # Import settings

router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
)

# --- Existing endpoints ---
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
    except IntegrityError as e:
        # Check if the error is due to a unique constraint violation
        if "duplicate key value violates unique constraint" in str(e):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Username or email already registered. Please use a different username or email."
            )
        else:
            # Re-raise other IntegrityErrors if they are not unique constraint violations
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="An unexpected database error occurred."
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
        "name": user.name,
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
async def read_users_me(current_user: user_model.Users = Depends(get_current_user)):
    """
    Get the current logged in user, including their company's PIC phone number.
    """
    company_pic_phone = None
    if current_user.company and current_user.company.pic_phone_number:
        company_pic_phone = current_user.company.pic_phone_number

    user_data = user_schema.User(
        id=current_user.id,
        name=current_user.name,
        username=current_user.username,
        email=current_user.email,
        role=current_user.role,
        company_id=current_user.company_id,
        division=current_user.division,
        is_active=current_user.is_active,
        company_pic_phone_number=company_pic_phone,
        profile_picture_url=current_user.profile_picture_url # Added to include profile picture URL
    )
    return user_data

# --- New endpoints for password reset ---

@router.post("/request-password-reset")
async def request_reset_route(email: str, db: AsyncSession = Depends(get_db)):
    """
    Request password reset.
    Expects an email address in the query parameters or request body.
    """
    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email is required for password reset request."
        )
    # Call the service function
    return await user_service.request_password_reset(db, email=email)

# Assuming a schema for password reset request exists in user_schema.py
# Example:
# class PasswordResetRequest(BaseModel):
#     email: EmailStr
#     token: str
#     new_password: str = Field(..., min_length=8)

@router.post("/reset-password")
async def reset_password_route(
    data: user_schema.PasswordResetRequest, # Assuming this schema exists
    db: AsyncSession = Depends(get_db)
):
    """
    Reset password with token.
    Expects email, token, and new_password.
    """
    if not data.email or not data.token or not data.new_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email, token, and new password are required."
        )
    
    # Call the service function
    return await user_service.reset_password(
        db,
        email=data.email,
        token=data.token,
        new_password=data.new_password
    )

# --- End of new endpoints ---