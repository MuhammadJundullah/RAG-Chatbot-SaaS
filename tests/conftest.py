import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock
from app.main import app
from app.models.user_model import Users
from app.core.dependencies import get_current_user, get_current_company_admin, get_current_super_admin, get_db
from sqlalchemy.ext.asyncio import AsyncSession
import pytest


@pytest.fixture
def mock_db_session():
    return AsyncMock(spec=AsyncSession)


@pytest.fixture(autouse=True)
def override_get_db(mock_db_session):
    async def _override():
        yield mock_db_session
    app.dependency_overrides[get_db] = _override
    yield
    app.dependency_overrides.pop(get_db, None)


@pytest.fixture(scope="module")
def authenticated_client():
    """Provide an authenticated client for testing (as regular user)."""
    mock_user = Users(
        id=1,
        name="Test User",
        username="testuser",
        role="employee",
        company_id=1,
        is_active=True
    )
    app.dependency_overrides[get_current_user] = lambda: mock_user
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


@pytest.fixture
def app_instance():
    return app


@pytest.fixture(scope="module")
def admin_client():
    """Provide an authenticated client as company admin."""
    mock_admin = Users(
        id=2,
        name="Admin User",
        username="adminuser",
        role="admin",
        company_id=1,
        is_active=True
    )
    app.dependency_overrides[get_current_company_admin] = lambda: mock_admin
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


@pytest.fixture(scope="module")
def super_admin_client():
    """Provide an authenticated client as super admin."""
    mock_super_admin = Users(
        id=3,
        name="Super Admin",
        username="superadmin",
        role="super_admin",
        company_id=None,
        is_active=True
    )
    app.dependency_overrides[get_current_super_admin] = lambda: mock_super_admin
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()
