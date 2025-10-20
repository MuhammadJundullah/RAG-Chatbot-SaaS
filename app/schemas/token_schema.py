from pydantic import BaseModel
from typing import List, Optional, Dict, Any

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[str] = None
    role: Optional[str] = None
    company_id: Optional[int] = None
    division_id: Optional[int] = None
