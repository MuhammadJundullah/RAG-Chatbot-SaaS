import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock
from app.main import app
from app.models.user_model import Users
from app.models.chatlog_model import Chatlogs


def test_chat_endpoint():
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
        
        # Mock chatlog
        mock_chatlog = Chatlogs(
            id=1,
            question="Hello, how are you?",
            answer="I'm doing well, thank you for asking!",
            UsersId=1,
            company_id=1,
            conversation_id="test_conversation"
        )
        
        # Mock the dependencies and services
        with patch('app.api.v1.endpoints.chat.get_current_user', return_value=mock_user), \
             patch('app.services.rag_service.rag_service.get_relevant_context', new_callable=AsyncMock) as mock_get_context, \
             patch('app.services.gemini_service.gemini_service.generate_chat_response') as mock_gen_response, \
             patch('app.repository.chatlog_repository.create_chatlog', new_callable=AsyncMock) as mock_create_chatlog:
            
            # Mock the RAG service response
            mock_get_context.return_value = "Relevant context from RAG"
            
            # Mock the Gemini service response
            async def mock_response_generator():
                yield "I'm doing well, thank you for asking!"
            
            mock_gen_response.return_value = mock_response_generator()
            
            # Mock the chatlog repository
            mock_create_chatlog.return_value = mock_chatlog
            
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


def test_chat_endpoint_without_conversation_id():
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
        
        # Mock chatlog
        mock_chatlog = Chatlogs(
            id=1,
            question="What can you do?",
            answer="I can answer questions based on your company documents!",
            UsersId=1,
            company_id=1,
            conversation_id="new_conversation"
        )
        
        # Mock the dependencies and services
        with patch('app.api.v1.endpoints.chat.get_current_user', return_value=mock_user), \
             patch('app.services.rag_service.rag_service.get_relevant_context', new_callable=AsyncMock) as mock_get_context, \
             patch('app.services.gemini_service.gemini_service.generate_chat_response') as mock_gen_response, \
             patch('app.repository.chatlog_repository.create_chatlog', new_callable=AsyncMock) as mock_create_chatlog:
            
            # Mock the RAG service response
            mock_get_context.return_value = "Relevant context from RAG"
            
            # Mock the Gemini service response
            async def mock_response_generator():
                yield "I can answer questions based on your company documents!"
            
            mock_gen_response.return_value = mock_response_generator()
            
            # Mock the chatlog repository
            mock_create_chatlog.return_value = mock_chatlog
            
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
