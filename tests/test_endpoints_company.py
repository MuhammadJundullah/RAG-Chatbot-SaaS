import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock
from app.main import app
from app.models.user_model import Users
from app.models.company_model import Company


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
            is_active=True
        )
        
        # Mock company
        mock_company = Company(
            id=1,
            name="Test Company",
            is_active=True
        )
        
        # Mock the dependencies and repository
        with patch('app.api.v1.endpoints.company.get_current_company_admin', return_value=mock_user), \
             patch('app.repository.company_repository.get_company', new_callable=AsyncMock) as mock_get_company:
            
            mock_get_company.return_value = mock_company
            
            response = client.get("/api/companies/me", headers={"Authorization": "Bearer mock_token"})
            
            # Check that the request was successful
            assert response.status_code == 200
            assert response.json()["id"] == 1
            assert response.json()["name"] == "Test Company"


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
            is_active=True
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
                is_active=True
            ),
            Users(
                id=2,
                name="Employee User",
                email="employee@example.com",
                username="empuser",
                role="employee",
                company_id=1,
                is_active=True
            )
        ]
        
        # Mock the dependency
        with patch('app.api.v1.endpoints.company.get_current_company_admin', return_value=mock_user), \
             patch('sqlalchemy.ext.asyncio.AsyncSession.execute', new_callable=AsyncMock) as mock_execute:
            
            # Mock the result of the query
            mock_result = AsyncMock()
            mock_result.scalars().all.return_value = mock_users
            mock_execute.return_value = mock_result
            
            response = client.get("/api/companies/users", headers={"Authorization": "Bearer mock_token"})
            
            # Check that the request was successful
            assert response.status_code == 200
            assert len(response.json()) == 2
            assert response.json()[0]["id"] == 1
            assert response.json()[1]["id"] == 2


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
            is_active=True
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
            is_active=True
        )
        
        # Mock the dependencies and services
        with patch('app.api.v1.endpoints.company.get_current_company_admin', return_value=mock_user), \
             patch('app.services.user_service.register_employee_by_admin', new_callable=AsyncMock) as mock_register_employee:
            
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
