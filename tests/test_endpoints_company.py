import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock
from app.models.user_model import Users
from app.models.company_model import Company
from app.core.dependencies import get_current_user, get_current_company_admin, get_current_super_admin
from app.schemas.conversation_schema import ConversationDetailResponse
from app.schemas.chatlog_schema import ChatMessage
from app.schemas.document_schema import ReferencedDocument
from datetime import datetime
import uuid

# --- Helper Fixtures for Dependency Overrides ---

@pytest.fixture
def override_get_current_user_as_admin(app):
    mock_user = Users(id=1, email="admin@example.com", company_id=1, role='admin', is_active=True)
    app.dependency_overrides[get_current_user] = lambda: mock_user
    yield
    app.dependency_overrides.clear()

@pytest.fixture
def override_get_current_company_admin(app):
    mock_admin = Users(id=1, email="admin@example.com", company_id=1, role='admin', is_active=True)
    app.dependency_overrides[get_current_company_admin] = lambda: mock_admin
    yield
    app.dependency_overrides.clear()

@pytest.fixture
def override_get_current_super_admin(app):
    mock_super_admin = Users(id=999, email="superadmin@example.com", company_id=None, role='super_admin', is_active=True)
    app.dependency_overrides[get_current_super_admin] = lambda: mock_super_admin
    yield
    app.dependency_overrides.clear()


# --- Test Functions ---

def test_read_my_company(admin_client):
    mock_company = Company(id=1, name="Test Company", code="TC", is_active=True)
    # Endpoint /api/v1/companies/me uses get_current_company_admin and calls get_my_company_service
    with patch('app.services.company_service.get_my_company_service', return_value=mock_company):
        # Perbaiki path ke endpoint lengkap
        response = admin_client.get("/api/v1/companies/me")
        assert response.status_code == 200
        assert response.json()["name"] == "Test Company"


def test_get_company_users_endpoint(admin_client):
    mock_users = [
        Users(id=1, name="Admin User", email="admin@example.com", company_id=1, role='admin', is_active=True),
        Users(id=2, name="Employee User", email="user@example.com", company_id=1, role='employee', is_active=True)
    ]
    with patch('app.services.company_service.get_company_users_service', return_value=mock_users):
        response = admin_client.get("/api/company/users")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["email"] == "admin@example.com"


def test_update_my_company(admin_client):
    update_data = {"name": "Updated Company", "code": "UC"}
    mock_updated = Company(id=1, name="Updated Company", code="UC", is_active=True)
    with patch('app.services.company_service.update_my_company_service', return_value=mock_updated):
        response = admin_client.put("/api/company/update", data=update_data)
        assert response.status_code == 200
        assert response.json()["name"] == "Updated Company"


def test_get_active_companies(super_admin_client):
    mock_companies = [
        Company(id=1, name="Active Co 1", code="AC1", is_active=True),
        Company(id=2, name="Active Co 2", code="AC2", is_active=True)
    ]
    with patch('app.services.admin_service.get_all_active_companies_service', return_value=mock_companies):
        response = super_admin_client.get("/api/admin/companies")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2


def test_get_pending_approval_companies(super_admin_client):
    mock_companies = [
        Company(id=3, name="Pending Co 1", code="PC1", is_active=False),
        Company(id=4, name="Pending Co 2", code="PC2", is_active=False)
    ]
    with patch('app.services.admin_service.get_pending_companies_service', return_value=mock_companies):
        response = super_admin_client.get("/api/admin/companies/pending")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2

@pytest.mark.asyncio
async def test_get_conversation_details_excludes_s3_path(override_get_current_company_admin, admin_client):
    # Mock data for a successful response, ensuring no s3_path in referenced_documents
    mock_conversation_id = str(uuid.uuid4())
    mock_referenced_docs = [
        ReferencedDocument(id=1, title="Doc 1"),
        ReferencedDocument(id=2, title="Doc 2")
    ]
    mock_chat_history = [
        ChatMessage(
            question="What is the company policy?",
            answer="The company policy is...",
            created_at=datetime.now()
        )
    ]
    mock_response = ConversationDetailResponse(
        conversation_id=uuid.UUID(mock_conversation_id),
        conversation_title="Test Conversation",
        conversation_created_at=datetime.now(),
        username="testuser",
        division_name="IT",
        chat_history=mock_chat_history,
        referenced_documents=mock_referenced_docs
    )

    # Mock the service call
    with patch(
        "app.services.chatlog_service.get_conversation_details_as_company_admin",
        return_value=mock_response
    ) as mock_service_call:
        # Make the request to the endpoint
        response = admin_client.get(f"/api/v1/company/chatlogs/{mock_conversation_id}")

        # Assertions
        assert response.status_code == 200
        response_data = response.json()

        # Check that the service was called correctly
        mock_service_call.assert_called_once()
        
        # Verify that s3_path is NOT in the response
        assert "s3_path" not in response_data["referenced_documents"][0]
        assert "s3_path" not in response_data["referenced_documents"][1]
        assert response_data["conversation_id"] == mock_conversation_id
        assert response_data["referenced_documents"][0]["title"] == "Doc 1"
        assert response_data["referenced_documents"][1]["title"] == "Doc 2"
