from pydantic import BaseModel
from typing import List, Optional, Dict, Any

class EmbeddingBase(BaseModel):
    vector_id: str
    DocumentsId: int

class EmbeddingCreate(EmbeddingBase):
    pass

class Embedding(EmbeddingBase):
    id: int

    class Config:
        from_attributes = True
