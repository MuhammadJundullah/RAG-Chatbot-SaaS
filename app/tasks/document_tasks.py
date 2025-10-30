import asyncio
import traceback
import os
from app.core.celery_app import celery_app
from app.core.database import DatabaseManager
from app.repository import document_repository
from app.services import ocr_service
from app.services.rag_service import RAGService
from app.core.s3_client import s3_client_manager
from app.core.config import settings
from app.models.document_model import DocumentStatus

# --- Logic for failure handling ---

async def _handle_task_failure(document_id: int, stage: str, exception: Exception):
    from app.core.database import db_manager
    async with db_manager.async_session_maker() as db:
        error_trace = traceback.format_exc()
        # Determine the correct failed status based on the stage
        failed_status = DocumentStatus.UPLOAD_FAILED if stage == 'Upload' else DocumentStatus.PROCESSING_FAILED
        reason = f"Task failed at stage '{stage}'. Error: {str(exception)}\nTrace: {error_trace}"
        await document_repository.update_document_status_and_reason(
            db,
            document_id=document_id,
            status=failed_status,
            reason=reason
        )
    print(f"Task for document {document_id} failed permanently at stage {stage}.")

# --- New Upload Task Logic ---

async def _run_upload_processing(document_id: int):
    """The actual async logic for uploading a file to S3."""
    from app.core.database import db_manager
    async with db_manager.async_session_maker() as db:
        doc = await document_repository.get_document(db, document_id)
        if not doc or not doc.temp_storage_path:
            print(f"[Upload Task] Document {document_id} not found or has no temp path.")
            return

        print(f"[Upload Task] Starting S3 upload for document: {doc.title} (ID: {document_id})")
        
        s3_path = f"documents/{doc.company_id}/{doc.id}_{doc.title}"
        
        try:
            print(f"[Upload Task] Attempting to get S3 client for document {document_id}.")
            s3 = await s3_client_manager.get_client()
            print(f"[Upload Task] Successfully obtained S3 client for document {document_id}.")
            if doc.temp_storage_path is None:
                raise ValueError(f"Document {document_id} has a None temp_storage_path before S3 upload.")
            with open(doc.temp_storage_path, "rb") as file:
                await s3.put_object(
                    Bucket=settings.S3_BUCKET_NAME,
                    Key=s3_path,
                    Body=file
                )
            
            print(f"[Upload Task] Successfully uploaded to S3 at {s3_path}")

            # Store temp_storage_path locally before it's cleared in the database update
            local_temp_path = doc.temp_storage_path

            # Update database with S3 path and new status
            await document_repository.update_document_after_upload(
                db,
                document_id=document_id,
                s3_path=s3_path,
                status=DocumentStatus.UPLOADED
            )

            # Clean up the temporary file using the locally stored path
            if local_temp_path and os.path.exists(local_temp_path):
                os.remove(local_temp_path)
                print(f"[Upload Task] Removed temporary file: {local_temp_path}")

            # Trigger the next task in the chain
            process_ocr_task.delay(document_id)
            print(f"[Upload Task] Triggered OCR task for document ID: {document_id}")

        except Exception as e:
            # If any part of the process fails, re-raise to be caught by Celery
            print(f"[Upload Task] Error during upload process for doc {document_id}: {e}")
            raise e
        finally:
            # Ensure temporary file is cleaned up even if upload fails
            if doc and doc.temp_storage_path:
                print(f"[Upload Task] Finally block: Checking temp file {doc.temp_storage_path}. Exists: {os.path.exists(doc.temp_storage_path)}")
                if os.path.exists(doc.temp_storage_path):
                    try:
                        print(f"[Upload Task] Attempting to remove temporary file: {doc.temp_storage_path}")
                        os.remove(doc.temp_storage_path)
                        print(f"[Upload Task] Ensured temporary file removed: {doc.temp_storage_path}")
                        print(f"[Upload Task] After os.remove: File exists? {os.path.exists(doc.temp_storage_path)}")
                    except OSError as e:
                        print(f"[Upload Task] Error: Failed to remove temporary file {doc.temp_storage_path} in finally block: {e}")

