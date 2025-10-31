from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, status, Form
from typing import List
from pydantic import BaseModel

from app.core.dependencies import get_current_user, get_db, get_current_company_admin
from app.models.user_model import Users
from app.schemas import document_schema
from sqlalchemy.ext.asyncio import AsyncSession
from app.services import document_service

router = APIRouter(
    prefix="/documents",
    tags=["Documents"],
)

class DocumentConfirmRequest(BaseModel):
    confirmed_text: str

# --- NEW ASYNC UPLOAD ENDPOINT ---
@router.post("/upload", response_model=document_schema.Document, status_code=status.HTTP_202_ACCEPTED)
async def upload_document(
    file: UploadFile = File(...),
    name: str = Form(...), # Added name field
    tags: str = Form(default=""), # Added tags field, default to empty string
    current_user: Users = Depends(get_current_company_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Accepts a file, name, and tags, saves it temporarily, creates a DB record with 'UPLOADING' status,
    and triggers a background task to upload to S3.
    """
    # Parse tags string into a list
    tag_list = [tag.strip() for tag in tags.split(',') if tag.strip()]

    return await document_service.upload_document_service(
        db=db,
        current_user=current_user,
        file=file,
        name=name, # Pass name to service
        tags=tag_list # Pass parsed tags to service
    )

# --- NEW RETRY ENDPOINT ---
@router.put("/{document_id}/retry", response_model=document_schema.Document)
async def retry_document_upload(
    document_id: int,
    current_user: Users = Depends(get_current_company_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Allows retrying the upload process for a document that previously failed to upload.
    """
    return await document_service.retry_document_upload_service(
        db=db,
        current_user=current_user,
        document_id=document_id
    )


@router.get("/", response_model=List[document_schema.Document])
async def read_all_company_documents(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user: Users = Depends(get_current_company_admin)
):
    """Gets all documents for the user's company, regardless of status."""
    return await document_service.get_all_company_documents_service(
        db=db,
        current_user=current_user,
        skip=skip,
        limit=limit
    )

@router.get("/pending-validation", response_model=List[document_schema.Document])
async def get_documents_pending_validation(
    current_user: Users = Depends(get_current_company_admin),
    db: AsyncSession = Depends(get_db)
):
    """Gets a list of documents that have been OCR'd and are awaiting user validation."""
    return await document_service.get_documents_pending_validation_service(
        db=db,
        current_user=current_user
    )

@router.post("/{document_id}/confirm", response_model=document_schema.Document, status_code=status.HTTP_202_ACCEPTED)
async def confirm_document_and_trigger_embedding(
    document_id: int,
    request: DocumentConfirmRequest,
    current_user: Users = Depends(get_current_company_admin),
    db: AsyncSession = Depends(get_db)
):
    """Receives user-confirmed text and triggers the embedding background task."""
    return await document_service.confirm_document_and_trigger_embedding_service(
        db=db,
        current_user=current_user,
        document_id=document_id,
        confirmed_text=request.confirmed_text
    )

@router.post("/{document_id}/retry-processing", response_model=document_schema.Document)
async def retry_failed_document_processing(
    document_id: int,
    current_user: Users = Depends(get_current_company_admin),
    db: AsyncSession = Depends(get_db)
):
    """Manually triggers a retry for a document that failed during OCR or Embedding."""
    return await document_service.retry_failed_document_processing_service(
        db=db,
        current_user=current_user,
        document_id=document_id
    )

@router.put("/{document_id}/content", response_model=document_schema.Document)
async def update_document_content(
    document_id: int,
    request: document_schema.DocumentUpdateContentRequest,
    current_user: Users = Depends(get_current_company_admin),
    db: AsyncSession = Depends(get_db)
):
    """Updates the text content of an existing document and re-generates its embeddings."""
    return await document_service.update_document_content_service(
        db=db,
        current_user=current_user,
        document_id=document_id,
        new_content=request.new_content,
        filename=request.filename
    )

@router.get("/{document_id}", response_model=document_schema.Document)
async def read_single_document(
    document_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Users = Depends(get_current_user)
):
    """Gets a single document by its ID, checking for appropriate permissions."""
    return await document_service.read_single_document_service(
        db=db,
        current_user=current_user,
        document_id=document_id
    )

@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: int,
    current_user: Users = Depends(get_current_company_admin),
    db: AsyncSession = Depends(get_db)
):
    """Deletes a document from the database, S3, and the RAG service."""
    await document_service.delete_document_service(
        db=db,
        current_user=current_user,
        document_id=document_id
    )
    return None