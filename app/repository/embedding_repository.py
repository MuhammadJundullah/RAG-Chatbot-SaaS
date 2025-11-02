from sqlalchemy.ext.asyncio import AsyncSession
from app.models import embedding_model
from app.schemas import embedding_schema
from app.repository.base_repository import BaseRepository

class EmbeddingRepository(BaseRepository[embedding_model.Embeddings]):
    def __init__(self):
        super().__init__(embedding_model.Embeddings)

    async def create_embedding(self, db: AsyncSession, embedding: embedding_schema.EmbeddingCreate) -> embedding_model.Embeddings:
        return await self.create(db, embedding)

embedding_repository = EmbeddingRepository()