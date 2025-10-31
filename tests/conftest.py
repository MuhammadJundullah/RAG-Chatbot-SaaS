import sys
import os
import pytest
from typing import Generator
from fastapi.testclient import TestClient

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.core.config import settings
from app.core.database import db_manager
from app.models.base import Base
from app.models.user_model import Users
from app.core.dependencies import get_current_user, get_current_company_admin

# Use an in-memory SQLite database for testing
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

# Create a synchronous engine for testing
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(name="db_session")
def db_session_fixture() -> Generator:
    """
    Create a clean SQLAlchemy session for each test.
    """
    Base.metadata.create_all(bind=engine)  # Create tables
    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)

    yield session

    session.close()
    transaction.rollback()
    connection.close()
    Base.metadata.drop_all(bind=engine)  # Drop tables

@pytest.fixture(name="client")
def client_fixture(db_session: Generator) -> TestClient:
    """
    Create a TestClient that uses the overridden get_db fixture.
    """
    async def override_get_db():
        yield db_session

    app.dependency_overrides[db_manager.get_db_session] = override_get_db
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()

@pytest.fixture(name="authenticated_client")
def authenticated_client_fixture(db_session: Generator) -> TestClient:
    """
    Create a TestClient with authenticated user dependencies overridden.
    """
    async def override_get_db():
        yield db_session

    mock_user = Users(
        id=1,
        name="Test User",
        email="test@example.com",
        username="testuser",
        role="admin",
        company_id=1,
        is_super_admin=False
    )

    async def override_get_current_user():
        return mock_user

    async def override_get_current_company_admin():
        return mock_user

    app.dependency_overrides[db_manager.get_db_session] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user
    app.dependency_overrides[get_current_company_admin] = override_get_current_company_admin

    with TestClient(app) as client:
        yield client

    app.dependency_overrides.clear()

# Override settings for tests
@pytest.fixture(autouse=True)
def override_settings():
    settings.DATABASE_URL = SQLALCHEMY_DATABASE_URL
    settings.TEST_DATABASE_URL = SQLALCHEMY_DATABASE_URL
    # You might want to mock other settings like API keys if they are used in tests
    # settings.GEMINI_API_KEY = "mock_gemini_key"
    # settings.PINECONE_API_KEY = "mock_pinecone_key"
    # settings.S3_AWS_ACCESS_KEY_ID = "mock_s3_key"
    # settings.S3_AWS_SECRET_ACCESS_KEY = "mock_s3_secret"
    # settings.S3_BUCKET_NAME = "mock_s3_bucket"
    # settings.REDIS_URL = "redis://localhost:6379/1" # Use a different Redis DB for tests