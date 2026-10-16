import pytest
import numpy as np
import cv2
from app.detectors.ppg_liveness import PPGLivenessDetector
from app.detectors.phoneme_viseme import PhonemeVisemeDetector
from app.detectors.financial_threat import FinancialThreatDetector
from app.detectors.deepfake_image import DeepfakeImageDetector


class TestPPGLivenessDetector:
    @pytest.fixture
    def detector(self):
        return PPGLivenessDetector()

    def test_initialization(self, detector):
        assert detector is not None
        assert detector.use_mediapipe or detector.face_cascade is not None

    def test_chrom_method(self, detector):
        # Create synthetic RGB signals
        n_frames = 100
        t = np.linspace(0, 10, n_frames)
        # Simulate pulse at 1 Hz
        pulse = np.sin(2 * np.pi * 1 * t) * 0.01
        rgb_signals = np.array([
            100 + pulse + np.random.randn(n_frames) * 0.001,
            100 + pulse * 0.5 + np.random.randn(n_frames) * 0.001,
            100 + np.random.randn(n_frames) * 0.001,
        ])
        
        result = detector._chrom_method(rgb_signals)
        assert len(result) == n_frames
        assert not np.allclose(result, 0)

    def test_pos_method(self, detector):
        n_frames = 100
        rgb_signals = np.random.rand(3, n_frames) * 100 + 50
        
        result = detector._pos_method(rgb_signals)
        assert len(result) == n_frames

    def test_bandpass_filter(self, detector):
        signal = np.sin(2 * np.pi * 1 * np.linspace(0, 10, 300))  # 1 Hz at 30 fps
        filtered = detector._bandpass_filter(signal, 30, 0.7, 4.0)
        assert len(filtered) == len(signal)

    def test_compute_snr(self, detector):
        signal = np.sin(2 * np.pi * 1.2 * np.linspace(0, 10, 300))  # 1.2 Hz
        snr = detector._compute_snr(signal, 30)
        assert snr > 0

    def test_estimate_heart_rate(self, detector):
        signal = np.sin(2 * np.pi * 1.2 * np.linspace(0, 10, 300))  # 72 BPM
        hr, conf = detector._estimate_heart_rate(signal, 30)
        assert hr is not None
        assert 60 < hr < 90
        assert conf > 0


class TestPhonemeVisemeDetector:
    @pytest.fixture
    def detector(self):
        return PhonemeVisemeDetector()

    def test_initialization(self, detector):
        assert detector is not None
        assert len(detector.PHONEME_TO_VISEME) > 0

    def test_viseme_mapping(self, detector):
        # Test some known mappings
        assert detector.PHONEME_TO_VISEME.get('p') == 13  # p, b -> lips closed
        assert detector.PHONEME_TO_VISEME.get('m') == 12  # m, n, ng -> lips closed
        assert detector.PHONEME_TO_VISEME.get('aa') == 1   # aa, ao -> open

    def test_fallback_sync_score(self, detector):
        phonemes = ['p', 'a', 't']
        phoneme_times = [0.0, 0.3, 0.6]
        visemes = [13, 1, 13]
        viseme_times = [0.05, 0.35, 0.65]
        
        score, path = detector._fallback_sync_score(
            phonemes, phoneme_times, visemes, viseme_times
        )
        assert 0 <= score <= 1
        assert len(path) > 0


class TestFinancialThreatDetector:
    @pytest.fixture
    def detector(self):
        return FinancialThreatDetector()

    def test_initialization(self, detector):
        assert detector is not None
        assert len(detector.compiled_patterns) > 0

    def test_entity_extraction(self, detector):
        text = "Contact me at +1-555-123-4567 or email test@example.com. Send BTC to 1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"
        entities = detector._extract_entities(text)
        
        types = {e['type'] for e in entities}
        assert 'phone' in types
        assert 'email' in types
        assert 'crypto_btc' in types

    def test_luhn_check(self, detector):
        # Valid Visa test number
        assert detector._luhn_check("4111111111111111") == True
        # Invalid
        assert detector._luhn_check("4111111111111112") == False

    def test_tactic_detection(self, detector):
        text = "Urgent! Act now! Your account will be closed immediately. Verify your password."
        tactics = detector._detect_tactics(text)
        
        tactic_names = {t.name for t in tactics}
        assert 'urgency' in tactic_names
        assert 'fear_intimidation' in tactic_names
        assert 'credential_harvesting' in tactic_names

    def test_suspicious_patterns(self, detector):
        text = "Dear customer, kindly verify your account at http://192.168.1.1/login"
        flags = detector._check_suspicious_patterns(text)
        
        flag_types = {f['type'] for f in flags}
        assert 'generic_greeting' in flag_types
        assert 'ip_address_url' in flag_types

    def test_risk_scoring(self, detector):
        entities = [
            {"type": "crypto_btc", "confidence": 0.95},
            {"type": "phone", "confidence": 0.85},
        ]
        from app.detectors.financial_threat import ThreatTactic
        tactics = [
            ThreatTactic("urgency", "desc", 0.8, ["urgent"]),
            ThreatTactic("authority_impersonation", "desc", 0.7, ["bank"]),
        ]
        flags = [{"type": "url_shortener", "count": 1, "severity": "medium"}]
        threat_intel = {"malicious_entities": [], "suspicious_entities": []}
        
        score = detector._compute_risk_score(entities, tactics, flags, threat_intel)
        assert 0 <= score <= 1


class TestDeepfakeImageDetector:
    @pytest.fixture
    def detector(self):
        return DeepfakeImageDetector()

    def test_initialization(self, detector):
        assert detector is not None
        assert detector.transform is not None
        assert detector.device is not None

    def test_face_detection(self, detector):
        # Create a simple test image with a face-like pattern
        img = np.zeros((480, 640, 3), dtype=np.uint8)
        # Add a simple rectangle as a "face"
        cv2.rectangle(img, (200, 150), (440, 390), (200, 180, 160), -1)
        cv2.rectangle(img, (250, 200), (290, 240), (100, 80, 70), -1)  # left eye
        cv2.rectangle(img, (350, 200), (390, 240), (100, 80, 70), -1)  # right eye
        cv2.rectangle(img, (280, 300), (360, 320), (100, 80, 70), -1)  # mouth
        
        faces = detector._detect_faces(img)
        # May or may not detect depending on detector availability
        assert isinstance(faces, list)

    def test_heuristic_analysis(self, detector):
        # Test with a simple face crop
        face = np.random.randint(0, 255, (224, 224, 3), dtype=np.uint8)
        score, details = detector._heuristic_analysis(face)
        assert 0 <= score <= 1
        assert isinstance(details, dict)
        assert 0 <= details["heuristic_score"] <= 1

    def test_radial_profile(self, detector):
        image = np.ones((100, 100))
        image[50, 50] = 100
        profile = detector._radial_profile(image, (50, 50))
        assert len(profile) > 0
        assert profile[0] == pytest.approx(100, abs=0.01)  # Center value

    def test_grid_artifact_detection(self, detector):
        # Create image with grid pattern
        img = np.zeros((224, 224))
        img[::16, :] = 1  # Horizontal lines
        img[:, ::16] = 1  # Vertical lines
        grad_x = np.zeros_like(img)
        grad_y = np.zeros_like(img)
        grad_mag = np.sqrt(grad_x**2 + grad_y**2)
        # This is a simplified test
        has_grid = detector._detect_grid_artifacts(grad_mag)
        assert isinstance(has_grid, bool)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])