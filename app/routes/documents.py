from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from typing import List
import urllib.parse

from app.services.rag_service import rag_service
from app.utils.auth import get_current_user
from app.database.schema import Users
from app.models import schemas
from app import crud
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.connection import db_manager

router = APIRouter(
    prefix="/documents",
    tags=["Documents"],
)

# --- RAG Document Management ---

@router.post(
    "/upload", 
    response_model=schemas.DocumentUploadResponse,
)
async def upload_document_to_rag(
    file: UploadFile = File(...),
    current_user: Users = Depends(get_current_user)
):
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
    "/",
    response_model=List[str],
)
async def list_rag_documents(
    current_user: Users = Depends(get_current_user)
):
    documents = await rag_service.list_documents(company_id=current_user.company_id)
    return documents

@router.delete(
    "/{filename}",
    response_model=schemas.DocumentDeleteResponse,
)
async def delete_rag_document(
    filename: str,
    current_user: Users = Depends(get_current_user),
    db: AsyncSession = Depends(db_manager.get_db_session)
):
    decoded_filename = urllib.parse.unquote(filename)
    
    try:
        # 1. Delete from RAG service (Pinecone)
        rag_result = await rag_service.delete_document(
            company_id=current_user.company_id,
            filename=decoded_filename
        )

        # 2. Delete from relational database
        db_document_result = await db.execute(
            select(schema.Documents).filter(
                schema.Documents.title == decoded_filename,
                schema.Documents.company_id == current_user.company_id
            )
        )
        db_document = db_document_result.scalar_one_or_none()

        if db_document:
            await crud.delete_document(db=db, document=db_document)

        if rag_result["status"] == "not_found" and not db_document:
            raise HTTPException(status_code=404, detail="Document not found in RAG or database.")
        
        return {"status": "success", "message": f"Document '{decoded_filename}' deleted successfully."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete document: {str(e)}")

# --- Database Document CRUD ---



@router.get("/db", response_model=List[schemas.Document])
async def read_documents(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(db_manager.get_db_session),
    current_user: Users = Depends(get_current_user)
):
    documents = await crud.get_documents(db, skip=skip, limit=limit)
    company_documents = [doc for doc in documents if doc.company_id == current_user.company_id]
    return company_documents

@router.get("/{document_id}/db", response_model=schemas.Document)
async def read_document(
    document_id: int,
    db: AsyncSession = Depends(db_manager.get_db_session),
    current_user: Users = Depends(get_current_user)
):
    db_document = await crud.get_document(db, document_id=document_id)
    if db_document is None:
        raise HTTPException(status_code=404, detail="Document not found")
    if db_document.company_id != current_user.company_id:
        raise HTTPException(status_code=403, detail="You do not have permission to access this document.")
    return db_document