"""Bounded whole-frame sampling using the shared image classifier."""
import asyncio
import os
import tempfile
import cv2
import numpy as np
from app.core.config import settings


def sample_frames(video_bytes, limit=12):
    path = None
    cap = None
    try:
        with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as stream:
            stream.write(video_bytes)
            path = stream.name
        cap = cv2.VideoCapture(path)
        count, fps = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)), cap.get(cv2.CAP_PROP_FPS)
        if count <= 0 or not np.isfinite(fps) or fps <= 0:
            return []
        frames = []
        for index in np.unique(np.linspace(0, count - 1, min(limit, count), dtype=int)):
            cap.set(cv2.CAP_PROP_POS_FRAMES, int(index))
            ok, frame = cap.read()
            if ok:
                encoded, data = cv2.imencode('.png', frame)
                if encoded:
                    frames.append((float(index / fps), data.tobytes()))
        return frames
    finally:
        if cap is not None:
            cap.release()
        if path:
            os.unlink(path)


async def detect_video_ai(detector, video_bytes):
    frames = await asyncio.to_thread(sample_frames, video_bytes)
    scores, failures, eligibility = [], 0, []
    for timestamp, image in frames:
        result = await detector.detect(image)
        activation = result.get('raw_model_score', result.get('ai_probability'))
        if activation is None:
            failures += 1
        else:
            eligibility.append(result.get('verdict_eligible') is True)
            scores.append({'timestamp_seconds': round(timestamp, 3),
                           'raw_model_score': activation,
                           'ai_probability': activation if result.get('verdict_eligible') is True else None})
    if not scores:
        return {'status': 'inconclusive', 'confidence': 0, 'sampled_frames': 0,
                'explanations': [{'type': 'video_sampling', 'severity': 'warning',
                                  'message': 'No video frames could be classified; authenticity is unknown.'}]}
    average = sum(item['raw_model_score'] for item in scores) / len(scores)
    # Mixed frame predictions or partial failure require review rather than a binary claim.
    low, high = settings.AI_IMAGE_REAL_THRESHOLD, settings.AI_IMAGE_FAKE_THRESHOLD
    mixed = min(item['raw_model_score'] for item in scores) <= low and max(item['raw_model_score'] for item in scores) >= high
    status = ('inconclusive' if mixed or failures else
              'suspicious' if average >= high else 'clean' if average <= low else 'inconclusive')
    eligible = bool(eligibility and all(eligibility))
    if not eligible:
        status = 'inconclusive'
    return {'status': status, 'confidence': round(max(average, 1-average), 4) if status != 'inconclusive' else 0,
            'verdict_eligible': eligible, 'score_kind': 'uncalibrated_softmax',
            'raw_model_score': round(average, 4), 'decision_reason': 'unvalidated_frame_classifier' if not eligible else 'experimental_opt_in',
            'decision_thresholds': {'real_max': low, 'ai_min': high},
            'ai_probability': round(average, 4) if eligible else None, 'sampled_frames': len(scores),
            'frame_scores': scores, 'mixed_frame_evidence': mixed, 'failed_frames': failures,
            'analysis_scope': 'sampled_whole_frames',
            'explanations': [{'type': 'video_ai_patterns', 'severity': 'warning' if status != 'clean' else 'info',
                              'message': f"Checked {len(scores)} whole frames across the clip. "
                                         + ('Their unvalidated classifier activations cannot establish video authenticity. ' if not eligible else f'Experimental average activation: {average:.1%}. ')
                                         + ('Frames disagree; the result needs review. ' if mixed else '')
                                         + 'This image model is applied to sampled frames; it is not a trained temporal video detector and may miss edits between samples.'}]}
