from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock
from app.main import app
from app.models.user_model import Users
from app.core.dependencies import get_current_user, get_db, check_quota_and_subscription
from app.modules.chat import service as chat_service


def test_chat_endpoint():
    with TestClient(app) as client:
        # Mock current user
        mock_user = Users(
            id=1,
            name="Test User",
            username="testuser",
            role="employee",
            company_id=1
        )
        
        # Use dependency override
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_db] = lambda: AsyncMock()
        app.dependency_overrides[check_quota_and_subscription] = lambda: None
        try:
            # Mock the dependencies and services
            with patch.object(chat_service.chat_service, "process_chat_message", new_callable=AsyncMock) as mock_process, \
                 patch("app.modules.chat.api.log_activity", new_callable=AsyncMock):
                mock_process.return_value = {
                    "response": "I'm doing well, thank you for asking!",
                    "conversation_id": "test_conversation",
                }
                
                # Send a chat request
                chat_data = {
                    "message": "Hello, how are you?",
                    "conversation_id": "test_conversation"
                }
                
                response = client.post(
                    "/api/chat", 
                    json=chat_data,
                    headers={"Authorization": "Bearer mock_token"}
                )
                
                # Check that the request was successful
                assert response.status_code == 200
                assert "response" in response.json()
                assert "conversation_id" in response.json()
                assert response.json()["response"] == "I'm doing well, thank you for asking!"
                assert response.json()["conversation_id"] == "test_conversation"
        finally:
            app.dependency_overrides.clear()


def test_chat_endpoint_without_conversation_id():
    with TestClient(app) as client:
        # Mock current user
        mock_user = Users(
            id=1,
            name="Test User",
            username="testuser",
            role="employee",
            company_id=1
        )
        
        # Use dependency override
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_db] = lambda: AsyncMock()
        app.dependency_overrides[check_quota_and_subscription] = lambda: None
        try:
            # Mock the dependencies and services
            with patch.object(chat_service.chat_service, "process_chat_message", new_callable=AsyncMock) as mock_process, \
                 patch("app.modules.chat.api.log_activity", new_callable=AsyncMock):
                mock_process.return_value = {
                    "response": "I can answer questions based on your company documents!",
                    "conversation_id": "generated-id",
                }
                
                # Send a chat request without conversation_id
                chat_data = {
                    "message": "What can you do?"
                }
                
                response = client.post(
                    "/api/chat", 
                    json=chat_data,
                    headers={"Authorization": "Bearer mock_token"}
                )
                
                # Check that the request was successful
                assert response.status_code == 200
                assert "response" in response.json()
                assert "conversation_id" in response.json()
                assert response.json()["response"] == "I can answer questions based on your company documents!"
                # The conversation_id should be generated
                assert len(response.json()["conversation_id"]) > 0
        finally:
            app.dependency_overrides.clear()