# --- Refactored Async Logic ---

async def _run_ocr_processing(document_id: int):
    from app.core.database import db_manager
    async with db_manager.async_session_maker() as db:
        doc = await document_repository.get_document(db, document_id)
        if not doc or not doc.s3_path: # Check for s3_path now
            print(f"[OCR Task] Document with ID {document_id} not found or has no S3 path.")
            return

        print(f"[OCR Task] Starting OCR for document: {doc.title} (ID: {document_id})")
        
        await document_repository.update_document_status_and_reason(db, document_id, DocumentStatus.OCR_PROCESSING)

        s3 = await s3_client_manager.get_client()
        response = await s3.get_object(Bucket=settings.S3_BUCKET_NAME, Key=doc.s3_path) # Use s3_path
        file_bytes = await response["Body"].read()

        print(f"[OCR Task] Document {document_id} content_type: {doc.content_type}")
        try:
            extracted_text = await ocr_service.extract_text_from_file(file_bytes, doc.content_type)
        except Exception as e:
            print(f"[OCR Task] Error during OCR extraction for doc {document_id}: {e}")
            traceback.print_exc()
            raise e

        await document_repository.update_document_text_and_status(
            db,
            document_id=document_id,
            text=extracted_text,
            status=DocumentStatus.PENDING_VALIDATION # Corrected status to use Enum
        )
        print(f"[OCR Task] Finished OCR for document ID: {document_id}. Status set to PENDING_VALIDATION.")

async def _run_embedding_processing(document_id: int):
    """The actual async logic for embedding processing."""
    rag_service = RAGService()
    local_db_manager = DatabaseManager()
    async with local_db_manager.async_session_maker() as db:
        doc = await document_repository.get_document(db, document_id)
        if not doc or not doc.extracted_text:
            print(f"[Embedding Task] Document {document_id} not found or has no text.")
            return

        print(f"[Embedding Task] Starting embedding for document: {doc.title} (ID: {document_id})")
        
        await document_repository.update_document_status_and_reason(db, document_id, DocumentStatus.EMBEDDING)

        result = await rag_service.add_text_as_document(
            text_content=doc.extracted_text,
            file_name=doc.title,
            company_id=doc.company_id,
            document_id=str(document_id)
        )
        if result.get("status") == "failed":
            raise ValueError(f"RAG service failed: {result.get('message')}")

        await document_repository.update_document_status_and_reason(
            db,
            document_id=document_id,
            status=DocumentStatus.COMPLETED
        )
        print(f"[Embedding Task] Finished embedding for document ID: {document_id}. Status set to COMPLETED.")

# --- Celery Task Definitions with Retry Logic ---

@celery_app.task(
    acks_late=True,
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    max_retries=3,
    retry_jitter=True
)
def upload_document_to_s3(self, document_id: int):
    """Celery task to upload a document to S3 from a temporary path."""
    try:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(_run_upload_processing(document_id))
    except Exception as exc:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(_handle_task_failure(document_id, 'Upload', exc))
        raise exc

@celery_app.task(
    acks_late=True,
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    max_retries=3,
    retry_jitter=True
)
def process_ocr_task(self, document_id: int):
    """Celery task to perform OCR on a document stored in S3."""
    try:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(_run_ocr_processing(document_id))
    except Exception as exc:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(_handle_task_failure(document_id, 'OCR', exc))
        raise exc

@celery_app.task(
    acks_late=True,
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    max_retries=3,
    retry_jitter=True
)
def process_embedding_task(self, document_id: int):
    """Celery task to chunk and embed confirmed text."""
    try:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(_run_embedding_processing(document_id))
    except Exception as exc:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(_handle_task_failure(document_id, 'Embedding', exc))
        raise exc
