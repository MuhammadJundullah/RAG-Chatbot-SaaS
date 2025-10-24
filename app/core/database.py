from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import text
from app.core.config import settings
from typing import AsyncGenerator
import asyncio
import os
from sqlalchemy.future import select
from app.utils.security import get_password_hash
from app.models.base import Base

import app.models

class DatabaseManager:
    def __init__(self):
        """Initializes the database engine and session maker upon creation."""
        self.engine = create_async_engine(settings.DATABASE_URL, echo=False)
        self.async_session_maker = async_sessionmaker(
            self.engine, expire_on_commit=False, class_=AsyncSession
        )

    async def close(self):
        """Closes the database engine connections."""
        if self.engine:
            await self.engine.dispose()

    async def get_db_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Provides a database session."""
        async with self.async_session_maker() as session:
            yield session

db_manager = DatabaseManager()

async def create_super_admin(db_session):
    """Creates the initial super admin user from environment variables or defaults."""
    SUPERADMIN_USERNAME = settings.SUPERADMIN_USERNAME
    SUPERADMIN_PASSWORD = settings.SUPERADMIN_PASSWORD
    if SUPERADMIN_USERNAME == "superadmin":
        print("\033[93mWARNING: SUPERADMIN_USERNAME not set. Using default: superadmin\033[0m")
    if SUPERADMIN_PASSWORD == "superadmin":
        print("\033[93mWARNING: SUPERADMIN_PASSWORD not set. Using default: superadmin\033[0m")

    from app.models.user_model import Users as UserModel
    result = await db_session.execute(select(UserModel).filter(UserModel.username == SUPERADMIN_USERNAME))
    if result.scalar_one_or_none():
        print(f"Super admin user '{SUPERADMIN_USERNAME}' already exists.")
        return

    hashed_password = get_password_hash(SUPERADMIN_PASSWORD)
    super_admin = UserModel(
        name="Super Admin",
        username=SUPERADMIN_USERNAME,
        email=None,
        password=hashed_password,
        role="super_admin",
        is_active_in_company=True,
        company_id=None
    )
    db_session.add(super_admin)
    await db_session.commit()
    print(f"Super admin user '{SUPERADMIN_USERNAME}' created successfully.")

async def init_db():
    """
    Creates all database tables and the initial super admin.
    """
    print("Initializing database...")
    async with db_manager.engine.begin() as conn:
        print(f"Tables known to Base.metadata: {Base.metadata.tables.keys()}")
        print("Dropping all existing tables...")
        await conn.run_sync(Base.metadata.drop_all)
        print("Finished dropping tables.")
        
        print("Creating all tables based on the current schema...")
        await conn.run_sync(Base.metadata.create_all)
    
    async for db in db_manager.get_db_session():
        try:
            await create_super_admin(db)
        finally:
            # This will exhaust the generator and close the session
            pass

    print("Database initialization finished successfully.")

if __name__ == "__main__":
    print("Running database initialization script...")
    asyncio.run(init_db())
    print("Script finished.")