import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock, ANY
from app.main import app
from app.models.user_model import Users
from app.models.company_model import Company
from app.core.dependencies import get_current_user, get_current_company_admin
from app.schemas.user_schema import User # Import User schema for response model


def test_register_endpoint():
    with TestClient(app) as client:
        # Mock data for registration
        registration_data = {
            "name": "Test User",
            "email": "test@example.com",
            "password": "password123",
            "company_name": "Test Company"
        }
        
        # Mock the user service and company repository
        with patch('app.services.user_service.user_repository.get_user_by_email', return_value=None), \
             patch('app.services.user_service.user_repository.create_user', new_callable=AsyncMock) as mock_create_user, \
             patch('app.services.user_service.company_repository.create_company', new_callable=AsyncMock) as mock_create_company, \
             patch('app.utils.security.get_password_hash', return_value="hashed_password"):
            
            # Set up mock return values
            user_instance = Users(
                id=1,
                name=registration_data["name"],
                email=registration_data["email"],
                username=None,
                password="hashed_password",
                role="admin",
                company_id=1,
                is_super_admin=False
            )
            mock_company = Company(
                id=1,
                name=registration_data["company_name"],
                is_active=False  # Awaiting approval
            )
            mock_create_user.return_value = user_instance
            mock_create_company.return_value = mock_company
            
            response = client.post("/api/auth/register", json=registration_data)
            
            # Check that the request was successful
            assert response.status_code == 201
            expected_message = "Company 'Test Company' and admin user 'test@example.com' registered successfully."
            assert response.json()["message"] == expected_message


def test_login_endpoint():
    with TestClient(app) as client:
        # Mock login data
        login_data = {
            "email": "test@example.com",
            "password": "password123"
        }
        
        # Mock the user service
        with patch('app.services.user_service.authenticate_user', new_callable=AsyncMock) as mock_auth_user:
            # Create a mock user instance
            user_instance = Users(
                id=1,
                name="Test User",
                email="test@example.com",
                username="testuser",
                password="hashed_password",
                role="employee",
                company_id=1,
                is_super_admin=False
            )
            mock_auth_user.return_value = user_instance
            
            # Mock the token creation
            with patch('app.utils.auth.create_access_token', return_value={"access_token": "mock_token", "expires_in": 3600}):
                response = client.post("/api/auth/user/token", json=login_data)
                
                # Check that the request was successful
                assert response.status_code == 200
                assert "access_token" in response.json()
                assert response.json()["token_type"] == "bearer"
                assert "user" in response.json()
                assert response.json()["user"]["id"] == 1
                assert response.json()["user"]["name"] == "Test User"


def test_get_current_user_endpoint():
    with TestClient(app) as client:
        # Mock current user instance
        user_instance = Users(
            id=1,
            name="Test User",
            email="test@example.com",
            username="testuser",
            role="employee",
            company_id=1,
            is_super_admin=False
        )
        
        # Mock company data for the user
        mock_company = Company(
            id=1,
            name="Test Company",
            is_active=True,
            pic_phone_number="+1234567890" # Company PIC phone number
        )
        user_instance.company = mock_company # Associate company with user

        # Use dependency override
        app.dependency_overrides[get_current_user] = lambda: user_instance
        try:
            response = client.get("/api/auth/me", headers={"Authorization": "Bearer mock_token"})
            
            # Check that the request was successful
            assert response.status_code == 200
            assert response.json()["id"] == 1
            assert response.json()["name"] == "Test User"
            assert response.json()["email"] == "test@example.com"
            # Assert that the user's personal pic_phone_number is NOT present
            assert "pic_phone_number" not in response.json() 
            # Assert that the company's pic_phone_number IS present
            assert response.json()["company_pic_phone_number"] == "+1234567890"
            assert response.json()["company_id"] == 1
        finally:
            app.dependency_overrides.clear()
