import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock
from app.main import app
from app.models.document_model import Documents, DocumentStatus
from app.models.user_model import Users


def test_get_documents_endpoint():
    with TestClient(app) as client:
        # Mock current user
        mock_user = Users(
            id=1,
            name="Test User",
            email="test@example.com",
            username="testuser",
            role="admin",
            company_id=1,
            is_active=True
        )
        
        # Mock documents
        mock_document = Documents(
            id=1,
            title="Test Document",
            company_id=1,
            status=DocumentStatus.UPLOADED,
            content_type="application/pdf"
        )
        
        # Mock the dependencies and repository
        with patch('app.api.v1.endpoints.documents.get_current_company_admin', return_value=mock_user), \
             patch('app.repository.document_repository.get_documents_by_company', new_callable=AsyncMock) as mock_get_docs:
            
            mock_get_docs.return_value = [mock_document]
            
            response = client.get("/api/documents/", headers={"Authorization": "Bearer mock_token"})
            
            # Check that the request was successful
            assert response.status_code == 200
            assert len(response.json()) == 1
            assert response.json()[0]["id"] == 1
            assert response.json()[0]["title"] == "Test Document"


def test_get_single_document_endpoint():
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
        
        # Mock document
        mock_document = Documents(
            id=1,
            title="Test Document",
            company_id=1,
            status=DocumentStatus.UPLOADED,
            content_type="application/pdf"
        )
        
        # Mock the dependencies and repository
        with patch('app.api.v1.endpoints.documents.get_current_user', return_value=mock_user), \
             patch('app.repository.document_repository.get_document', new_callable=AsyncMock) as mock_get_doc:
            
            mock_get_doc.return_value = mock_document
            
            response = client.get("/api/documents/1", headers={"Authorization": "Bearer mock_token"})
            
            # Check that the request was successful
            assert response.status_code == 200
            assert response.json()["id"] == 1
            assert response.json()["title"] == "Test Document"


def test_upload_document_endpoint():
    with TestClient(app) as client:
        # Mock current user
        mock_user = Users(
            id=1,
            name="Test User",
            email="test@example.com",
            username="testuser",
            role="admin",
            company_id=1,
            is_active=True
        )
        
        # Mock document
        mock_document = Documents(
            id=1,
            title="test_file.txt",
            company_id=1,
            status=DocumentStatus.UPLOADING,
            content_type="text/plain"
        )
        
        # Mock the dependencies and repository
        with patch('app.api.v1.endpoints.documents.get_current_company_admin', return_value=mock_user), \
             patch('app.repository.document_repository.create_document', new_callable=AsyncMock) as mock_create_doc:
            
            mock_create_doc.return_value = mock_document
            
            # Create a mock file
            test_file_content = b"This is a test file."
            
            response = client.post(
                "/api/documents/upload", 
                files={"file": ("test_file.txt", test_file_content, "text/plain")},
                headers={"Authorization": "Bearer mock_token"}
            )
            
            # Check that the request was successful
            assert response.status_code == 202  # Accepted
            assert response.json()["id"] == 1
            assert response.json()["title"] == "test_file.txt"
            assert response.json()["status"] == "UPLOADING"


def test_delete_document_endpoint():
    with TestClient(app) as client:
        # Mock current user
        mock_user = Users(
            id=1,
            name="Test User",
            email="test@example.com",
            username="testuser",
            role="admin",
            company_id=1,
            is_active=True
        )
        
        # Mock the dependencies and repository
        with patch('app.api.v1.endpoints.documents.get_current_company_admin', return_value=mock_user), \
             patch('app.repository.document_repository.get_document', new_callable=AsyncMock) as mock_get_doc, \
             patch('app.repository.document_repository.delete_document', new_callable=AsyncMock) as mock_delete_doc:
            
            mock_get_doc.return_value = Documents(
                id=1,
                title="Test Document",
                company_id=1,
                status=DocumentStatus.COMPLETED,
                content_type="application/pdf"
            )
            
            response = client.delete("/api/documents/1", headers={"Authorization": "Bearer mock_token"})
            
            # Check that the request was successful
            assert response.status_code == 204  # No Content
