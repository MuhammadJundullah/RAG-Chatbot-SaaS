import pytest
from unittest.mock import patch, ANY
from app.models.user_model import Users
from app.models.company_model import Company
from app.core.dependencies import get_current_user, get_current_company_admin, get_current_super_admin
from app.schemas.conversation_schema import ConversationDetailResponse
from app.schemas.chatlog_schema import ChatMessage
from app.schemas.document_schema import ReferencedDocument
from datetime import datetime
import uuid
from app.services.user_service import EmployeeDeletionError
from app.schemas.user_schema import User # Import User schema for mock response
from app.models.division_model import Division # Import Division model for mock

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
async def test_delete_employee_by_admin_success(override_get_current_company_admin, admin_client):
    with patch("app.services.user_service.delete_employee_by_admin", return_value=None) as mock_delete_service:
        response = admin_client.delete("/api/v1/companies/employees/2")
        assert response.status_code == 204
        mock_delete_service.assert_called_once_with(db=ANY, company_id=1, employee_id=2)

@pytest.mark.asyncio
async def test_delete_employee_by_admin_not_found(override_get_current_company_admin, admin_client):
    with patch("app.services.user_service.delete_employee_by_admin", side_effect=EmployeeDeletionError(detail="Employee not found.", status_code=404)) as mock_delete_service:
        response = admin_client.delete("/api/v1/companies/employees/999")
        assert response.status_code == 404
        assert response.json() == {"detail": "Employee not found."}
        mock_delete_service.assert_called_once_with(db=ANY, company_id=1, employee_id=999)

@pytest.mark.asyncio
async def test_delete_employee_by_admin_unauthorized(override_get_current_company_admin, admin_client):
    with patch("app.services.user_service.delete_employee_by_admin", side_effect=EmployeeDeletionError(detail="Not authorized to delete this employee.", status_code=403)) as mock_delete_service:
        response = admin_client.delete("/api/v1/companies/employees/3")
        assert response.status_code == 403
        assert response.json() == {"detail": "Not authorized to delete this employee."}
        mock_delete_service.assert_called_once_with(db=ANY, company_id=1, employee_id=3)

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

# --- New Test for Employee Registration ---

@pytest.mark.asyncio
async def test_register_employee_by_admin_new_division(override_get_current_company_admin, admin_client):
    # Mock data for the request
    employee_data = {
        "name": "New Employee",
        "email": "new.employee@example.com",
        "username": "newemp",
        "password": "password123",
        "division_name": "R&D" # New division
    }
    
    # Mock the division service to simulate creating a new division
    mock_division = Division(id=10, name="R&D", company_id=1)
    mock_get_division = patch("app.services.division_service.get_division_by_name_service", return_value=None)
    mock_create_division = patch("app.services.division_service.create_division_service", return_value=mock_division)

    # Mock the user service to simulate successful employee registration
    mock_user = User(
        id=5,
        name="New Employee",
        email="new.employee@example.com",
        username="newemp",
        role="employee",
        company_id=1,
        division_id=10, # Should be the ID of the new division
        is_active=True,
        profile_picture_url=None
    )
    mock_register_user = patch("app.services.user_service.register_employee_by_admin", return_value=mock_user)

    with mock_get_division as m_get, mock_create_division as m_create, mock_register_user as m_register:
        response = admin_client.post("/api/v1/companies/employees/register", data=employee_data)
        
        assert response.status_code == 200
        response_data = response.json()
        
        # Assertions for the response
        assert response_data["name"] == "New Employee"
        assert response_data["email"] == "new.employee@example.com"
        assert response_data["username"] == "newemp"
        assert response_data["role"] == "employee"
        assert response_data["company_id"] == 1
        assert response_data["division_id"] == 10 # Verify the new division ID
        assert response_data["profile_picture_url"] is None

        # Assertions for mock calls
        m_get.assert_called_once_with(ANY, 1, "R&D")
        m_create.assert_called_once_with(db=ANY, division_name="R&D", current_user=ANY)
        m_register.assert_called_once_with(
            db=ANY,
            company_id=1,
            employee_data=ANY, # EmployeeRegistrationByAdmin object
            current_user=ANY,
            profile_picture_file=None
        )

