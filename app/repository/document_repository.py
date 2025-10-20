from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List

from app.models import document_model
from app.schemas import document_schema

async def create_document(db: AsyncSession, document: document_schema.DocumentCreate) -> document_model.Documents:
    """Creates a new document record in the database."""
    db_document = document_model.Documents(**document.model_dump())
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

async def update_document_text_and_status(db: AsyncSession, document_id: int, text: str, status: str) -> document_model.Documents | None:
    """Updates the extracted_text and status of a document."""
    db_document = await get_document(db, document_id=document_id)
    if db_document:
        db_document.extracted_text = text
        db_document.status = status
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