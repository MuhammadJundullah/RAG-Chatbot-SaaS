from fastapi import APIRouter, UploadFile, File, Depends, status, Form
from typing import List
from math import ceil
from pydantic import BaseModel
import datetime

from app.core.dependencies import get_db, get_current_company_admin
from app.models.user_model import Users
from app.schemas import document_schema
from sqlalchemy.ext.asyncio import AsyncSession
from app.services import document_service
from app.utils.activity_logger import log_activity

router = APIRouter(
    prefix="/documents",
    tags=["Documents"],
)

class DocumentConfirmRequest(BaseModel):
    confirmed_text: str

# --- New Pydantic model for paginated response ---
class PaginatedDocumentsResponse(BaseModel):
    documents: List[document_schema.Document]
    total_pages: int
    current_page: int
    total_documents: int

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

    uploaded_document = await document_service.upload_document_service(
        db=db,
        current_user=current_user,
        file=file,
        name=name,
        tags=tag_list
    )
    
    # Log document upload
    company_id_to_log = current_user.company_id if current_user.company else None
    await log_activity(
        db=db, # Pass the database session
        user_id=current_user.id, # Use integer user ID
        activity_type_category="Proses Dokumen", # Or "Data/CRUD"
        company_id=company_id_to_log, # Use integer company ID
        activity_description=f"Document '{uploaded_document.title}' uploaded by admin '{current_user.email}'.",
    )
    return uploaded_document

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
    retried_document = await document_service.retry_document_upload_service(
        db=db,
        current_user=current_user,
        document_id=document_id
    )
    
    # Log document upload retry
    company_id_to_log = current_user.company_id if current_user.company else None
    await log_activity(
        db=db, # Pass the database session
        user_id=current_user.id, # Use integer user ID
        activity_type_category="Proses Dokumen", # Or "Data/CRUD"
        company_id=company_id_to_log, # Use integer company ID
        activity_description=f"Document ID {document_id} upload retried by admin '{current_user.email}'.",
    )
    return retried_document


@router.get("/", response_model=PaginatedDocumentsResponse) # Changed response_model
async def read_all_company_documents(
    page: int = 1,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user: Users = Depends(get_current_company_admin)
):
    """
    Gets all documents for the user's company, regardless of status.
    Supports pagination via 'page' (page number) and 'limit' (number of items per page) query parameters.
    Returns a list of documents and pagination details.
    Example: /api/documents/?page=1&limit=20
    """
    # Calculate skip based on page and limit
    skip_calculated = (page - 1) * limit

    # First call: get paginated documents for the current page
    documents, total_count = await document_service.get_all_company_documents_service(
        db=db,
        current_user=current_user,
        skip=skip_calculated,
        limit=limit
    )

    # Calculate total pages
    total_pages = ceil(total_count / limit) if limit > 0 else 0

    # Log document list retrieval
    company_id_to_log = current_user.company_id if current_user.company else None
    await log_activity(
        db=db, # Pass the database session
        user_id=current_user.id, # Use integer user ID
        activity_type_category="Data/CRUD",
        company_id=company_id_to_log, # Use integer company ID
        activity_description=f"Admin '{current_user.email}' retrieved list of documents. Found {total_count} documents.",
    )

    return PaginatedDocumentsResponse(
        documents=documents,
        total_pages=total_pages,
        current_page=page,
        total_documents=total_count
    )

@router.get("/pending-validation", response_model=List[document_schema.Document])
async def get_documents_pending_validation(
    current_user: Users = Depends(get_current_company_admin),
    db: AsyncSession = Depends(get_db)
):
    """Gets a list of documents that have been OCR'd and are awaiting user validation."""
    documents = await document_service.get_documents_pending_validation_service(
        db=db,
        current_user=current_user
    )
    
    # Log document list retrieval
    company_id_to_log = current_user.company_id if current_user.company else None
    await log_activity(
        db=db, # Pass the database session
        user_id=current_user.id, # Use integer user ID
        activity_type_category="Proses Dokumen", # Or "Data/CRUD"
        company_id=company_id_to_log, # Use integer company ID
        activity_description=f"Admin '{current_user.email}' retrieved list of documents pending validation. Found {len(documents)} documents.",
    )
    return documents

