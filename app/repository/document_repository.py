from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List, Optional
from sqlalchemy import func, case

from app.models import document_model
from app.schemas import document_schema
from app.repository.base_repository import BaseRepository

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

    async def count_documents_by_company(self, db: AsyncSession, company_id: int) -> int:
        """Counts all documents for a specific company."""
        result = await db.execute(
            select(func.count(self.model.id))
            .filter(self.model.company_id == company_id)
        )
        return result.scalar_one()

    async def get_documents_by_company(self, db: AsyncSession, company_id: int, skip: int, limit: int) -> (List[document_model.Documents], int):
        """Gets all documents for a specific company with total count."""
        result = await db.execute(
            select(self.model)
            .filter(self.model.company_id == company_id)
            .order_by(self.model.id.desc())
            .offset(skip)
            .limit(limit)
        )
        documents = result.scalars().all()
        total_count = await self.count_documents_by_company(db, company_id)
        return documents, total_count

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

    async def clear_temp_storage_path(self, db: AsyncSession, document_id: int) -> Optional[document_model.Documents]:
        """Clears the temporary storage path of a document."""
        db_document = await self.get(db, document_id)
        if db_document:
            db_document.temp_storage_path = None
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

    async def get_documents_by_ids(self, db: AsyncSession, document_ids: List[int]) -> List[document_model.Documents]:
        if not document_ids:
            return []
        result = await db.execute(
            select(self.model)
            .filter(self.model.id.in_(document_ids))
        )
        return result.scalars().all()

    async def get_document_summary(self, db: AsyncSession, company_id: int) -> dict:
        """Gets a summary of document counts by status for a company."""
        processing_statuses = [
            document_model.DocumentStatus.UPLOADING,
            document_model.DocumentStatus.UPLOADED,
            document_model.DocumentStatus.OCR_PROCESSING,
            document_model.DocumentStatus.PENDING_VALIDATION,
            document_model.DocumentStatus.EMBEDDING,
        ]
        failed_statuses = [
            document_model.DocumentStatus.UPLOAD_FAILED,
            document_model.DocumentStatus.PROCESSING_FAILED,
        ]

        query = select(
            func.count(self.model.id).label("total_documents"),
            func.count(case((self.model.status.in_(processing_statuses), self.model.id))).label("processing_documents"),
            func.count(case((self.model.status == document_model.DocumentStatus.COMPLETED, self.model.id))).label("completed_documents"),
            func.count(case((self.model.status.in_(failed_statuses), self.model.id))).label("failed_documents")
        ).filter(self.model.company_id == company_id)

        result = await db.execute(query)
        summary = result.one()
        return {
            "total_documents": summary.total_documents,
            "processing_documents": summary.processing_documents,
            "completed_documents": summary.completed_documents,
            "failed_documents": summary.failed_documents,
        }

    async def get_recent_documents(self, db: AsyncSession, company_id: int, limit: int = 3) -> List[document_model.Documents]:
        """Gets the most recently updated documents for a company."""
        result = await db.execute(
            select(self.model)
            .filter(self.model.company_id == company_id)
            .order_by(self.model.updated_at.desc().nulls_last())
            .limit(limit)
        )
        return result.scalars().all()

document_repository = DocumentRepository()