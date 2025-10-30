from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, status
from typing import List
import os
import pathlib
import uuid
from pydantic import BaseModel
from botocore.exceptions import ClientError

from app.core.dependencies import get_current_user, get_db, get_current_company_admin
from app.models.user_model import Users
from app.models.document_model import DocumentStatus
from app.schemas import document_schema
from app.repository import document_repository
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.s3_client import s3_client_manager
from app.core.config import settings
from app.services.rag_service import rag_service
from app.tasks.document_tasks import upload_document_to_s3, process_ocr_task, process_embedding_task

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
    current_user: Users = Depends(get_current_company_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Accepts a file, saves it temporarily, creates a DB record with 'UPLOADING' status,
    and triggers a background task to upload to S3.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file name provided.")

    # Create a temporary directory if it doesn't exist within the project
    temp_dir = pathlib.Path("tmp/smartai_uploads")
    temp_dir.mkdir(parents=True, exist_ok=True)

    # Generate a unique filename to avoid collisions
    safe_filename = "".join(c for c in file.filename if c.isalnum() or c in ('.', '-', '_')).rstrip()
    unique_id = uuid.uuid4()
    temp_file_path = temp_dir / f"{unique_id}-{safe_filename}"

    # Save the file to the temporary location
    try:
        with open(temp_file_path, "wb") as buffer:
            buffer.write(await file.read())
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save temporary file: {e}")

    # Create a document record in the database
    doc_create = document_schema.DocumentCreate(
        title=file.filename,
        company_id=current_user.company_id,
        content_type=file.content_type,
        temp_storage_path=str(temp_file_path)
    )
    db_document = await document_repository.create_document(db=db, document=doc_create)
    print(f"[Upload Endpoint] Document {db_document.id} created with temp_storage_path: {db_document.temp_storage_path}")

    # Trigger the background task for S3 upload
    upload_document_to_s3.delay(db_document.id)

    return db_document

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
    db_document = await document_repository.get_document(db, document_id=document_id)

    if not db_document or db_document.company_id != current_user.company_id:
        raise HTTPException(status_code=404, detail="Document not found.")

    if db_document.status != DocumentStatus.UPLOAD_FAILED:
        raise HTTPException(
            status_code=400,
            detail=f"Document is not in a failed upload state. Current status: {db_document.status.value}"
        )
    
    # Case 1: S3 path exists, meaning upload was successful at some point, proceed to OCR
    if db_document.s3_path:
        updated_doc = await document_repository.update_document_status_and_reason(
            db, document_id=document_id, status=DocumentStatus.UPLOADED, reason=None
        )
        process_ocr_task.delay(document_id)
        print(f"Document {document_id} has been re-queued for OCR processing (S3 path found).")
        return updated_doc

    # Case 2: No S3 path, but temp file exists, retry upload
    if db_document.temp_storage_path and os.path.exists(db_document.temp_storage_path):
        # Reset status to UPLOADING and clear failure reason
        updated_doc = await document_repository.update_document_status_and_reason(
            db, document_id=document_id, status=DocumentStatus.UPLOADING, reason=None
        )
        # Re-queue the upload task
        upload_document_to_s3.delay(document_id)
        print(f"Document {document_id} has been re-queued for S3 upload (temp file found).")
        return updated_doc

    # Case 3: Neither S3 path nor temp file exists, document is unrecoverable
    raise HTTPException(
        status_code=400,
        detail="Cannot retry: The temporary file for this document no longer exists and no S3 path was recorded. Document is unrecoverable."
    )


@router.get("/", response_model=List[document_schema.Document])
async def read_all_company_documents(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user: Users = Depends(get_current_company_admin)
):
    """Gets all documents for the user's company, regardless of status."""
    documents = await document_repository.get_documents_by_company(
        db, company_id=current_user.company_id, skip=skip, limit=limit
    )
    return documents

@router.get("/pending-validation", response_model=List[document_schema.Document])
async def get_documents_pending_validation(
    current_user: Users = Depends(get_current_company_admin),
    db: AsyncSession = Depends(get_db)
):
    """Gets a list of documents that have been OCR'd and are awaiting user validation."""
    documents = await document_repository.get_documents_by_status(
        db, status=DocumentStatus.PENDING_VALIDATION, company_id=current_user.company_id
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
    db_document = await document_repository.get_document(db, document_id=document_id)
    if not db_document or db_document.company_id != current_user.company_id:
        raise HTTPException(status_code=404, detail="Document not found.")
    
    if db_document.status != DocumentStatus.PENDING_VALIDATION:
        raise HTTPException(status_code=400, detail=f"Document is not pending validation. Current status: {db_document.status.value}")

    updated_doc = await document_repository.update_document_text_and_status(
        db, 
        document_id=document_id, 
        text=request.confirmed_text, 
        status=DocumentStatus.EMBEDDING
    )

    process_embedding_task.delay(document_id)

    return updated_doc

@router.post("/{document_id}/retry-processing", response_model=document_schema.Document)
async def retry_failed_document_processing(
    document_id: int,
    current_user: Users = Depends(get_current_company_admin),
    db: AsyncSession = Depends(get_db)
):
    """Manually triggers a retry for a document that failed during OCR or Embedding."""
    db_document = await document_repository.get_document(db, document_id=document_id)

    if not db_document or db_document.company_id != current_user.company_id:
        raise HTTPException(status_code=404, detail="Document not found.")

    if db_document.status != DocumentStatus.PROCESSING_FAILED:
        raise HTTPException(
            status_code=400,
            detail=f"Document is not in a failed processing state. Current status: {db_document.status.value}"
        )

    # Smart retry based on which stage it failed
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

@router.put("/{document_id}/content", response_model=document_schema.Document)
async def update_document_content(
    document_id: int,
    request: document_schema.DocumentUpdateContentRequest,
    current_user: Users = Depends(get_current_company_admin),
    db: AsyncSession = Depends(get_db)
):
    """Updates the text content of an existing document and re-generates its embeddings."""
    db_document = await document_repository.get_document(db, document_id=document_id)
    if not db_document or db_document.company_id != current_user.company_id:
        raise HTTPException(status_code=404, detail="Document not found.")

    await document_repository.update_document_text_and_status(
        db, 
        document_id=document_id, 
        text=request.new_content, 
        status=DocumentStatus.EMBEDDING
    )

    rag_update_result = await rag_service.update_document_content(
        document_id=str(document_id), 
        new_text_content=request.new_content,
        company_id=current_user.company_id,
        source_filename=request.filename 
    )

    if rag_update_result.get("status") == "failed":
        raise HTTPException(status_code=500, detail=f"Failed to update RAG embeddings: {rag_update_result.get('message')}")

    final_updated_doc = await document_repository.update_document_status_and_reason(
        db, document_id=document_id, status=DocumentStatus.COMPLETED
    )

    return final_updated_doc

@router.get("/{document_id}", response_model=document_schema.Document)
async def read_single_document(
    document_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Users = Depends(get_current_user)
):
    """Gets a single document by its ID, checking for appropriate permissions."""
    db_document = await document_repository.get_document(db, document_id=document_id)
    if db_document is None:
        raise HTTPException(status_code=404, detail="Document not found")
    
    if not current_user.is_super_admin and db_document.company_id != current_user.company_id:
        raise HTTPException(status_code=403, detail="You do not have permission to access this document.")
        
    return db_document

@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: int,
    current_user: Users = Depends(get_current_company_admin),
    db: AsyncSession = Depends(get_db)
):
    """Deletes a document from the database, S3, and the RAG service."""
    db_document = await document_repository.get_document(db, document_id=document_id)
    if not db_document or db_document.company_id != current_user.company_id:
        raise HTTPException(status_code=404, detail="Document not found.")

    try:
        await rag_service.delete_document_by_id(
            document_id=str(document_id), 
            company_id=db_document.company_id
        )

        if db_document.s3_path: # Check if s3_path exists
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
                # delete_objects might return errors for individual objects in the 'Errors' list
                # For a single object, a ClientError on the call itself is still relevant.
                if e.response['Error']['Code'] not in ['404', 'NoSuchKey']:
                    raise e
                print(f"Warning: S3 object not found during deletion, proceeding. Key: {db_document.s3_path}")

        # Also ensure the temporary file is deleted if it still exists
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