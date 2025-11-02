import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock, ANY
from fastapi import HTTPException
from app.main import app
from app.models.document_model import Documents, DocumentStatus
from app.models.user_model import Users
from typing import List, Optional # Import List and Optional

# --- Existing tests ---

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
            files={"file": ("test_file.txt", test_file_content, "text/plain")},
            data={"name": "test_file.txt", "tags": "tag1,tag2"} # Added tags for upload test
        )
        
        # Check that the request was successful
        assert response.status_code == 202  # Accepted
        assert response.json()["id"] == 1
        assert response.json()["title"] == "test_file.txt"
        assert response.json()["status"] == "UPLOADING"
        assert response.json()["tags"] == ["tag1", "tag2"] # Check if tags are returned


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
        content_type="application/pdf",
        tags=["admin", "confidential"] # Added tags for admin document
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
        assert response.json()["tags"] == ["admin", "confidential"] # Check if tags are returned
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

# --- New tests for updating document content, title, and tags ---

@pytest.mark.asyncio
async def test_update_document_content_title_and_tags(authenticated_client: TestClient):
    """
    Test that a document's content, title, and tags can be updated successfully.
    """
    document_id = 1
    updated_content = "This is the new, updated content of the document."
    new_title = "Updated Document Title"
    new_tags = ["finance", "report", "2025"]

    # Mock the existing document
    mock_document = Documents(
        id=document_id,
        title="Original Document",
        company_id=1,
        status=DocumentStatus.COMPLETED,
        extracted_text="Original content.",
        tags=["old_tag"]
    )

    # Mock the repository's get_document and update_document_text_and_status methods
    mock_get_doc = AsyncMock(return_value=mock_document)
    # The update method should return the updated document
    mock_updated_doc = mock_document # Create a copy to simulate update
    mock_updated_doc.extracted_text = updated_content
    mock_updated_doc.title = new_title # Update title
    mock_updated_doc.tags = new_tags
    mock_updated_doc.status = DocumentStatus.EMBEDDING # Status is set to EMBEDDING during update
    
    mock_update_repo = AsyncMock(return_value=mock_updated_doc)

    # Mock the RAG service's update_document_content method
    mock_rag_update = AsyncMock(return_value={"status": "success"})

    # Mock the dependency for getting the current user (admin)
    mock_admin_user = Users(id=1, email="admin@example.com", company_id=1, is_admin=True)

    # Patch the dependencies
    with patch('app.repository.document_repository.get_document', new=mock_get_doc) as _, \
         patch('app.repository.document_repository.update_document_text_and_status', new=mock_update_repo) as _, \
         patch('app.services.rag_service.rag_service.update_document_content', new=mock_rag_update) as _, \
         patch('app.core.dependencies.get_current_company_admin', return_value=mock_admin_user) as _:

        # Make the PUT request to update the document
        response = authenticated_client.put(
            f"/api/documents/{document_id}/content",
            json={
                "new_content": updated_content,
                "title": new_title, # Include title in the request
                "tags": new_tags # Include tags in the request
            }
        )

        # Assertions
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["id"] == document_id
        assert response_data["extracted_text"] == updated_content
        assert response_data["title"] == new_title # Check if title was updated
        assert response_data["tags"] == new_tags
        assert response_data["status"] == DocumentStatus.COMPLETED.value # Final status after successful update

        # Verify that the repository methods were called correctly
        mock_get_doc.assert_awaited_once_with(ANY, document_id)
        mock_update_repo.assert_awaited_once_with(
            ANY,
            document_id=document_id,
            text=updated_content,
            status=DocumentStatus.EMBEDDING,
            tags=new_tags, # Ensure tags were passed
            title=new_title # Ensure title was passed
        )

        # Verify that the RAG service method was called correctly
        mock_rag_update.assert_awaited_once_with(
            document_id=str(document_id),
            new_text_content=updated_content,
            company_id=mock_admin_user.company_id,
            title=new_title, # Ensure title was passed to RAG service
            tags=new_tags # Ensure tags were passed to RAG service
        )

