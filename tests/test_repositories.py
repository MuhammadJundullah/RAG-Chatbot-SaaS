import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.repository.user_repository import user_repository
from app.repository.company_repository import company_repository
from app.repository.document_repository import document_repository
from app.repository.chatlog_repository import chatlog_repository
from app.models.user_model import Users
from app.models.company_model import Company
from app.models.document_model import Documents
from app.models.chatlog_model import Chatlogs
from app.schemas.company_schema import CompanyCreate
from app.schemas.document_schema import DocumentCreate
from app.schemas.chatlog_schema import ChatlogCreate


class MockDBSession:
    def __init__(self):
        self.add = MagicMock()
        self.commit = AsyncMock()
        self.refresh = AsyncMock()
        
        # Mock data storage
        self.users = []
        self.companies = []
        self.documents = []


@pytest.mark.asyncio
async def test_get_user():
    db = MockDBSession()
    user = Users(id=1, name="Test User")
    db.users.append(user)
    
    with patch('sqlalchemy.ext.asyncio.AsyncSession.execute', new_callable=AsyncMock) as mock_execute:
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = user
        mock_execute.return_value = mock_result
        
        result = await user_repository.get_user(db, user_id=1)
        assert result.id == 1
        assert result.name == "Test User"


@pytest.mark.asyncio
async def test_create_user():
    db = MockDBSession()
    new_user = Users(
        id=1,
        name="New User",
        username="newuser",
        role="employee",
        company_id=1
    )
    
    with patch('app.repository.user_repository.Users', return_value=new_user):
        result = await user_repository.create_user(db, new_user)
        assert result.name == "New User"
        assert result.role == "employee"


@pytest.mark.asyncio
async def test_get_company():
    db = MockDBSession()
    company = Company(id=1, name="Test Company", is_active=True)
    db.companies.append(company)
    
    with patch('sqlalchemy.ext.asyncio.AsyncSession.execute', new_callable=AsyncMock) as mock_execute:
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = company
        mock_execute.return_value = mock_result
        
        result = await company_repository.get_company(db, company_id=1)
        assert result.id == 1
        assert result.name == "Test Company"


@pytest.mark.asyncio
async def test_create_company():
    db = MockDBSession()
    company_create = CompanyCreate(name="New Company")
    
    new_company = Company(
        id=1,
        **company_create.dict()
    )
    
    with patch('app.repository.company_repository.Company', return_value=new_company):
        result = await company_repository.create_company(db, new_company)
        assert result.name == "New Company"


@pytest.mark.asyncio
async def test_get_document():
    db = MockDBSession()
    document = Documents(id=1, title="Test Document", company_id=1)
    db.documents.append(document)
    
    with patch('sqlalchemy.ext.asyncio.AsyncSession.execute', new_callable=AsyncMock) as mock_execute:
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = document
        mock_execute.return_value = mock_result
        
        result = await document_repository.get_document(db, document_id=1)
        assert result.id == 1
        assert result.title == "Test Document"


@pytest.mark.asyncio
async def test_create_document():
    db = MockDBSession()
    document_create = DocumentCreate(
        title="New Document",
        company_id=1,
        content_type="application/pdf"
    )
    
    new_document = Documents(
        id=1,
        **document_create.dict()
    )
    
    with patch('app.repository.document_repository.Documents', return_value=new_document):
        result = await document_repository.create_document(db, new_document)
        assert result.title == "New Document"
        assert result.company_id == 1


@pytest.mark.asyncio
async def test_create_chatlog():
    db = MockDBSession()
    chatlog_create = ChatlogCreate(
        question="Test question?",
        answer="Test answer.",
        UsersId=1,
        company_id=1,
        conversation_id="test_conversation"
    )
    
    new_chatlog = Chatlogs(
        id=1,
        **chatlog_create.dict()
    )
    
    with patch('app.repository.chatlog_repository.Chatlogs', return_value=new_chatlog):
        result = await chatlog_repository.create_chatlog(db, new_chatlog)
        assert result.question == "Test question?"
        assert result.answer == "Test answer."
        assert result.conversation_id == "test_conversation"
