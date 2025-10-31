import pytest
from unittest.mock import AsyncMock, MagicMock
from app.repository.user_repository import get_user, get_user_by_email, create_user
from app.repository.company_repository import get_company, create_company
from app.repository.document_repository import get_document, create_document
from app.repository.division_repository import get_division, create_division
from app.repository.chatlog_repository import create_chatlog
from app.models.user_model import Users
from app.models.company_model import Company
from app.models.document_model import Documents
from app.models.division_model import Division
from app.models.chatlog_model import Chatlogs
from app.schemas.user_schema import UserRegistration
from app.schemas.company_schema import CompanyCreate
from app.schemas.document_schema import DocumentCreate
from app.schemas.division_schema import DivisionCreate
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
        self.divisions = []
        self.chatlogs = []


@pytest.mark.asyncio
async def test_get_user():
    db = MockDBSession()
    user = Users(id=1, name="Test User", email="test@example.com")
    db.users.append(user)
    
    with patch('sqlalchemy.ext.asyncio.AsyncSession.execute', new_callable=AsyncMock) as mock_execute:
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = user
        mock_execute.return_value = mock_result
        
        result = await get_user(db, user_id=1)
        assert result.id == 1
        assert result.name == "Test User"


@pytest.mark.asyncio
async def test_get_user_by_email():
    db = MockDBSession()
    user = Users(id=1, name="Test User", email="test@example.com")
    db.users.append(user)
    
    with patch('sqlalchemy.ext.asyncio.AsyncSession.execute', new_callable=AsyncMock) as mock_execute:
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = user
        mock_execute.return_value = mock_result
        
        result = await get_user_by_email(db, email="test@example.com")
        assert result.email == "test@example.com"


@pytest.mark.asyncio
async def test_create_user():
    db = MockDBSession()
    user_create = UserCreate(
        name="New User",
        email="new@example.com",
        password="hashed_password",
        role="employee",
        company_id=1
    )
    
    new_user = Users(
        id=1,
        **user_create.dict(exclude={'password'})
    )
    
    with patch('app.repository.user_repository.Users', return_value=new_user):
        result = await create_user(db, user_create)
        assert result.name == "New User"
        assert result.email == "new@example.com"
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
        
        result = await get_company(db, company_id=1)
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
        result = await create_company(db, company_create)
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
        
        result = await get_document(db, document_id=1)
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
        result = await create_document(db, document_create)
        assert result.title == "New Document"
        assert result.company_id == 1


@pytest.mark.asyncio
async def test_get_division():
    db = MockDBSession()
    division = Divisions(id=1, name="Test Division", company_id=1)
    db.divisions.append(division)
    
    with patch('sqlalchemy.ext.asyncio.AsyncSession.execute', new_callable=AsyncMock) as mock_execute:
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = division
        mock_execute.return_value = mock_result
        
        result = await get_division(db, division_id=1)
        assert result.id == 1
        assert result.name == "Test Division"


@pytest.mark.asyncio
async def test_create_division():
    db = MockDBSession()
    division_create = DivisionCreate(
        name="New Division",
        company_id=1
    )
    
    new_division = Divisions(
        id=1,
        **division_create.dict()
    )
    
    with patch('app.repository.division_repository.Divisions', return_value=new_division):
        result = await create_division(db, division_create)
        assert result.name == "New Division"
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
        result = await create_chatlog(db, chatlog_create)
        assert result.question == "Test question?"
        assert result.answer == "Test answer."
        assert result.conversation_id == "test_conversation"

from unittest.mock import patch
