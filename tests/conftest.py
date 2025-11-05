import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock
from app.main import app
from app.models.user_model import Users
from app.core.dependencies import get_current_user, get_current_company_admin, get_current_super_admin
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.fixture
def mock_db_session():
    return AsyncMock(spec=AsyncSession)


@pytest.fixture(scope="module")
def authenticated_client():
    """Provide an authenticated client for testing (as regular user)."""
    mock_user = Users(
        id=1,
        name="Test User",
        email="test@example.com",
        username="testuser",
        role="employee",
        company_id=1,
        is_active=True
    )
    app.dependency_overrides[get_current_user] = lambda: mock_user
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


@pytest.fixture(scope="module")
def admin_client():
    """Provide an authenticated client as company admin."""
    mock_admin = Users(
        id=2,
        name="Admin User",
        email="admin@example.com",
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
        email="superadmin@example.com",
        username="superadmin",
        role="super_admin",
        company_id=None,
        is_active=True
    )
    app.dependency_overrides[get_current_super_admin] = lambda: mock_super_admin
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()