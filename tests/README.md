# Testing Documentation for RAG-Chatbot-SaaS

This directory contains all the tests for the RAG-Chatbot-SaaS application.

## Test Structure

The tests are organized by component:

- `test_main.py`: Tests for the main application endpoints
- `test_models.py`: Tests for the SQLAlchemy models
- `test_schemas.py`: Tests for the Pydantic schemas
- `test_services.py`: Tests for the service layer
- `test_repositories.py`: Tests for the repository layer
- `test_endpoints_auth.py`: Tests for the authentication endpoints
- `test_endpoints_documents.py`: Tests for the document management endpoints
- `conftest.py`: Shared test fixtures

## Running Tests

To run the tests, use the following command:

```bash
pytest
```

To run tests with coverage report:

```bash
pytest --cov=app
```

To run a specific test file:

```bash
pytest tests/test_models.py
```

## Test Coverage

The tests aim to cover:

- Model definitions and relationships
- Schema validation
- Service layer functionality
- Repository/database operations
- API endpoint responses
- Authentication and authorization flows
- Error handling
- Edge cases

## Mocking Strategy

The tests use mocking extensively to isolate units of code:

- Database sessions are mocked to prevent actual database operations
- External services (like S3, RAG, etc.) are mocked
- Dependencies are mocked to test individual components

## Async Testing

Since the application uses async/await, the tests use `pytest-asyncio` to handle asynchronous functions.

## Test Data

Tests use mock data rather than real data to ensure consistency and prevent side effects.