from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List, Optional

from app.models import document_model
from app.schemas import document_schema
from app.repository.base_repository import BaseRepository, ModelType, CreateSchemaType, UpdateSchemaType

class DocumentRepository(BaseRepository[document_model.Documents]):
    def __init__(self):
        super().__init__(document_model.Documents)

    async def create_document(self, db: AsyncSession, document: document_schema.DocumentCreate) -> document_model.Documents:
        return await self.create(db, document)

    async def get_document(self, db: AsyncSession, document_id: int) -> Optional[document_model.Documents]:
        return await self.get(db, document_id)

    async def get_documents_by_status(self, db: AsyncSession, status: str, company_id: int) -> List[document_model.Documents]:
        """Gets a list of documents with a specific status for a company."""
        result = await db.execute(
            select(self.model)
            .filter(self.model.company_id == company_id)
            .filter(self.model.status == status)
            .order_by(self.model.id.desc())
        )
        return result.scalars().all()

    async def get_documents_by_company(self, db: AsyncSession, company_id: int, skip: int, limit: int) -> List[document_model.Documents]:
        """Gets all documents for a specific company."""
        result = await db.execute(
            select(self.model)
            .filter(self.model.company_id == company_id)
            .order_by(self.model.id.desc())
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()

    async def update_document_text_and_status(self, db: AsyncSession, document_id: int, text: str, status: document_model.DocumentStatus, tags: Optional[List[str]] = None, title: Optional[str] = None) -> Optional[document_model.Documents]:
        db_document = await self.get(db, document_id)
        if db_document:
            db_document.extracted_text = text
            db_document.status = status
            if tags is not None:
                db_document.tags = tags
            if title is not None:
                db_document.title = title
            await db.commit()
            await db.refresh(db_document)
        return db_document

    async def update_document_after_upload(self, db: AsyncSession, document_id: int, s3_path: str, status: document_model.DocumentStatus) -> Optional[document_model.Documents]:
        """Updates a document's status and S3 path after a successful upload."""
        db_document = await self.get(db, document_id)
        if db_document:
            db_document.s3_path = s3_path
            db_document.status = status
            db_document.temp_storage_path = None
            db_document.failed_reason = None
            await db.commit()
            await db.refresh(db_document)
        return db_document

    async def update_document_status_and_reason(self, db: AsyncSession, document_id: int, status: document_model.DocumentStatus, reason: str | None = None) -> Optional[document_model.Documents]:
        """Updates the status and optionally the failure reason of a document."""
        db_document = await self.get(db, document_id)
        if db_document:
            db_document.status = status
            db_document.failed_reason = reason
            if status not in [document_model.DocumentStatus.PROCESSING_FAILED, document_model.DocumentStatus.UPLOAD_FAILED]:
                db_document.failed_reason = None
            await db.commit()
            await db.refresh(db_document)
        return db_document

    async def delete_document(self, db: AsyncSession, document_id: int) -> Optional[document_model.Documents]:
        return await self.delete(db, document_id)

document_repository = DocumentRepository()