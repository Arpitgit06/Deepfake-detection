import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_image_upload_round_trip(monkeypatch):
    import io
    from PIL import Image
    from app.core.config import settings
    monkeypatch.setattr(settings, 'LLM_ENABLED', False)
    payload = io.BytesIO()
    Image.new('RGB', (128, 128), 'white').save(payload, format='PNG')
    response = client.post('/api/v1/analyze/image', files={
        'file': ('sample.png', payload.getvalue(), 'image/png'),
    }, data={'return_heatmap': 'true', 'sensitivity': '0.5'})
    assert response.status_code == 200
    result = response.json()
    assert 'image_deepfake' in result['results']
    assert result['timestamp']
    report = client.get(f"/api/v1/analyze/{result['analysis_id']}/report")
    assert report.status_code == 200
    assert report.json()['analysis_id'] == result['analysis_id']


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


@pytest.mark.parametrize('text', ['', '   \n '])
def test_analyze_text_empty(text):
    response = client.post(
        "/api/v1/analyze/text",
        json={
            "text": text,
        },
    )
    assert response.status_code == 422


@pytest.mark.parametrize('endpoint,mime', [('image', 'image/png'), ('video', 'video/mp4')])
def test_upload_limits_and_empty_files(monkeypatch, endpoint, mime):
    from app.core.config import settings
    monkeypatch.setattr(settings, 'MAX_FILE_SIZE', 8)
    for contents, expected in [(b'', 400), (b'123456789', 413)]:
        response = client.post(f'/api/v1/analyze/{endpoint}', files={
            'file': ('sample', contents, mime)})
        assert response.status_code == expected


def test_scan_option_ranges():
    response = client.post('/api/v1/analyze/video', files={
        'file': ('sample.mp4', b'clip', 'video/mp4')}, data={'sample_rate': '0'})
    assert response.status_code == 422
    response = client.post('/api/v1/analyze/image', files={
        'file': ('sample.png', b'image', 'image/png')}, data={'sensitivity': '2'})
    assert response.status_code == 422


def test_multimodal_rejects_empty_and_invalid_uploads(monkeypatch):
    from app.core.config import settings
    assert client.post('/api/v1/analyze/multimodal').status_code == 400
    assert client.post('/api/v1/analyze/multimodal', data={'text_content': '  '}).status_code == 400
    assert client.post('/api/v1/analyze/multimodal', files={
        'image': ('bad.txt', b'bad', 'text/plain')}).status_code == 400
    monkeypatch.setattr(settings, 'MAX_FILE_SIZE', 8)
    assert client.post('/api/v1/analyze/multimodal', files={
        'image': ('large.png', b'123456789', 'image/png')}).status_code == 413
    assert client.post('/api/v1/analyze/multimodal', files={
        'audio': ('audio.wav', b'audio', 'audio/wav')}).status_code == 400


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
