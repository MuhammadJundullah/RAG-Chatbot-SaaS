from pydantic import BaseModel, model_validator
from typing import Optional

class UserBase(BaseModel):
    name: str
    email: Optional[str] = None
    username: Optional[str] = None

class UserRegistration(BaseModel):
    name: str
    email: str
    username: Optional[str] = None
    password: str
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
    role: str
    company_id: Optional[int] = None
    division_id: Optional[int] = None
    is_active: Optional[bool] = None
    class Config:
        from_attributes = True
        
class AdminCreate(BaseModel):
    name: str
    email: str
    password: str

class UserLoginCombined(BaseModel):
    email: Optional[str] = None
    username: Optional[str] = None
    password: str

    @model_validator(mode='after')
    def check_email_or_username(self) -> 'UserLoginCombined':
        if not self.email and not self.username:
            raise ValueError('Either email or username must be provided')
        if self.email and self.username:
            raise ValueError('Only one of email or username can be provided')
        return self

class EmployeeRegistrationByAdmin(BaseModel):
    name: str
    email: str
    username: str
    password: str
    division_id: Optional[int] = None
