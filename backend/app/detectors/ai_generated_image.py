"""Whole-image AI classification, independent of face detection.

Only pinned local safetensors are loaded; inference never uploads input media.
Metadata declarations and classifier scores are kept separate and neither is
presented as proof of authenticity.
"""
import asyncio
import io
import logging
import threading
from pathlib import Path
from xml.etree import ElementTree as ET

import torch
from PIL import Image, ImageOps
from transformers import AutoImageProcessor, AutoModelForImageClassification

from app.core.config import settings
from app.detectors.image_reliability import inspect_image_domain

logger = logging.getLogger(__name__)
IPTC_SOURCE = '{http://iptc.org/std/Iptc4xmpExt/2008-02-29/}DigitalSourceType'
AI_SOURCE_TYPES = {
    'trainedAlgorithmicMedia': 'AI generation declared',
    'compositeWithTrainedAlgorithmicMedia': 'Generative-AI editing declared',
    'compositeSynthetic': 'Composite containing AI-generated content declared',
}


def read_ai_metadata(image: Image.Image) -> list[dict]:
    """Read structured IPTC declarations, not arbitrary comments or filenames."""
    raw = image.info.get('XML:com.adobe.xmp') or image.info.get('xmp')
    if not raw:
        raw = image.getexif().get(700)
    if not isinstance(raw, (str, bytes)) or len(raw) > 262144:
        return []
    if isinstance(raw, bytes):
        raw = raw.decode('utf-8', errors='replace')
    if '<!DOCTYPE' in raw.upper() or '<!ENTITY' in raw.upper():
        return []
    try:
        root = ET.fromstring(raw)
    except (ET.ParseError, ValueError):
        return []
    values = set()
    for element in root.iter():
        if element.tag == IPTC_SOURCE:
            values.add((element.text or '').strip())
            resource = element.attrib.get('{http://www.w3.org/1999/02/22-rdf-syntax-ns#}resource')
            if resource:
                values.add(resource)
        if IPTC_SOURCE in element.attrib:
            values.add(element.attrib[IPTC_SOURCE])
    evidence = []
    for value in sorted(values):
        for scheme in ('http', 'https'):
            prefix = f'{scheme}://cv.iptc.org/newscodes/digitalsourcetype/'
            source = value.removeprefix(prefix)
            if value.startswith(prefix) and source in AI_SOURCE_TYPES:
                evidence.append({'source_type': source, 'description': AI_SOURCE_TYPES[source],
                                 'verified': False})
    return evidence


