"""Automated test suite for Moonscape AI Scientific Explainer service (Phase 7)."""

import json
from unittest.mock import MagicMock, patch
import pytest
from fastapi.testclient import TestClient

from app.schemas.ai import AIExplainRequest, AIExplainResponse
from app.services.ai_explainer import ai_explainer_service
from app.services.ai_providers import (
    AIAuthenticationError,
    AIProviderError,
    AIRateLimitError,
    AITimeoutError,
    AIUnavailableError,
    BaseAIProvider,
    GeminiProvider,
    MockDeterministicProvider,
    OpenAIProvider,
    get_ai_provider,
)
from app.services.analysis_store import analysis_store


def test_ai_explain_analysis_001_success(client: TestClient) -> None:
    """Verifies POST /api/ai/explain succeeds with seeded analysis_001 and returns Phase 7 contract."""
    payload = {"analysis_id": "analysis_001"}
    response = client.post("/api/ai/explain", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["analysis_id"] == "analysis_001"
    assert isinstance(data["explanation"], str)
    assert len(data["explanation"]) > 30
    assert isinstance(data["positive_factors"], list)
    assert len(data["positive_factors"]) >= 1
    assert isinstance(data["risk_factors"], list)
    assert len(data["risk_factors"]) >= 1
    assert isinstance(data["limitations"], list)
    assert len(data["limitations"]) >= 1
    assert "Preliminary assessment only" in data["conclusion"]
    assert "DISCLAIMER" in data["disclaimer"]


def test_ai_explain_nonexistent_analysis_404(client: TestClient) -> None:
    """Verifies querying a non-existent analysis ID returns a 404 status code."""
    payload = {"analysis_id": "ANL-UNKNOWN-9999"}
    response = client.post("/api/ai/explain", json=payload)
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_ai_explain_empty_request_400(client: TestClient) -> None:
    """Verifies that a request with neither analysis_id nor site_id returns a 400 error."""
    payload = {}
    response = client.post("/api/ai/explain", json=payload)
    assert response.status_code == 400
    assert "either" in response.json()["detail"].lower()


def test_ai_explain_dynamic_analysis_workflow(client: TestClient) -> None:
    """End-to-end integration: run POST /api/analysis/run then explain the resulting analysis_id."""
    analysis_req = {
        "center_lat": -89.46,
        "center_lon": 222.00,
        "radius_meters": 1000.0,
        "max_acceptable_slope_deg": 10.0,
        "max_acceptable_roughness_m": 0.5,
    }
    analysis_res = client.post("/api/analysis/run", json=analysis_req)
    assert analysis_res.status_code == 200
    analysis_data = analysis_res.json()
    generated_id = analysis_data["analysis_id"]

    # Verify it is now in the analysis store
    assert analysis_store.has(generated_id)

    # Request explanation
    explain_req = {
        "analysis_id": generated_id,
        "focus_topics": ["topography", "slope"],
    }
    explain_res = client.post("/api/ai/explain", json=explain_req)
    assert explain_res.status_code == 200
    explain_data = explain_res.json()

    assert explain_data["analysis_id"] == generated_id
    assert len(explain_data["explanation"]) > 20
    assert len(explain_data["positive_factors"]) >= 1
    assert len(explain_data["risk_factors"]) >= 1


class MockCustomLLMProvider(BaseAIProvider):
    """Custom mock provider for testing service injection."""

    def __init__(self, response_dict: dict, name: str = "Mock Custom LLM") -> None:
        self.response_dict = response_dict
        self.name = name

    def generate_json(self, prompt: str, system_prompt: str, timeout_seconds=None):
        return self.response_dict

    def is_configured(self) -> bool:
        return True

    def get_provider_name(self) -> str:
        return self.name


def test_ai_provider_mock_injection(client: TestClient) -> None:
    """Tests injecting a custom provider returning structured predictions."""
    custom_resp = {
        "explanation": "Target zone exhibits 86% solar illumination and benign local slopes.",
        "positive_factors": ["High cumulative solar illumination.", "Slope average 6.8 deg."],
        "risk_factors": ["Elongated grazing shadows at South Pole."],
        "limitations": ["Preliminary screening only."],
        "conclusion": "Favorable preliminary candidate.",
    }
    mock_prov = MockCustomLLMProvider(custom_resp, name="Google Gemini (gemini-1.5-flash)")
    ai_explainer_service.set_provider(mock_prov)

    try:
        response = client.post("/api/ai/explain", json={"analysis_id": "analysis_001"})
        assert response.status_code == 200
        data = response.json()
        assert "86% solar illumination" in data["explanation"]
        assert len(data["positive_factors"]) == 2
        assert "Google Gemini" in data["model_origin"]
    finally:
        ai_explainer_service.set_provider(None)


class FailingProvider(BaseAIProvider):
    """Provider that raises an explicit error for fallback testing."""

    def __init__(self, exception_to_raise: Exception, name: str = "Failing Provider") -> None:
        self.exception_to_raise = exception_to_raise
        self.name = name

    def generate_json(self, prompt: str, system_prompt: str, timeout_seconds=None):
        raise self.exception_to_raise

    def is_configured(self) -> bool:
        return True

    def get_provider_name(self) -> str:
        return self.name


def test_ai_provider_timeout_fallback(client: TestClient) -> None:
    """Verifies that if the remote LLM provider times out, the backend gracefully falls back to deterministic rule engine."""
    provider = FailingProvider(AITimeoutError("Gemini request timed out after 15.0 seconds."), name="Google Gemini")
    ai_explainer_service.set_provider(provider)

    try:
        response = client.post("/api/ai/explain", json={"analysis_id": "analysis_001"})
        assert response.status_code == 200
        data = response.json()
        assert data["analysis_id"] == "analysis_001"
        assert len(data["explanation"]) > 20
        assert any("offline rule engine" in lim.lower() for lim in data["limitations"])
    finally:
        ai_explainer_service.set_provider(None)


def test_ai_provider_rate_limit_fallback(client: TestClient) -> None:
    """Verifies that rate limit errors (HTTP 429) from LLM providers trigger graceful fallback."""
    provider = FailingProvider(AIRateLimitError("Gemini rate limit exceeded. 429 Too Many Requests."), name="Google Gemini")
    ai_explainer_service.set_provider(provider)

    try:
        response = client.post("/api/ai/explain", json={"analysis_id": "analysis_001"})
        assert response.status_code == 200
        data = response.json()
        assert data["analysis_id"] == "analysis_001"
        assert len(data["positive_factors"]) >= 1
        assert any("offline rule engine" in lim.lower() for lim in data["limitations"])
    finally:
        ai_explainer_service.set_provider(None)


def test_ai_provider_auth_error_fallback(client: TestClient) -> None:
    """Verifies that authentication errors trigger graceful fallback."""
    provider = FailingProvider(AIAuthenticationError("Invalid API key."), name="Google Gemini")
    ai_explainer_service.set_provider(provider)

    try:
        response = client.post("/api/ai/explain", json={"analysis_id": "analysis_001"})
        assert response.status_code == 200
        data = response.json()
        assert data["analysis_id"] == "analysis_001"
        assert len(data["explanation"]) > 20
        assert any("offline rule engine" in lim.lower() for lim in data["limitations"])
    finally:
        ai_explainer_service.set_provider(None)


def test_gemini_provider_direct_http_parsing() -> None:
    """Directly tests GeminiProvider parsing raw Google AI response structure."""
    fake_gemini_json = {
        "candidates": [
            {
                "content": {
                    "parts": [
                        {
                            "text": json.dumps({
                                "explanation": "Direct Gemini response parsing test.",
                                "positive_factors": ["Factor A"],
                                "risk_factors": ["Risk B"],
                                "limitations": ["Limitation C"],
                                "conclusion": "Conclusion D",
                            })
                        }
                    ]
                }
            }
        ]
    }

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = fake_gemini_json

    mock_client = MagicMock()
    mock_client.__enter__.return_value = mock_client
    mock_client.post.return_value = mock_resp

    provider = GeminiProvider(api_key="mock_key_abc", model="gemini-1.5-flash")
    with patch("httpx.Client", return_value=mock_client):
        parsed = provider.generate_json("test prompt", "test system")
        assert parsed["explanation"] == "Direct Gemini response parsing test."
        assert parsed["positive_factors"] == ["Factor A"]


def test_openai_provider_direct_http_parsing() -> None:
    """Directly tests OpenAIProvider parsing raw chat completions response."""
    fake_openai_json = {
        "choices": [
            {
                "message": {
                    "content": json.dumps({
                        "explanation": "Direct OpenAI parsing test.",
                        "positive_factors": ["Factor 1"],
                        "risk_factors": ["Risk 1"],
                        "limitations": ["Limitation 1"],
                        "conclusion": "Conclusion 1",
                    })
                }
            }
        ]
    }

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = fake_openai_json

    mock_client = MagicMock()
    mock_client.__enter__.return_value = mock_client
    mock_client.post.return_value = mock_resp

    provider = OpenAIProvider(api_key="sk-mock-12345", model="gpt-4o-mini")
    with patch("httpx.Client", return_value=mock_client):
        parsed = provider.generate_json("test prompt", "test system")
        assert parsed["explanation"] == "Direct OpenAI parsing test."
        assert parsed["conclusion"] == "Conclusion 1"


def test_ai_provider_factory_selection() -> None:
    """Tests provider factory auto-selection logic."""
    # Explicit mock
    prov_mock = get_ai_provider("mock")
    assert isinstance(prov_mock, MockDeterministicProvider)

    # Gemini without key
    with patch.dict("os.environ", {"GEMINI_API_KEY": ""}):
        gemini = GeminiProvider(api_key="")
        assert not gemini.is_configured()

    # Gemini with key
    gemini_configured = GeminiProvider(api_key="AIzaSyDummyKey")
    assert gemini_configured.is_configured()
    assert "Google Gemini" in gemini_configured.get_provider_name()
