import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock, ANY # Added ANY
from app.main import app
from app.models.user_model import Users
from app.models.company_model import Company
from app.core.dependencies import get_current_company_admin


def test_get_company_me_endpoint():
    with TestClient(app) as client:
        # Mock current user (company admin)
        mock_user = Users(
            id=1,
            name="Admin User",
            email="admin@example.com",
            username="adminuser",
            role="admin",
            company_id=1,
            is_super_admin=False
        )
        
        # Mock company
        mock_company = Company(
            id=1,
            name="Test Company",
            is_active=True,
            pic_phone_number="+1234567890" # Added pic_phone_number
        )
        
        # Use dependency override
        app.dependency_overrides[get_current_company_admin] = lambda: mock_user
        try:
            # Mock the repository
            with patch('app.repository.company_repository.get_company', new_callable=AsyncMock) as mock_get_company:
                mock_get_company.return_value = mock_company
                
                response = client.get("/api/companies/me", headers={"Authorization": "Bearer mock_token"})
                
                # Check that the request was successful
                assert response.status_code == 200
                assert response.json()["id"] == 1
                assert response.json()["name"] == "Test Company"
                assert response.json()["pic_phone_number"] == "+1234567890" # Added assertion for pic_phone_number        finally:
            app.dependency_overrides.clear()


def test_get_company_users_endpoint():
    with TestClient(app) as client:
        # Mock current user (company admin)
        mock_user = Users(
            id=1,
            name="Admin User",
            email="admin@example.com",
            username="adminuser",
            role="admin",
            company_id=1,
            is_super_admin=False
        )
        
        # Mock company users
        mock_users = [
            Users(
                id=1,
                name="Admin User",
                email="admin@example.com",
                username="adminuser",
                role="admin",
                company_id=1,
                is_super_admin=False
            ),
            Users(
                id=2,
                name="Employee User",
                email="employee@example.com",
                username="empuser",
                role="employee",
                company_id=1,
                is_super_admin=False
            )
        ]
        
        # Use dependency override
        app.dependency_overrides[get_current_company_admin] = lambda: mock_user
        try:
            with patch('sqlalchemy.ext.asyncio.AsyncSession.execute', new_callable=AsyncMock) as mock_execute:
                # Mock the result of the query
                mock_result = AsyncMock()
                mock_result.scalars.return_value.all.return_value = mock_users
                mock_execute.return_value = mock_result
                
                response = client.get("/api/companies/users", headers={"Authorization": "Bearer mock_token"})
                
                # Check that the request was successful
                assert response.status_code == 200
                assert len(response.json()) == 2
                assert response.json()[0]["id"] == 1
                assert response.json()[1]["id"] == 2
        finally:
            app.dependency_overrides.clear()


def test_register_employee_endpoint():
    with TestClient(app) as client:
        # Mock current user (company admin)
        mock_user = Users(
            id=1,
            name="Admin User",
            email="admin@example.com",
            username="adminuser",
            role="admin",
            company_id=1,
            is_super_admin=False
        )
        
        # Mock new employee
        mock_employee = Users(
            id=2,
            name="New Employee",
            email="newemp@example.com",
            username="newempuser",
            password="hashed_password",
            role="employee",
            company_id=1,
            is_super_admin=False
        )
        
        # Use dependency override
        app.dependency_overrides[get_current_company_admin] = lambda: mock_user
        try:
            # Mock the service
            with patch('app.services.user_service.register_employee_by_admin', new_callable=AsyncMock) as mock_register_employee:
                mock_register_employee.return_value = mock_employee
                
                # Send employee registration data
                employee_data = {
                    "name": "New Employee",
                    "email": "newemp@example.com",
                    "password": "password123",
                    "username": "newempuser"
                }
                
                response = client.post(
                    "/api/companies/employees/register", 
                    json=employee_data,
                    headers={"Authorization": "Bearer mock_token"}
                )
                
                # Check that the request was successful
                assert response.status_code == 201
                assert response.json()["id"] == 2
                assert response.json()["name"] == "New Employee"
                assert response.json()["role"] == "employee"
                assert response.json()["company_id"] == 1
        finally:
            app.dependency_overrides.clear()

# --- New test for updating company details ---

def test_update_my_company_endpoint():
    with TestClient(app) as client:
        # Mock current user (company admin)
        mock_user = Users(
            id=1,
            name="Admin User",
            email="admin@example.com",
            username="adminuser",
            role="admin",
            company_id=1,
            is_super_admin=False
        )
        
        # Mock updated company data
        updated_company_data = {
            "name": "Updated Company Name",
            "code": "UPD",
            "address": "123 Updated St",
            "pic_phone_number": "+1987654321" # New PIC phone number
        }
        
        # Mock the updated company object returned by the repository
        mock_updated_company = Company(
            id=1,
            name="Updated Company Name",
            code="UPD",
            address="123 Updated St",
            pic_phone_number="+1987654321", # Include pic_phone_number
            is_active=True,
            logo_s3_path="http://example.com/logo.png" # Keep existing logo path
        )
        
        # Use dependency override
        app.dependency_overrides[get_current_company_admin] = lambda: mock_user
        try:
            # Mock the service call
            with patch('app.services.company_service.update_my_company_service', new_callable=AsyncMock) as mock_update_service:
                mock_update_service.return_value = mock_updated_company
                
                # Send company update data
                response = client.put(
                    "/api/companies/me", 
                    data={
                        "name": "Updated Company Name",
                        "code": "UPD",
                        "address": "123 Updated St",
                        "pic_phone_number": "+1987654321" # Send pic_phone_number in form data
                    },
                    headers={"Authorization": "Bearer mock_token"}
                )
                
                # Check that the request was successful
                assert response.status_code == 200
                assert response.json()["id"] == 1
                assert response.json()["name"] == "Updated Company Name"
                assert response.json()["code"] == "UPD"
                assert response.json()["address"] == "123 Updated St"
                assert response.json()["pic_phone_number"] == "+1987654321" # Assert updated pic_phone_number
                assert response.json()["logo_s3_path"] == "http://example.com/logo.png" # Ensure logo path is preserved

                # Verify the service was called correctly
                mock_update_service.assert_awaited_once_with(
                    db=ANY, # Assuming db is passed implicitly or handled by fixture
                    current_user=mock_user,
                    name="Updated Company Name",
                    code="UPD",
                    address="123 Updated St",
                    logo_file=None, # No logo file uploaded in this test
                    pic_phone_number="+1987654321" # Verify pic_phone_number was passed
                )
        finally:
            app.dependency_overrides.clear()
