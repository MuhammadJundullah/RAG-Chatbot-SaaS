import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock
import io

from app.main import app
from app.modules.auth import service as user_service
from app.schemas.user_schema import PaginatedUserResponse

# Assuming conftest.py provides admin_client fixture

@pytest.mark.asyncio
async def test_register_employee_with_profile_picture(
    admin_client: TestClient,
    mock_db_session: AsyncMock,
):
    """
    Tests successful employee registration with a profile picture upload.
    """
    # Mock the user_service.register_employee_by_admin to return a dummy user
    mock_user_data = {
        "id": 10,
        "name": "John Doe",
        "username": "johndoe",
        "role": "employee",
        "company_id": 1,
        "division_id": 1,
        "profile_picture_url": "http://localhost:9000/test-bucket/employee_profile_pictures/1/dummy-uuid-123.jpg",
        "is_active": True
    }
    mock_registered_user = AsyncMock(**mock_user_data)
    
    # Patch the service call to avoid hitting real dependencies
    with patch.object(user_service, 'register_employee_by_admin', return_value=mock_registered_user) as mock_register_service, \
         patch.object(app.dependency_overrides.get('get_db'), '__call__', return_value=mock_db_session): # Mock get_db dependency
        
        # Prepare employee data
        employee_payload = {
            "name": "John Doe",
            "username": "johndoe",
            "password": "securepassword123",
            "division_id": 1
        }
        
        # Prepare dummy profile picture file
        dummy_image_content = b"fake image data"
        dummy_image_file = io.BytesIO(dummy_image_content)
        dummy_image_file.filename = "profile.jpg"
        dummy_image_file.content_type = "image/jpeg"

        # Make the request using form data for file upload
        response = admin_client.post(
            "/companies/employees/register",
            data={
                "name": employee_payload["name"],
                "username": employee_payload["username"],
                "password": employee_payload["password"],
                "division_id": employee_payload["division_id"],
            },
            files={"profile_picture_file": (dummy_image_file.filename, dummy_image_file, dummy_image_file.content_type)}
        )
        
        # Assertions
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["name"] == "John Doe"
        assert response_data["profile_picture_url"] == mock_user_data["profile_picture_url"]
        
        # Verify service was called correctly
        mock_register_service.assert_called_once()
        # Check arguments passed to the service
        # The company_id is derived from the admin_client's mock user (id=2, company_id=1)
        # employee_data is constructed from form fields
        assert mock_register_service.call_args[1]["db"] == mock_db_session
        assert mock_register_service.call_args[1]["company_id"] == 1
        assert isinstance(mock_register_service.call_args[1]["employee_data"], user_service.user_schema.EmployeeRegistrationByAdmin)
        assert mock_register_service.call_args[1]["employee_data"].name == "John Doe"
        assert mock_register_service.call_args[1]["profile_picture_file"] is not None # File object should be passed


@pytest.mark.asyncio
async def test_register_employee_without_profile_picture(
    admin_client: TestClient,
    mock_db_session: AsyncMock,
):
    """
    Tests successful employee registration without a profile picture.
    """
    mock_user_data = {
        "id": 11,
        "name": "Jane Smith",
        "username": "janesmith",
        "role": "employee",
        "company_id": 1,
        "division_id": 1,
        "profile_picture_url": None, # No profile picture
        "is_active": True
    }
    mock_registered_user = AsyncMock(**mock_user_data)
    
    # Mock the user_service.register_employee_by_admin
    with patch.object(user_service, 'register_employee_by_admin', return_value=mock_registered_user) as mock_register_service, \
         patch.object(app.dependency_overrides.get('get_db'), '__call__', return_value=mock_db_session):
        
        employee_payload = {
            "name": "Jane Smith",
            "username": "janesmith",
            "password": "securepassword456",
            "division_id": 1
        }
        
        # Make the request using form data for employee fields
        response = admin_client.post(
            "/companies/employees/register",
            data={
                "name": employee_payload["name"],
                "username": employee_payload["username"],
                "password": employee_payload["password"],
                "division_id": employee_payload["division_id"],
            }
        )
        
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["name"] == "Jane Smith"
        assert response_data["profile_picture_url"] is None
        
        # Verify service was called correctly
        mock_register_service.assert_called_once()


@pytest.mark.asyncio
async def test_register_employee_duplicate_username(
    admin_client: TestClient,
    mock_db_session: AsyncMock,
):
    """
    Tests employee registration when the username already exists.
    """
    # Mock the user_service to raise an error
    with patch.object(user_service, 'register_employee_by_admin', side_effect=user_service.UserRegistrationError("Username is already registered.")) as mock_register_service, \
         patch.object(app.dependency_overrides.get('get_db'), '__call__', return_value=mock_db_session):
        
        employee_payload = {
            "name": "Existing User",
            "username": "existinguser",
            "password": "password",
            "division_id": 1
        }
        
        # Send as form data
        response = admin_client.post(
            "/companies/employees/register",
            data={
                "name": employee_payload["name"],
                "username": employee_payload["username"],
                "password": employee_payload["password"],
                "division_id": employee_payload["division_id"],
            }
        )
        
        assert response.status_code == 400 # Expecting Bad Request for registration errors
        assert response.json()["detail"] == "Username is already registered."
        
        mock_register_service.assert_called_once()


