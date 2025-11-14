import pytest
from fastapi.testclient import TestClient
from fastapi import FastAPI, HTTPException, status
from unittest.mock import patch

# Import the main FastAPI app instance
from app.main import app # Assuming app is created in app/main.py

# --- Test Client Setup ---
client = TestClient(app)

# --- Helper function to create a mock endpoint for testing ---
def create_test_endpoint(app: FastAPI, path: str, status_code: int, detail: str, exception_type: type = HTTPException):
    @app.get(path)
    async def mock_endpoint():
        if exception_type == HTTPException:
            raise HTTPException(status_code=status_code, detail=detail)
        elif exception_type == RequestValidationError:
            # This is harder to simulate directly without a request body,
            # but we can test the handler's behavior if it were raised.
            # For now, we focus on HTTPException and general exceptions.
            pass
        else:
            raise exception_type(detail)
    return mock_endpoint

# --- Integration Tests for Global Error Handlers ---

@pytest.mark.asyncio
async def test_global_http_exception_handling():
    """
    Tests if the global http_exception_handler correctly processes HTTPException.
    """
    # Temporarily add a route that raises HTTPException
    @app.get("/test-http-exception")
    async def raise_http_exception():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="This is a test 404 error")

    response = client.get("/test-http-exception")
    
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {"message": "This is a test 404 error", "code": 404}

    # Clean up the temporary route (optional, but good practice if running many tests)
    # In a real scenario, you might want to use a fixture to manage app state.
    # For simplicity here, we assume the app state is clean between tests or managed by pytest.

@pytest.mark.asyncio
async def test_global_validation_exception_handling():
    """
    Tests if the global validation_exception_handler correctly processes RequestValidationError.
    This requires simulating a request that would cause a validation error.
    We'll use a simple endpoint that expects a query parameter.
    """
    # Define a simple endpoint that requires a query parameter
    @app.get("/test-validation-error")
    async def endpoint_with_validation(item_id: int):
        return {"item_id": item_id}

    # Make a request with invalid data type for item_id (e.g., string instead of int)
    response = client.get("/test-validation-error?item_id=abc")
    
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    # The exact structure of validation errors can vary slightly, but we expect a specific format
    response_data = response.json()
    assert response_data["message"] == "Validation failed"
    assert response_data["code"] == status.HTTP_422_UNPROCESSABLE_ENTITY
    assert "details" in response_data
    assert "errors" in response_data["details"]
    assert isinstance(response_data["details"]["errors"], list)
    assert len(response_data["details"]["errors"]) > 0
    # Check for specific error message content if possible, e.g., "value is not a valid integer"
    assert any("value is not a valid integer" in err for err in response_data["details"]["errors"])

@pytest.mark.asyncio
async def test_global_general_exception_handling():
    """
    Tests if the global general_exception_handler catches unexpected exceptions.
    """
    # Temporarily add a route that raises a generic Exception
    @app.get("/test-general-exception")
    async def raise_general_exception():
        raise ValueError("A simulated internal error occurred")

    # Patch the logger to check if it's called
    with patch("app.core.global_error_handler.logger") as mock_logger:
        response = client.get("/test-general-exception")
        
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert response.json() == {"message": "An unexpected internal server error occurred.", "code": 500}
        
        # Check if the error was logged
        mock_logger.error.assert_called_once()

# --- Test for specific custom exceptions (if any were defined and handled) ---
# If we had custom exceptions like UserAlreadyExistsError, we would test them here.
# For example:
# @pytest.mark.asyncio
# async def test_custom_user_already_exists_exception():
#     # Assume a route that raises UserAlreadyExistsError
#     # And assume a handler for it in global_error_handler.py
#     response = client.post("/auth/register", json={"email": "existing@example.com", ...})
#     assert response.status_code == status.HTTP_409_CONFLICT
#     assert response.json()["message"] == "User with this email already exists."

# --- Cleanup temporary routes (if necessary) ---
# In a more complex setup, you might need to remove routes added during tests.
# For this example, we'll assume pytest's scope handles it or the app is reloaded.
