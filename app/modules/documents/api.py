from fastapi import APIRouter, UploadFile, File, Depends, status, Form
from typing import List
from math import ceil
from pydantic import BaseModel

from app.core.dependencies import get_db, get_current_company_admin
from app.models.user_model import Users
from app.schemas import document_schema
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.documents import service as document_service
from app.utils.activity_logger import log_activity
from app.utils.user_identifier import get_user_identifier

router = APIRouter(
    prefix="/documents",
    tags=["Documents"],
)


class DocumentConfirmRequest(BaseModel):
    confirmed_text: str


class PaginatedDocumentsResponse(BaseModel):
    documents: List[document_schema.Document]
    total_pages: int
    current_page: int
    total_documents: int


@router.post("/upload", response_model=document_schema.Document, status_code=status.HTTP_202_ACCEPTED)
async def upload_document(
    file: UploadFile = File(...),
    name: str = Form(...),
    tags: str = Form(default=""),
    current_user: Users = Depends(get_current_company_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Accepts a file, name, and tags, saves it temporarily, creates a DB record with 'UPLOADING' status,
    and triggers a background task to upload to S3.
    """
    tag_list = [tag.strip() for tag in tags.split(',') if tag.strip()]

    uploaded_document = await document_service.upload_document_service(
        db=db,
        current_user=current_user,
        file=file,
        name=name,
        tags=tag_list
    )

    company_id_to_log = current_user.company_id if current_user.company else None
    admin_identifier = get_user_identifier(current_user)
    await log_activity(
        db=db,
        user_id=current_user.id,
        activity_type_category="Proses Dokumen",
        company_id=company_id_to_log,
        activity_description=f"Document '{uploaded_document.title}' uploaded by admin '{admin_identifier}'.",
    )
    return uploaded_document


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

    company_id_to_log = current_user.company_id if current_user.company else None
    admin_identifier = get_user_identifier(current_user)
    await log_activity(
        db=db,
        user_id=current_user.id,
        activity_type_category="Proses Dokumen",
        company_id=company_id_to_log,
        activity_description=f"Document ID {document_id} upload retried by admin '{admin_identifier}'.",
    )
    return retried_document


@router.get("/", response_model=PaginatedDocumentsResponse)
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
    skip_calculated = (page - 1) * limit

    documents, total_count = await document_service.get_all_company_documents_service(
        db=db,
        current_user=current_user,
        skip=skip_calculated,
        limit=limit
    )

    total_pages = ceil(total_count / limit) if limit > 0 else 0

    company_id_to_log = current_user.company_id if current_user.company else None
    admin_identifier = get_user_identifier(current_user)
    await log_activity(
        db=db,
        user_id=current_user.id,
        activity_type_category="Data/CRUD",
        company_id=company_id_to_log,
        activity_description=f"Admin '{admin_identifier}' retrieved list of documents. Found {total_count} documents.",
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
    documents = await document_service.get_documents_pending_validation_service(
        db=db,
        current_user=current_user
    )

    company_id_to_log = current_user.company_id if current_user.company else None
    admin_identifier = get_user_identifier(current_user)
    await log_activity(
        db=db,
        user_id=current_user.id,
        activity_type_category="Proses Dokumen",
        company_id=company_id_to_log,
        activity_description=f"Admin '{admin_identifier}' retrieved list of documents pending validation. Found {len(documents)} documents.",
    )
    return documents


@router.post("/{document_id}/confirm", response_model=document_schema.Document, status_code=status.HTTP_202_ACCEPTED)
async def confirm_document_and_trigger_embedding(
    document_id: int,
    request: DocumentConfirmRequest,
    current_user: Users = Depends(get_current_company_admin),
    db: AsyncSession = Depends(get_db)
):
    confirmed_document = await document_service.confirm_document_and_trigger_embedding_service(
        db=db,
        current_user=current_user,
        document_id=document_id,
        confirmed_text=request.confirmed_text
    )

    company_id_to_log = current_user.company_id if current_user.company else None
    admin_identifier = get_user_identifier(current_user)
    await log_activity(
        db=db,
        user_id=current_user.id,
        activity_type_category="Proses Dokumen",
        company_id=company_id_to_log,
        activity_description=f"Document ID {document_id} confirmed and embedding triggered by admin '{admin_identifier}'.",
    )
    return confirmed_document


@router.post("/{document_id}/retry-processing", response_model=document_schema.Document)
async def retry_failed_document_processing(
    document_id: int,
    current_user: Users = Depends(get_current_company_admin),
    db: AsyncSession = Depends(get_db)
):
    retried_document = await document_service.retry_failed_document_processing_service(
        db=db,
        current_user=current_user,
        document_id=document_id
    )

    company_id_to_log = current_user.company_id if current_user.company else None
    admin_identifier = get_user_identifier(current_user)
    await log_activity(
        db=db,
        user_id=current_user.id,
        activity_type_category="Proses Dokumen",
        company_id=company_id_to_log,
        activity_description=f"Document ID {document_id} processing retried by admin '{admin_identifier}'.",
    )
    return retried_document


@router.put("/{document_id}/content", response_model=document_schema.Document)
async def update_document_content(
    document_id: int,
    request: document_schema.DocumentUpdateContentRequest,
    current_user: Users = Depends(get_current_company_admin),
    db: AsyncSession = Depends(get_db)
):
    updated_document = await document_service.update_document_content_service(
        db=db,
        current_user=current_user,
        document_id=document_id,
        new_content=request.new_content,
        title=request.title,
        tags=request.tags
    )

    company_id_to_log = current_user.company_id if current_user.company else None
    admin_identifier = get_user_identifier(current_user)
    await log_activity(
        db=db,
        user_id=current_user.id,
        activity_type_category="Data/CRUD",
        company_id=company_id_to_log,
        activity_description=f"Document ID {document_id} content updated by admin '{admin_identifier}'.",
    )
    return updated_document


@router.get("/{document_id}", response_model=document_schema.Document)
async def read_single_document(
    document_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Users = Depends(get_current_company_admin)
):
    document = await document_service.read_single_document_service(
        db=db,
        current_user=current_user,
        document_id=document_id
    )

    company_id_to_log = current_user.company_id if current_user.company else None
    admin_identifier = get_user_identifier(current_user)
    await log_activity(
        db=db,
        user_id=current_user.id,
        activity_type_category="Data/CRUD",
        company_id=company_id_to_log,
        activity_description=f"Document ID {document_id} read by admin '{admin_identifier}'.",
    )
    return document


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: int,
    current_user: Users = Depends(get_current_company_admin),
    db: AsyncSession = Depends(get_db)
):
    await document_service.delete_document_service(
        db=db,
        current_user=current_user,
        document_id=document_id
    )

    company_id_to_log = current_user.company_id if current_user.company else None
    admin_identifier = get_user_identifier(current_user)
    await log_activity(
        db=db,
        user_id=current_user.id,
        activity_type_category="Data/CRUD",
        company_id=company_id_to_log,
        activity_description=f"Document ID {document_id} deleted by admin '{admin_identifier}'.",
    )
    return None