@pytest.mark.asyncio
async def test_register_employee_upload_failure(
    admin_client: TestClient,
    mock_db_session: AsyncMock,
):
    """
    Tests employee registration when upload fails.
    """
    mock_upload_failure = user_service.UserRegistrationError("Failed to upload profile picture: disk error")

    with patch.object(user_service, 'register_employee_by_admin', side_effect=mock_upload_failure) as mock_register_service, \
         patch.object(app.dependency_overrides.get('get_db'), '__call__', return_value=mock_db_session):
        
        employee_payload = {
            "name": "John Doe",
            "username": "johndoe",
            "password": "securepassword123",
            "division_id": 1
        }
        
        dummy_image_content = b"fake image data"
        dummy_image_file = io.BytesIO(dummy_image_content)
        dummy_image_file.filename = "profile.jpg"
        dummy_image_file.content_type = "image/jpeg"

        response = admin_client.post(
            "/companies/employees/register",
            data={
                "name": employee_payload["name"],
                "username": employee_payload["username"],
                "password": employee_payload["password"],
                "division_id": employee_payload["division_id"],
            }, # Using form data for file upload
            files={"profile_picture_file": (dummy_image_file.filename, dummy_image_file, dummy_image_file.content_type)}
        )
        
        assert response.status_code == 400 # Expecting Bad Request for upload failure
        assert "Failed to upload profile picture" in response.json()["detail"]
        
        mock_register_service.assert_called_once() # Service should still be called to attempt upload

@pytest.mark.asyncio
async def test_get_company_users_by_admin(
    admin_client: TestClient,
    mock_db_session: AsyncMock,
):
    """
    Tests the GET /companies/users endpoint for company administrators.
    """
    # Mock data for users
    mock_users_data = [
        user_schema.User(
            id=1, name="User One", username="userone",
            role="employee", company_id=1, division="HR", is_active=True, profile_picture_url=None
        ),
        user_schema.User(
            id=2, name="User Two", username="usertwo",
            role="employee", company_id=1, division="IT", is_active=True, profile_picture_url=None
        ),
        user_schema.User(
            id=3, name="Admin User", username="adminuser",
            role="admin", company_id=1, division="Management", is_active=True, profile_picture_url=None
        ),
    ]

    # Scenario 1: Get all users, first page
    mock_paginated_response_all = PaginatedUserResponse(
        items=mock_users_data[:2], total=len(mock_users_data), page=1, limit=2
    )
    with patch("app.modules.company.service.get_company_users_paginated", AsyncMock(return_value=mock_paginated_response_all)) as mock_service:
        response = admin_client.get("/companies/users?page=1&limit=2")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == len(mock_users_data)
        assert data["page"] == 1
        assert data["limit"] == 2
        assert len(data["items"]) == 2
        assert data["items"][0]["username"] == "userone"
        mock_service.assert_called_once_with(
            db=mock_db_session, company_id=1, page=1, limit=2, username=None
        )

    # Scenario 2: Filter by username
    mock_paginated_response_filtered = PaginatedUserResponse(
        items=[mock_users_data[0]], total=1, page=1, limit=100
    )
    with patch("app.modules.company.service.get_company_users_paginated", AsyncMock(return_value=mock_paginated_response_filtered)) as mock_service:
        response = admin_client.get("/companies/users?username=userone")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["username"] == "userone"
        mock_service.assert_called_once_with(
            db=mock_db_session, company_id=1, page=1, limit=100, username="userone"
        )

    # Scenario 3: No users found
    mock_paginated_response_empty = PaginatedUserResponse(
        items=[], total=0, page=1, limit=100
    )
    with patch("app.modules.company.service.get_company_users_paginated", AsyncMock(return_value=mock_paginated_response_empty)) as mock_service:
        response = admin_client.get("/companies/users?username=nonexistent")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert len(data["items"]) == 0
        mock_service.assert_called_once_with(
            db=mock_db_session, company_id=1, page=1, limit=100, username="nonexistent"
        )

    # Scenario 4: Internal server error from service
    with patch("app.modules.company.service.get_company_users_paginated", AsyncMock(side_effect=Exception("Service error"))) as mock_service:
        response = admin_client.get("/companies/users")
        assert response.status_code == 500
        assert "Service error" in response.json()["detail"]
        mock_service.assert_called_once()
