from sqlalchemy.ext.asyncio import AsyncSession
from app.models import embedding_model
from app.schemas import embedding_schema

async def create_embedding(db: AsyncSession, embedding: embedding_schema.EmbeddingCreate):
    db_embedding = embedding_model.Embeddings(**embedding.model_dump())
    db.add(db_embedding)
    await db.commit()
    await db.refresh(db_embedding)
    return db_embedding
