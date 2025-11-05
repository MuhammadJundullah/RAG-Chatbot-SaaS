from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import db_manager
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from app.core.config import settings
from app.models import user_model
from app.schemas import token_schema
from app.repository.user_repository import user_repository

# The tokenUrl should point to a generic token endpoint
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/user/token")

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
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
        
        token_data = token_schema.TokenData(
            sub=user_id, 
            role=payload.get("role"), 
            company_id=payload.get("company_id"),
            division_id=payload.get("division_id"),
            name=payload.get("name")
        )

    except JWTError:
        raise credentials_exception
    
    user = await user_repository.get_user(db, user_id=int(token_data.sub))
    if user is None:
        raise credentials_exception
        
    # Eagerly load the company relationship to ensure company details are available
    if user.company:
        await db.refresh(user, attribute_names=["company"])
        
    return user

async def get_current_super_admin(current_user: user_model.Users = Depends(get_current_user)) -> user_model.Users:
    """
    Dependency to ensure the user is a super admin.
    """
    if current_user.role != 'super_admin':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The user does not have super admin privileges",
        )
    return current_user

async def get_current_company_admin(current_user: user_model.Users = Depends(get_current_user)) -> user_model.Users:
    """
    Dependency to ensure the user is a company admin and the company is approved.
    """
    if not current_user.company or not current_user.company.is_active or not current_user.role == 'admin':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The user does not have admin company privileges",
        )
    return current_user

async def get_current_employee(current_user: user_model.Users = Depends(get_current_user)) -> user_model.Users:
    """
    Dependency to ensure the user is an employee.
    """
    if current_user.role != 'employee':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The user does not have employee privileges",
        )
    return current_user
