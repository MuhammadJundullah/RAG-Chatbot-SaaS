import pytest
from unittest.mock import MagicMock

@pytest.fixture
def mock_db_session():
    session = MagicMock()
    session.add = MagicMock()
    session.commit = MagicMock()
    session.refresh = MagicMock()
    return session

@pytest.fixture
def mock_async_db_session():
    session = MagicMock()
    session.add = MagicMock()
    session.commit = MagicMock()
    session.refresh = MagicMock()
    return session
