from pydantic import BaseModel, Field, field_validator
from typing import List, Optional, Dict, Any
from app.database.schema import UserRole

# --- Token Models ---

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None
    role: Optional[UserRole] = None
    company_id: Optional[int] = None
    division_id: Optional[int] = None

# --- User & Auth Models ---

class UserBase(BaseModel):
    username: str

class UserCreate(UserBase):
    password: str
    
    @field_validator('password')
    @classmethod
    def validate_password_length(cls, v):
        if len(v.encode('utf-8')) > 200:  
            raise ValueError('Password is too long (max 200 bytes)')
        return v

class EmployeeCreate(UserCreate):
    company_code: str
    company_secret: str
    division_id: Optional[int] = None 

class UserInDB(UserBase):
    id: int
    hashed_password: str
    role: UserRole
    is_active: bool
    company_id: int
    division_id: Optional[int] = None

    class Config:
        from_attributes = True

class UserPublic(UserBase):
    id: int
    role: UserRole
    is_active: bool
    company_id: int
    division_id: Optional[int] = None

    class Config:
        from_attributes = True

# --- Division Models ---

class DivisionBase(BaseModel):
    name: str

class DivisionCreate(DivisionBase):
    pass

class DivisionUpdate(BaseModel):
    name: Optional[str] = None

class DivisionPublic(DivisionBase):
    id: int
    company_id: int

    class Config:
        from_attributes = True

# --- Company Models ---

class CompanyBase(BaseModel):
    name: str

class CompanyCreate(CompanyBase):
    admin_username: str
    admin_password: str = Field(..., min_length=8)
    
    @field_validator('admin_password')
    @classmethod
    def validate_password_length(cls, v):
        if len(v.encode('utf-8')) > 200: 
            raise ValueError('Password is too long (max 200 bytes)')
        return v

class CompanyPublic(CompanyBase):
    id: int
    company_code: str

    class Config:
        from_attributes = True

class CompanyWithDivisions(CompanyPublic):
    divisions: List[DivisionPublic] = []

class CompanyRegistrationResponse(CompanyPublic):
    company_secret_one_time: str


# --- Dynamic Database Models ---
class DBConnectionStringCreate(BaseModel):
    db_url: str

class DBConnectionStatus(BaseModel):
    is_configured: bool
    db_host: Optional[str] = None


# --- Chat Models ---

class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None

class ChatResponse(BaseModel):
    reply: str
    conversation_id: str
    sources: Optional[List[str]] = None
    used_database: bool = False

# --- RAG/Document Models ---
class DocumentUploadResponse(BaseModel):
    status: str
    message: str
    chunks_added: Optional[int] = None

class DocumentDeleteResponse(BaseModel):
    status: str
    message: str
    chunks_deleted: Optional[int] = None

# --- Query Service Models ---
class SQLQueryResult(BaseModel):
    success: bool
    data: Optional[List[Dict[str, Any]]] = None
    error: Optional[str] = None
    query: Optional[str] = None