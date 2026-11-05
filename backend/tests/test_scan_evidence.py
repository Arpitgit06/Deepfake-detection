import json
from unittest.mock import AsyncMock
import numpy as np
import pytest
from app.detectors.phoneme_viseme import PhonemeVisemeDetector
from app.detectors.financial_threat import FinancialThreatDetector
from app.detectors.ai_generated_video import detect_video_ai
from app.services.evidence_report import build_evidence_report
from app.services.llm_manager import LLMManager
from app.services.analysis_service import AnalysisService
from app.core.config import settings


@pytest.mark.asyncio
@pytest.mark.parametrize('failure', ['no_audio', 'no_speech', 'exception', 'missing_model'])
async def test_lip_sync_unavailable_never_crashes_or_calls_video_fake(monkeypatch, failure):
    detector = PhonemeVisemeDetector.__new__(PhonemeVisemeDetector)
    detector.use_asr = failure != 'missing_model'
    extraction = AsyncMock(return_value=(None, 30, []))
    if failure == 'exception':
        extraction.side_effect = ValueError('bad clip')
    elif failure == 'no_speech':
        extraction.return_value = (np.ones(10), 30, [np.zeros((10, 10, 3))])
        detector._extract_phonemes = AsyncMock(return_value=([], []))
        detector._extract_visemes = AsyncMock(return_value=([], []))
    monkeypatch.setattr(detector, '_extract_audio_video', extraction)
    result = await detector.detect(b'clip')
    assert result['status'] == 'inconclusive'
    assert result['is_synchronized'] is None
    assert result['sync_score'] == 0
    assert result['confidence'] == 0


@pytest.mark.asyncio
@pytest.mark.parametrize('scores,status', [([.9, .95], 'suspicious'), ([.1, .2], 'clean'),
                                         ([.6, .6], 'inconclusive'), ([.1, .9], 'inconclusive'),
                                         ([None, .95], 'inconclusive')])
async def test_video_frame_scores_and_timestamps(monkeypatch, scores, status):
    from app.detectors import ai_generated_video
    monkeypatch.setattr(ai_generated_video, 'sample_frames', lambda _: [(0, b'a'), (2, b'b')])
    detector = type('Detector', (), {})()
    detector.detect = AsyncMock(side_effect=[{'ai_probability': score, 'verdict_eligible': True} for score in scores])
    result = await detect_video_ai(detector, b'clip')
    assert result['status'] == status
    assert result['frame_scores'][-1]['timestamp_seconds'] == 2


@pytest.mark.asyncio
@pytest.mark.parametrize('payload,expected', [
    ({'status': 'suspicious', 'findings': [{'quote': 'send your password', 'reason': 'Requests a secret.'}]}, 'suspicious'),
    ({'status': 'suspicious', 'findings': [{'quote': 'invented evidence', 'reason': 'Scam.'}]}, 'inconclusive'),
    ({'status': 'clean', 'findings': []}, 'clean'),
    ({'status': 'certainly fake', 'findings': []}, 'unavailable'),
    ([], 'unavailable'),
])
async def test_qwen_text_evidence_must_exist_in_input(monkeypatch, payload, expected):
    monkeypatch.setattr(settings, 'LLM_ENABLED', True)
    manager = LLMManager()
    monkeypatch.setattr(manager, 'generate', AsyncMock(return_value=json.dumps(payload)))
    result = await manager.scan_text('Please send your password now.', {})
    assert result['status'] == expected
    assert result['confidence'] == 0


def test_conflicting_text_verdicts_abstain():
    service = AnalysisService.__new__(AnalysisService)
    result = service._format_response('conflict', {
        'financial_threat': {'status': 'clean', 'risk_score': .1},
        'llm_text_review': {'status': 'suspicious', 'findings': []}}, 0)
    assert result['status'] == 'inconclusive'
    combined = service._format_response('multimodal-conflict', {
        'financial_threat': {'status': 'clean', 'risk_score': .1},
        'llm_text_review': {'status': 'suspicious', 'findings': []},
        'ai_generated_image': {'status': 'suspicious', 'ai_probability': .99}}, 0)
    assert combined['status'] == 'suspicious'


