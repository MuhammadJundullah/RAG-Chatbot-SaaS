from pydantic import BaseModel, model_validator
from typing import Optional

class UserBase(BaseModel):
    name: str
    email: Optional[str] = None
    username: Optional[str] = None

class UserRegistration(BaseModel):
    name: str
    email: str
    password: str
    pic_phone_number: Optional[str] = None
    # For new company registration
    company_name: Optional[str] = None
    # For joining an existing company
    company_id: Optional[int] = None

class UserUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    password: Optional[str] = None
    division_id: Optional[int] = None

class User(UserBase):
    id: int
    pic_phone_number: Optional[str] = None
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

class SuperAdminLogin(BaseModel):
    username: str
    password: str

class EmployeeRegistrationByAdmin(BaseModel):
    name: str
    email: str
    password: str
    division_id: Optional[int] = None
