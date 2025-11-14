import pytest
from unittest.mock import MagicMock, patch
from starlette.requests import Request
from starlette.exceptions import HTTPException as StarletteHTTPException
from fastapi.exceptions import RequestValidationError
from fastapi import FastAPI, status

from app.core.global_error_handler import (
    http_exception_handler,
    validation_exception_handler,
    general_exception_handler,
    create_error_response,
    register_global_exception_handlers
)

# --- Mocking dependencies ---
# Mocking logging to check if it's called
@pytest.fixture
def mock_logger():
    with patch("app.core.global_error_handler.logger") as mock:
        yield mock

# Mocking traceback for general exception handler
@pytest.fixture
def mock_traceback():
    with patch("app.core.global_error_handler.traceback") as mock:
        mock.format_exc.return_value = "Mocked Traceback"
        yield mock

# Mocking JSONResponse to check its arguments
@pytest.fixture
def mock_json_response():
    with patch("app.core.global_error_handler.JSONResponse") as mock:
        yield mock

# Mocking FastAPI app for registration tests
@pytest.fixture
def mock_fastapi_app():
    mock_app = MagicMock(spec=FastAPI)
    mock_app.exception_handler = MagicMock() # Mock the exception_handler decorator
    return mock_app

# --- Test Cases ---

# Test for create_error_response helper function
def test_create_error_response():
    response = create_error_response(status.HTTP_404_NOT_FOUND, "Not Found")
    assert response == {"message": "Not Found", "code": 404}

    response_with_details = create_error_response(status.HTTP_422_UNPROCESSABLE_ENTITY, "Validation Error", {"field": "email"})
    assert response_with_details == {"message": "Validation Error", "code": 422, "details": {"field": "email"}}

# Test for http_exception_handler
@pytest.mark.asyncio
async def test_http_exception_handler(mock_logger, mock_json_response):
    mock_request = MagicMock(spec=Request)
    mock_request.method = "GET"
    mock_request.url.path = "/test"
    
    exc = StarletteHTTPException(status_code=404, detail="Resource not found")
    
    await http_exception_handler(mock_request, exc)
    
    mock_logger.warning.assert_called_once_with("HTTP Exception: 404 - Resource not found for GET /test")
    mock_json_response.assert_called_once_with(
        status_code=404,
        content={"message": "Resource not found", "code": 404}
    )

# Test for validation_exception_handler
@pytest.mark.asyncio
async def test_validation_exception_handler(mock_logger, mock_json_response):
    mock_request = MagicMock(spec=Request)
    mock_request.method = "POST"
    mock_request.url.path = "/items"
    
    # Sample validation error structure
    validation_errors = [
        {"loc": ["body", "email"], "msg": "field required", "type": "value_error.missing"},
        {"loc": ["body", "age"], "msg": "ensure this value is greater than or equal to 18", "type": "value_error.number.min_value", "ctx": {"limit_value": 18}}
    ]
    exc = RequestValidationError(errors=validation_errors)
    
    await validation_exception_handler(mock_request, exc)
    
    mock_logger.warning.assert_called_once() # Check if warning was logged
    mock_json_response.assert_called_once_with(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "message": "Validation failed",
            "code": status.HTTP_422_UNPROCESSABLE_ENTITY,
            "details": {
                "errors": [
                    "Field 'body.email': field required",
                    "Field 'body.age': ensure this value is greater than or equal to 18"
                ]
            }
        }
    )

# Test for general_exception_handler
@pytest.mark.asyncio
async def test_general_exception_handler(mock_logger, mock_traceback, mock_json_response):
    mock_request = MagicMock(spec=Request)
    mock_request.method = "GET"
    mock_request.url.path = "/internal"
    
    exc = ValueError("Something went wrong internally")
    
    await general_exception_handler(mock_request, exc)
    
    mock_logger.error.assert_called_once() # Check if error was logged
    mock_json_response.assert_called_once_with(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"message": "An unexpected internal server error occurred.", "code": 500}
    )

# Test for register_global_exception_handlers
def test_register_global_exception_handlers(mock_fastapi_app):
    register_global_exception_handlers(mock_fastapi_app)
    
    # Check if exception_handler was called for each type
    assert mock_fastapi_app.exception_handler.call_count == 3
    
    # Verify calls for specific handlers
    mock_fastapi_app.exception_handler.assert_any_call(StarletteHTTPException)
    mock_fastapi_app.exception_handler.assert_any_call(RequestValidationError)
    mock_fastapi_app.exception_handler.assert_any_call(Exception)