@pytest.mark.asyncio
async def test_url_heuristics_are_not_external_intelligence():
    detector = FinancialThreatDetector()
    result = await detector.detect('Open https://example.xyz immediately to verify your password.')
    intel = result['threat_intelligence']
    assert intel['status'] == 'not_configured'
    assert intel['checked_entities'] == 0
    assert not intel['malicious_entities']
    assert not intel['clean_entities']
    points = sum(item['points'] for item in result['score_basis']) / 100
    assert min(points, 1) == pytest.approx(result['risk_score'], abs=.001)


def test_keywords_do_not_match_inside_unrelated_words():
    assert not FinancialThreatDetector()._detect_tactics('The application is a pineapple illustration.')


def test_sixty_percent_report_explains_abstention_without_invented_artifacts():
    report = build_evidence_report({'ai_generated_image': {'ai_probability': .6, 'status': 'inconclusive'}})
    assert '60.0%' in report['findings'][0]['observation']
    assert 'abstains' in report['findings'][0]['meaning']
    assert 'does not localize' in report['limitations'][0]


def test_occlusion_reports_measured_score_change(monkeypatch):
    from PIL import Image
    from app.detectors.ai_generated_image import AIGeneratedImageDetector
    image = Image.new('RGB', (90, 90), 'gray')
    image.paste('red', (0, 0, 30, 30))
    detector = AIGeneratedImageDetector()
    monkeypatch.setattr(detector, '_predict', lambda value: .9 if value.getpixel((0, 0))[0] > 200 else .1)
    result = detector._explain_regions(image, .9)
    assert result['regions'][0]['region'] == 'upper left'
    assert result['regions'][0]['support_drop_points'] == 80
    assert result['preview_base64']
    assert 'not proven' in result['limitation']


@pytest.mark.asyncio
async def test_media_review_requires_references_to_actual_findings(monkeypatch):
    manager = LLMManager()
    monkeypatch.setattr(manager, 'generate', AsyncMock(return_value=json.dumps({
        'assessment': 'needs_review', 'finding_indices': [99], 'reason': 'Unsupported finding.'})))
    result = await manager.review_media_evidence({'evidence_report': {'findings': [{'check': 'a'}]}})
    assert result['status'] == 'unavailable'


@pytest.mark.asyncio
async def test_ppg_sampling_rate_matches_returned_timestamps(monkeypatch):
    from app.detectors import ppg_liveness
    detector = ppg_liveness.PPGLivenessDetector.__new__(ppg_liveness.PPGLivenessDetector)
    class Capture:
        index = 0
        def get(self, _):
            return 30
        def read(self):
            self.index += 1
            return (self.index <= 60, np.zeros((4, 4, 3), dtype=np.uint8))
        def release(self):
            pass
    monkeypatch.setattr(ppg_liveness.cv2, 'VideoCapture', lambda _: Capture())
    frames, fps, times = await detector._extract_frames(b'clip', 5)
    assert len(frames) == 10
    assert fps == pytest.approx(1 / (times[1] - times[0]))
    assert fps == 5  # Source video was 30 fps; sampled signal is not.


@pytest.mark.asyncio
async def test_short_video_does_not_claim_missing_pulse_is_fake(monkeypatch):
    from app.detectors.ppg_liveness import PPGLivenessDetector
    detector = PPGLivenessDetector.__new__(PPGLivenessDetector)
    monkeypatch.setattr(detector, '_extract_frames', AsyncMock(return_value=(
        [np.zeros((4, 4, 3))] * 30, 10, [i / 10 for i in range(30)])))
    result = await detector.detect(b'clip')
    assert result['status'] == 'inconclusive'
    assert result['confidence'] == 0
