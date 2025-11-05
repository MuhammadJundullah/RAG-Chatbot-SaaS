from fastapi.testclient import TestClient
from unittest.mock import patch
from fastapi import HTTPException
from app.main import app
from app.models.document_model import Documents, DocumentStatus


# --- Test Functions using admin_client fixture ---

def test_get_documents_endpoint(admin_client: TestClient):
    mock_document = Documents(
        id=1,
        title="Test Document",
        company_id=1,
        status=DocumentStatus.UPLOADED,
        content_type="application/pdf"
    )
    with patch('app.services.document_service.get_all_company_documents_service', return_value=[mock_document]):
        response = admin_client.get("/api/documents/")
        assert response.status_code == 200
        # The endpoint now returns a paginated response
        assert len(response.json()["documents"]) == 1
        assert response.json()["documents"][0]["id"] == 1


def test_get_single_document_endpoint(admin_client: TestClient):
    mock_document = Documents(
        id=1,
        title="Test Document",
        company_id=1,
        status=DocumentStatus.UPLOADED,
        content_type="application/pdf"
    )
    with patch('app.services.document_service.read_single_document_service', return_value=mock_document):
        response = admin_client.get("/api/documents/1")
        assert response.status_code == 200
        assert response.json()["id"] == 1


def test_upload_document_endpoint(admin_client: TestClient):
    mock_document = Documents(
        id=1,
        title="test_file.txt",
        company_id=1,
        status=DocumentStatus.UPLOADING,
        content_type="text/plain"
    )
    with patch('app.services.document_service.upload_document_service', return_value=mock_document):
        test_file_content = b"This is a test file."
        response = admin_client.post(
            "/api/documents/upload",
            files={"file": ("test_file.txt", test_file_content, "text/plain")},
            data={"name": "test_file.txt", "tags": "tag1,tag2"}
        )
        assert response.status_code == 202
        assert response.json()["id"] == 1


def test_delete_document_endpoint(admin_client: TestClient):
    with patch('app.services.document_service.delete_document_service', return_value=None):
        response = admin_client.delete("/api/documents/1")
        assert response.status_code == 204


def test_admin_can_get_single_document(admin_client: TestClient):
    mock_document = Documents(
        id=1,
        title="Admin Document",
        company_id=1,
        status=DocumentStatus.COMPLETED,
        content_type="application/pdf",
        tags=["admin", "confidential"]
    )
    with patch('app.services.document_service.read_single_document_service', return_value=mock_document):
        response = admin_client.get("/api/documents/1")
        assert response.status_code == 200
        assert response.json()["tags"] == ["admin", "confidential"]


def test_non_admin_cannot_get_single_document():
    # Use a fresh TestClient without admin permissions
    with TestClient(app) as client:
        response = client.get("/api/documents/1")
        # Endpoint might return 401, 403, or 404 if not authorized or not found
        assert response.status_code in [401, 403, 404]


def test_get_single_document_not_found(admin_client: TestClient):
    with patch('app.services.document_service.read_single_document_service', side_effect=HTTPException(status_code=404, detail="Document not found")):
        response = admin_client.get("/api/documents/999")
        assert response.status_code == 404