"""Unit and integration tests for Lunar Hazard Detection ML inference (Phase 4).

Tests:
1. Model unavailable fallback (exact Task 5 schema)
2. Valid image decoding and inference
3. Corrupted / invalid image encoding handling
4. Empty image payload handling
5. Wrong dimensions handling
6. Model inference runtime error handling
7. Confidence threshold filtering
8. Output schema conformity, metric spatial calibration, and Apollo domain gap documentation
"""

import base64
import io
from typing import Any, Dict, List
import numpy as np
import pytest
from PIL import Image, ImageDraw
from fastapi.testclient import TestClient

from app.config.hazard_settings import hazard_settings
from app.services.hazard_detection import APOLLO_DOMAIN_LIMITATION, hazard_detection_service


def create_test_image_b64(width: int = 128, height: int = 128) -> str:
    """Generates a small synthetic grayscale lunar surface patch in Base64 PNG format."""
    img = Image.new("L", (width, height), color=128)
    draw = ImageDraw.Draw(img)
    # Synthetic crater: dark depression with bright rim
    draw.ellipse([30, 30, 60, 60], fill=40, outline=220)
    # Synthetic boulder: bright reflective peak
    draw.rectangle([80, 80, 88, 88], fill=250)

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("utf-8")


@pytest.fixture(autouse=True)
def ensure_clean_service_state():
    """Guarantees service state is restored after each test."""
    hazard_detection_service.reset()
    yield
    hazard_detection_service.reset()


def test_hazard_model_unavailable_contract(client: TestClient) -> None:
    """TASK 5: When no trained model exists, return exact specified schema."""
    hazard_detection_service.reset()
    assert not hazard_detection_service.is_available()

    payload = {
        "image_base64": create_test_image_b64(),
    }
    response = client.post("/api/hazards/predict", json=payload)
    assert response.status_code == 200
    data = response.json()

    # Exact Task 5 contract assertions
    assert data["status"] == "not_available"
    assert data["detections"] == []
    assert data["crater_count"] is None
    assert data["rock_count"] is None
    assert data["warnings"] == ["Hazard detection model is not configured."]


def test_hazard_empty_image_error(client: TestClient) -> None:
    """Tests that an empty image (0 bytes or empty string) returns 400 Bad Request."""
    # Inject active test runner
    hazard_detection_service.set_test_model(lambda t: [])

    # Empty string
    response = client.post("/api/hazards/predict", json={"image_base64": ""})
    assert response.status_code == 400
    assert "empty" in response.json()["detail"].lower()

    # 0-byte encoded data
    empty_b64 = base64.b64encode(b"").decode("utf-8")
    response2 = client.post("/api/hazards/predict", json={"image_base64": empty_b64})
    assert response2.status_code == 400
    assert "empty" in response2.json()["detail"].lower()


def test_hazard_corrupted_image_error(client: TestClient) -> None:
    """Tests that corrupt image bytes return 400 Bad Request without server crash."""
    hazard_detection_service.set_test_model(lambda t: [])

    # Invalid base64 characters
    response = client.post("/api/hazards/predict", json={"image_base64": "!!!NOT_VALID_BASE64!!!"})
    assert response.status_code == 400

    # Valid base64, but not an image
    garbage_b64 = base64.b64encode(b"THIS_IS_NOT_A_VALID_IMAGE_HEADER_123456").decode("utf-8")
    response2 = client.post("/api/hazards/predict", json={"image_base64": garbage_b64})
    assert response2.status_code == 400
    assert "corrupted" in response2.json()["detail"].lower() or "invalid image" in response2.json()["detail"].lower()


def test_hazard_wrong_dimensions_error(client: TestClient) -> None:
    """Tests that images exceeding maximum dimension limits are rejected with 400."""
    hazard_detection_service.set_test_model(lambda t: [])

    # Mock an oversized image
    orig_max = hazard_settings.MAX_IMAGE_WIDTH
    hazard_settings.MAX_IMAGE_WIDTH = 256
    try:
        oversized_b64 = create_test_image_b64(width=300, height=300)
        response = client.post("/api/hazards/predict", json={"image_base64": oversized_b64})
        assert response.status_code == 400
        assert "exceed maximum allowed size" in response.json()["detail"]
    finally:
        hazard_settings.MAX_IMAGE_WIDTH = orig_max


