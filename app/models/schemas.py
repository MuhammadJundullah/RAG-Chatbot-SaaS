from pydantic import BaseModel
from typing import List, Optional, Dict, Any

# --- Company Models ---

class CompanyBase(BaseModel):
    name: str
    code: str
    logo: Optional[str] = None

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


class CompanyAdminCreate(BaseModel):
    company_name: str
    company_code: str
    company_logo: Optional[str] = None
    admin_name: str
    admin_email: str
    admin_password: str

# --- Division Models ---

class DivisionBase(BaseModel):
    name: str
    Companyid: int

class DivisionCreate(DivisionBase):
    pass

class Division(DivisionBase):
    id: int

    class Config:
        from_attributes = True

# --- User Models ---

class UserBase(BaseModel):
    name: str
    email: str
    status: Optional[str] = None

class UserCreate(UserBase):
    password: str
    role: str  # 'admin' or 'employee'
    Companyid: int
    Divisionid: Optional[int] = None

class UserUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    password: Optional[str] = None
    status: Optional[str] = None
    Divisionid: Optional[int] = None

class User(UserBase):
    id: int
    role: str
    Companyid: int
    Divisionid: Optional[int] = None

    class Config:
        from_attributes = True

# --- Document Models ---

class DocumentBase(BaseModel):
    title: str
    isi_dokumen: str
    Companyid: int



class DocumentUpdate(BaseModel):
    title: Optional[str] = None
    isi_dokumen: Optional[str] = None

class Document(DocumentBase):
    id: int

    class Config:
        from_attributes = True

# --- Chatlog Models ---

class ChatlogBase(BaseModel):
    question: str
    answer: str
    UsersId: int
    Companyid: int

class ChatlogCreate(ChatlogBase):
    pass

class Chatlog(ChatlogBase):
    id: int

    class Config:
        from_attributes = True

# --- Embedding Models ---

class EmbeddingBase(BaseModel):
    vector_id: str
    DocumentsId: int

class EmbeddingCreate(EmbeddingBase):
    pass

class Embedding(EmbeddingBase):
    id: int

    class Config:
        from_attributes = True

# --- Token Models ---

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[str] = None
    role: Optional[str] = None
    company_id: Optional[int] = None
    division_id: Optional[int] = None

# --- Chat Models ---

class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None

class ChatResponse(BaseModel):
    reply: str
    conversation_id: str

# --- SQL Query Models ---
class SQLQueryResult(BaseModel):
    success: bool
    data: Optional[List[Dict[str, Any]]] = None
    error: Optional[str] = None
    query: Optional[str] = None

# --- RAG/Document Models ---
class DocumentUploadResponse(BaseModel):
    status: str
    message: str
    chunks_added: Optional[int] = None

class DocumentDeleteResponse(BaseModel):
    status: str
    message: str
    chunks_deleted: Optional[int] = None