import asyncio
import traceback
import os
from app.core.celery_app import celery_app
from app.core.database import DatabaseManager
import app.repository.document_repository as doc_repo_module
from app.services import ocr_service
from app.services.rag_service import RAGService
from app.models.document_model import DocumentStatus

# --- Logic for failure handling ---

async def _handle_task_failure(document_id: int, stage: str, exception: Exception):
    from app.core.database import db_manager
    async with db_manager.async_session_maker() as db:
        error_trace = traceback.format_exc()
        # Determine the correct failed status based on the stage
        failed_status = DocumentStatus.PROCESSING_FAILED # Simplified failure status
        reason = f"Task failed at stage '{stage}'. Error: {str(exception)}\nTrace: {error_trace}"
        await doc_repo_module.document_repository.update_document_status_and_reason(
            db,
            document_id=document_id,
            status=failed_status,
            reason=reason
        )
    print(f"Task for document {document_id} failed permanently at stage {stage}.")

# --- Refactored Async Logic ---

async def _run_ocr_processing(document_id: int):
    from app.core.database import db_manager
    async with db_manager.async_session_maker() as db:
        doc = await doc_repo_module.document_repository.get_document(db, document_id)
        if not doc or not doc.temp_storage_path:
            print(f"[OCR Task] Document with ID {document_id} not found or has no temp storage path.")
            return

        if not os.path.exists(doc.temp_storage_path):
            print(f"[OCR Task] Temporary file not found for document {document_id} at path {doc.temp_storage_path}.")
            await _handle_task_failure(document_id, 'OCR', FileNotFoundError(f"Temporary file not found at {doc.temp_storage_path}"))
            return

        print(f"[OCR Task] Starting OCR for document: {doc.title} (ID: {document_id}) from path {doc.temp_storage_path}")
        
        await doc_repo_module.document_repository.update_document_status_and_reason(db, document_id, DocumentStatus.OCR_PROCESSING)

        local_temp_path = doc.temp_storage_path # Store path for cleanup

        try:
            with open(local_temp_path, "rb") as f:
                file_bytes = f.read()

            print(f"[OCR Task] Document {document_id} content_type: {doc.content_type}")
            extracted_text = await ocr_service.extract_text_from_file(file_bytes, doc.content_type)

            await doc_repo_module.document_repository.update_document_text_and_status(
                db,
                document_id=document_id,
                text=extracted_text,
                status=DocumentStatus.PENDING_VALIDATION 
            )
            print(f"[OCR Task] Finished OCR for document ID: {document_id}. Status set to PENDING_VALIDATION.")

        except Exception as e:
            print(f"[OCR Task] Error during OCR extraction for doc {document_id}: {e}")
            traceback.print_exc()
            # Re-raise the exception to be handled by Celery's retry/failure mechanism
            raise e
        finally:
            # Clean up the temporary file after processing
            if os.path.exists(local_temp_path):
                os.remove(local_temp_path)
                print(f"[OCR Task] Removed temporary file: {local_temp_path}")
            # Clear the temp_storage_path from the database record
            await doc_repo_module.document_repository.clear_temp_storage_path(db, document_id)


async def _run_embedding_processing(document_id: int):
    """
    The actual async logic for embedding processing, including deletion of old embeddings
    and addition of new ones via Celery.
    """
    rag_service = RAGService()
    local_db_manager = DatabaseManager()
    async with local_db_manager.async_session_maker() as db:
        doc = await doc_repo_module.document_repository.get_document(db, document_id)
        if not doc or not doc.extracted_text:
            print(f"[Embedding Task] Document {document_id} not found or has no extracted text.")
            await doc_repo_module.document_repository.update_document_status_and_reason(
                db, document_id, DocumentStatus.PROCESSING_FAILED, "Document not found or has no extracted text."
            )
            return

        print(f"[Embedding Task] Starting embedding for document: {doc.title} (ID: {document_id})")
        
        # Update status to EMBEDDING before starting
        await doc_repo_module.document_repository.update_document_status_and_reason(db, document_id, DocumentStatus.EMBEDDING)

        try:
            # 1. Delete old embeddings using the rag_service update_document_content method
            print(f"[Embedding Task] Calling rag_service.update_document_content for document ID: {document_id} to delete old embeddings.")
            delete_result = await rag_service.update_document_content(
                document_id=str(document_id),
                new_text_content="",
                company_id=doc.company_id,
                title=doc.title, # Pass title for metadata if needed by delete_document_by_id
                tags=doc.tags # Pass tags if needed by delete_document_by_id
            )
            print(f"[Embedding Task] Result from rag_service.update_document_content for document ID {document_id}: {delete_result}") # Log the result

            # Check if deletion was marked as failed.
            if delete_result.get("status") == "failed":
                error_message = delete_result.get("message", "Unknown error during deletion.")
                print(f"[Embedding Task] Deletion of old embeddings failed for document ID {document_id}: {error_message}")
                # Raise an exception to fail the task and trigger Celery retries/failure handling
                raise RuntimeError(f"Failed to delete old embeddings for document {document_id}: {error_message}")
            
            print(f"[Embedding Task] Old embeddings deletion process completed for document ID: {document_id}. Status: {delete_result.get('status')}")

            # 2. Add new embeddings using the add_text_as_document method
            add_result = await rag_service.add_text_as_document(
                text_content=doc.extracted_text,
                file_name=doc.title,
                company_id=doc.company_id,
                document_id=str(document_id),
                tags=doc.tags # Pass tags to add_text_as_document
            )
            if add_result.get("status") == "failed":
                raise ValueError(f"RAG service failed to add document: {add_result.get('message')}")

            # 3. Update status to COMPLETED if successful
            await doc_repo_module.document_repository.update_document_status_and_reason(
                db,
                document_id=document_id,
                status=DocumentStatus.COMPLETED
            )
            print(f"[Embedding Task] Finished embedding for document ID: {document_id}. Status set to COMPLETED.")

        except Exception as e:
            # Handle any exceptions during deletion or addition
            print(f"[Embedding Task] Error during embedding processing for doc {document_id}: {e}")
            # Re-raise to trigger Celery's retry mechanism and _handle_task_failure
            raise e

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
    """Celery task to perform OCR on a document stored locally."""
    try:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(_run_ocr_processing(document_id))
        # Log successful OCR task completion
        print(f"[Celery Task] OCR task completed for document ID: {document_id}")
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
    """Celery task to chunk, embed, and upsert document text, including deletion of old embeddings."""
    try:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(_run_embedding_processing(document_id))
        # Log successful embedding task completion
        print(f"[Celery Task] Embedding task completed for document ID: {document_id}")
    except Exception as exc:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(_handle_task_failure(document_id, 'Embedding', exc))
        raise exc
