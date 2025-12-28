from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from jose import jwt
from fastapi.security import OAuth2PasswordBearer

from app.core.config import settings

# The tokenUrl should point to the new login endpoint
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/user/token")

# --- JWT Token Management ---

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> Dict[str, Any]:
    """Creates a new JWT access token and returns it along with its expiry."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now() + expires_delta
        expires_in_seconds = int(expires_delta.total_seconds())
    else:
        expire = datetime.now() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        expires_in_seconds = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return {"access_token": encoded_jwt, "expires_in": expires_in_seconds}
