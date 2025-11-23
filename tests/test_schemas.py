import uuid
from datetime import datetime
from app.schemas.user_schema import UserRegistration, UserLoginCombined, User
from app.schemas.company_schema import Company
from app.schemas.document_schema import DocumentCreate, Document
from app.schemas.chatlog_schema import ChatlogCreate, Chatlog
from app.schemas.token_schema import Token
from app.schemas.chat_schema import ChatRequest
from app.models.document_model import DocumentStatus


def test_user_registration_schema():
    user_data = UserRegistration(
        name="Test User",
        email="test@example.com",
        password="password123",
        company_name="Test Company"
    )
    
    assert user_data.name == "Test User"
    assert user_data.email == "test@example.com"
    assert user_data.password == "password123"
    assert user_data.company_name == "Test Company"


def test_user_login_schema():
    login_data = UserLoginCombined(
        email="test@example.com",
        password="password123"
    )
    assert login_data.email == "test@example.com"
    assert login_data.password == "password123"


def test_user_schema():
    user = User(
        id=1,
        name="Test User",
        email="test@example.com",
        username="testuser",
        role="employee",
        company_id=1,
        division="Test Division",
        is_active=True
    )
    
    assert user.id == 1
    assert user.name == "Test User"
    assert user.email == "test@example.com"
    assert user.username == "testuser"
    assert user.role == "employee"
    assert user.company_id == 1
    assert user.division == "Test Division"
    assert user.is_active


def test_company_schema():
    company = Company(
        id=1,
        name="Test Company",
        code="TESTCO",
        is_active=True
    )
    assert company.id == 1
    assert company.name == "Test Company"
    assert company.is_active


def test_document_create_schema():
    doc_create = DocumentCreate(
        title="Test Document",
        company_id=1,
        temp_storage_path="/tmp/test_document.pdf",
        content_type="application/pdf"
    )
    assert doc_create.title == "Test Document"
    assert doc_create.company_id == 1
    assert doc_create.content_type == "application/pdf"


def test_document_schema():
    doc = Document(
        id=1,
        title="Test Document",
        company_id=1,
        status=DocumentStatus.UPLOADED,
        content_type="application/pdf"
    )
    
    assert doc.id == 1
    assert doc.title == "Test Document"
    assert doc.company_id == 1
    assert doc.status == DocumentStatus.UPLOADED
    assert doc.content_type == "application/pdf"


def test_chatlog_create_schema():
    test_uuid = uuid.uuid4()
    chatlog_create = ChatlogCreate(
        question="Test question?",
        answer="Test answer.",
        UsersId=1,
        company_id=1,
        conversation_id=test_uuid
    )
    
    assert chatlog_create.question == "Test question?"
    assert chatlog_create.answer == "Test answer."
    assert chatlog_create.UsersId == 1
    assert chatlog_create.company_id == 1
    assert chatlog_create.conversation_id == test_uuid


def test_chatlog_schema():
    test_uuid = uuid.uuid4()
    chatlog = Chatlog(
        id=1,
        question="Test question?",
        answer="Test answer.",
        UsersId=1,
        company_id=1,
        conversation_id=test_uuid,
        created_at=datetime.utcnow()
    )
    
    assert chatlog.id == 1
    assert chatlog.question == "Test question?"
    assert chatlog.answer == "Test answer."
    assert chatlog.UsersId == 1
    assert chatlog.company_id == 1
    assert chatlog.conversation_id == test_uuid


def test_token_schema():
    user_mock = User(
        id=1,
        name="Test User",
        email="test@example.com",
        username="testuser",
        role="employee",
        company_id=1,
        division="Test Division",
        is_active=True
    )

    token = Token(
        access_token="test_access_token",
        token_type="bearer",
        expires_in=3600,
        user=user_mock
    )
    
    assert token.access_token == "test_access_token"
    assert token.token_type == "bearer"


def test_chat_request_schema():
    chat_request = ChatRequest(
        message="Hello, how are you?",
        conversation_id="test_conversation"
    )
    
    assert chat_request.message == "Hello, how are you?"
    assert chat_request.conversation_id == "test_conversation"