def test_hazard_valid_image_inference_and_scaling(client: TestClient) -> None:
    """Tests successful ML inference with calibrated spatial resolution (meters per pixel)."""
    # Mock inference detections
    def mock_infer(tensor: np.ndarray) -> List[Dict[str, Any]]:
        return [
            {
                "label": "crater",
                "confidence": 0.95,
                "box": [30.0, 30.0, 60.0, 60.0],  # 30 px span
            },
            {
                "label": "rock",
                "confidence": 0.88,
                "box": [80.0, 80.0, 88.0, 88.0],  # 8 px span
            },
        ]

    hazard_detection_service.set_test_model(
        mock_infer,
        metadata={
            "model_name": "LOLA-LROC Test Polar Detector",
            "version": "1.0.0-test",
            "architecture": "MobileNetV3-FPN",
        },
    )

    payload = {
        "image_base64": create_test_image_b64(128, 128),
        "spatial_resolution_mpp": 0.50,  # 0.5 meters per pixel
        "confidence_threshold": 0.50,
    }
    response = client.post("/api/hazards/predict", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "success"
    assert data["crater_count"] == 1
    assert data["rock_count"] == 1
    assert len(data["detections"]) == 2
    assert data["model_name"] == "LOLA-LROC Test Polar Detector"
    assert data["model_version"] == "1.0.0-test"

    # Verify physical metric sizing
    crater_det = data["detections"][0]
    assert crater_det["label"] == "crater"
    assert crater_det["pixel_diameter"] == 30.0
    assert crater_det["estimated_size_m"] == 15.0  # 30 px * 0.5 m/px = 15.0 m
    assert crater_det["severity"] == "high"

    rock_det = data["detections"][1]
    assert rock_det["label"] == "rock"
    assert rock_det["pixel_diameter"] == 8.0
    assert rock_det["estimated_size_m"] == 4.0  # 8 px * 0.5 m/px = 4.0 m
    assert rock_det["severity"] == "critical"  # Rock > 2.0 m is critical

    # Verify Apollo scientific domain limitation is present
    assert "CRITICAL SCIENTIFIC NOTICE" in data["limitations"]
    assert "Apollo" in data["limitations"]


def test_hazard_uncalibrated_spatial_resolution(client: TestClient) -> None:
    """SCIENTIFIC INTEGRITY: Without spatial resolution, do not convert pixels to meters."""
    def mock_infer(tensor: np.ndarray) -> List[Dict[str, Any]]:
        return [
            {"label": "crater", "confidence": 0.92, "box": [10.0, 10.0, 50.0, 50.0]},
        ]

    hazard_detection_service.set_test_model(mock_infer)

    # Omit spatial_resolution_mpp
    payload = {
        "image_base64": create_test_image_b64(128, 128),
    }
    response = client.post("/api/hazards/predict", json=payload)
    assert response.status_code == 200
    data = response.json()

    crater = data["detections"][0]
    assert crater["pixel_diameter"] == 40.0
    assert crater["estimated_size_m"] is None  # MUST be null when uncalibrated!

    # Warning must explicitly document lack of spatial calibration
    assert any("uncalibrated" in w.lower() for w in data["warnings"])


def test_hazard_confidence_threshold_filtering(client: TestClient) -> None:
    """Tests that confidence threshold accurately filters detection results."""
    def mock_infer(tensor: np.ndarray) -> List[Dict[str, Any]]:
        return [
            {"label": "crater", "confidence": 0.95, "box": [10, 10, 20, 20]},
            {"label": "crater", "confidence": 0.70, "box": [30, 30, 40, 40]},
            {"label": "rock", "confidence": 0.40, "box": [50, 50, 60, 60]},
        ]

    hazard_detection_service.set_test_model(mock_infer)
    b64_img = create_test_image_b64(128, 128)

    # Default threshold 0.50 -> rock (0.40) filtered out
    resp_50 = client.post("/api/hazards/predict", json={"image_base64": b64_img, "confidence_threshold": 0.50})
    data_50 = resp_50.json()
    assert len(data_50["detections"]) == 2
    assert data_50["crater_count"] == 2
    assert data_50["rock_count"] == 0

    # High threshold 0.80 -> only 0.95 crater remains
    resp_80 = client.post("/api/hazards/predict", json={"image_base64": b64_img, "confidence_threshold": 0.80})
    data_80 = resp_80.json()
    assert len(data_80["detections"]) == 1
    assert data_80["detections"][0]["confidence"] == 0.95

    # Low threshold 0.30 -> all 3 remain
    resp_30 = client.post("/api/hazards/predict", json={"image_base64": b64_img, "confidence_threshold": 0.30})
    data_30 = resp_30.json()
    assert len(data_30["detections"]) == 3
    assert data_30["rock_count"] == 1


def test_hazard_model_inference_error_handling(client: TestClient) -> None:
    """Tests that internal inference execution failure returns 500 without crashing server."""
    def broken_infer(tensor: np.ndarray):
        raise RuntimeError("Simulated GPU VRAM Out-of-Memory exception during tensor convolution.")

    hazard_detection_service.set_test_model(broken_infer)

    response = client.post(
        "/api/hazards/predict",
        json={"image_base64": create_test_image_b64(128, 128)},
    )
    assert response.status_code == 500
    assert "Simulated GPU VRAM Out-of-Memory" in response.json()["detail"]


def test_hazard_data_uri_prefix_support(client: TestClient) -> None:
    """Tests that data URI scheme prefix (e.g. data:image/png;base64,...) is correctly parsed."""
    def mock_infer(tensor: np.ndarray) -> List[Dict[str, Any]]:
        return [{"label": "crater", "confidence": 0.85, "box": [10, 10, 20, 20]}]

    hazard_detection_service.set_test_model(mock_infer)

    raw_b64 = create_test_image_b64(128, 128)
    data_uri = f"data:image/png;base64,{raw_b64}"

    response = client.post("/api/hazards/predict", json={"image_base64": data_uri})
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert len(response.json()["detections"]) == 1


def test_hazard_image_path_input(client: TestClient, tmp_path) -> None:
    """Tests that local image file path is supported as input."""
    # Save a temporary test image
    temp_img_file = tmp_path / "test_surface.png"
    img = Image.new("L", (100, 100), color=150)
    img.save(str(temp_img_file), format="PNG")

    hazard_detection_service.set_test_model(
        lambda t: [{"label": "crater", "confidence": 0.88, "box": [10, 10, 30, 30]}]
    )

    response = client.post("/api/hazards/predict", json={"image_path": str(temp_img_file)})
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["crater_count"] == 1


def test_hazard_numpy_matrix_postprocessing(client: TestClient) -> None:
    """Tests postprocessing when model outputs raw (N, 6) numpy detection tensor."""
    # Output: [ymin, xmin, ymax, xmax, score, class_id]
    raw_detections = np.array([
        [20.0, 20.0, 50.0, 50.0, 0.91, 0.0],  # crater
        [70.0, 70.0, 78.0, 78.0, 0.87, 1.0],  # rock
        [10.0, 10.0, 15.0, 15.0, 0.25, 0.0],  # crater (low confidence)
    ], dtype=np.float32)

    hazard_detection_service.set_test_model(lambda t: raw_detections)

    payload = {
        "image_base64": create_test_image_b64(128, 128),
        "confidence_threshold": 0.50,
        "spatial_resolution_mpp": 1.0,
    }
    response = client.post("/api/hazards/predict", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["crater_count"] == 1
    assert data["rock_count"] == 1
    assert len(data["detections"]) == 2


def test_hazard_load_model_missing_file_graceful() -> None:
    """Tests that loading a non-existent model path returns False and does not crash."""
    result = hazard_detection_service.load_model("path/to/nonexistent/weights.onnx")
    assert result is False
    assert not hazard_detection_service.is_available()

