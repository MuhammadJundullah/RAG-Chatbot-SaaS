from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List

from app.models import document_model
from app.schemas import document_schema

async def create_document(db: AsyncSession, document: document_schema.DocumentCreate) -> document_model.Documents:
    """Creates a new document record in the database."""
    # Note: The status will default to UPLOADING as per the model definition
    db_document = document_model.Documents(
        title=document.title,
        company_id=document.company_id,
        temp_storage_path=document.temp_storage_path,
        content_type=document.content_type
    )
    db.add(db_document)
    await db.commit()
    await db.refresh(db_document)
    return db_document

async def get_document(db: AsyncSession, document_id: int) -> document_model.Documents | None:
    """Gets a single document by its ID."""
    result = await db.execute(
        select(document_model.Documents).filter(document_model.Documents.id == document_id)
    )
    return result.scalar_one_or_none()

async def get_documents_by_status(db: AsyncSession, status: str, company_id: int) -> List[document_model.Documents]:
    """Gets a list of documents with a specific status for a company."""
    result = await db.execute(
        select(document_model.Documents)
        .filter(document_model.Documents.company_id == company_id)
        .filter(document_model.Documents.status == status)
        .order_by(document_model.Documents.id.desc())
    )
    return result.scalars().all()

async def get_documents_by_company(db: AsyncSession, company_id: int, skip: int, limit: int) -> List[document_model.Documents]:
    """Gets all documents for a specific company."""
    result = await db.execute(
        select(document_model.Documents)
        .filter(document_model.Documents.company_id == company_id)
        .order_by(document_model.Documents.id.desc())
        .offset(skip)
        .limit(limit)
    )
    return result.scalars().all()

async def update_document_text_and_status(db: AsyncSession, document_id: int, text: str, status: document_model.DocumentStatus) -> document_model.Documents | None:
    """Updates the extracted_text and status of a document."""
    db_document = await get_document(db, document_id=document_id)
    if db_document:
        db_document.extracted_text = text
        db_document.status = status
        await db.commit()
        await db.refresh(db_document)
    return db_document

async def update_document_after_upload(db: AsyncSession, document_id: int, s3_path: str, status: document_model.DocumentStatus) -> document_model.Documents | None:
    """Updates a document's status and S3 path after a successful upload."""
    db_document = await get_document(db, document_id=document_id)
    if db_document:
        db_document.s3_path = s3_path
        db_document.status = status
        db_document.temp_storage_path = None # Clear the temp path
        db_document.failed_reason = None # Clear any previous failure reason
        await db.commit()
        await db.refresh(db_document)
    return db_document

async def update_document_status_and_reason(db: AsyncSession, document_id: int, status: document_model.DocumentStatus, reason: str | None = None) -> document_model.Documents | None:
    """Updates the status and optionally the failure reason of a document."""
    db_document = await get_document(db, document_id=document_id)
    if db_document:
        db_document.status = status
        db_document.failed_reason = reason
        # Clear reason if status is not a failed one
        if status not in [document_model.DocumentStatus.PROCESSING_FAILED, document_model.DocumentStatus.UPLOAD_FAILED]:
            db_document.failed_reason = None
        await db.commit()
        await db.refresh(db_document)
    return db_document

async def delete_document(db: AsyncSession, document_id: int) -> document_model.Documents | None:
    """Deletes a document from the database by its ID."""
    db_document = await get_document(db, document_id=document_id)
    if db_document:
        await db.delete(db_document)
        await db.commit()
    return db_document
