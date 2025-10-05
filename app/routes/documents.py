from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from typing import List
import urllib.parse

from app.services.rag_service import rag_service
from app.utils.auth import get_current_company_admin
from app.database.schema import User
from app.models import schemas

router = APIRouter()

@router.post(
    "/documents/upload", 
    response_model=schemas.DocumentUploadResponse,
    tags=["Documents"]
)
async def upload_document(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_company_admin)
):
    """
    Uploads a document (e.g., PDF) to the company's RAG knowledge base.
    This endpoint requires COMPANY_ADMIN authentication.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file name provided.")

    try:
        file_content = await file.read()
        result = await rag_service.process_and_add_document(
            file_content=file_content, 
            file_name=file.filename,
            company_id=current_user.company_id
        )
        
        if result["status"] == "failed":
            raise HTTPException(status_code=400, detail=result["message"])
            
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process document: {str(e)}")

@router.get(
    "/documents",
    response_model=List[str],
    tags=["Documents"]
)
async def list_uploaded_documents(
    current_user: User = Depends(get_current_company_admin)
):
    """
    Lists all unique document filenames that have been uploaded for the company.
    Requires COMPANY_ADMIN authentication.
    """
    documents = await rag_service.list_documents(company_id=current_user.company_id)
    return documents

@router.delete(
    "/documents/{filename}",
    response_model=schemas.DocumentDeleteResponse,
    tags=["Documents"]
)
async def delete_document(
    filename: str,
    current_user: User = Depends(get_current_company_admin)
):
    """
    Deletes a document and all its associated chunks from the RAG knowledge base.
    The filename must be URL-encoded if it contains special characters.
    Requires COMPANY_ADMIN authentication.
    """
    decoded_filename = urllib.parse.unquote(filename)
    
    try:
        result = await rag_service.delete_document(
            company_id=current_user.company_id,
            filename=decoded_filename
        )
        if result["status"] == "not_found":
            raise HTTPException(status_code=404, detail=result["message"])
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete document: {str(e)}")
