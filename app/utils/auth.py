from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import settings
from app.database.connection import db_manager
from app.database import schema
from app.models import schemas
from app import crud

# The tokenUrl should point to the new login endpoint
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")

# --- JWT Token Management ---

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Creates a new JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

# --- User Authentication and Authorization Dependencies ---

async def get_current_user(token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(db_manager.get_db_session)) -> schema.Users:
    """
    Dependency to get the current user from a JWT token.
    Decodes the token, validates the user, and returns the full user object.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
        
        token_data = schemas.TokenData(
            email=email, 
            role=payload.get("role"), 
            company_id=payload.get("company_id")
        )

    except JWTError:
        raise credentials_exception
    
    user = await crud.get_user_by_email(db, email=token_data.email)
    if user is None:
        raise credentials_exception
        
    return user

async def get_current_super_admin(current_user: schema.Users = Depends(get_current_user)) -> schema.Users:
    """Dependency to ensure the user is a super admin."""
    if not current_user.is_super_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The user does not have super admin privileges",
        )
    return current_user

async def get_current_company_admin(current_user: schema.Users = Depends(get_current_user)) -> schema.Users:
    """Dependency to ensure the user is a company admin and the company is approved."""
    if not current_user.role == 'admin' or not current_user.is_active_in_company:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is not an active admin for the company",
        )
    if not current_user.company.is_approved:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Company is not approved yet.",
        )
    return current_user
