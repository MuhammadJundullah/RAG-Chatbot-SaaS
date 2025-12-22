import pytest
from unittest.mock import patch, ANY
from app.models.user_model import Users
from app.main import app
from app.models.company_model import Company
from app.core.dependencies import get_current_user, get_current_company_admin, get_current_super_admin, get_current_employee
from datetime import datetime
import uuid
from app.modules.auth.service import EmployeeDeletionError, EmployeeUpdateError
from app.schemas.user_schema import User, PaginatedUserResponse  # Import User schema for mock response

# --- Helper Fixtures for Dependency Overrides ---

@pytest.fixture
def override_get_current_user_as_admin():
    mock_user = Users(id=1, company_id=1, role='admin', is_active=True)
    app.dependency_overrides[get_current_user] = lambda: mock_user
    yield
    app.dependency_overrides.clear()

@pytest.fixture
def override_get_current_company_admin():
    mock_admin = Users(id=1, company_id=1, role='admin', is_active=True)
    app.dependency_overrides[get_current_company_admin] = lambda: mock_admin
    yield
    app.dependency_overrides.clear()

@pytest.fixture
def override_get_current_super_admin():
    mock_super_admin = Users(id=999, company_id=None, role='super_admin', is_active=True)
    app.dependency_overrides[get_current_super_admin] = lambda: mock_super_admin
    yield
    app.dependency_overrides.clear()


# --- Test Functions ---

def test_read_my_company(admin_client):
    mock_company = Company(id=1, name="Test Company", code="TC", is_active=True)
    employee = Users(id=1, company_id=1, role='employee', is_active=True)
    app.dependency_overrides[get_current_employee] = lambda: employee
    try:
        with patch('app.modules.company.service.get_company_by_user_service', return_value=mock_company):
            response = admin_client.get("/api/companies/")
            assert response.status_code == 200
            assert response.json()["name"] == "Test Company"
    finally:
        app.dependency_overrides.pop(get_current_employee, None)


def test_get_company_users_endpoint(admin_client):
    mock_users = [
        User(id=1, name="Admin User", company_id=1, role='admin', is_active=True),
        User(id=2, name="Employee User", company_id=1, role='employee', is_active=True)
    ]
    mock_response = PaginatedUserResponse(users=mock_users, total_users=2, current_page=1, total_pages=1)
    with patch('app.modules.company.service.get_company_users_paginated', return_value=mock_response):
        response = admin_client.get("/api/companies/users?page=1&limit=20")
        assert response.status_code == 200
        data = response.json()
        assert data['total_users'] == 2
        assert data['current_page'] == 1
        assert len(data['users']) == 2


def test_update_my_company(admin_client):
    update_data = {"name": "Updated Company", "code": "UC"}
    # Service returns tuple (company, admin) in real flow
    mock_updated_company = Company(id=1, name="Updated Company", code="UC", is_active=True)
    mock_admin = Users(id=1, company_id=1, role='admin', is_active=True)
    with patch('app.modules.company.service.update_company_by_admin_service', return_value=(mock_updated_company, mock_admin)):
        response = admin_client.put("/api/companies/me", data=update_data)
        assert response.status_code == 200
        assert response.json()["name"] == "Updated Company"


def test_get_active_companies(super_admin_client):
    mock_companies = [
        Company(id=1, name="Active Co 1", code="AC1", is_active=True),
        Company(id=2, name="Active Co 2", code="AC2", is_active=True)
    ]
    with patch('app.modules.company.service.get_active_companies_service', return_value=mock_companies):
        response = super_admin_client.get("/api/companies/active")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2


def test_get_pending_approval_companies(super_admin_client):
    mock_companies = [
        Company(id=3, name="Pending Co 1", code="PC1", is_active=False),
        Company(id=4, name="Pending Co 2", code="PC2", is_active=False)
    ]
    with patch('app.modules.company.service.get_pending_approval_companies_service', return_value=mock_companies):
        response = super_admin_client.get("/api/companies/pending-approval")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2

