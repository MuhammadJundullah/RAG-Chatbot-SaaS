import asyncio
from app.core.celery_app import celery_app
from app.core.database import DatabaseManager  # Import the class
from app.repository import document_repository
from app.services import ocr_service
from app.services.rag_service import RAGService  # Import the class
from app.core.s3_client import s3_client_manager
from app.core.config import settings

async def _run_ocr_processing(document_id: int):
    """The actual async logic for OCR processing."""
    local_db_manager = DatabaseManager()
    try:
        async with local_db_manager.async_session_maker() as db:
            doc = await document_repository.get_document(db, document_id)
            if not doc:
                print(f"[OCR Task] Document with ID {document_id} not found.")
                return

            print(f"[OCR Task] Starting OCR for document: {doc.title} (ID: {document_id})")

            try:
                s3 = await s3_client_manager.get_client()
                response = await s3.get_object(Bucket=settings.S3_BUCKET_NAME, Key=doc.storage_path)
                file_bytes = await response["Body"].read()
            except Exception as e:
                print(f"[OCR Task] Failed to download from S3. Error: {e}")
                return

            try:
                extracted_text = await ocr_service.extract_text_from_file(file_bytes, doc.content_type)
            except Exception as e:
                print(f"[OCR Task] Failed to extract text. Error: {e}")
                return

            await document_repository.update_document_text_and_status(
                db,
                document_id=document_id,
                text=extracted_text,
                status="PENDING_VALIDATION"
            )
            print(f"[OCR Task] Finished OCR for document ID: {document_id}. Status set to PENDING_VALIDATION.")
    finally:
        await local_db_manager.close()

async def _run_embedding_processing(document_id: int):
    """The actual async logic for embedding processing."""
    rag_service = RAGService()
    local_db_manager = DatabaseManager()
    try:
        async with local_db_manager.async_session_maker() as db:
            doc = await document_repository.get_document(db, document_id)
            if not doc or not doc.extracted_text:
                print(f"[Embedding Task] Document {document_id} not found or has no text.")
                return

            print(f"[Embedding Task] Starting embedding for document: {doc.title} (ID: {document_id})")

            try:
                result = await rag_service.add_text_as_document(
                    text_content=doc.extracted_text,
                    file_name=doc.title,
                    company_id=doc.company_id
                )
                if result.get("status") == "failed":
                    print(f"[Embedding Task] Failed to embed document ID {document_id}: {result.get('message')}")
                    return
            except Exception as e:
                print(f"[Embedding Task] An exception occurred during embedding for document ID {document_id}. Error: {e}")
                return

            await document_repository.update_document_text_and_status(
                db,
                document_id=document_id,
                text=doc.extracted_text,
                status="COMPLETED"
            )
            print(f"[Embedding Task] Finished embedding for document ID: {document_id}. Status set to COMPLETED.")
    finally:
        await local_db_manager.close()

@celery_app.task(acks_late=True, bind=True)
def process_ocr_task(self, document_id: int):
    """Celery task to perform OCR on a document stored in S3."""
    return asyncio.run(_run_ocr_processing(document_id))

@celery_app.task(acks_late=True, bind=True)
def process_embedding_task(self, document_id: int):
    """Celery task to chunk and embed confirmed text."""
    return asyncio.run(_run_embedding_processing(document_id))