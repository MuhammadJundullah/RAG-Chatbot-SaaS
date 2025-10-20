from pydantic import BaseModel
from typing import List, Optional, Dict, Any

class UserBase(BaseModel):
    name: str
    email: str

class UserRegistration(BaseModel):
    name: str
    email: str
    password: str
    # For new company registration
    company_name: Optional[str] = None
    company_code: Optional[str] = None
    # For joining an existing company
    company_id: Optional[int] = None

class UserUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    password: Optional[str] = None
    division_id: Optional[int] = None

class User(UserBase):
    id: int
    is_super_admin: bool
    is_active_in_company: bool
    role: str
    company_id: Optional[int] = None
    class Config:
        from_attributes = True
        
class AdminCreate(BaseModel):
    name: str
    email: str
    password: str

class UserLogin(BaseModel):
    email: str
    password: str