@pytest.mark.asyncio
async def test_delete_employee_by_admin_success(override_get_current_company_admin, admin_client):
    with patch("app.modules.auth.service.delete_employee_by_admin", return_value=None) as mock_delete_service:
        response = admin_client.delete("/api/companies/employees/2")
        assert response.status_code == 204
        mock_delete_service.assert_called_once_with(db=ANY, company_id=1, employee_id=2)

@pytest.mark.asyncio
async def test_delete_employee_by_admin_not_found(override_get_current_company_admin, admin_client):
    with patch("app.modules.auth.service.delete_employee_by_admin", side_effect=EmployeeDeletionError(detail="Employee not found.", status_code=404)) as mock_delete_service:
        response = admin_client.delete("/api/companies/employees/999")
        assert response.status_code == 404
        assert response.json() == {"detail": "Employee not found."}
        mock_delete_service.assert_called_once_with(db=ANY, company_id=1, employee_id=999)

@pytest.mark.asyncio
async def test_delete_employee_by_admin_unauthorized(override_get_current_company_admin, admin_client):
    with patch("app.modules.auth.service.delete_employee_by_admin", side_effect=EmployeeDeletionError(detail="Not authorized to delete this employee.", status_code=403)) as mock_delete_service:
        response = admin_client.delete("/api/companies/employees/3")
        assert response.status_code == 403
        assert response.json() == {"detail": "Not authorized to delete this employee."}
        mock_delete_service.assert_called_once_with(db=ANY, company_id=1, employee_id=3)

# --- New Test for Employee Registration ---

@pytest.mark.asyncio
@pytest.mark.parametrize("division_name, expected_division", [
    ("R&D", "R&D"),
    ("Sales", "Sales"),
    (None, None)
])
async def test_register_employee_by_admin(override_get_current_company_admin, admin_client, division_name, expected_division):
    # Mock data for the request
    employee_data = {
        "name": "New Employee",
        "username": "newemp",
        "password": "password123",
    }
    if division_name:
        employee_data["division"] = division_name

    # Mock the user service to simulate successful employee registration
    mock_user = User(
        id=5,
        name="New Employee",
        username="newemp",
        role="employee",
        company_id=1,
        division=expected_division,
        is_active=True,
        profile_picture_url=None
    )
    mock_register_user = patch("app.modules.auth.service.register_employee_by_admin", return_value=mock_user)

    with mock_register_user as m_register:
        response = admin_client.post("/api/companies/employees/register", data=employee_data)
        
        assert response.status_code == 200
        response_data = response.json()
        
        # Assertions for the response
        assert response_data["name"] == "New Employee"
        assert response_data["division"] == expected_division

        # Assertions for mock calls
        m_register.assert_called_once_with(
            db=ANY,
            company_id=1,
            employee_data=ANY, # EmployeeRegistrationByAdmin object
            current_user=ANY,
            profile_picture_file=None
        )

# --- End of New Test ---

@pytest.mark.asyncio
@pytest.mark.parametrize("update_data, expected_name, expected_division", [
    ({"name": "Updated Name"}, "Updated Name", "Engineering"),
    ({"division": "HR"}, "Test Employee", "HR"),
])
async def test_update_employee_by_admin(override_get_current_company_admin, admin_client, update_data, expected_name, expected_division):
    employee_id = 2
    mock_updated_user = User(
        id=employee_id,
        name=expected_name,
        username="testemp",
        role="employee",
        company_id=1,
        division=expected_division,
        is_active=True,
        profile_picture_url=None
    )

    with patch("app.modules.auth.service.update_employee_by_admin", return_value=mock_updated_user) as mock_update_service:
        response = admin_client.put(f"/api/companies/employees/{employee_id}", data=update_data)
        
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["name"] == expected_name
        assert response_data["division"] == expected_division
        mock_update_service.assert_called_once()

@pytest.mark.asyncio
async def test_update_employee_not_found(override_get_current_company_admin, admin_client):
    employee_id = 999
    update_data = {"name": "Any Name"}
    with patch("app.modules.auth.service.update_employee_by_admin", side_effect=EmployeeUpdateError(detail="Employee not found", status_code=404)):
        response = admin_client.put(f"/api/companies/employees/{employee_id}", data=update_data)
        assert response.status_code == 404
        assert response.json() == {"detail": "Employee not found"}
