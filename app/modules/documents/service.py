from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import UploadFile, HTTPException
from typing import List, Optional
import os
import pathlib
import uuid
from botocore.exceptions import ClientError

from app.models.user_model import Users
from app.models.document_model import DocumentStatus
from app.schemas import document_schema
from app.repository.document_repository import document_repository
from app.core.config import settings
from app.services.rag_service import rag_service
from app.tasks.document_tasks import process_ocr_task, process_embedding_task
from app.utils.activity_logger import log_activity


async def upload_document_service(
    db: AsyncSession,
    current_user: Users,
    file: UploadFile,
    name: str,
    tags: List[str]
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file name provided.")

    temp_dir = pathlib.Path("tmp/smartai_uploads")
    temp_dir.mkdir(parents=True, exist_ok=True)

    safe_filename = "".join(c for c in file.filename if c.isalnum() or c in ('.', '-', '_')).rstrip()
    unique_id = uuid.uuid4()
    temp_file_path = temp_dir / f"{unique_id}-{safe_filename}"

    try:
        with open(temp_file_path, "wb") as buffer:
            buffer.write(await file.read())
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save temporary file: {e}")

    doc_create = document_schema.DocumentCreate(
        title=name,
        company_id=current_user.company_id,
        content_type=file.content_type,
        temp_storage_path=str(temp_file_path),
        tags=tags
    )
    db_document = await document_repository.create_document(db=db, document=doc_create)

    db_document = await document_repository.update_document_status_and_reason(
        db, document_id=db_document.id, status=DocumentStatus.UPLOADED
    )

    company_id_to_log = current_user.company_id if current_user.company else None
    await log_activity(
        db=db,
        user_id=current_user.id,
        activity_type_category="Proses Dokumen",
        company_id=company_id_to_log,
        activity_description=f"Document '{db_document.title}' (ID: {db_document.id}) uploaded by admin '{current_user.email}'.",
    )

    process_ocr_task.delay(db_document.id)

    return db_document


async def retry_document_upload_service(
    db: AsyncSession,
    current_user: Users,
    document_id: int
):
    db_document = await document_repository.get_document(db, document_id=document_id)

    if not db_document or db_document.company_id != current_user.company_id:
        raise HTTPException(status_code=404, detail="Document not found.")

    if db_document.temp_storage_path and os.path.exists(db_document.temp_storage_path):
        updated_doc = await document_repository.update_document_status_and_reason(
            db, document_id=document_id, status=DocumentStatus.UPLOADED, reason=None
        )

        company_id_to_log = current_user.company_id if current_user.company else None
        await log_activity(
            db=db,
            user_id=current_user.id,
            activity_type_category="Proses Dokumen",
            company_id=company_id_to_log,
            activity_description=f"Document ID {document_id} processing retried by admin '{current_user.email}'.",
        )
        process_ocr_task.delay(document_id)
        return updated_doc

    raise HTTPException(
        status_code=400,
        detail="Cannot retry: The temporary file for this document no longer exists. Document is unrecoverable."
    )


async def get_all_company_documents_service(
    db: AsyncSession,
    current_user: Users,
    skip: int = 0,
    limit: int = 100
):
    documents, total_count = await document_repository.get_documents_by_company(
        db, company_id=current_user.company_id, skip=skip, limit=limit
    )

    company_id_to_log = current_user.company_id if current_user.company else None
    await log_activity(
        db=db,
        user_id=current_user.id,
        activity_type_category="Data/CRUD",
        company_id=company_id_to_log,
        activity_description=f"Admin '{current_user.email}' retrieved list of all company documents. Found {total_count} documents.",
    )
    return documents, total_count


async def get_documents_pending_validation_service(
    db: AsyncSession,
    current_user: Users
):
    documents = await document_repository.get_documents_by_status(
        db, status=DocumentStatus.PENDING_VALIDATION, company_id=current_user.company_id
    )

    company_id_to_log = current_user.company_id if current_user.company else None
    await log_activity(
        db=db,
        user_id=current_user.id,
        activity_type_category="Proses Dokumen",
        company_id=company_id_to_log,
        activity_description=f"Admin '{current_user.email}' retrieved list of documents pending validation. Found {len(documents)} documents.",
    )
    return documents


async def confirm_document_and_trigger_embedding_service(
    db: AsyncSession,
    current_user: Users,
    document_id: int,
    confirmed_text: str
):
    db_document = await document_repository.get_document(db, document_id=document_id)
    if not db_document or db_document.company_id != current_user.company_id:
        raise HTTPException(status_code=404, detail="Document not found.")

    if db_document.status != DocumentStatus.PENDING_VALIDATION:
        raise HTTPException(status_code=400, detail=f"Document is not pending validation. Current status: {db_document.status.value}")

    updated_doc = await document_repository.update_document_text_and_status(
        db,
        document_id=document_id,
        text=confirmed_text,
        status=DocumentStatus.EMBEDDING
    )

    process_embedding_task.delay(document_id)

    return updated_doc


async def retry_failed_document_processing_service(
    db: AsyncSession,
    current_user: Users,
    document_id: int
):
    db_document = await document_repository.get_document(db, document_id=document_id)

    if not db_document or db_document.company_id != current_user.company_id:
        raise HTTPException(status_code=404, detail="Document not found.")

    if db_document.status != DocumentStatus.PROCESSING_FAILED:
        raise HTTPException(
            status_code=400,
            detail=f"Document is not in a failed processing state. Current status: {db_document.status.value}"
        )

    if db_document.failed_reason and "OCR" in db_document.failed_reason:
        updated_doc = await document_repository.update_document_status_and_reason(
            db, document_id=document_id, status=DocumentStatus.UPLOADED, reason=None
        )
        process_ocr_task.delay(document_id)
        print(f"Document {document_id} has been re-queued for OCR processing.")
    elif db_document.failed_reason and "Embedding" in db_document.failed_reason:
        updated_doc = await document_repository.update_document_status_and_reason(
            db, document_id=document_id, status=DocumentStatus.PENDING_VALIDATION, reason=None
        )
        process_embedding_task.delay(document_id)
        print(f"Document {document_id} has been re-queued for embedding.")
    else:
        raise HTTPException(status_code=400, detail="Unknown failure reason, cannot determine retry step.")

    return updated_doc


async def update_document_content_service(
    db: AsyncSession,
    current_user: Users,
    document_id: int,
    new_content: str,
    title: Optional[str] = None,
    tags: Optional[List[str]] = None
):
    db_document = await document_repository.get_document(db, document_id=document_id)
    if not db_document or db_document.company_id != current_user.company_id:
        raise HTTPException(status_code=404, detail="Document not found.")

    updated_doc_repo = await document_repository.update_document_text_and_status(
        db,
        document_id=document_id,
        text=new_content,
        status=DocumentStatus.EMBEDDING,
        tags=tags,
        title=title
    )

    process_embedding_task.delay(document_id)
    print(f"[Service] Queued embedding task for document ID: {document_id}")

    company_id_to_log = current_user.company_id if current_user.company else None
    await log_activity(
        db=db,
        user_id=current_user.id,
        activity_type_category="Data/CRUD",
        company_id=company_id_to_log,
        activity_description=f"Document ID {document_id} content updated by admin '{current_user.email}'.",
    )

    return updated_doc_repo


async def read_single_document_service(
    db: AsyncSession,
    current_user: Users,
    document_id: int
):
    db_document = await document_repository.get_document(db, document_id=document_id)
    if db_document is None:
        raise HTTPException(status_code=404, detail="Document not found")

    if db_document.company_id != current_user.company_id:
        raise HTTPException(status_code=403, detail="You do not have permission to access this document.")

    company_id_to_log = current_user.company_id if current_user.company else None
    await log_activity(
        db=db,
        user_id=current_user.id,
        activity_type_category="Data/CRUD",
        company_id=company_id_to_log,
        activity_description=f"Document ID {document_id} read by admin '{current_user.email}'.",
    )

    return db_document


async def delete_document_service(
    db: AsyncSession,
    current_user: Users,
    document_id: int
):
    db_document = await document_repository.get_document(db, document_id=document_id)
    if not db_document or db_document.company_id != current_user.company_id:
        raise HTTPException(status_code=404, detail="Document not found.")

    try:
        await rag_service.delete_document_by_id(
            document_id=str(document_id),
            company_id=db_document.company_id
        )

        if db_document.temp_storage_path and os.path.exists(db_document.temp_storage_path):
            try:
                os.remove(db_document.temp_storage_path)
                print(f"[Delete Document] Removed temporary file: {db_document.temp_storage_path}")
            except OSError as e:
                print(f"[Delete Document] Error: Failed to remove temporary file {db_document.temp_storage_path}: {e}")

        await document_repository.delete_document(db=db, document_id=document_id)

        company_id_to_log = current_user.company_id if current_user.company else None
        await log_activity(
            db=db,
            user_id=current_user.id,
            activity_type_category="Data/CRUD",
            company_id=company_id_to_log,
            activity_description=f"Document ID {document_id} deleted by admin '{current_user.email}'."
        )

        return None

    except Exception as e:
        print(f"[ERROR] Failed to delete document: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to delete document: {str(e)}")
