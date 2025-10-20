from pydantic import BaseModel
from typing import List, Optional, Dict, Any

class OcrExtractResponse(BaseModel):
    extracted_text: str
    temp_doc_id: str 

class OcrEmbedRequest(BaseModel):
    temp_doc_id: str
    confirmed_text: str
    original_filename: str
