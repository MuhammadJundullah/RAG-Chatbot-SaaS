import asyncio
import os
from sqlalchemy import text
from sqlalchemy.future import select

from app.database.connection import db_manager, Base
from app.database import schema
from app.utils.security import get_password_hash

async def create_super_admin(db_session):
    """Creates the initial super admin user from environment variables or defaults."""
    SUPERADMIN_EMAIL = os.environ.get("SUPERADMIN_EMAIL", "superadmin@example.com")
    SUPERADMIN_PASSWORD = os.environ.get("SUPERADMIN_PASSWORD", "superadmin")

    if SUPERADMIN_EMAIL == "superadmin@example.com":
        print("\033[93mWARNING: SUPERADMIN_EMAIL not set. Using default: superadmin@example.com\033[0m")
    if SUPERADMIN_PASSWORD == "superadmin":
        print("\033[93mWARNING: SUPERADMIN_PASSWORD not set. Using default: superadmin\033[0m")

    # Check if super admin already exists
    result = await db_session.execute(select(schema.Users).filter(schema.Users.email == SUPERADMIN_EMAIL))
    if result.scalar_one_or_none():
        print(f"Super admin user '{SUPERADMIN_EMAIL}' already exists.")
        return

    # Create super admin user
    hashed_password = get_password_hash(SUPERADMIN_PASSWORD)
    super_admin = schema.Users(
        name="Super Admin",
        email=SUPERADMIN_EMAIL,
        password=hashed_password,
        role="super_admin",
        is_super_admin=True,
        is_active_in_company=True, # Super admin must be active to log in
        company_id=None # Super admin does not belong to any company
    )
    db_session.add(super_admin)
    await db_session.commit()
    print(f"Super admin user '{SUPERADMIN_EMAIL}' created successfully.")

async def init_db():
    """
    Creates all database tables and the initial super admin.
    """
    print("Initializing database...")
    async with db_manager.engine.begin() as conn:
        print("Dropping all existing tables...")
        await conn.run_sync(Base.metadata.drop_all)
        
        print("Creating all tables based on the current schema...")
        await conn.run_sync(Base.metadata.create_all)
    
    # Correctly handle the async generator for the session
    db_session_generator = db_manager.get_db_session()
    db = await anext(db_session_generator)
    try:
        await create_super_admin(db)
    finally:
        try:
            # This is how you exhaust the generator to trigger its finally block
            await anext(db_session_generator)
        except StopAsyncIteration:
            pass

    print("Database initialization finished successfully.")

if __name__ == "__main__":
    print("Running database initialization script...")
    asyncio.run(init_db())
    print("Script finished.")
