from pydantic import BaseModel
from typing import Optional
from app.schemas import user_schema

class Token(BaseModel):
    access_token: str
    token_type: str
    expires_in: int
    user: user_schema.User

class TokenData(BaseModel):
    sub: Optional[str] = None
    role: Optional[str] = None
    company_id: Optional[int] = None
    division_id: Optional[int] = None