def test_update_document_content_with_title_no_tags(authenticated_client: TestClient):
    """
    Test updating document content and title without providing new tags.
    """
    document_id = 1
    updated_content = "Content updated, title changed, no new tags."
    new_title = "New Title Without Tags"
    
    # Mock the existing document with some tags
    mock_document = Documents(
        id=document_id,
        title="Original Document",
        company_id=1,
        status=DocumentStatus.COMPLETED,
        extracted_text="Original content.",
        tags=["existing", "tags"]
    )

    # Mock the repository's get_document and update_document_text_and_status methods
    mock_get_doc = AsyncMock(return_value=mock_document)
    # Simulate update: content and title change, tags remain the same
    mock_updated_doc = mock_document # Create a copy to simulate update
    mock_updated_doc.extracted_text = updated_content
    mock_updated_doc.title = new_title
    # Tags should remain the same as they were not provided in the update
    
    mock_update_repo = AsyncMock(return_value=mock_updated_doc)

    # Mock the RAG service's update_document_content method
    mock_rag_update = AsyncMock(return_value={"status": "success"})

    # Mock the dependency for getting the current user (admin)
    mock_admin_user = Users(id=1, email="admin@example.com", company_id=1, is_admin=True)

    # Patch the dependencies
    with patch('app.repository.document_repository.get_document', new=mock_get_doc) as _, \
         patch('app.repository.document_repository.update_document_text_and_status', new=mock_update_repo) as _, \
         patch('app.services.rag_service.rag_service.update_document_content', new=mock_rag_update) as _, \
         patch('app.core.dependencies.get_current_company_admin', return_value=mock_admin_user) as _:

        # Make the PUT request to update the document, omitting tags
        response = authenticated_client.put(
            f"/api/documents/{document_id}/content",
            json={
                "new_content": updated_content,
                "title": new_title
                # Tags are omitted
            }
        )

        # Assertions
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["id"] == document_id
        assert response_data["extracted_text"] == updated_content
        assert response_data["title"] == new_title
        # Check that tags were not updated (or kept original if repository logic implies that)
        assert response_data["tags"] == ["existing", "tags"]

        # Verify that the repository methods were called correctly
        mock_get_doc.assert_awaited_once_with(ANY, document_id)
        mock_update_repo.assert_awaited_once_with(
            ANY,
            document_id=document_id,
            text=updated_content,
            status=DocumentStatus.EMBEDDING,
            tags=None, # Ensure None was passed for tags
            title=new_title # Ensure title was passed
        )

        # Verify that the RAG service method was called correctly
        mock_rag_update.assert_awaited_once_with(
            document_id=str(document_id),
            new_text_content=updated_content,
            company_id=mock_admin_user.company_id,
            title=new_title, # Ensure title was passed to RAG service
            tags=None # Ensure None was passed for tags
        )

def test_update_document_content_clears_tags(authenticated_client: TestClient):
    """
    Test that providing an empty list for tags clears existing tags.
    """
    document_id = 1
    updated_content = "Content updated, tags cleared."
    updated_title = "Document With Cleared Tags"
    cleared_tags = [] # Empty list to clear tags
    
    # Mock the existing document with some tags
    mock_document = Documents(
        id=document_id,
        title="Document With Tags",
        company_id=1,
        status=DocumentStatus.COMPLETED,
        extracted_text="Original content.",
        tags=["existing", "tags"]
    )

    # Mock the repository's get_document and update_document_text_and_status methods
    mock_get_doc = AsyncMock(return_value=mock_document)
    # Simulate update: title and tags are updated
    mock_updated_doc = mock_document # Create a copy to simulate update
    mock_updated_doc.extracted_text = updated_content
    mock_updated_doc.title = updated_title
    mock_updated_doc.tags = cleared_tags # Tags should be updated to empty list
    
    mock_update_repo = AsyncMock(return_value=mock_updated_doc)

    # Mock the RAG service's update_document_content method
    mock_rag_update = AsyncMock(return_value={"status": "success"})

    # Mock the dependency for getting the current user (admin)
    mock_admin_user = Users(id=1, email="admin@example.com", company_id=1, is_admin=True)

    # Patch the dependencies
    with patch('app.repository.document_repository.get_document', new=mock_get_doc) as _, \
         patch('app.repository.document_repository.update_document_text_and_status', new=mock_update_repo) as _, \
         patch('app.services.rag_service.rag_service.update_document_content', new=mock_rag_update) as _, \
         patch('app.core.dependencies.get_current_company_admin', return_value=mock_admin_user) as _:

        # Make the PUT request to update the document, providing an empty list for tags
        response = authenticated_client.put(
            f"/api/documents/{document_id}/content",
            json={
                "new_content": updated_content,
                "title": updated_title,
                "tags": cleared_tags # Provide empty list to clear tags
            }
        )

        # Assertions
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["id"] == document_id
        assert response_data["extracted_text"] == updated_content
        assert response_data["title"] == updated_title
        assert response_data["tags"] == cleared_tags # Tags should be an empty list

        # Verify that the repository methods were called correctly
        mock_get_doc.assert_awaited_once_with(ANY, document_id)
        mock_update_repo.assert_awaited_once_with(
            ANY,
            document_id=document_id,
            text=updated_content,
            status=DocumentStatus.EMBEDDING,
            tags=cleared_tags, # Ensure empty list was passed for tags
            title=updated_title # Ensure title was passed
        )

        # Verify that the RAG service method was called correctly
        mock_rag_update.assert_awaited_once_with(
            document_id=str(document_id),
            new_text_content=updated_content,
            company_id=mock_admin_user.company_id,
            title=updated_title, # Ensure title was passed to RAG service
            tags=cleared_tags # Ensure empty list was passed for tags
        )

