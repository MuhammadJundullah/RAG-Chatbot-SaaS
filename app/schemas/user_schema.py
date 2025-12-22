from pydantic import BaseModel, model_validator, Field, EmailStr
from typing import Optional


class UserBase(BaseModel):
    name: Optional[str] = None
    username: Optional[str] = None


class UserRegistration(BaseModel):
    name: str
    email: EmailStr  # digunakan sebagai company_email
    username: Optional[str] = None
    password: str
    company_name: str
    # gunakan field email untuk company_email agar form tetap satu input
    company_email: Optional[EmailStr] = None
    pic_phone_number: Optional[str] = None
    company_id: Optional[int] = None


class EmployeeUpdate(BaseModel):
    name: Optional[str] = None
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
        

class UserLoginCombined(BaseModel):
    # Login: company admin pakai email perusahaan, superadmin/employee pakai username
    email: Optional[EmailStr] = None
    username: Optional[str] = None
    password: str

    @model_validator(mode="after")
    def validate_identifier(self):
        if not self.email and not self.username:
            raise ValueError("Either email or username must be provided.")
        if self.email and self.username:
            raise ValueError("Provide only one of email or username.")
        return self


class EmployeeRegistrationByAdmin(BaseModel):
    name: str
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
    username: Optional[str] = None
    password: Optional[str] = None


class PaginatedUserResponse(BaseModel):
    users: list[User]
    total_users: int
    current_page: int
    total_pages: int


class AdminSuperadminUpdate(BaseModel):
    name: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
