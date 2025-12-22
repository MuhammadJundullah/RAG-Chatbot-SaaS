from pydantic import BaseModel, EmailStr, field_validator
from typing import Optional, List
from datetime import datetime

from app.utils.url_builder import add_app_base_url
class CompanyBase(BaseModel):
    name: str
    code: str
    logo_s3_path: Optional[str] = None
    address: Optional[str] = None
    is_active: bool = False
    pic_phone_number: Optional[str] = None 
    company_email: Optional[str] = None
    created_at: Optional[datetime] = None

    @field_validator("logo_s3_path", mode="before")
    @classmethod
    def build_logo_url(cls, value: Optional[str]) -> Optional[str]:
        return add_app_base_url(value)

class CompanyCreate(CompanyBase):
    pass

class CompanyUpdate(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None
    address: Optional[str] = None
    logo_s3_path: Optional[str] = None
    is_active: Optional[bool] = None 
    pic_phone_number: Optional[str] = None 

class Company(CompanyBase):
    id: int

    class Config:
        from_attributes = True

class CompanyUpdateMe(BaseModel):
    name: Optional[str] = None
    company_email: Optional[EmailStr] = None
    admin_name: Optional[str] = None
    admin_password: Optional[str] = None

class CompanyMeResponse(Company):
    admin_name: str

class PaginatedCompanyResponse(BaseModel):
    companies: List[Company]
    total_company: int
    current_page: int
    total_pages: int


class CompanyAdminSummary(BaseModel):
    id: int
    name: Optional[str] = None
    username: Optional[str] = None
    role: Optional[str] = None
    company_id: Optional[int] = None
    is_active: Optional[bool] = None

    class Config:
        from_attributes = True


class CompanySuperadminUpdate(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None
    address: Optional[str] = None
    company_email: Optional[EmailStr] = None
    pic_phone_number: Optional[str] = None
    is_active: Optional[bool] = None
    admin_name: Optional[str] = None
    admin_password: Optional[str] = None


class CompanySuperadminCreate(BaseModel):
    name: str
    company_email: EmailStr
    admin_name: str
    admin_password: str
    code: Optional[str] = None
    address: Optional[str] = None
    pic_phone_number: Optional[str] = None
    is_active: bool = True


class CompanyDetailWithAdmins(Company):
    admins: List[CompanyAdminSummary] = []

    class Config:
        from_attributes = True


class CompanyStatusUpdate(BaseModel):
    is_active: bool