class AIGeneratedImageDetector:
    def __init__(self):
        self._lock = threading.Lock()
        self.model = None
        self.processor = None
        self.device = None
        self.last_error = None

    def status(self):
        path = Path(settings.AI_IMAGE_MODEL_PATH)
        return {'model_id': settings.AI_IMAGE_MODEL_ID,
                'revision': settings.AI_IMAGE_MODEL_REVISION,
                'downloaded': all((path / f).is_file() for f in
                                  ('config.json', 'preprocessor_config.json', 'model.safetensors')),
                'loaded': self.model is not None, 'device': self.device,
                'calibration_status': 'unvalidated_for_uploads',
                'experimental_verdicts_enabled': settings.AI_IMAGE_EXPERIMENTAL_VERDICTS,
                'gpu_required': settings.AI_IMAGE_REQUIRE_GPU, 'last_error': self.last_error}

    def _load(self):
        if self.model is not None:
            return
        if not self.status()['downloaded']:
            raise RuntimeError('Whole-image classifier missing. Run backend/download_image_model.py.')
        if settings.AI_IMAGE_REQUIRE_GPU and not torch.cuda.is_available():
            raise RuntimeError('Whole-image classifier requires CUDA PyTorch. CPU fallback is disabled.')
        device = 'cuda:0' if torch.cuda.is_available() else 'cpu'
        processor = AutoImageProcessor.from_pretrained(settings.AI_IMAGE_MODEL_PATH, local_files_only=True)
        model = AutoModelForImageClassification.from_pretrained(
            settings.AI_IMAGE_MODEL_PATH, local_files_only=True,
            use_safetensors=True, trust_remote_code=False,
        )
        labels = {int(k): str(v).lower() for k, v in model.config.id2label.items()}
        fake_labels = [i for i, label in labels.items() if label in ('fake', 'ai', 'artificial', 'ai-generated')]
        real_labels = [i for i, label in labels.items() if label in ('real', 'human', 'hum')]
        if len(labels) != 2 or len(fake_labels) != 1 or len(real_labels) != 1:
            raise RuntimeError(f'Unsupported classifier label mapping: {labels}')
        model.to(device).eval()
        self.model, self.processor = model, processor
        self.fake_label = fake_labels[0]
        self.device = device
        self.last_error = None

    def _predict(self, image):
        with self._lock:
            self._load()
            inputs = self.processor(images=image, return_tensors='pt')
            inputs = {key: value.to(self.device) for key, value in inputs.items()}
            with torch.inference_mode():
                probabilities = torch.softmax(self.model(**inputs).logits, dim=-1)
            score = float(probabilities[0, self.fake_label].item())
            if not 0 <= score <= 1:
                raise RuntimeError('Classifier returned an invalid probability')
            return score

    def _explain_regions(self, image, baseline):
        """Occlusion sensitivity: measure score changes, not proven forgery locations."""
        from PIL import ImageStat, ImageDraw
        import base64
        reduced = image.copy()
        reduced.thumbnail((960, 960))
        width, height = reduced.size
        fill = tuple(int(value) for value in ImageStat.Stat(reduced).mean[:3])
        regions = []
        # Use the same resolution for both baseline and masked predictions.
        input_score = baseline
        baseline = self._predict(reduced)
        target_ai = baseline >= .5
        for row in range(3):
            for column in range(3):
                box = (column * width // 3, row * height // 3,
                       (column + 1) * width // 3, (row + 1) * height // 3)
                masked = reduced.copy()
                masked.paste(fill, box)
                masked_score = self._predict(masked)
                change = baseline - masked_score if target_ai else masked_score - baseline
                regions.append({'region': ['upper', 'middle', 'lower'][row] + ' ' + ['left', 'center', 'right'][column],
                                'box_normalized': [box[0]/width, box[1]/height, box[2]/width, box[3]/height],
                                'support_drop_points': round(change * 100, 2),
                                'masked_ai_score': round(masked_score, 4)})
        regions.sort(key=lambda item: item['support_drop_points'], reverse=True)
        regions = [item for item in regions[:3] if item['support_drop_points'] >= 1]
        draw = ImageDraw.Draw(reduced)
        for index, item in enumerate(regions):
            box = [int(value * (width if position % 2 == 0 else height))
                   for position, value in enumerate(item['box_normalized'])]
            draw.rectangle(box, outline='orange', width=max(2, width//180))
            draw.text((box[0]+6, box[1]+6), str(index+1), fill='orange', stroke_width=1)
        output = io.BytesIO()
        reduced.save(output, format='JPEG', quality=85)
        return {'method': '3x3_occlusion_sensitivity', 'target_class': 'AI' if target_ai else 'human',
                'baseline_ai_score': round(baseline, 4), 'input_ai_score': round(input_score, 4), 'regions': regions,
                'preview_base64': base64.b64encode(output.getvalue()).decode(),
                'limitation': 'Highlighted areas influenced the classifier when covered with a solid color. '
                              'They are not proven manipulated regions. Masking introduces artificial changes and can itself affect predictions.'}

    async def detect(self, image_bytes: bytes, explain_regions: bool = False):
        try:
            with Image.open(io.BytesIO(image_bytes)) as source:
                metadata = read_ai_metadata(source)
                image = ImageOps.exif_transpose(source).convert('RGB')
                image.load()
        except Exception as exc:
            return self._result('error', None, [], [{
                'type': 'decode_error', 'severity': 'error',
                'message': 'Image could not be decoded; authenticity was not assessed.',
            }], error=str(exc))

        explanations = [{
            'type': 'whole_image_scope', 'severity': 'info',
            'message': 'Analyzes the entire image for AI-generation patterns. A face is not required.',
        }]
        score = None
        error = None
        domain = await asyncio.to_thread(inspect_image_domain, image)
        eligible = settings.AI_IMAGE_EXPERIMENTAL_VERDICTS and domain['kind'] != 'document_like'
        try:
            score = await asyncio.to_thread(self._predict, image)
            status = ('suspicious' if score >= settings.AI_IMAGE_FAKE_THRESHOLD else
                      'clean' if score <= settings.AI_IMAGE_REAL_THRESHOLD else 'inconclusive')
            if not eligible:
                status = 'inconclusive'
            descriptions = {
                'suspicious': 'Experimental classifier indicator exceeds the configured threshold; this is not verified evidence of AI generation.',
                'clean': 'The classifier favors the real/human class; this does not prove authenticity.',
                'inconclusive': 'No reliable authenticity verdict is available. An unvalidated classifier activation cannot establish whether this image is real or AI-generated.',
            }
            explanations.append({'type': 'ai_image_prediction',
                                 'severity': 'warning' if status != 'clean' else 'info',
                                 'message': descriptions[status],
                                 'details': {'raw_classifier_activation': round(score, 4),
                                             'model': settings.AI_IMAGE_MODEL_ID}})
        except Exception as exc:
            error = self.last_error = str(exc)
            logger.warning('Whole-image classification unavailable: %s', exc)
            status = 'unavailable'
            explanations.append({'type': 'classifier_unavailable', 'severity': 'warning',
                                 'message': error})

        if metadata:
            for item in metadata:
                explanations.append({'type': 'ai_metadata', 'severity': 'warning',
                    'message': f"{item['description']} in IPTC metadata. This unsigned declaration can be edited and is not verified proof.",
                    'details': item})
        explanations.append({'type': 'detector_limitations', 'severity': 'info',
            'message': 'Model scores are not calibrated certainty. New generators, screenshots, compression and digital artwork can cause false positives or false negatives.'})
        result = self._result(status, score, metadata, explanations, error=error)
        result.update({'verdict_eligible': bool(eligible and score is not None),
                       'raw_model_score': round(score, 4) if score is not None else None,
                       'score_kind': 'uncalibrated_softmax', 'input_domain': domain,
                       'decision_thresholds': {'real_max': settings.AI_IMAGE_REAL_THRESHOLD,
                                               'ai_min': settings.AI_IMAGE_FAKE_THRESHOLD},
                       'decision_reason': ('unsupported_document_domain' if domain['kind'] == 'document_like' else
                                           'experimental_opt_in' if eligible else 'unvalidated_classifier')})
        if not eligible:
            result['ai_probability'] = None
            result['is_ai_generated'] = None
            result['confidence'] = 0
            result['explanations'].append({'type': 'reliability_abstention', 'severity': 'warning',
                                          'message': domain['observation'] + ' The classifier score is diagnostic only; no authenticity probability is available.'})
        if explain_regions and score is not None and eligible:
            try:
                result['region_analysis'] = await asyncio.to_thread(self._explain_regions, image, score)
            except Exception as exc:
                logger.warning('Region explanation unavailable: %s', exc)
                result['region_analysis_error'] = 'Region influence could not be measured; the classifier score is still available.'
        return result

    def _result(self, status, score, metadata, explanations, error=None):
        return {'detector': 'ai_generated_image', 'status': status,
                'is_ai_generated': (None if score is None else True if score >= settings.AI_IMAGE_FAKE_THRESHOLD
                                    else False if score <= settings.AI_IMAGE_REAL_THRESHOLD else None),
                'ai_probability': round(score, 4) if score is not None else None,
                'confidence': round(max(score, 1 - score), 4) if score is not None else 0.0,
                'analysis_scope': 'whole_image', 'metadata_evidence': metadata,
                'model_used': settings.AI_IMAGE_MODEL_ID if score is not None else None,
                'model_available': score is not None, 'device': self.device,
                'classifier_error': error, 'explanations': explanations}
