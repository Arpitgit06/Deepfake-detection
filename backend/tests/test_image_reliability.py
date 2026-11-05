import io
from unittest.mock import AsyncMock
import pytest
from PIL import Image, ImageDraw
from app.core.config import settings
from app.detectors.ai_generated_image import AIGeneratedImageDetector
from app.detectors.image_reliability import inspect_image_domain
from app.detectors.ai_generated_video import detect_video_ai
from app.services.analysis_service import AnalysisService
from app.services.evidence_report import build_evidence_report
from app.services.llm_manager import LLMManager


def encoded(image):
    stream = io.BytesIO()
    image.save(stream, format='PNG')
    return stream.getvalue()


@pytest.mark.asyncio
@pytest.mark.parametrize('scores,expected', [
    ([.99, .98, .97], 'suspicious'),
    ([.01, .02, .03], 'clean'),
    ([.55, .60, .65], 'inconclusive'),
    ([.01, .99], 'inconclusive'),
])
async def test_experimental_video_classifies_strong_consistent_scores(monkeypatch, scores, expected):
    from app.detectors import ai_generated_video
    monkeypatch.setattr(ai_generated_video, 'sample_frames',
                        lambda _: [(i, b'frame') for i in range(len(scores))])
    detector = type('Detector', (), {})()
    detector.detect = AsyncMock(side_effect=[
        {'raw_model_score': score, 'verdict_eligible': True} for score in scores])
    result = await detect_video_ai(detector, b'clip')
    assert result['status'] == expected
    assert result['verdict_eligible'] is True
    assert result['decision_reason'] == 'experimental_opt_in'
    report = build_evidence_report({'ai_generated_video': result})
    assert any('experimental' in note.lower() for note in report['limitations'])


@pytest.mark.asyncio
async def test_video_uses_configured_not_hardcoded_thresholds(monkeypatch):
    from app.detectors import ai_generated_video
    monkeypatch.setattr(settings, 'AI_IMAGE_FAKE_THRESHOLD', .9)
    monkeypatch.setattr(ai_generated_video, 'sample_frames', lambda _: [(0, b'frame')])
    detector = type('Detector', (), {})()
    detector.detect = AsyncMock(return_value={'raw_model_score': .8, 'verdict_eligible': True})
    result = await detect_video_ai(detector, b'clip')
    assert result['status'] == 'inconclusive'
    report = build_evidence_report({'ai_generated_video': result})
    assert any('90%' in item['meaning'] for item in report['findings'])


@pytest.mark.asyncio
@pytest.mark.parametrize('activation', [.01, .60, .8324, .9999])
async def test_uncalibrated_activation_is_not_a_verdict(monkeypatch, activation):
    monkeypatch.setattr(settings, 'AI_IMAGE_EXPERIMENTAL_VERDICTS', False)
    detector = AIGeneratedImageDetector()
    monkeypatch.setattr(detector, '_predict', lambda _: activation)
    result = await detector.detect(encoded(Image.new('RGB', (160, 160), 'navy')), explain_regions=True)
    assert result['raw_model_score'] == activation
    assert result['ai_probability'] is None
    assert result['verdict_eligible'] is False
    assert result['status'] == 'inconclusive'
    assert result['confidence'] == 0
    assert result['is_ai_generated'] is None
    assert 'region_analysis' not in result
    report = build_evidence_report({'ai_generated_image': result})
    assert not any('threshold' in item['meaning'] for item in report['findings'])


def test_page_layout_is_not_a_real_or_fake_label():
    image = Image.new('RGB', (720, 960), '#454545')
    draw = ImageDraw.Draw(image)
    # Repeated letter-sized marks exercise both polarity and row routing,
    # independently of the user's photograph or file name.
    for row in range(24):
        for column in range(32):
            x, y = 40 + column*17, 40 + row*32
            draw.rectangle((x, y, x+7, y+11), fill='#dddddd')
    domain = inspect_image_domain(image)
    assert domain['kind'] == 'document_like'
    assert domain['text_like_rows'] >= 8
    assert 'cannot distinguish' in domain['limitation']


@pytest.mark.asyncio
async def test_document_guard_cannot_be_overridden_by_experimental_opt_in(monkeypatch):
    monkeypatch.setattr(settings, 'AI_IMAGE_EXPERIMENTAL_VERDICTS', True)
    from app.detectors import ai_generated_image
    monkeypatch.setattr(ai_generated_image, 'inspect_image_domain', lambda _: {
        'kind': 'document_like', 'text_like_rows': 12, 'observation': 'Repeated text-like rows.'})
    detector = AIGeneratedImageDetector()
    monkeypatch.setattr(detector, '_predict', lambda _: .99)
    result = await detector.detect(encoded(Image.new('RGB', (300, 400), 'gray')))
    assert result['status'] == 'inconclusive'
    assert result['decision_reason'] == 'unsupported_document_domain'


@pytest.mark.asyncio
async def test_video_does_not_turn_repeated_unreliable_scores_into_certainty(monkeypatch):
    from app.detectors import ai_generated_video
    monkeypatch.setattr(ai_generated_video, 'sample_frames', lambda _: [(0, b'a'), (1, b'b')])
    detector = type('Detector', (), {})()
    detector.detect = AsyncMock(return_value={'ai_probability': .99, 'verdict_eligible': False})
    result = await detect_video_ai(detector, b'clip')
    assert result['status'] == 'inconclusive'
    assert result['confidence'] == 0
    assert result['verdict_eligible'] is False


@pytest.mark.asyncio
async def test_persuasive_media_summary_is_not_requested_for_unsupported_score(monkeypatch):
    from app.services import analysis_service as module
    monkeypatch.setattr(settings, 'LLM_ENABLED', True)
    summarize = AsyncMock(return_value='This is definitely fake.')
    monkeypatch.setattr(module.llm_manager, 'summarize', summarize)
    monkeypatch.setattr(module.llm_manager, 'unload', lambda: None)
    service = AnalysisService.__new__(AnalysisService)
    payload = service._format_response('unreliable', {'ai_generated_image': {
        'status': 'suspicious', 'confidence': .99, 'ai_probability': .99, 'verdict_eligible': False}}, 0)
    result = await service._attach_llm_summary(payload)
    assert result['status'] == 'inconclusive'
    assert result['explanation_source'] == 'measured_findings'
    assert 'not a reliable real/fake percentage' in result['llm_summary']
    summarize.assert_not_awaited()
    manager = LLMManager()
    monkeypatch.setattr(manager, 'generate', summarize)
    answer = await manager.ask('Why is it fake?', payload)
    assert 'inconclusive' in answer
    summarize.assert_not_awaited()


def test_evaluation_does_not_count_abstention_as_correct():
    from evaluate_image_detector import summarize
    metrics = summarize([
        {'label': 'real', 'raw_score': .8324, 'verdict': 'inconclusive'},
        {'label': 'ai', 'raw_score': .99, 'verdict': 'inconclusive'}])
    assert metrics['raw_false_positives'] == 1
    assert metrics['policy_coverage'] == 0
    assert metrics['policy_accuracy_on_decisions'] is None
