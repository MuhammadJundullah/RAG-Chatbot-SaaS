import pytest
from unittest.mock import patch
from app.modules.documents.rag_service import RAGService
from app.modules.chat.together_service import TogetherService
from app.modules.auth.service import authenticate_user, register_user
from app.models.user_model import Users
from app.models.company_model import Company
from app.schemas.user_schema import UserRegistration


def test_rag_service_initialization():
    rag_service = RAGService()
    assert rag_service is not None


def test_together_service_initialization():
    llm_service = TogetherService()
    assert llm_service is not None


@pytest.mark.asyncio
async def test_authenticate_user_success(mock_db_session):
    # Mock user data
    company = Company(id=1, name="Test Company", is_active=True)
    user = Users(
        id=1,
        name="Test User",
        username="testuser",
        password="hashed_password",
        role="admin",
        company_id=1,
        is_active=True
    )
    user.company = company
    
    with patch('app.modules.auth.service.company_repository.get_company_by_email', return_value=company), \
         patch('app.modules.auth.service.user_repository.get_first_admin_by_company', return_value=user), \
         patch('app.utils.security.verify_password', return_value=True):
        
        result = await authenticate_user(mock_db_session, email="test@example.com", password="password123")
        assert result == user


@pytest.mark.asyncio
async def test_authenticate_user_failure(mock_db_session):
    with patch('app.modules.auth.service.company_repository.get_company_by_email', return_value=None):
        result = await authenticate_user(mock_db_session, email="nonexistent@example.com", password="password123")
        assert result is None


@pytest.mark.asyncio
async def test_register_user(mock_db_session):
    user_data = UserRegistration(
        name="New User",
        email="newuser@example.com",
        password="password123",
        company_name="New Company"
    )
    
    # Mock the user and company creation
    new_user = Users(
        id=1,
        name=user_data.name,
        username=user_data.email,
        password="hashed_password",
        role="admin", 
        is_active=False
    )
    
    new_company = Company(
        id=1,
        name=user_data.company_name,
        is_active=False 
    )
    
    with patch('app.modules.auth.service.user_repository.get_user_by_username', return_value=None), \
         patch('app.modules.auth.service.user_repository.create_user', return_value=new_user), \
         patch('app.modules.auth.service.company_repository.get_company_by_name', return_value=None), \
         patch('app.modules.auth.service.company_repository.get_company_by_email', return_value=None), \
         patch('app.utils.security.get_password_hash', return_value="hashed_password"):
        
        result = await register_user(mock_db_session, user_data=user_data)
        assert result.username == user_data.email
        assert result.role == "admin"
        assert not result.is_active
