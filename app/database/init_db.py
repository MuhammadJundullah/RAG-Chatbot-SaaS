import asyncio
from app.database.connection import db_manager, Base

# Import all models to ensure they are registered with Base
from app.database import schema

async def init_db():
    """
    Creates all database tables based on the SQLAlchemy models.
    """
    print("Initializing database...")
    async with db_manager.engine.begin() as conn:
        # To start fresh, you can uncomment the following lines to drop all tables.
        # This is useful in development if you make schema changes.
        # print("Dropping all existing tables...")
        await conn.run_sync(Base.metadata.drop_all)
        
        print("Creating all tables based on the current schema...")
        await conn.run_sync(Base.metadata.create_all)
    print("Database tables created successfully.")

if __name__ == "__main__":
    print("Running database initialization script...")
    asyncio.run(init_db())
    print("Script finished.")