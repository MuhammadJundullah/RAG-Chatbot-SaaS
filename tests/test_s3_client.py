import pytest
import asyncio
import io
from unittest.mock import patch, AsyncMock

from app.core.s3_client import AsyncS3Client
from app.core.config import settings

# Mock settings for S3 client
MOCK_S3_ENDPOINT_URL = "http://localhost:9000"
MOCK_S3_ACCESS_KEY_ID = "test_key"
MOCK_S3_SECRET_ACCESS_KEY = "test_secret"
MOCK_S3_BUCKET_NAME = "test-bucket"

@pytest.fixture
def mock_s3_settings():
    with patch.dict('app.core.config.settings.values', {
        'S3_ENDPOINT_URL': MOCK_S3_ENDPOINT_URL,
        'S3_AWS_ACCESS_KEY_ID': MOCK_S3_ACCESS_KEY_ID,
        'S3_AWS_SECRET_ACCESS_KEY': MOCK_S3_SECRET_ACCESS_KEY,
        'S3_BUCKET_NAME': MOCK_S3_BUCKET_NAME,
    }, clear=True):
        yield

@pytest.fixture
def mock_aiobotocore_client():
    """Mocks the aiobotocore S3 client and its put_object method."""
    mock_client = AsyncMock()
    mock_client.put_object = AsyncMock()
    
    # Mock the context manager behavior of create_client
    mock_context_manager = AsyncMock()
    mock_context_manager.__aenter__.return_value = mock_client
    mock_context_manager.__aexit__.return_value = None
    
    mock_session = AsyncMock()
    mock_session.create_client.return_value = mock_context_manager
    
    with patch('aiobotocore.session.get_session', return_value=mock_session) as mock_get_session:
        yield mock_get_session, mock_client, mock_context_manager

@pytest.mark.asyncio
async def test_s3_client_upload_file(mock_s3_settings, mock_aiobotocore_client):
    """Tests the upload_file method of the AsyncS3Client."""
    mock_get_session, mock_client, mock_context_manager = mock_aiobotocore_client
    
    s3_client = AsyncS3Client()
    
    # Dummy file data
    file_content = b"This is a test file content."
    file_object = io.BytesIO(file_content)
    file_key = "test/path/to/file.txt"
    bucket_name = MOCK_S3_BUCKET_NAME
    
    # Call the method to test
    uploaded_url = await s3_client.upload_file(file_object, bucket_name, file_key)
    
    # Assertions
    # Check if get_session was called
    mock_get_session.assert_called_once()
    
    # Check if create_client was called with correct parameters
    mock_session_instance = mock_get_session()
    mock_session_instance.create_client.assert_called_once_with(
        "s3",
        endpoint_url=MOCK_S3_ENDPOINT_URL,
        aws_access_key_id=MOCK_S3_ACCESS_KEY_ID,
        aws_secret_access_key=MOCK_S3_SECRET_ACCESS_KEY,
        config=mock_aiobotocore_client[0].return_value.config # Check config object if needed, here just checking it's called
    )
    
    # Check if put_object was called correctly
    mock_client.put_object.assert_called_once_with(
        Bucket=bucket_name,
        Key=file_key,
        Body=file_content # Ensure the body is the raw content
    )
    
    # Check if the returned URL is correct
    expected_url = f"{MOCK_S3_ENDPOINT_URL}/{bucket_name}/{file_key}"
    assert uploaded_url == expected_url
    
    # Check if the client was closed
    await s3_client.close()
    mock_context_manager.__aexit__.assert_called_once()

@pytest.mark.asyncio
async def test_s3_client_upload_file_error(mock_s3_settings, mock_aiobotocore_client):
    """Tests error handling in the upload_file method."""
    mock_get_session, mock_client, mock_context_manager = mock_aiobotocore_client
    
    # Simulate an error during put_object
    mock_client.put_object.side_effect = Exception("S3 upload failed")
    
    s3_client = AsyncS3Client()
    
    file_content = b"This is a test file content."
    file_object = io.BytesIO(file_content)
    file_key = "test/path/to/file.txt"
    bucket_name = MOCK_S3_BUCKET_NAME
    
    # Expect an exception to be raised
    with pytest.raises(Exception, match="S3 upload failed"):
        await s3_client.upload_file(file_object, bucket_name, file_key)
        
    # Check if put_object was called
    mock_client.put_object.assert_called_once()
    
    # Check if the client was closed even after an error
    await s3_client.close()
    mock_context_manager.__aexit__.assert_called_once()
