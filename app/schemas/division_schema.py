from pydantic import BaseModel
from typing import List, Optional, Dict, Any

class DivisionBase(BaseModel):
    name: str
    company_id: int

class DivisionCreate(DivisionBase):
    pass

class Division(DivisionBase):
    id: int

    class Config:
        from_attributes = True
