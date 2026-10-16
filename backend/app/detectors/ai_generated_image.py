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

    async def detect(self, image_bytes: bytes):
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
        try:
            score = await asyncio.to_thread(self._predict, image)
            status = ('suspicious' if score >= settings.AI_IMAGE_FAKE_THRESHOLD else
                      'clean' if score <= settings.AI_IMAGE_REAL_THRESHOLD else 'inconclusive')
            descriptions = {
                'suspicious': 'The whole-image classifier predicts likely AI-generated content.',
                'clean': 'The classifier favors the real/human class; this does not prove authenticity.',
                'inconclusive': 'The classifier is uncertain whether this image is AI-generated.',
            }
            explanations.append({'type': 'ai_image_prediction',
                                 'severity': 'warning' if status != 'clean' else 'info',
                                 'message': descriptions[status],
                                 'details': {'ai_generation_score': round(score, 4),
                                             'model': settings.AI_IMAGE_MODEL_ID}})
        except Exception as exc:
            error = self.last_error = str(exc)
            logger.warning('Whole-image classification unavailable: %s', exc)
            status = 'unavailable'
            explanations.append({'type': 'classifier_unavailable', 'severity': 'warning',
                                 'message': error})

        if metadata:
            status = 'suspicious'
            for item in metadata:
                explanations.append({'type': 'ai_metadata', 'severity': 'warning',
                    'message': f"{item['description']} in IPTC metadata. This unsigned declaration can be edited and is not verified proof.",
                    'details': item})
        explanations.append({'type': 'detector_limitations', 'severity': 'info',
            'message': 'Model scores are not calibrated certainty. New generators, screenshots, compression and digital artwork can cause false positives or false negatives.'})
        return self._result(status, score, metadata, explanations, error=error)

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
