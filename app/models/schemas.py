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

# --- User Models ---

class UserBase(BaseModel):
    name: str
    email: str

class UserRegistration(BaseModel):
    name: str
    email: str
    password: str
    # For new company registration
    company_name: Optional[str] = None
    company_code: Optional[str] = None
    # For joining an existing company
    company_id: Optional[int] = None

class UserUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    password: Optional[str] = None
    division_id: Optional[int] = None

class User(UserBase):
    id: int
    is_super_admin: bool
    is_active_in_company: bool
    role: str
    company_id: Optional[int] = None
    class Config:
        from_attributes = True
        
# --- Division Models ---

class DivisionBase(BaseModel):
    name: str
    company_id: int

class DivisionCreate(DivisionBase):
    pass

class Division(DivisionBase):
    id: int

    class Config:
        from_attributes = True


class AdminCreate(BaseModel):
    name: str
    email: str
    password: str


# --- Document Models ---

class DocumentBase(BaseModel):
    title: str
    isi_dokumen: str
    company_id: int



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
    company_id: int

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

class UserLogin(BaseModel):
    email: str
    password: str

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