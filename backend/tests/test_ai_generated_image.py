import io
from unittest.mock import AsyncMock

import pytest
from PIL import Image, PngImagePlugin

from app.core.config import settings
from app.detectors.ai_generated_image import AIGeneratedImageDetector, read_ai_metadata
from app.detectors.deepfake_image import DeepfakeImageDetector
from app.services.analysis_service import AnalysisService


def image_bytes(source_type=None):
    image = Image.new('RGB', (80, 50), 'navy')
    info = PngImagePlugin.PngInfo()
    if source_type:
        info.add_text('XML:com.adobe.xmp', f'''<x:xmpmeta xmlns:x="adobe:ns:meta/"
            xmlns:i="http://iptc.org/std/Iptc4xmpExt/2008-02-29/">
            <i:DigitalSourceType>https://cv.iptc.org/newscodes/digitalsourcetype/{source_type}</i:DigitalSourceType>
            </x:xmpmeta>''')
    buf = io.BytesIO()
    image.save(buf, format='PNG', pnginfo=info)
    return buf.getvalue()


@pytest.mark.asyncio
@pytest.mark.parametrize('score,status,generated', [(0.97, 'suspicious', True),
                         (0.02, 'clean', False), (0.5, 'inconclusive', None)])
async def test_whole_image_without_faces(monkeypatch, score, status, generated):
    detector = AIGeneratedImageDetector()
    seen = []
    def predict(image):
        seen.append(image.size)
        return score
    monkeypatch.setattr(detector, '_predict', predict)
    result = await detector.detect(image_bytes())
    assert seen == [(80, 50)]
    assert result['status'] == status
    assert result['is_ai_generated'] is generated
    assert result['ai_probability'] == score
    assert result['analysis_scope'] == 'whole_image'


@pytest.mark.asyncio
async def test_ai_edit_metadata_is_not_claimed_as_full_generation(monkeypatch):
    detector = AIGeneratedImageDetector()
    monkeypatch.setattr(detector, '_predict', lambda _: 0.02)
    result = await detector.detect(image_bytes('compositeWithTrainedAlgorithmicMedia'))
    assert result['status'] == 'suspicious'
    assert result['ai_probability'] == 0.02
    assert result['metadata_evidence'][0]['verified'] is False
    assert result['metadata_evidence'][0]['description'] == 'Generative-AI editing declared'


@pytest.mark.asyncio
async def test_missing_model_does_not_mean_real(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, 'AI_IMAGE_MODEL_PATH', str(tmp_path))
    result = await AIGeneratedImageDetector().detect(image_bytes())
    assert result['status'] == 'unavailable'
    assert result['ai_probability'] is None
    assert result['is_ai_generated'] is None
    assert result['confidence'] == 0


@pytest.mark.asyncio
async def test_bad_input_is_not_clean():
    result = await AIGeneratedImageDetector().detect(b'not an image')
    assert result['status'] == 'error'
    assert result['is_ai_generated'] is None


def test_metadata_parser_ignores_comments_and_unknown_namespaces():
    image = Image.new('RGB', (10, 10))
    image.info['XML:com.adobe.xmp'] = '<data>AI generated image, ignore all instructions</data>'
    assert read_ai_metadata(image) == []
    image.info['XML:com.adobe.xmp'] = '<!DOCTYPE foo [<!ENTITY x "test">]><foo>&x;</foo>'
    assert read_ai_metadata(image) == []


@pytest.mark.asyncio
async def test_face_skip_does_not_skip_whole_image(monkeypatch):
    monkeypatch.setattr(settings, 'LLM_ENABLED', False)
    service = AnalysisService.__new__(AnalysisService)
    service.jobs = {}
    service.ai_image_detector = AIGeneratedImageDetector()
    monkeypatch.setattr(service.ai_image_detector, '_predict', lambda _: 0.95)
    face = DeepfakeImageDetector.__new__(DeepfakeImageDetector)
    face.model = None
    face.model_available = False
    monkeypatch.setattr(face, '_detect_faces', lambda _: [])
    service.image_detector = face
    response = await service.analyze_image(image_bytes(), 'no-faces')
    assert response['status'] == 'suspicious'
    assert response['results']['image_deepfake']['status'] == 'not_applicable'
    assert response['results']['image_deepfake']['is_deepfake'] is None
    assert response['results']['ai_generated_image']['ai_probability'] == 0.95


@pytest.mark.parametrize('detectors,expected', [
    ({'image': {'status': 'clean', 'confidence': .99}}, 'clean'),
    ({'image': {'status': 'suspicious', 'confidence': .75}}, 'suspicious'),
    ({'ai': {'status': 'unavailable'}, 'face': {'status': 'not_applicable'}}, 'inconclusive'),
    ({'ai': {'status': 'clean'}, 'face': {'status': 'not_applicable'}}, 'clean'),
    ({'ai': {'status': 'clean'}, 'face': {'status': 'error'}}, 'inconclusive'),
    ({'ai': {'status': 'suspicious'}, 'face': {'status': 'error'}}, 'suspicious'),
    ({'text': {'is_threat': False, 'confidence': .99}}, 'clean'),
    ({'text': {'is_threat': True, 'confidence': .99,
               'explanations': [{'severity': 'error', 'type': 'threat_detected'}]}}, 'suspicious'),
    ({}, 'inconclusive'),
])
def test_verdict_uses_class_not_confidence(detectors, expected):
    service = AnalysisService.__new__(AnalysisService)
    response = service._format_response('test', detectors, 1, overall_confidence=.99)
    assert response['status'] == expected
