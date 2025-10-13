from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import text
from app.config.settings import settings
from typing import AsyncGenerator


# Base for SQLAlchemy declarative models
Base = declarative_base()

class DatabaseManager:
    def __init__(self):
        # Use asyncpg driver with SQLAlchemy
        self.engine = create_async_engine(settings.DATABASE_URL, echo=False, connect_args={"ssl": "require"})
        self.async_session_maker = async_sessionmaker(
            self.engine, expire_on_commit=False, class_=AsyncSession
        )

    async def connect(self):
        # No explicit connect needed for async_session_maker, it manages connections
        pass

    async def close(self):
        await self.engine.dispose()

    async def get_db_session(self) -> AsyncGenerator[AsyncSession, None]:
        async with self.async_session_maker() as session:
            yield session

    async def execute_raw_query(self, query: str) -> list[dict]:
        """Executes a raw SQL query and returns results as a list of dicts."""
        async with self.async_session_maker() as session:
            result = await session.execute(text(query))
            # For SELECT statements, fetch all rows and convert to dicts
            if result.returns_rows:
                return [row._asdict() for row in result.fetchall()]
            return []

    async def get_schema_info(self) -> str:
        """
        Get database schema information from SQLAlchemy models for Gemini context.
        This assumes models are defined in app/database/schema.py and inherit from Base.
        """
        from app.database.schema import Base as AppBase # Import the Base from schema.py

        formatted_schema = "Database Schema (SQLAlchemy Models):\n"
        for table_name, table_obj in AppBase.metadata.tables.items():
            formatted_schema += f"- {table_name}:\n"
            for column in table_obj.columns:
                formatted_schema += f"  - {column.name} ({column.type})\n"
        return formatted_schema

db_manager = DatabaseManager()