def test_update_document_content_fails_rag_update(authenticated_client: TestClient):
    """
    Test that if RAG update fails, an HTTPException is raised and document status is updated to PROCESSING_FAILED.
    """
    document_id = 1
    updated_content = "This content will fail RAG update."
    updated_title = "Document Failing RAG"
    new_tags = ["error", "test"]

    # Mock the existing document
    mock_document = Documents(
        id=document_id,
        title="Document to Fail RAG",
        company_id=1,
        status=DocumentStatus.COMPLETED,
        extracted_text="Original content.",
        tags=["old_tag"]
    )

    # Mock the repository's get_document and update_document_text_and_status methods
    mock_get_doc = AsyncMock(return_value=mock_document)
    # The update method should return the updated document with status EMBEDDING
    mock_update_repo_intermediate = mock_document # Create a copy to simulate update
    mock_update_repo_intermediate.extracted_text = updated_content
    mock_update_repo_intermediate.title = updated_title
    mock_update_repo_intermediate.tags = new_tags
    mock_update_repo_intermediate.status = DocumentStatus.EMBEDDING
    
    mock_update_repo = AsyncMock(return_value=mock_update_repo_intermediate)

    # Mock the RAG service's update_document_content method to simulate failure
    mock_rag_update = AsyncMock(return_value={"status": "failed", "message": "Pinecone error"})

    # Mock the repository's update_document_status_and_reason for failure case
    mock_update_status_reason = AsyncMock(return_value=None) # This method is called on failure

    # Mock the dependency for getting the current user (admin)
    mock_admin_user = Users(id=1, email="admin@example.com", company_id=1, is_admin=True)

    # Patch the dependencies
    with patch('app.repository.document_repository.get_document', new=mock_get_doc) as _, \
         patch('app.repository.document_repository.update_document_text_and_status', new=mock_update_repo) as _, \
         patch('app.services.rag_service.rag_service.update_document_content', new=mock_rag_update) as _, \
         patch('app.repository.document_repository.update_document_status_and_reason', new=mock_update_status_reason) as _, \
         patch('app.core.dependencies.get_current_company_admin', return_value=mock_admin_user) as _:

        # Make the PUT request to update the document
        response = authenticated_client.put(
            f"/api/documents/{document_id}/content",
            json={
                "new_content": updated_content,
                "title": updated_title,
                "tags": new_tags
            }
        )

        # Assertions
        assert response.status_code == 500 # Expecting 500 Internal Server Error
        assert "Failed to update RAG embeddings" in response.json()["detail"]

        # Verify that the repository methods were called correctly
        mock_get_doc.assert_awaited_once_with(ANY, document_id)
        mock_update_repo.assert_awaited_once_with( # Initial update to EMBEDDING status
            ANY,
            document_id=document_id,
            text=updated_content,
            status=DocumentStatus.EMBEDDING,
            tags=new_tags,
            title=updated_title
        )
        mock_rag_update.assert_awaited_once_with( # RAG update called
            document_id=str(document_id),
            new_text_content=updated_content,
            company_id=mock_admin_user.company_id,
            title=updated_title, # Ensure title was passed to RAG service
            tags=new_tags
        )
        mock_update_status_reason.assert_awaited_once_with( # Status updated to PROCESSING_FAILED on RAG error
            ANY,
            document_id=document_id,
            status=DocumentStatus.PROCESSING_FAILED,
            reason="RAG Embedding Update Failed: Pinecone error"
        )