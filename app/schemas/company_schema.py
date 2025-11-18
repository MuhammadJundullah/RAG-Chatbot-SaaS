from pydantic import BaseModel, EmailStr
from typing import Optional

class CompanyBase(BaseModel):
    name: str
    code: str
    logo_s3_path: Optional[str] = None
    address: Optional[str] = None
    is_active: bool = False
    pic_phone_number: Optional[str] = None 
    company_email: Optional[str] = None

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
    admin_email: Optional[EmailStr] = None
    admin_password: Optional[str] = None

class CompanyMeResponse(Company):
    admin_name: str
    admin_email: EmailStr
