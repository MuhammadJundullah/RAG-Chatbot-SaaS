import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock
import io

from app.main import app
from app.modules.auth import service as user_service
from app.schemas.user_schema import PaginatedUserResponse
from app.core.s3_client import s3_client_manager

# Assuming conftest.py provides admin_client fixture

# Mock settings for S3 client
MOCK_S3_ENDPOINT_URL = "http://localhost:9000"
MOCK_S3_BUCKET_NAME = "test-bucket"
MOCK_PUBLIC_S3_BASE_URL = "http://example.com/public-s3" # Assuming this might be used elsewhere or for URL construction

@pytest.fixture
def mock_s3_settings_for_test():
    """Mocks S3 related settings for tests."""
    with patch.dict('app.core.config.settings.values', {
        'S3_ENDPOINT_URL': MOCK_S3_ENDPOINT_URL,
        'S3_BUCKET_NAME': MOCK_S3_BUCKET_NAME,
        'PUBLIC_S3_BASE_URL': MOCK_PUBLIC_S3_BASE_URL, # Mock if used in URL construction
    }, clear=True):
        yield

@pytest.mark.asyncio
async def test_register_employee_with_profile_picture(
    admin_client: TestClient,
    mock_db_session: AsyncMock,
    mock_s3_settings_for_test
):
    """
    Tests successful employee registration with a profile picture upload.
    """
    # Mock the user_service.register_employee_by_admin to return a dummy user
    mock_user_data = {
        "id": 10,
        "name": "John Doe",
        "email": "john.doe@example.com",
        "username": "johndoe",
        "role": "employee",
        "company_id": 1,
        "division_id": 1,
        "profile_picture_url": "http://localhost:9000/test-bucket/employee_profile_pictures/1/dummy-uuid-123.jpg",
        "is_active": True
    }
    mock_registered_user = AsyncMock(**mock_user_data)
    
    # Mock the S3 upload call
    mock_s3_upload = AsyncMock(return_value=mock_user_data["profile_picture_url"])
    
    # Patch the service and s3 client manager
    with patch.object(user_service, 'register_employee_by_admin', return_value=mock_registered_user) as mock_register_service, \
         patch.object(s3_client_manager, 'upload_file', new=mock_s3_upload), \
         patch.object(app.dependency_overrides.get('get_db'), '__call__', return_value=mock_db_session): # Mock get_db dependency
        
        # Prepare employee data
        employee_payload = {
            "name": "John Doe",
            "email": "john.doe@example.com",
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
                "email": employee_payload["email"],
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
        assert response_data["email"] == "john.doe@example.com"
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
        
        # Verify S3 upload was called
        mock_s3_upload.assert_called_once()
        # Check arguments passed to S3 upload
        assert mock_s3_upload.call_args[1]["bucket_name"] == MOCK_S3_BUCKET_NAME
        assert mock_s3_upload.call_args[1]["content_type"] == "image/jpeg"
        assert isinstance(mock_s3_upload.call_args[1]["file_object"], io.BytesIO)


@pytest.mark.asyncio
async def test_register_employee_without_profile_picture(
    admin_client: TestClient,
    mock_db_session: AsyncMock,
    mock_s3_settings_for_test
):
    """
    Tests successful employee registration without a profile picture.
    """
    mock_user_data = {
        "id": 11,
        "name": "Jane Smith",
        "email": "jane.smith@example.com",
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
         patch.object(s3_client_manager, 'upload_file') as mock_s3_upload, \
         patch.object(app.dependency_overrides.get('get_db'), '__call__', return_value=mock_db_session):
        
        employee_payload = {
            "name": "Jane Smith",
            "email": "jane.smith@example.com",
            "username": "janesmith",
            "password": "securepassword456",
            "division_id": 1
        }
        
        # Make the request using form data for employee fields
        response = admin_client.post(
            "/companies/employees/register",
            data={
                "name": employee_payload["name"],
                "email": employee_payload["email"],
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
        mock_register_service.assert_called_once_with(
            db=mock_db_session,
            company_id=1,
            employee_data=pytest.approx(employee_payload), # Pydantic model constructed from form fields
            profile_picture_file=None # Ensure file is None
        )
        
        # Verify S3 upload was NOT called
        mock_s3_upload.assert_not_called()


@pytest.mark.asyncio
async def test_register_employee_duplicate_email(
    admin_client: TestClient,
    mock_db_session: AsyncMock,
    mock_s3_settings_for_test
):
    """
    Tests employee registration when the email already exists.
    """
    # Mock the user_service to raise an error
    with patch.object(user_service, 'register_employee_by_admin', side_effect=user_service.UserRegistrationError("Email is already registered.")) as mock_register_service, \
         patch.object(s3_client_manager, 'upload_file') as mock_s3_upload, \
         patch.object(app.dependency_overrides.get('get_db'), '__call__', return_value=mock_db_session):
        
        employee_payload = {
            "name": "Existing User",
            "email": "existing@example.com",
            "username": "existinguser",
            "password": "password",
            "division_id": 1
        }
        
        # Send as form data
        response = admin_client.post(
            "/companies/employees/register",
            data={
                "name": employee_payload["name"],
                "email": employee_payload["email"],
                "username": employee_payload["username"],
                "password": employee_payload["password"],
                "division_id": employee_payload["division_id"],
            }
        )
        
        assert response.status_code == 400 # Expecting Bad Request for registration errors
        assert response.json()["detail"] == "Email is already registered."
        
        mock_register_service.assert_called_once()
        mock_s3_upload.assert_not_called()


@pytest.mark.asyncio
async def test_register_employee_s3_upload_failure(
    admin_client: TestClient,
    mock_db_session: AsyncMock,
    mock_s3_settings_for_test
):
    """
    Tests employee registration when S3 upload fails.
    """
    # Mock S3 upload to fail
    mock_s3_upload_failure = Exception("S3 upload failed")
    
    # Mock the user_service to raise an error during S3 upload
    # The service itself should catch the S3 error and raise UserRegistrationError
    with patch.object(user_service, 'register_employee_by_admin', side_effect=user_service.UserRegistrationError(f"Failed to upload profile picture: {mock_s3_upload_failure}")) as mock_register_service, \
         patch.object(s3_client_manager, 'upload_file', side_effect=mock_s3_upload_failure) as mock_s3_upload, \
         patch.object(app.dependency_overrides.get('get_db'), '__call__', return_value=mock_db_session):
        
        employee_payload = {
            "name": "John Doe",
            "email": "john.doe@example.com",
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
                "email": employee_payload["email"],
                "username": employee_payload["username"],
                "password": employee_payload["password"],
                "division_id": employee_payload["division_id"],
            }, # Using form data for file upload
            files={"profile_picture_file": (dummy_image_file.filename, dummy_image_file, dummy_image_file.content_type)}
        )
        
        assert response.status_code == 400 # Expecting Bad Request for upload failure
        assert "Failed to upload profile picture" in response.json()["detail"]
        
        mock_register_service.assert_called_once() # Service should still be called to attempt upload
        mock_s3_upload.assert_called_once() # S3 upload should be attempted

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
            id=1, name="User One", email="user1@example.com", username="userone",
            role="employee", company_id=1, division="HR", is_active=True, profile_picture_url=None
        ),
        user_schema.User(
            id=2, name="User Two", email="user2@example.com", username="usertwo",
            role="employee", company_id=1, division="IT", is_active=True, profile_picture_url=None
        ),
        user_schema.User(
            id=3, name="Admin User", email="admin@example.com", username="adminuser",
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
