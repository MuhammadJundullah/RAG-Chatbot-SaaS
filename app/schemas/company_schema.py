from pydantic import BaseModel, EmailStr, Field, AliasChoices, field_validator
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
    logo_s3_path: Optional[str] = None
    admin_name: Optional[str] = None
    admin_password: Optional[str] = None


class CompanySuperadminCreate(BaseModel):
    name: str
    company_email: EmailStr
    admin_name: str
    password: str
    code: Optional[str] = None
    address: Optional[str] = None
    pic_phone_number: Optional[str] = None
    is_active: bool = True


class CompanyDetailWithAdmins(Company):
    admins: List[CompanyAdminSummary] = []

    class Config:
        from_attributes = True


class CompanyWithAdmins(Company):
    admins: List[CompanyAdminSummary] = []

    class Config:
        from_attributes = True


class PaginatedCompanyWithAdminsResponse(BaseModel):
    companies: List[CompanyWithAdmins]
    total_company: int
    current_page: int
    total_pages: int


class CompanyAdminListItem(BaseModel):
    company_id: int
    company_name: str
    admin_id: Optional[int] = None
    admin_name: Optional[str] = None
    admin_username: Optional[str] = None


class CompanyUserListItem(BaseModel):
    company_id: Optional[int] = None
    company_name: Optional[str] = None
    company_email: Optional[str] = None
    company_code: Optional[str] = None
    company_logo_s3_path: Optional[str] = None
    company_is_active: Optional[bool] = None
    company_address: Optional[str] = None
    company_pic_phone_number: Optional[str] = None
    company_created_at: Optional[datetime] = None
    subscription_plan: Optional[str] = None
    admin_name: Optional[str] = None
    admin_profile_picture_url: Optional[str] = None

    @field_validator("company_logo_s3_path", mode="before")
    @classmethod
    def build_company_logo_url(cls, value: Optional[str]) -> Optional[str]:
        return add_app_base_url(value)

    @field_validator("admin_profile_picture_url", mode="before")
    @classmethod
    def build_user_profile_picture_url(cls, value: Optional[str]) -> Optional[str]:
        return add_app_base_url(value)


class PaginatedCompanyUserListResponse(BaseModel):
    companies: List[CompanyUserListItem]
    total_company: int
    current_page: int
    total_page: int


class CompanyAdminUpdatePayload(BaseModel):
    company_id: Optional[int] = None
    company_name: Optional[str] = None
    company_email: Optional[EmailStr] = None
    company_code: Optional[str] = None
    company_logo_s3_path: Optional[str] = None
    company_is_active: Optional[bool] = None
    company_activation_email_sent: Optional[bool] = None
    company_address: Optional[str] = None
    company_pic_phone_number: Optional[str] = None
    company_created_at: Optional[datetime] = None
    admin_name: Optional[str] = None
    admin_profile_picture_url: Optional[str] = None


class CompanyStatusUpdate(BaseModel):
    is_active: bool
