from pydantic import BaseModel
from typing import Optional

class CompanyBase(BaseModel):
    name: str
    code: str
    logo_s3_path: Optional[str] = None
    address: Optional[str] = None
    is_active: bool = False # New field for company active status

class CompanyCreate(CompanyBase):
    pass

class CompanyUpdate(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None
    address: Optional[str] = None
    logo_s3_path: Optional[str] = None
    is_active: Optional[bool] = None # Allow updating active status

class Company(CompanyBase):
    id: int

    class Config:
        from_attributes = True
