import asyncio
import traceback
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
    """Helper function to update document status on final failure."""
    local_db_manager = DatabaseManager()
    async with local_db_manager.async_session_maker() as db:
        error_trace = traceback.format_exc()
        reason = f"Task failed at stage '{stage}'. Error: {str(exception)}\nTrace: {error_trace}"
        await document_repository.update_document_status_and_reason(
            db,
            document_id=document_id,
            status=DocumentStatus.PROCESSING_FAILED,
            reason=reason
        )
    print(f"Task for document {document_id} failed permanently at stage {stage}.")

# --- Refactored Async Logic ---

async def _run_ocr_processing(document_id: int):
    """The actual async logic for OCR processing."""
    local_db_manager = DatabaseManager()
    async with local_db_manager.async_session_maker() as db:
        doc = await document_repository.get_document(db, document_id)
        if not doc:
            print(f"[OCR Task] Document with ID {document_id} not found.")
            return

        print(f"[OCR Task] Starting OCR for document: {doc.title} (ID: {document_id})")
        
        await document_repository.update_document_status_and_reason(db, document_id, DocumentStatus.OCR_PROCESSING)

        s3 = await s3_client_manager.get_client()
        response = await s3.get_object(Bucket=settings.S3_BUCKET_NAME, Key=doc.storage_path)
        file_bytes = await response["Body"].read()

        extracted_text = await ocr_service.extract_text_from_file(file_bytes, doc.content_type)

        await document_repository.update_document_text_and_status(
            db,
            document_id=document_id,
            text=extracted_text,
            status="PENDING_VALIDATION"
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
            company_id=doc.company_id
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
def process_ocr_task(self, document_id: int):
    """Celery task to perform OCR on a document stored in S3."""
    try:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(_run_ocr_processing(document_id))
    except Exception as exc:
        # On the final retry failure, Celery re-raises the exception.
        # We catch it here to trigger our failure handling logic.
        loop = asyncio.get_event_loop()
        loop.run_until_complete(_handle_task_failure(document_id, 'OCR', exc))
        # Re-raise the exception so the task is marked as FAILED in Celery backend
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
