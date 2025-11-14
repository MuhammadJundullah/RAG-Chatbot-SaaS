from pydantic import BaseModel, model_validator, Field, EmailStr # Import Field and EmailStr
from typing import Optional

class UserBase(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    username: Optional[str] = None

class UserRegistration(BaseModel):
    name: str
    email: str
    username: Optional[str] = None
    password: str
    # For new company registration
    company_name: Optional[str] = None
    pic_phone_number: Optional[str] = None
    # For joining an existing company
    company_id: Optional[int] = None

class EmployeeUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    password: Optional[str] = None
    division: Optional[str] = None

class User(UserBase):
    id: int
    role: str
    company_id: Optional[int] = None
    division: Optional[str] = None
    is_active: Optional[bool] = None
    profile_picture_url: Optional[str] = None # Added for profile picture URL

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
    division: Optional[str] = None

# New schema for password reset request
class PasswordResetRequest(BaseModel):
    email: EmailStr
    token: str
    new_password: str = Field(..., min_length=8) # Enforce minimum password length

class PaginatedUserResponse(BaseModel):
    users: list[User]
    total: int
    page: int
    limit: int