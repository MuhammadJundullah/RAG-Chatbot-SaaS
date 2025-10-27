from pydantic import BaseModel
from typing import List, Optional, Dict, Any

class CompanyBase(BaseModel):
    name: str
    code: str
    logo: Optional[str] = None
    address: Optional[str] = None

class CompanyCreate(CompanyBase):
    pass

class CompanyUpdate(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None
    logo: Optional[str] = None

class Company(CompanyBase):
    id: int

    class Config:
        from_attributes = True
