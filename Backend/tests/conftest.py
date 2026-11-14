"""Pytest configuration and shared fixtures for Moonscape backend test suite."""

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(scope="session")
def client() -> TestClient:
    """Provides a shared FastAPI TestClient instance."""
    with TestClient(app) as test_client:
        yield test_client