@pytest.mark.asyncio
async def test_register_employee_by_admin_existing_division(override_get_current_company_admin, admin_client):
    # Mock data for the request
    employee_data = {
        "name": "Existing Employee",
        "email": "existing.employee@example.com",
        "username": "exemp",
        "password": "password456",
        "division_name": "Sales" # Existing division
    }
    
    # Mock the division service to simulate using an existing division
    mock_division = Division(id=5, name="Sales", company_id=1)
    mock_get_division = patch("app.services.division_service.get_division_by_name_service", return_value=mock_division)
    mock_create_division = patch("app.services.division_service.create_division_service") # Should not be called

    # Mock the user service to simulate successful employee registration
    mock_user = User(
        id=6,
        name="Existing Employee",
        email="existing.employee@example.com",
        username="exemp",
        role="employee",
        company_id=1,
        division_id=5, # Should be the ID of the existing division
        is_active=True,
        profile_picture_url=None
    )
    mock_register_user = patch("app.services.user_service.register_employee_by_admin", return_value=mock_user)

    with mock_get_division as m_get, mock_create_division as m_create, mock_register_user as m_register:
        response = admin_client.post("/api/v1/companies/employees/register", data=employee_data)
        
        assert response.status_code == 200
        response_data = response.json()
        
        # Assertions for the response
        assert response_data["name"] == "Existing Employee"
        assert response_data["email"] == "existing.employee@example.com"
        assert response_data["username"] == "exemp"
        assert response_data["role"] == "employee"
        assert response_data["company_id"] == 1
        assert response_data["division_id"] == 5 # Verify the existing division ID
        assert response_data["profile_picture_url"] is None

        # Assertions for mock calls
        m_get.assert_called_once_with(ANY, 1, "Sales")
        m_create.assert_not_called() # Ensure create_division_service was not called
        m_register.assert_called_once_with(
            db=ANY,
            company_id=1,
            employee_data=ANY, # EmployeeRegistrationByAdmin object
            current_user=ANY,
            profile_picture_file=None
        )

@pytest.mark.asyncio
async def test_register_employee_by_admin_no_division(override_get_current_company_admin, admin_client):
    # Mock data for the request
    employee_data = {
        "name": "No Division Employee",
        "email": "nodiv.employee@example.com",
        "username": "nodivemp",
        "password": "password789",
        # No division_name or division_id provided
    }
    
    # Mock the user service to simulate successful employee registration with no division
    mock_user = User(
        id=7,
        name="No Division Employee",
        email="nodiv.employee@example.com",
        username="nodivemp",
        role="employee",
        company_id=1,
        division_id=None, # Should be None
        is_active=True,
        profile_picture_url=None
    )
    mock_register_user = patch("app.services.user_service.register_employee_by_admin", return_value=mock_user)

    # Mock division services to ensure they are not called
    mock_get_division = patch("app.services.division_service.get_division_by_name_service")
    mock_create_division = patch("app.services.division_service.create_division_service")

    with mock_get_division as m_get, mock_create_division as m_create, mock_register_user as m_register:
        response = admin_client.post("/api/v1/companies/employees/register", data=employee_data)
        
        assert response.status_code == 200
        response_data = response.json()
        
        # Assertions for the response
        assert response_data["name"] == "No Division Employee"
        assert response_data["email"] == "nodiv.employee@example.com"
        assert response_data["username"] == "nodivemp"
        assert response_data["role"] == "employee"
        assert response_data["company_id"] == 1
        assert response_data["division_id"] is None # Verify division_id is None
        assert response_data["profile_picture_url"] is None

        # Assertions for mock calls
        m_get.assert_not_called()
        m_create.assert_not_called()
        m_register.assert_called_once_with(
            db=ANY,
            company_id=1,
            employee_data=ANY, # EmployeeRegistrationByAdmin object
            current_user=ANY,
            profile_picture_file=None
        )

# --- End of New Test ---
