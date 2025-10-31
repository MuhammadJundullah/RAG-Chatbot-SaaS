import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.services.rag_service import RAGService
from app.services.gemini_service import GeminiService
from app.services.user_service import authenticate_user, register_user
from app.models.user_model import Users
from app.models.company_model import Company
from app.schemas.user_schema import UserRegistration


def test_rag_service_initialization():
    rag_service = RAGService()
    assert rag_service is not None


def test_gemini_service_initialization():
    gemini_service = GeminiService()
    assert gemini_service is not None


# Mock database session for testing
@pytest.fixture
def mock_db_session():
    session = MagicMock()
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    return session


class TestUserRepository:
    @staticmethod
    async def get_user_by_email(db, email):
        # Mock user that exists
        if email == "existing@example.com":
            user = Users(
                id=1,
                name="Existing User",
                email="existing@example.com",
                username="existinguser",
                password="hashed_password",
                role="employee",
                company_id=1,
                is_active=True
            )
            return user
        return None
    
    @staticmethod
    async def create_user(db, user):
        # Return the same user object with id set
        user.id = 1
        return user


class TestCompanyRepository:
    @staticmethod
    async def create_company(db, company):
        company.id = 1
        return company


@pytest.mark.asyncio
async def test_authenticate_user_success(mock_db_session):
    # Mock user data
    user = Users(
        id=1,
        name="Test User",
        email="test@example.com",
        username="testuser",
        password="hashed_password",
        role="employee",
        company_id=1,
        is_active=True
    )
    
    with patch('app.services.user_service.user_repository.get_user_by_email', return_value=user), \
         patch('app.utils.security.verify_password', return_value=True):
        
        result = await authenticate_user(mock_db_session, email="test@example.com", password="password123")
        assert result == user


@pytest.mark.asyncio
async def test_authenticate_user_failure(mock_db_session):
    with patch('app.services.user_service.user_repository.get_user_by_email', return_value=None):
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
        email=user_data.email,
        username=None, 
        password="hashed_password",
        role="admin", 
        is_active=False
    )
    
    new_company = Company(
        id=1,
        name=user_data.company_name,
        is_active=False 
    )
    
    with patch('app.services.user_service.user_repository.get_user_by_email', return_value=None), \
         patch('app.services.user_service.user_repository.create_user', return_value=new_user), \
         patch('app.services.user_service.company_repository.create_company', return_value=new_company), \
         patch('app.utils.security.get_password_hash', return_value="hashed_password"):
        
        result = await register_user(mock_db_session, user_data=user_data)
        assert result.email == user_data.email
        assert result.role == "admin"
        assert result.is_active == False
