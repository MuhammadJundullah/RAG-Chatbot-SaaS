import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock, ANY # Added ANY
from fastapi import HTTPException # Added HTTPException
from app.main import app
from app.models.document_model import Documents, DocumentStatus
from app.models.user_model import Users


def test_get_documents_endpoint(authenticated_client: TestClient):
    # Mock documents
    mock_document = Documents(
        id=1,
        title="Test Document",
        company_id=1,
        status=DocumentStatus.UPLOADED,
        content_type="application/pdf"
    )
    
    # Mock the repository
    with patch('app.repository.document_repository.get_documents_by_company', new_callable=AsyncMock) as mock_get_docs:
        mock_get_docs.return_value = [mock_document]
        
        response = authenticated_client.get("/api/documents/")
        
        # Check that the request was successful
        assert response.status_code == 200
        assert len(response.json()) == 1
        assert response.json()[0]["id"] == 1
        assert response.json()[0]["title"] == "Test Document"


def test_get_single_document_endpoint(authenticated_client: TestClient):
    # Mock document
    mock_document = Documents(
        id=1,
        title="Test Document",
        company_id=1,
        status=DocumentStatus.UPLOADED,
        content_type="application/pdf"
    )
    
    # Mock the repository
    with patch('app.repository.document_repository.get_document', new_callable=AsyncMock) as mock_get_doc:
        mock_get_doc.return_value = mock_document
        
        response = authenticated_client.get("/api/documents/1")
        
        # Check that the request was successful
        assert response.status_code == 200
        assert response.json()["id"] == 1
        assert response.json()["title"] == "Test Document"


def test_upload_document_endpoint(authenticated_client: TestClient):
    # Mock document
    mock_document = Documents(
        id=1,
        title="test_file.txt",
        company_id=1,
        status=DocumentStatus.UPLOADING,
        content_type="text/plain"
    )
    
    # Mock the repository
    with patch('app.repository.document_repository.create_document', new_callable=AsyncMock) as mock_create_doc:
        mock_create_doc.return_value = mock_document
        
        # Create a mock file
        test_file_content = b"This is a test file."
        
        response = authenticated_client.post(
            "/api/documents/upload", 
            files={"file": ("test_file.txt", test_file_content, "text/plain")}
        )
        
        # Check that the request was successful
        assert response.status_code == 202  # Accepted
        assert response.json()["id"] == 1
        assert response.json()["title"] == "test_file.txt"
        assert response.json()["status"] == "UPLOADING"


def test_delete_document_endpoint(authenticated_client: TestClient):
    # Mock the repository
    with patch('app.repository.document_repository.get_document', new_callable=AsyncMock) as mock_get_doc, \
         patch('app.repository.document_repository.delete_document', new_callable=AsyncMock) as mock_delete_doc:
        
        mock_get_doc.return_value = Documents(
            id=1,
            title="Test Document",
            company_id=1,
            status=DocumentStatus.COMPLETED,
            content_type="application/pdf"
        )
        
        response = authenticated_client.delete("/api/documents/1")
        
        # Check that the request was successful
        assert response.status_code == 204  # No Content

# --- New tests for admin-only document retrieval ---

def test_admin_can_get_single_document(authenticated_client: TestClient):
    """
    Test that an admin user can successfully retrieve a single document by its ID.
    """
    mock_document = Documents(
        id=1,
        title="Admin Document",
        company_id=1,
        status=DocumentStatus.COMPLETED,
        content_type="application/pdf"
    )
    # Mock a user that is an admin
    mock_admin_user = Users(id=1, email="admin@example.com", company_id=1, is_admin=True) # Simplified mock user

    # Mock the repository and the dependency
    with patch('app.repository.document_repository.get_document', return_value=mock_document) as mock_get_doc, \
         patch('app.core.dependencies.get_current_company_admin', return_value=mock_admin_user) as mock_get_admin:

        response = authenticated_client.get("/api/documents/1")

        assert response.status_code == 200
        assert response.json()["id"] == 1
        assert response.json()["title"] == "Admin Document"
        # Assuming get_document takes db session and document_id
        mock_get_doc.assert_awaited_once_with(ANY, 1)
        mock_get_admin.assert_awaited_once()

def test_non_admin_cannot_get_single_document(authenticated_client: TestClient):
    """
    Test that a non-admin user is denied access to retrieve a single document by its ID.
    """
    # Mock a user that is NOT an admin
    mock_regular_user = Users(id=2, email="user@example.com", company_id=1, is_admin=False) # Simplified mock user

    # Mock the dependency to raise an HTTPException for non-admins
    with patch('app.core.dependencies.get_current_company_admin', side_effect=HTTPException(status_code=403, detail="Not enough permissions")) as mock_get_admin:

        response = authenticated_client.get("/api/documents/1")

        assert response.status_code == 403
        mock_get_admin.assert_awaited_once()

def test_get_single_document_not_found(authenticated_client: TestClient):
    """
    Test that a 404 is returned if the document ID does not exist.
    """
    # Mock a user that is an admin
    mock_admin_user = Users(id=1, email="admin@example.com", company_id=1, is_admin=True) # Simplified mock user

    # Mock the repository to return None (document not found)
    with patch('app.repository.document_repository.get_document', return_value=None) as mock_get_doc, \
         patch('app.core.dependencies.get_current_company_admin', return_value=mock_admin_user) as mock_get_admin:

        response = authenticated_client.get("/api/documents/999") # Non-existent ID

        assert response.status_code == 404
        # Assuming get_document takes db session and document_id
        mock_get_doc.assert_awaited_once_with(ANY, 999)
        mock_get_admin.assert_awaited_once()