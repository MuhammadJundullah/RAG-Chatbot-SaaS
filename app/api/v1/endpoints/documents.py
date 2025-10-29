from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, status
from typing import List
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
from app.tasks.document_tasks import process_ocr_task, process_embedding_task

router = APIRouter(
    prefix="/documents",
    tags=["Documents"],
)

class DocumentConfirmRequest(BaseModel):
    confirmed_text: str


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


@router.post("/upload", response_model=document_schema.Document, status_code=status.HTTP_202_ACCEPTED)
async def upload_document(
    file: UploadFile = File(...),
    current_user: Users = Depends(get_current_company_admin),
    db: AsyncSession = Depends(get_db)
):
    """Accepts a file, uploads it to S3, creates a DB record, and triggers an OCR task."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file name provided.")

    file_content = await file.read()
    safe_filename = "".join(c for c in file.filename if c.isalnum() or c in ('.', '-', '_')).rstrip()
    s3_key = f"smartai/uploads/{current_user.company_id}/{uuid.uuid4()}-{safe_filename}"

    try:
        s3 = await s3_client_manager.get_client()
        await s3.put_object(
            Bucket=settings.S3_BUCKET_NAME,
            Key=s3_key,
            Body=file_content
        )
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to upload file to storage.")

    doc_create = document_schema.DocumentCreate(
        title=file.filename,
        storage_path=s3_key,
        company_id=current_user.company_id,
        content_type=file.content_type
    )
    db_document = await document_repository.create_document(db=db, document=doc_create)

    process_ocr_task.delay(db_document.id)

    return db_document

@router.get("/pending-validation", response_model=List[document_schema.Document])
async def get_documents_pending_validation(
    current_user: Users = Depends(get_current_company_admin),
    db: AsyncSession = Depends(get_db)
):
    """Gets a list of documents that have been OCR'd and are awaiting user validation."""
    documents = await document_repository.get_documents_by_status(
        db, status="PENDING_VALIDATION", company_id=current_user.company_id
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
        status="EMBEDDING"
    )

    process_embedding_task.delay(document_id)

    return updated_doc

@router.get("/failed", response_model=List[document_schema.Document])
async def get_failed_documents(
    current_user: Users = Depends(get_current_company_admin),
    db: AsyncSession = Depends(get_db)
):
    """Gets a list of documents that failed during processing."""
    documents = await document_repository.get_documents_by_status(
        db, status="PROCESSING_FAILED", company_id=current_user.company_id
    )
    return documents

@router.post("/{document_id}/retry", response_model=document_schema.Document)
async def retry_failed_document_processing(
    document_id: int,
    current_user: Users = Depends(get_current_company_admin),
    db: AsyncSession = Depends(get_db)
):
    """Manually triggers a retry for a document that failed during processing."""
    db_document = await document_repository.get_document(db, document_id=document_id)

    if not db_document or db_document.company_id != current_user.company_id:
        raise HTTPException(status_code=404, detail="Document not found.")

    if db_document.status != DocumentStatus.PROCESSING_FAILED:
        raise HTTPException(
            status_code=400,
            detail=f"Document is not in a failed state. Current status: {db_document.status.value}"
        )

    # Smart retry based on which stage it failed
    if db_document.failed_reason and "OCR" in db_document.failed_reason:
        # If OCR failed, we restart from the beginning
        updated_doc = await document_repository.update_document_status_and_reason(
            db, document_id=document_id, status=DocumentStatus.UPLOADED
        )
        process_ocr_task.delay(document_id)
        print(f"Document {document_id} has been re-queued for OCR processing.")
    elif db_document.failed_reason and "Embedding" in db_document.failed_reason:
        # If Embedding failed, we restart from the embedding step
        updated_doc = await document_repository.update_document_status_and_reason(
            db, document_id=document_id, status=DocumentStatus.PENDING_VALIDATION
        )
        process_embedding_task.delay(document_id)
        print(f"Document {document_id} has been re-queued for embedding.")
    else:
        # Fallback for unknown failure reason
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

    # Update the document's extracted text in the database
    await document_repository.update_document_text_and_status(
        db, 
        document_id=document_id, 
        text=request.new_content, 
        status=DocumentStatus.EMBEDDING
    )

    # Update embeddings in Pinecone
    rag_update_result = await rag_service.update_document_content(
        document_id=str(document_id), 
        new_text_content=request.new_content,
        company_id=current_user.company_id,
        source_filename=request.filename 
    )

    if rag_update_result.get("status") == "failed":
        raise HTTPException(status_code=500, detail=f"Failed to update RAG embeddings: {rag_update_result.get('message')}")

    # After successful RAG update, set status to COMPLETED
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
        # Use the new delete_document_by_id which filters by document_id
        await rag_service.delete_document_by_id(
            document_id=str(document_id), 
            company_id=db_document.company_id
        )

        try:
            s3 = await s3_client_manager.get_client()
            await s3.delete_objects(
                Bucket=settings.S3_BUCKET_NAME,
                Delete={
                    "Objects": [
                        {"Key": db_document.storage_path}
                    ]
                }
            )
        except ClientError as e:
            # delete_objects might not raise an error for non-existent keys,
            # but rather list them in the 'Deleted' response.
            # Keeping this general ClientError handling for other potential S3 issues.
            if e.response['Error']['Code'] not in ['404', 'NoSuchKey']:
                raise e
            print(f"Warning: S3 object not found during deletion, proceeding. Key: {db_document.storage_path}")

        await document_repository.delete_document(db=db, document_id=document_id)

    except Exception as e:
        print(f"[ERROR] Failed to delete document: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to delete document: {str(e)}")

    return None