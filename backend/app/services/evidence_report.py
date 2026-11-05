"""User-facing observations derived only from detector measurements."""


def build_evidence_report(results):
    findings, limitations = [], []
    for name, result in results.items():
        score = result.get('ai_probability')
        if result.get('verdict_eligible') is False:
            domain = result.get('input_domain') or {}
            findings.append({'check': 'Authenticity assessment withheld',
                             'observation': domain.get('observation', 'The available image classifier is not independently validated for these inputs.'),
                             'meaning': 'A raw model activation is not a measured probability of forgery. No reliable real/fake percentage is available.'})
            if domain.get('kind') == 'document_like':
                findings.append({'check': 'Document-like layout',
                                 'observation': f"Measured {domain['text_like_rows']} repeated text-like rows with low color variation.",
                                 'meaning': 'These describe the layout only. Real and AI-generated documents can both have this structure.'})
            limitations.append('This classifier is uncalibrated for the uploaded input. Its raw activation is excluded from the verdict and must not be treated as evidence of AI generation.')
            score = None
        if score is not None:
            video = bool(result.get('sampled_frames'))
            thresholds = result.get('decision_thresholds') or {}
            low, high = thresholds.get('real_max', .3), thresholds.get('ai_min', .7)
            findings.append({
                'check': 'AI patterns across video frames' if video else 'Whole-image AI patterns',
                'observation': (f"The classifier's AI-generation score is {score:.1%}. "
                                + (f"It examined {result['sampled_frames']} sampled frames; "
                                   "the score is their average. " if video else "It examined the whole image. ")),
                'meaning': (f'The score meets the {high:.0%} experimental flagging threshold.' if score >= high else
                            f'The score meets the {low:.0%} low-indicator threshold.' if score <= low else
                            f'The score falls between {low:.0%} and {high:.0%}, where the system abstains: '
                            'the learned patterns do not clearly favor either class.'),
                'score': score,
            })
            if video:
                limitations.append('Only sampled frames were checked with an image classifier. '
                                   'Motion consistency and unsampled moments were not assessed by this model.')
                if result.get('mixed_frame_evidence'):
                    limitations.append('Some frames scored low and others high for AI patterns; the mixed evidence makes this check inconclusive.')
                if result.get('failed_frames'):
                    limitations.append(f"{result['failed_frames']} sampled frames could not be classified.")
                for frame in result.get('frame_scores', []):
                    findings.append({'check': f"Frame at {frame['timestamp_seconds']:.2f}s",
                                     'observation': f"AI-pattern score: {frame['ai_probability']:.1%}.",
                                     'meaning': 'This identifies a sampled time to inspect, not a proven manipulated region.'})
            limitations.append('Experimental classifier decisions can be wrong, including on unfamiliar real photos and new AI generators. '
                               'The image classifier does not localize defects or explain individual pixels. '
                               'Its score is not the percentage of pixels that are fake or a verified probability of forgery.')
            attribution = result.get('region_analysis')
            if attribution:
                for region in attribution.get('regions', []):
                    findings.append({'check': 'Area influencing the model',
                                     'observation': f"Covering the {region['region']} area reduced support for the {attribution['target_class']} class by {region['support_drop_points']:g} score points.",
                                     'meaning': 'A measured sensitivity test, not proof that this area was edited.'})
                limitations.append(attribution['limitation'])
        for evidence in result.get('metadata_evidence', []):
            findings.append({'check': 'File metadata', 'observation': evidence['description'],
                             'meaning': 'This is an unsigned declaration and can be changed; it is not verified provenance.'})
        if 'ppg' in name:
            pulse = result.get('has_pulse') and result.get('confidence', 0) > 0
            findings.append({'check': 'Pulse-like skin color changes',
                             'observation': (f"Detected a pulse-like signal near {result.get('heart_rate_bpm')} beats per minute."
                                             if pulse else 'A reliable pulse-like signal could not be established.'),
                             'meaning': 'Lighting, motion, compression, clip length and sampling affect this check. '
                                        'Missing pulse evidence does not establish a fake.'})
        if 'phoneme' in name:
            findings.append({'check': 'Speech and mouth timing',
                             'observation': ('Speech sounds were compared with mouth movements.'
                                             if result.get('method') == 'phoneme_alignment' and result.get('confidence')
                                             else 'Reliable speech-to-mouth alignment was unavailable.'),
                             'meaning': ('Alignment score: ' + f"{result.get('sync_score', 0):.1%}. "
                                         if result.get('confidence') else '') +
                                        'No audio, no visible speaker, or missing speech models prevent this check; '
                                        'those cases are inconclusive.'})
        if 'deepfake' in name:
            for explanation in result.get('explanations', []):
                findings.append({'check': 'Facial manipulation check',
                                 'observation': explanation.get('message', ''),
                                 'meaning': 'Face-specific evidence is separate from whole-scene AI generation.'})
        if name == 'financial_threat':
            findings.append({'check': 'Text scam patterns',
                             'observation': f"Rule-based risk score: {result.get('risk_score', 0):.1%}.",
                             'meaning': 'A heuristic score based on matched tactics and patterns, not a verified probability of fraud.'})
            for tactic in result.get('tactics', []):
                findings.append({'check': tactic['name'].replace('_', ' ').capitalize(),
                                 'observation': 'Matched text: ' + ', '.join(tactic.get('evidence', [])),
                                 'meaning': tactic['description']})
            for contribution in result.get('score_basis', []):
                findings.append({'check': 'Rule score contribution',
                                 'observation': f"{contribution['evidence']}: +{contribution['points']:g} risk points.",
                                 'meaning': contribution['source'].replace('_', ' ') + '; contributions add up and are capped at 100 points.'})
            limitations.append('External threat intelligence is not configured; local URL patterns do not establish a malicious or safe website.')
        if name == 'llm_text_review':
            for item in result.get('findings', []):
                findings.append({'check': 'Qwen contextual text review',
                                 'observation': f"“{item['quote']}”", 'meaning': item['reason']})
        if result.get('status') in ('inconclusive', 'not_applicable', 'unavailable', 'error'):
            limitations.append(f"{name.replace('_', ' ')}: {result['status'].replace('_', ' ')}.")
    return {'findings': findings, 'limitations': list(dict.fromkeys(limitations)),
            'score_note': 'Model scores are not verified authenticity probabilities. Experimental classification uses the configured thresholds; '
                          'unsupported inputs remain excluded from the verdict. '
                          'Scores from different checks are not averaged into a chance that the input is fake. '
                          'An inconclusive result or no detected indicators does not certify authenticity.'}
