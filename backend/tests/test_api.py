import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_root():
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "TruthLens AI"
    assert data["status"] == "operational"


def test_health():
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data
    assert "gpu_available" in data


def test_detailed_health():
    response = client.get("/api/v1/health/detailed")
    assert response.status_code == 200
    data = response.json()
    assert "system" in data
    assert "gpu" in data
    assert "opencv" in data
    assert "torch" in data


def test_analyze_text_endpoint():
    response = client.post(
        "/api/v1/analyze/text",
        json={
            "text": "This is a test message",
            "extract_entities": True,
            "check_threat_intel": True,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert "analysis_id" in data
    assert "status" in data
    assert "confidence" in data
    assert "results" in data
    assert "explanations" in data
    assert "financial_threat" in data["results"]


def test_analyze_text_empty():
    response = client.post(
        "/api/v1/analyze/text",
        json={
            "text": "",
        },
    )
    # Should handle empty text gracefully
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_ppg_detector_import():
    from app.detectors.ppg_liveness import PPGLivenessDetector
    detector = PPGLivenessDetector()
    assert detector is not None


@pytest.mark.asyncio
async def test_phoneme_viseme_detector_import():
    from app.detectors.phoneme_viseme import PhonemeVisemeDetector
    detector = PhonemeVisemeDetector()
    assert detector is not None


@pytest.mark.asyncio
async def test_financial_threat_detector_import():
    from app.detectors.financial_threat import FinancialThreatDetector
    detector = FinancialThreatDetector()
    assert detector is not None


@pytest.mark.asyncio
async def test_deepfake_detector_import():
    from app.detectors.deepfake_image import DeepfakeImageDetector
    detector = DeepfakeImageDetector()
    assert detector is not None