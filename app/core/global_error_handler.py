from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from fastapi.exceptions import RequestValidationError
from typing import Any, Optional
import traceback
import logging
from app.modules.auth.service import UserRegistrationError

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Define a standard error response format
def create_error_response(status_code: int, message: str, details: Optional[Any] = None) -> dict:
    response = {
        "message": message,
        "code": status_code,
    }
    if details:
        response["details"] = details
    return response

async def user_registration_exception_handler(request: Request, exc: UserRegistrationError):
    """Handles UserRegistrationError to return a 400 Bad Request."""
    logger.warning(f"User Registration Error: {exc.detail} for {request.method} {request.url.path}")
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content=create_error_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            message=exc.detail,
        ),
    )

async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Handles StarletteHTTPException (which includes FastAPI's HTTPException)."""
    logger.warning(f"HTTP Exception: {exc.status_code} - {exc.detail} for {request.method} {request.url.path}")
    return JSONResponse(
        status_code=exc.status_code,
        content=create_error_response(
            status_code=exc.status_code,
            message=exc.detail,
        ),
    )

async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handles RequestValidationError for input validation errors."""
    logger.warning(f"Validation Error: {exc.errors()} for {request.method} {request.url.path}")
    # Extracting specific error messages for better client feedback
    error_details = []
    for error in exc.errors():
        field = ".".join(map(str, error["loc"]))
        msg = error["msg"]
        error_details.append(f"Field '{field}': {msg}")
        
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=create_error_response(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            message="Validation failed",
            details={"errors": error_details}
        ),
    )

async def general_exception_handler(request: Request, exc: Exception):
    """Handles any other unhandled exceptions."""
    # Log the full traceback for internal debugging
    logger.error(f"Unhandled Exception: {exc}\n{traceback.format_exc()} for {request.method} {request.url.path}")
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=create_error_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message="An unexpected internal server error occurred.",
        ),
    )

# Function to register all handlers with the FastAPI app
def register_global_exception_handlers(app: FastAPI):
    app.exception_handler(UserRegistrationError)(user_registration_exception_handler)
    app.exception_handler(StarletteHTTPException)(http_exception_handler)
    app.exception_handler(RequestValidationError)(validation_exception_handler)
    app.exception_handler(Exception)(general_exception_handler)
