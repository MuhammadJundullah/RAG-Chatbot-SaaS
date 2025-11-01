from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import UploadFile, HTTPException, status
from typing import List
import os
import pathlib
import uuid
from botocore.exceptions import ClientError

from app.models.user_model import Users
from app.models.document_model import DocumentStatus
from app.schemas import document_schema
from app.repository.document_repository import document_repository
from app.core.s3_client import s3_client_manager
from app.core.config import settings
from app.services.rag_service import rag_service
from app.tasks.document_tasks import upload_document_to_s3, process_ocr_task, process_embedding_task


async def upload_document_service(
    db: AsyncSession,
    current_user: Users,
    file: UploadFile,
    name: str, # Added name parameter
    tags: List[str] # Added tags parameter
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
        title=name, # Use provided name for title
        company_id=current_user.company_id,
        content_type=file.content_type,
        temp_storage_path=str(temp_file_path),
        tags=tags # Pass tags to the schema
    )
    db_document = await document_repository.create_document(db=db, document=doc_create)
    print(f"[Upload Service] Document {db_document.id} created with temp_storage_path: {db_document.temp_storage_path}")

    upload_document_to_s3.delay(db_document.id)

    return db_document

async def retry_document_upload_service(
    db: AsyncSession,
    current_user: Users,
    document_id: int
):
    db_document = await document_repository.get_document(db, document_id=document_id)

    if not db_document or db_document.company_id != current_user.company_id:
        raise HTTPException(status_code=404, detail="Document not found.")

    if db_document.status != DocumentStatus.UPLOAD_FAILED:
        raise HTTPException(
            status_code=400,
            detail=f"Document is not in a failed upload state. Current status: {db_document.status.value}"
        )
    
    if db_document.s3_path:
        updated_doc = await document_repository.update_document_status_and_reason(
            db, document_id=document_id, status=DocumentStatus.UPLOADED, reason=None
        )
        process_ocr_task.delay(document_id)
        print(f"Document {document_id} has been re-queued for OCR processing (S3 path found).")
        return updated_doc

    if db_document.temp_storage_path and os.path.exists(db_document.temp_storage_path):
        updated_doc = await document_repository.update_document_status_and_reason(
            db, document_id=document_id, status=DocumentStatus.UPLOADING, reason=None
        )
        upload_document_to_s3.delay(document_id)
        print(f"Document {document_id} has been re-queued for S3 upload (temp file found).")
        return updated_doc

    raise HTTPException(
        status_code=400,
        detail="Cannot retry: The temporary file for this document no longer exists and no S3 path was recorded. Document is unrecoverable."
    )

async def get_all_company_documents_service(
    db: AsyncSession,
    current_user: Users,
    skip: int = 0,
    limit: int = 100
):
    documents = await document_repository.get_documents_by_company(
        db, company_id=current_user.company_id, skip=skip, limit=limit
    )
    return documents

async def get_documents_pending_validation_service(
    db: AsyncSession,
    current_user: Users
):
    documents = await document_repository.get_documents_by_status(
        db, status=DocumentStatus.PENDING_VALIDATION, company_id=current_user.company_id
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
    filename: str
):
    db_document = await document_repository.get_document(db, document_id=document_id)
    if not db_document or db_document.company_id != current_user.company_id:
        raise HTTPException(status_code=404, detail="Document not found.")

    await document_repository.update_document_text_and_status(
        db, 
        document_id=document_id, 
        text=new_content, 
        status=DocumentStatus.EMBEDDING
    )

    rag_update_result = await rag_service.update_document_content(
        document_id=str(document_id), 
        new_text_content=new_content,
        company_id=current_user.company_id,
        source_filename=filename 
    )

    if rag_update_result.get("status") == "failed":
        raise HTTPException(status_code=500, detail=f"Failed to update RAG embeddings: {rag_update_result.get('message')}")

    final_updated_doc = await document_repository.update_document_status_and_reason(
        db, document_id=document_id, status=DocumentStatus.COMPLETED
    )

    return final_updated_doc

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

        if db_document.s3_path:
            try:
                s3 = await s3_client_manager.get_client()
                await s3.delete_objects(
                    Bucket=settings.S3_BUCKET_NAME,
                    Delete={
                        "Objects": [
                            {"Key": db_document.s3_path}
                        ]
                    }
                )
            except ClientError as e:
                if e.response['Error']['Code'] not in ['404', 'NoSuchKey']:
                    raise e
                print(f"Warning: S3 object not found during deletion, proceeding. Key: {db_document.s3_path}")

        if db_document.temp_storage_path and os.path.exists(db_document.temp_storage_path):
            print("[Delete Document] Entering temporary file cleanup block.")
            try:
                print(f"[Delete Document] Attempting to remove temporary file: {db_document.temp_storage_path}")
                os.remove(db_document.temp_storage_path)
                print(f"[Delete Document] Removed temporary file: {db_document.temp_storage_path}")
                print(f"[Delete Document] After os.remove: File exists? {os.path.exists(db_document.temp_storage_path)}")
            except OSError as e:
                print(f"[Delete Document] Error: Failed to remove temporary file {db_document.temp_storage_path}: {e}")

        await document_repository.delete_document(db=db, document_id=document_id)

    except Exception as e:
        print(f"[ERROR] Failed to delete document: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to delete document: {str(e)}")

    return None