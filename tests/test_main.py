import pytest
from fastapi.testclient import TestClient
from app.main import app


def test_root():
    with TestClient(app) as client:
        response = client.get("/api/")
        assert response.status_code == 200
        assert response.json() == {"message": "Multi-Tenant Company Chatbot API is running"}


def test_health_check():
    with TestClient(app) as client:
        response = client.get("/api/health")
        assert response.status_code == 200
        assert response.json() == {"status": "healthy"}