@router.post("/{document_id}/confirm", response_model=document_schema.Document, status_code=status.HTTP_202_ACCEPTED)
async def confirm_document_and_trigger_embedding(
    document_id: int,
    request: DocumentConfirmRequest,
    current_user: Users = Depends(get_current_company_admin),
    db: AsyncSession = Depends(get_db)
):
    """Receives user-confirmed text and triggers the embedding background task."""
    confirmed_document = await document_service.confirm_document_and_trigger_embedding_service(
        db=db,
        current_user=current_user,
        document_id=document_id,
        confirmed_text=request.confirmed_text
    )
    
    # Log document confirmation and embedding trigger
    company_id_to_log = current_user.company_id if current_user.company else None
    await log_activity(
        db=db, # Pass the database session
        user_id=current_user.id, # Use integer user ID
        activity_type_category="Proses Dokumen",
        company_id=company_id_to_log, # Use integer company ID
        activity_description=f"Document ID {document_id} confirmed and embedding triggered by admin '{current_user.email}'.",
    )
    return confirmed_document

@router.post("/{document_id}/retry-processing", response_model=document_schema.Document)
async def retry_failed_document_processing(
    document_id: int,
    current_user: Users = Depends(get_current_company_admin),
    db: AsyncSession = Depends(get_db)
):
    """Manually triggers a retry for a document that failed during OCR or Embedding."""
    retried_document = await document_service.retry_failed_document_processing_service(
        db=db,
        current_user=current_user,
        document_id=document_id
    )
    
    # Log document processing retry
    company_id_to_log = current_user.company_id if current_user.company else None
    await log_activity(
        db=db, # Pass the database session
        user_id=current_user.id, # Use integer user ID
        activity_type_category="Proses Dokumen",
        company_id=company_id_to_log, # Use integer company ID
        activity_description=f"Document ID {document_id} processing retried by admin '{current_user.email}'.",
    )
    return retried_document

@router.put("/{document_id}/content", response_model=document_schema.Document)
async def update_document_content(
    document_id: int,
    request: document_schema.DocumentUpdateContentRequest,
    current_user: Users = Depends(get_current_company_admin),
    db: AsyncSession = Depends(get_db)
):
    """Updates the text content, title, and tags of an existing document and re-generates its embeddings."""
    updated_document = await document_service.update_document_content_service(
        db=db,
        current_user=current_user,
        document_id=document_id,
        new_content=request.new_content,
        title=request.title,
        tags=request.tags
    )
    
    # Log document content update
    company_id_to_log = current_user.company_id if current_user.company else None
    await log_activity(
        db=db, # Pass the database session
        user_id=current_user.id, # Use integer user ID
        activity_type_category="Data/CRUD",
        company_id=company_id_to_log, # Use integer company ID
        activity_description=f"Document ID {document_id} content updated by admin '{current_user.email}'.",
    )
    return updated_document

@router.get("/{document_id}", response_model=document_schema.Document)
async def read_single_document(
    document_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Users = Depends(get_current_company_admin)
):
    """Gets a single document by its ID. Accessible only by company administrators."""
    document = await document_service.read_single_document_service(
        db=db,
        current_user=current_user,
        document_id=document_id
    )
    
    # Log document read
    company_id_to_log = current_user.company_id if current_user.company else None
    await log_activity(
        db=db, # Pass the database session
        user_id=current_user.id, # Use integer user ID
        activity_type_category="Data/CRUD",
        company_id=company_id_to_log, # Use integer company ID
        activity_description=f"Document ID {document_id} read by admin '{current_user.email}'.",
    )
    return document

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
    
    # Log document deletion
    company_id_to_log = current_user.company_id if current_user.company else None
    await log_activity(
        db=db, # Pass the database session
        user_id=current_user.id, # Use integer user ID
        activity_type_category="Data/CRUD",
        company_id=company_id_to_log, # Use integer company ID
        activity_description=f"Document ID {document_id} deleted by admin '{current_user.email}'.",
    )
    return None