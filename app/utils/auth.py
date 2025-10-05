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

# OAuth2PasswordBearer for token extraction from the Authorization header
# The tokenUrl should point to the new login endpoint
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token")

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

async def get_current_user(token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(db_manager.get_db_session)) -> schema.User:
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
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        
        # The payload is now just for identification (username), fetch full user data from DB
        token_data = schemas.TokenData(username=username)

    except JWTError:
        raise credentials_exception
    
    user = await crud.get_user_by_username(db, username=token_data.username)
    if user is None:
        raise credentials_exception
        
    return user

# --- Role-based Authorization Dependencies ---

def get_current_company_admin(current_user: schema.User = Depends(get_current_user)) -> schema.User:
    """
    Dependency to ensure the current user is a COMPANY_ADMIN.
    Raises a 403 Forbidden error if the user does not have the correct role.
    """
    if current_user.role != schema.UserRole.COMPANY_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The user does not have enough permissions. Company admin required.",
        )
    return current_user