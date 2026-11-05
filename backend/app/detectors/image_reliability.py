"""Input measurements and conservative decisions; never infer authenticity from layout."""
import cv2
import numpy as np


def inspect_image_domain(image):
    # Normalize measurements to a fixed width. No OCR, filename, or supplied
    # ground-truth label is used in this routing heuristic.
    width = min(720, image.width)
    height = max(1, round(image.height * width / image.width))
    if height > 1600:
        width, height = max(1, round(width * 1600 / height)), 1600
    pixels = np.asarray(image.resize((width, height)))
    gray = cv2.cvtColor(pixels, cv2.COLOR_RGB2GRAY)
    chroma = float(np.mean((pixels.max(axis=2).astype(float) - pixels.min(axis=2)) / 255))
    best_rows = best_components = 0
    if min(width, height) >= 120:
        for operation in (cv2.MORPH_TOPHAT, cv2.MORPH_BLACKHAT):
            high = cv2.morphologyEx(gray, operation, np.ones((15, 15), np.uint8))
            _, mask = cv2.threshold(high, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            _, _, stats, _ = cv2.connectedComponentsWithStats(mask)
            components = [(x, y, w, h) for x, y, w, h, area in stats[1:]
                          if 2 <= w <= 24 and 5 <= h <= 26 and 5 <= area <= 300 and .1 <= w/h <= 2]
            rows = {}
            for x, y, w, h in components:
                rows.setdefault(round((y+h/2)/10), []).append((x, w))
            repeated_rows = sum(len(row) >= 6 and max(x+w for x, w in row)-min(x for x, _ in row) > width*.25
                                for row in rows.values())
            if repeated_rows > best_rows:
                best_rows, best_components = int(repeated_rows), len(components)
    document_like = best_rows >= 8 and best_components >= 80 and chroma < .06
    return {'kind': 'document_like' if document_like else 'unverified_image_domain',
            'method': 'layout_heuristic_not_authenticity_detection',
            'text_like_rows': best_rows, 'small_components': best_components,
            'mean_chroma': round(chroma, 4),
            'observation': (f'Found {best_rows} repeated text-like rows and low color variation; '
                            'the image may be a document, printout, or screen photograph.' if document_like else
                            'These layout checks do not establish a validated input domain.'),
            'limitation': 'Layout cannot distinguish real documents from AI-generated documents.'}


def explain_unreliable_media(results):
    media = [value for name, value in results.items()
             if name in ('ai_generated_image', 'ai_generated_video') and value.get('verdict_eligible') is False]
    if not media:
        return None
    observations = [value.get('input_domain', {}).get('observation') for value in media]
    observation = next((item for item in observations if item), '')
    declarations = any(value.get('metadata_evidence') for value in media)
    return ('Authenticity is inconclusive. ' + (observation + ' ' if observation else '') +
            'The installed image classifier has not been validated for this use, so its raw activation '
            'is not a reliable real/fake percentage and cannot establish AI generation. '
            + ('File metadata declares AI editing, but that declaration is unsigned and unverified. ' if declarations else '') +
            'No verified manipulation evidence was established by this check. Check the original source or capture history.')
