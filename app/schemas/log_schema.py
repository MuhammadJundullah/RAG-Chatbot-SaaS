from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from .user_schema import User
from .company_schema import Company

class ActivityLogBase(BaseModel):
    activity_type_category: str
    activity_description: str

class ActivityLog(ActivityLogBase):
    id: int
    timestamp: datetime
    user: Optional[User] = None
    company: Optional[Company] = None

    class Config:
        from_attributes = True

class PaginatedActivityLogResponse(BaseModel):
    logs: list[ActivityLog]
    total_pages: int
    current_page: int
    total_logs: int

class CategoryList(BaseModel):
    categories: List[str]

class CategoryListResponse(BaseModel):
    categories: List[str]
