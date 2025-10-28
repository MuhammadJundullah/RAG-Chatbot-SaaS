from pydantic import BaseModel

class DivisionBase(BaseModel):
    name: str
    company_id: int

class DivisionCreate(DivisionBase):
    pass

class Division(DivisionBase):
    id: int

    class Config:
        from_attributes = True
