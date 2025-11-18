from pydantic import BaseModel, model_validator, Field, EmailStr
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
    company_name: Optional[str] = None
    pic_phone_number: Optional[str] = None
    company_id: Optional[int] = None


class EmployeeUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    username: Optional[str] = None  # Fixed: Added username field
    password: Optional[str] = None
    division: Optional[str] = None


class User(UserBase):
    id: int
    role: str
    company_id: Optional[int] = None
    division: Optional[str] = None
    is_active: Optional[bool] = None
    profile_picture_url: Optional[str] = None

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
    new_password: str = Field(..., min_length=8)

# New schema for updating user details
class UserUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None


class PaginatedUserResponse(BaseModel):
    users: list[User]
    total_users: int
    current_page: int
    total_pages: int