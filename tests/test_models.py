import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.user_model import Users
from app.models.company_model import Company
from app.models.document_model import Documents, DocumentStatus
from app.models.division_model import Division
from app.models.chatlog_model import Chatlogs
from app.models.embedding_model import Embeddings
from app.models.base import Base

# Create an in-memory SQLite database for testing
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"

test_engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


def test_user_model():
    # Create tables
    Base.metadata.create_all(bind=test_engine)
    
    # Create a test user instance
    user = Users(
        name="Test User",
        email="test@example.com",
        username="testuser",
        password="hashed_password",
        role="employee",
        company_id=1,
        division_id=1,
        is_active=True
    )
    
    assert user.name == "Test User"
    assert user.email == "test@example.com"
    assert user.username == "testuser"
    assert user.role == "employee"
    assert user.company_id == 1
    assert user.division_id == 1
    assert user.is_active == True


def test_company_model():
    # Create a test company instance
    company = Company(
        name="Test Company",
        is_active=True
    )
    
    assert company.name == "Test Company"
    assert company.is_active == True


def test_document_model():
    # Create a test document instance
    document = Documents(
        title="Test Document",
        company_id=1,
        status=DocumentStatus.UPLOADED,
        content_type="application/pdf"
    )
    
    assert document.title == "Test Document"
    assert document.company_id == 1
    assert document.status == DocumentStatus.UPLOADED
    assert document.content_type == "application/pdf"


def test_division_model():
    # Create a test division instance
    division = Division(
        name="Test Division",
        company_id=1
    )
    
    assert division.name == "Test Division"
    assert division.company_id == 1


def test_chatlog_model():
    # Create a test chatlog instance
    chatlog = Chatlogs(
        question="Test question?",
        answer="Test answer.",
        UsersId=1,
        company_id=1,
        conversation_id="test_conversation"
    )
    
    assert chatlog.question == "Test question?"
    assert chatlog.answer == "Test answer."
    assert chatlog.UsersId == 1
    assert chatlog.company_id == 1
    assert chatlog.conversation_id == "test_conversation"


def test_embedding_model():
    # Create a test embedding instance
    embedding = Embeddings(
        document_id=1,
        vector_id="test_vector_id"
    )
    
    assert embedding.document_id == 1
    assert embedding.vector_id == "test_vector_id"
