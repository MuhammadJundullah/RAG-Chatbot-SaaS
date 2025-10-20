from typing import AsyncGenerator, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import db_manager
from datetime import datetime, timedelta
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from app.core.config import settings
from app.models import user_model
from app.schemas import token_schema
from app.repository import user_repository

# The tokenUrl should point to the new login endpoint
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async for session in db_manager.get_db_session():
        yield session

# --- User Authentication and Authorization Dependencies ---

async def get_current_user(token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)) -> user_model.Users:
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
        
        token_data = token_schema.TokenData(
            email=email, 
            role=payload.get("role"), 
            company_id=payload.get("company_id")
        )

    except JWTError:
        raise credentials_exception
    
    user = await user_repository.get_user_by_email(db, email=token_data.email)
    if user is None:
        raise credentials_exception
        
    return user

async def get_current_super_admin(current_user: user_model.Users = Depends(get_current_user)) -> user_model.Users:
    """Dependency to ensure the user is a super admin."""
    if not current_user.is_super_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The user does not have super admin privileges",
        )
    return current_user

async def get_current_company_admin(current_user: user_model.Users = Depends(get_current_user)) -> user_model.Users:
    """Dependency to ensure the user is a company admin and the company is approved."""
    if not current_user.role == 'admin' or not current_user.is_active_in_company:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is not an active admin for the company",
        )
    return current_user
