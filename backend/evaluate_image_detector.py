"""Evaluate fixed model/policy on labeled, held-out inputs. Never tune on this set.

JSONL manifest: {"path": "photos/example.jpg", "label": "real" or "ai"}.
Paths are relative to the manifest. Duplicate bytes are rejected to avoid
double-counting copies. Labels are supplied by the dataset author, not inferred.
"""
import argparse
import asyncio
import hashlib
import json
from pathlib import Path
from app.core.config import settings
from app.detectors.ai_generated_image import AIGeneratedImageDetector


def summarize(rows):
    usable = [row for row in rows if row['raw_score'] is not None]
    real = [row for row in usable if row['label'] == 'real']
    ai = [row for row in usable if row['label'] == 'ai']
    fp = sum(row['raw_score'] >= settings.AI_IMAGE_FAKE_THRESHOLD for row in real)
    fn = sum(row['raw_score'] < settings.AI_IMAGE_FAKE_THRESHOLD for row in ai)
    decisions = [row for row in rows if row['verdict'] in ('clean', 'suspicious')]
    correct = sum((row['verdict'] == 'suspicious') == (row['label'] == 'ai') for row in decisions)
    return {'total': len(rows), 'scored': len(usable), 'real_count': len(real), 'ai_count': len(ai),
            'raw_threshold': settings.AI_IMAGE_FAKE_THRESHOLD,
            'raw_false_positives': fp, 'raw_false_negatives': fn,
            'raw_false_positive_rate': fp/len(real) if real else None,
            'raw_false_negative_rate': fn/len(ai) if ai else None,
            'policy_decisions': len(decisions), 'policy_coverage': len(decisions)/len(rows) if rows else 0,
            'policy_accuracy_on_decisions': correct/len(decisions) if decisions else None,
            'abstentions': len(rows)-len(decisions),
            'interpretation': 'Evaluation only; not calibration or proof of general accuracy. '
                              'A two-example regression check cannot establish accuracy. '
                              'Abstentions are excluded from accuracy and reported as lost coverage.'}


async def evaluate(manifest):
    detector = AIGeneratedImageDetector()
    seen, rows = set(), []
    for line in manifest.read_text(encoding='utf-8').splitlines():
        if not line.strip():
            continue
        record = json.loads(line)
        if record.get('label') not in ('real', 'ai'):
            raise ValueError('Each label must be real or ai')
        path = Path(record['path'])
        if not path.is_absolute():
            path = manifest.parent / path
        data = path.read_bytes()
        digest = hashlib.sha256(data).hexdigest()
        if digest in seen:
            raise ValueError('Duplicate image bytes in evaluation manifest')
        seen.add(digest)
        result = await detector.detect(data)
        rows.append({'id': digest, 'label': record['label'], 'raw_score': result.get('raw_model_score'),
                     'verdict': result['status'], 'decision_reason': result.get('decision_reason'),
                     'input_domain': result.get('input_domain', {}).get('kind')})
    if not rows:
        raise ValueError('Evaluation manifest is empty')
    return {'model_id': settings.AI_IMAGE_MODEL_ID, 'model_revision': settings.AI_IMAGE_MODEL_REVISION,
            'experimental_verdicts': settings.AI_IMAGE_EXPERIMENTAL_VERDICTS,
            'metrics': summarize(rows), 'samples': rows}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = asyncio.run(evaluate(args.manifest))
    args.output.write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps(result['metrics'], indent=2))
