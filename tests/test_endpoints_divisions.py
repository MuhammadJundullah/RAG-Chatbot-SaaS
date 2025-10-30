import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock
from app.main import app
from app.models.user_model import Users
from app.models.division_model import Divisions


def test_create_division_endpoint():
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
        
        # Mock new division
        mock_division = Divisions(
            id=1,
            name="New Division",
            company_id=1
        )
        
        # Mock the dependencies and repository
        with patch('app.api.v1.endpoints.divisions.get_current_company_admin', return_value=mock_user), \
             patch('app.repository.division_repository.create_division', new_callable=AsyncMock) as mock_create_division:
            
            mock_create_division.return_value = mock_division
            
            # Send division creation data
            division_data = {
                "name": "New Division"
            }
            
            response = client.post(
                "/api/divisions/", 
                json=division_data,
                headers={"Authorization": "Bearer mock_token"}
            )
            
            # Check that the request was successful
            assert response.status_code == 200
            assert response.json()["id"] == 1
            assert response.json()["name"] == "New Division"
            assert response.json()["company_id"] == 1


def test_get_divisions_endpoint():
    with TestClient(app) as client:
        # Mock current user
        mock_user = Users(
            id=1,
            name="Test User",
            email="test@example.com",
            username="testuser",
            role="employee",
            company_id=1,
            is_active=True
        )
        
        # Mock divisions
        mock_divisions = [
            Divisions(
                id=1,
                name="Division 1",
                company_id=1
            ),
            Divisions(
                id=2,
                name="Division 2",
                company_id=1
            )
        ]
        
        # Mock the dependencies and repository
        with patch('app.api.v1.endpoints.divisions.get_current_user', return_value=mock_user), \
             patch('app.repository.division_repository.get_divisions_by_company', new_callable=AsyncMock) as mock_get_divisions:
            
            mock_get_divisions.return_value = mock_divisions
            
            response = client.get("/api/divisions/", headers={"Authorization": "Bearer mock_token"})
            
            # Check that the request was successful
            assert response.status_code == 200
            assert len(response.json()) == 2
            assert response.json()[0]["id"] == 1
            assert response.json()[1]["id"] == 2


def test_get_public_divisions_endpoint():
    with TestClient(app) as client:
        # Mock divisions
        mock_divisions = [
            Divisions(
                id=1,
                name="Public Division 1",
                company_id=1
            ),
            Divisions(
                id=2,
                name="Public Division 2",
                company_id=1
            )
        ]
        
        # Mock the repository
        with patch('app.repository.division_repository.get_divisions_by_company', new_callable=AsyncMock) as mock_get_divisions:
            
            mock_get_divisions.return_value = mock_divisions
            
            response = client.get("/api/divisions/public/1")  # Public endpoint, no auth required
            
            # Check that the request was successful
            assert response.status_code == 200
            assert len(response.json()) == 2
            assert response.json()[0]["id"] == 1
            assert response.json()[1]["id"] == 2
