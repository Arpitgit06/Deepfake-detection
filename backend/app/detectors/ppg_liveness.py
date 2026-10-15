import cv2
import numpy as np
import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
import asyncio
import io
import tempfile
import os

from app.core.config import settings

logger = logging.getLogger(__name__)


@dataclass
class PPGResult:
    has_pulse: bool
    confidence: float
    heart_rate_bpm: Optional[float]
    signal_quality: float
    snr_db: float
    explanations: List[Dict[str, Any]]
    raw_signal: Optional[List[float]] = None
    timestamps: Optional[List[float]] = None


class PPGLivenessDetector:
    """
    Photoplethysmography (PPG) based liveness detection.
    Uses CHROM (Chrominance) and POS (Plane-Orthogonal-to-Skin) methods
    to extract subtle color changes from skin caused by blood volume pulse.
    """

    def __init__(self):
        self.face_detector = None
        self.landmark_predictor = None
        self._initialize_detectors()

    def _initialize_detectors(self):
        """Initialize face detection with multiple fallbacks."""
        # Try MediaPipe first (most accurate)
        try:
            import mediapipe as mp
            self.mp_face_detection = mp.solutions.face_detection.FaceDetection(
                model_selection=1, min_detection_confidence=0.5
            )
            self.mp_face_mesh = mp.solutions.face_mesh.FaceMesh(
                static_image_mode=False,
                max_num_faces=1,
                refine_landmarks=True,
                min_detection_confidence=0.5,
                min_tracking_confidence=0.5,
            )
            self.use_mediapipe = True
            logger.info("MediaPipe face detection initialized")
        except Exception as e:
            logger.warning(f"MediaPipe not available: {e}, falling back to OpenCV")
            self.use_mediapipe = False

        # OpenCV Haar cascade fallback
        try:
            cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
            self.face_cascade = cv2.CascadeClassifier(cascade_path)
            if self.face_cascade.empty():
                raise ValueError("Failed to load Haar cascade")
            logger.info("OpenCV Haar cascade loaded")
        except Exception as e:
            logger.warning(f"Haar cascade not available: {e}")
            self.face_cascade = None

    async def detect(
        self,
        video_bytes: bytes,
        sample_rate: int = 5,
    ) -> Dict[str, Any]:
        """
        Detect liveness via PPG signal from video frames.
        
        Args:
            video_bytes: Raw video file bytes
            sample_rate: Frames per second to analyze
            
        Returns:
            Dictionary with detection results and explanations
        """
        try:
            # Extract frames
            frames, fps, timestamps = await self._extract_frames(video_bytes, sample_rate)
            
            if len(frames) < 30:  # Need at least ~6 seconds at 5 fps
                return self._create_result(
                    has_pulse=False,
                    confidence=0.0,
                    explanations=[{
                        "type": "insufficient_frames",
                        "message": f"Only {len(frames)} frames extracted, need at least 30 for reliable PPG",
                        "severity": "warning"
                    }]
                )

            # Extract ROIs (forehead, cheeks) from each frame
            roi_signals = await self._extract_roi_signals(frames)
            
            if roi_signals is None or len(roi_signals) == 0:
                return self._create_result(
                    has_pulse=False,
                    confidence=0.0,
                    explanations=[{
                        "type": "no_face_detected",
                        "message": "Could not detect face in video frames",
                        "severity": "error"
                    }]
                )

            # Compute PPG signal using CHROM method
            ppg_signal = self._chrom_method(roi_signals)
            
            # Alternative: POS method
            ppg_signal_pos = self._pos_method(roi_signals)
            
            # Use the better signal (higher SNR)
            snr_chrom = self._compute_snr(ppg_signal, fps)
            snr_pos = self._compute_snr(ppg_signal_pos, fps)
            
            if snr_pos > snr_chrom:
                ppg_signal = ppg_signal_pos
                method_used = "POS"
                snr = snr_pos
            else:
                method_used = "CHROM"
                snr = snr_chrom

            # Bandpass filter for heart rate range (0.7-4 Hz = 42-240 BPM)
            filtered_signal = self._bandpass_filter(ppg_signal, fps, 0.7, 4.0)
            
            # Estimate heart rate
            hr_bpm, hr_confidence = self._estimate_heart_rate(filtered_signal, fps)
            
            # Signal quality metrics
            signal_quality = self._compute_signal_quality(filtered_signal, fps)
            
            # Determine if pulse is present
            has_pulse = signal_quality > 0.3 and snr > 3.0 and hr_confidence > 0.3
            
            # Overall confidence
            confidence = min(signal_quality * 0.4 + (snr / 20.0) * 0.3 + hr_confidence * 0.3, 1.0)
            
            # Adjust confidence based on threshold
            final_confidence = confidence if has_pulse else (1.0 - confidence)
            
            explanations = self._generate_explanations(
                has_pulse, signal_quality, snr, hr_bpm, hr_confidence, method_used, len(frames)
            )

            return self._create_result(
                has_pulse=has_pulse,
                confidence=round(final_confidence, 4),
                heart_rate_bpm=round(hr_bpm, 1) if hr_bpm else None,
                signal_quality=round(signal_quality, 4),
                snr_db=round(snr, 2),
                explanations=explanations,
                raw_signal=filtered_signal.tolist()[:500],  # Limit size
                timestamps=timestamps[:500] if timestamps else None,
            )

        except Exception as e:
            logger.error(f"PPG detection failed: {e}")
            return self._create_result(
                has_pulse=False,
                confidence=0.0,
                explanations=[{
                    "type": "processing_error",
                    "message": f"PPG analysis failed: {str(e)}",
                    "severity": "error"
                }]
            )

    async def _extract_frames(
        self, video_bytes: bytes, sample_rate: int
    ) -> Tuple[List[np.ndarray], float, List[float]]:
        """Extract frames from video at specified sample rate."""
        frames = []
        timestamps = []
        
        with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as tmp:
            tmp.write(video_bytes)
            tmp_path = tmp.name
        
        try:
            cap = cv2.VideoCapture(tmp_path)
            fps = cap.get(cv2.CAP_PROP_FPS)
            if fps <= 0:
                fps = 30.0
            
            frame_interval = max(1, int(fps / sample_rate))
            frame_count = 0
            
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                    
                if frame_count % frame_interval == 0:
                    frames.append(frame)
                    timestamps.append(frame_count / fps)
                    
                frame_count += 1
                
            cap.release()
        finally:
            try:
                os.unlink(tmp_path)
            except:
                pass
                
        return frames, fps, timestamps

    async def _extract_roi_signals(self, frames: List[np.ndarray]) -> Optional[np.ndarray]:
        """Extract RGB signals from facial ROIs (forehead, cheeks)."""
        roi_signals_r = []
        roi_signals_g = []
        roi_signals_b = []
        
        for frame in frames:
            roi_r, roi_g, roi_b = self._extract_face_rois(frame)
            if roi_r is not None:
                roi_signals_r.append(roi_r)
                roi_signals_g.append(roi_g)
                roi_signals_b.append(roi_b)
            else:
                # Use previous frame's values if detection fails (interpolation)
                if roi_signals_r:
                    roi_signals_r.append(roi_signals_r[-1])
                    roi_signals_g.append(roi_signals_g[-1])
                    roi_signals_b.append(roi_signals_b[-1])
        
        if len(roi_signals_r) < 10:
            return None
            
        # Stack: (3, n_frames) for R, G, B
        return np.array([roi_signals_r, roi_signals_g, roi_signals_b], dtype=np.float32)

    def _extract_face_rois(self, frame: np.ndarray) -> Tuple[Optional[float], Optional[float], Optional[float]]:
        """Extract mean RGB values from forehead and cheek ROIs."""
        h, w = frame.shape[:2]
        
        if self.use_mediapipe:
            return self._extract_rois_mediapipe(frame)
        else:
            return self._extract_rois_opencv(frame)

    def _extract_rois_mediapipe(self, frame: np.ndarray) -> Tuple[Optional[float], Optional[float], Optional[float]]:
        """Extract ROIs using MediaPipe FaceMesh for precise landmarks."""
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.mp_face_mesh.process(rgb_frame)
        
        if not results.multi_face_landmarks:
            return None, None, None
            
        landmarks = results.multi_face_landmarks[0].landmark
        h, w = frame.shape[:2]
        
        # Key landmark indices for MediaPipe FaceMesh
        # Forehead: 10, 151, 9, 8 (top of head/forehead region)
        # Left cheek: 234, 127, 162, 21, 54, 103, 67, 109
        # Right cheek: 454, 356, 389, 251, 284, 332, 297, 338
        
        forehead_indices = [10, 151, 9, 8, 168, 197, 195, 5]
        left_cheek_indices = [234, 127, 162, 21, 54, 103, 67, 109]
        right_cheek_indices = [454, 356, 389, 251, 284, 332, 297, 338]
        
        def get_roi_mean(indices):
            points = []
            for idx in indices:
                lm = landmarks[idx]
                x, y = int(lm.x * w), int(lm.y * h)
                if 0 <= x < w and 0 <= y < h:
                    points.append((x, y))
            if not points:
                return None
            # Create mask and get mean
            mask = np.zeros((h, w), dtype=np.uint8)
            cv2.fillPoly(mask, [np.array(points)], 255)
            mean_val = cv2.mean(frame, mask=mask)
            return mean_val[0], mean_val[1], mean_val[2]  # B, G, R
        
        forehead = get_roi_mean(forehead_indices)
        left_cheek = get_roi_mean(left_cheek_indices)
        right_cheek = get_roi_mean(right_cheek_indices)
        
        # Average across all ROIs
        valid_rois = [r for r in [forehead, left_cheek, right_cheek] if r is not None]
        if not valid_rois:
            return None, None, None
            
        avg_b = np.mean([r[0] for r in valid_rois])
        avg_g = np.mean([r[1] for r in valid_rois])
        avg_r = np.mean([r[2] for r in valid_rois])
        
        return avg_r, avg_g, avg_b

    def _extract_rois_opencv(self, frame: np.ndarray) -> Tuple[Optional[float], Optional[float], Optional[float]]:
        """Extract ROIs using OpenCV Haar cascade (fallback)."""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = self.face_cascade.detectMultiScale(gray, 1.1, 5, minSize=(100, 100))
        
        if len(faces) == 0:
            return None, None, None
            
        # Use largest face
        x, y, w, h = max(faces, key=lambda f: f[2] * f[3])
        
        # Define ROIs relative to face bounding box
        # Forehead: upper 25% of face, middle 60% width
        forehead_y = y + int(h * 0.05)
        forehead_h = int(h * 0.20)
        forehead_x = x + int(w * 0.20)
        forehead_w = int(w * 0.60)
        
        # Left cheek: middle vertically, left 25% width
        cheek_y = y + int(h * 0.35)
        cheek_h = int(h * 0.30)
        left_cheek_x = x + int(w * 0.05)
        left_cheek_w = int(w * 0.25)
        
        # Right cheek: middle vertically, right 25% width
        right_cheek_x = x + int(w * 0.70)
        right_cheek_w = int(w * 0.25)
        
        rois = [
            frame[forehead_y:forehead_y+forehead_h, forehead_x:forehead_x+forehead_w],
            frame[cheek_y:cheek_y+cheek_h, left_cheek_x:left_cheek_x+left_cheek_w],
            frame[cheek_y:cheek_y+cheek_h, right_cheek_x:right_cheek_x+right_cheek_w],
        ]
        
        valid_means = []
        for roi in rois:
            if roi.size > 0:
                mean_bgr = cv2.mean(roi)
                valid_means.append(mean_bgr[:3])
                
        if not valid_means:
            return None, None, None
            
        avg_b = np.mean([m[0] for m in valid_means])
        avg_g = np.mean([m[1] for m in valid_means])
        avg_r = np.mean([m[2] for m in valid_means])
        
        return avg_r, avg_g, avg_b

    def _chrom_method(self, rgb_signals: np.ndarray) -> np.ndarray:
        """
        CHROM (Chrominance-based) method for PPG extraction.
        de Haan & Jeanne, 2013.
        
        X = 3*Rn - 2*Gn
        Y = 1.5*Rn + Gn - 1.5*Bn
        Alpha = std(X) / std(Y)
        Pulse = X - Alpha * Y
        """
        # Normalize by temporal mean
        rgb_norm = rgb_signals / (np.mean(rgb_signals, axis=1, keepdims=True) + 1e-6)
        
        Rn, Gn, Bn = rgb_norm[0], rgb_norm[1], rgb_norm[2]
        
        X = 3 * Rn - 2 * Gn
        Y = 1.5 * Rn + Gn - 1.5 * Bn
        
        # Alpha tuning parameter
        alpha = np.std(X) / (np.std(Y) + 1e-6)
        
        pulse = X - alpha * Y
        return pulse

    def _pos_method(self, rgb_signals: np.ndarray) -> np.ndarray:
        """
        POS (Plane-Orthogonal-to-Skin) method for PPG extraction.
        Wang et al., 2017.
        
        Projects RGB onto plane orthogonal to skin tone.
        """
        rgb_norm = rgb_signals / (np.mean(rgb_signals, axis=1, keepdims=True) + 1e-6)
        
        Rn, Gn, Bn = rgb_norm[0], rgb_norm[1], rgb_norm[2]
        
        # POS projection matrix (fixed for typical skin tones)
        # Projection onto plane orthogonal to [1, 1, 1] in normalized space
        # Equivalent to: [0, 1, -1] and [-2, 1, 1] projections
        S1 = Gn - Bn
        S2 = -2 * Rn + Gn + Bn
        
        # Tune alpha
        alpha = np.std(S1) / (np.std(S2) + 1e-6)
        
        pulse = S1 + alpha * S2
        return pulse

    def _bandpass_filter(
        self, signal: np.ndarray, fps: float, low_hz: float, high_hz: float
    ) -> np.ndarray:
        """Apply Butterworth bandpass filter."""
        from scipy.signal import butter, filtfilt
        
        nyquist = fps / 2.0
        low = low_hz / nyquist
        high = high_hz / nyquist
        
        # Clamp to valid range
        low = max(0.001, min(low, 0.99))
        high = max(low + 0.001, min(high, 0.99))
        
        try:
            b, a = butter(4, [low, high], btype='band')
            filtered = filtfilt(b, a, signal)
            return filtered
        except:
            # Fallback: simple moving average difference
            return signal - np.convolve(signal, np.ones(5)/5, mode='same')

    def _compute_snr(self, signal: np.ndarray, fps: float) -> float:
        """Compute Signal-to-Noise Ratio in dB."""
        if len(signal) < 10:
            return 0.0
            
        # FFT
        n = len(signal)
        freqs = np.fft.rfftfreq(n, d=1.0/fps)
        fft_vals = np.abs(np.fft.rfft(signal))
        
        # Heart rate range: 0.7-4 Hz (42-240 BPM)
        hr_mask = (freqs >= 0.7) & (freqs <= 4.0)
        
        if not np.any(hr_mask):
            return 0.0
            
        signal_power = np.max(fft_vals[hr_mask])
        noise_power = np.mean(fft_vals[~hr_mask]) if np.any(~hr_mask) else 1e-6
        
        snr = 10 * np.log10(signal_power / noise_power + 1e-6)
        return max(0.0, snr)

    def _estimate_heart_rate(
        self, signal: np.ndarray, fps: float
    ) -> Tuple[Optional[float], float]:
        """Estimate heart rate from filtered PPG signal."""
        if len(signal) < 10:
            return None, 0.0
            
        n = len(signal)
        freqs = np.fft.rfftfreq(n, d=1.0/fps)
        fft_vals = np.abs(np.fft.rfft(signal))
        
        # Heart rate range
        hr_mask = (freqs >= 0.7) & (freqs <= 4.0)
        
        if not np.any(hr_mask):
            return None, 0.0
            
        hr_freqs = freqs[hr_mask]
        hr_fft = fft_vals[hr_mask]
        
        # Find peak
        peak_idx = np.argmax(hr_fft)
        peak_freq = hr_freqs[peak_idx]
        peak_power = hr_fft[peak_idx]
        
        # Confidence: peak prominence relative to neighbors
        if len(hr_fft) > 2:
            # Exclude peak and compute local noise
            neighbor_mask = np.ones(len(hr_fft), dtype=bool)
            neighbor_mask[peak_idx] = False
            if peak_idx > 0:
                neighbor_mask[peak_idx - 1] = False
            if peak_idx < len(hr_fft) - 1:
                neighbor_mask[peak_idx + 1] = False
            local_noise = np.mean(hr_fft[neighbor_mask]) if np.any(neighbor_mask) else 1e-6
            confidence = min(peak_power / (local_noise + 1e-6) / 10.0, 1.0)
        else:
            confidence = 0.5
            
        hr_bpm = peak_freq * 60.0
        
        # Sanity check
        if hr_bpm < 40 or hr_bpm > 200:
            return None, 0.0
            
        return hr_bpm, confidence

    def _compute_signal_quality(self, signal: np.ndarray, fps: float) -> float:
        """Compute overall signal quality metric (0-1)."""
        if len(signal) < 20:
            return 0.0
            
        # 1. Periodicity (autocorrelation at heart rate lag)
        acf = np.correlate(signal, signal, mode='full')
        acf = acf[len(acf)//2:]
        acf = acf / (acf[0] + 1e-6)
        
        # Expected lag for ~60-80 BPM at this fps
        expected_lag = int(fps * 60 / 70)  # ~70 BPM
        if expected_lag < len(acf):
            periodicity = max(0, acf[expected_lag])
        else:
            periodicity = 0
            
        # 2. Stationarity (variance of rolling std)
        window = int(fps * 2)  # 2-second windows
        if len(signal) > window * 2:
            rolling_std = np.array([
                np.std(signal[i:i+window]) 
                for i in range(0, len(signal) - window, window//2)
            ])
            stationarity = 1.0 - min(np.std(rolling_std) / (np.mean(rolling_std) + 1e-6), 1.0)
        else:
            stationarity = 0.5
            
        # 3. Spectral concentration (energy in HR band vs total)
        n = len(signal)
        freqs = np.fft.rfftfreq(n, d=1.0/fps)
        fft_vals = np.abs(np.fft.rfft(signal))
        total_power = np.sum(fft_vals**2)
        hr_mask = (freqs >= 0.7) & (freqs <= 4.0)
        hr_power = np.sum(fft_vals[hr_mask]**2)
        spectral_concentration = hr_power / (total_power + 1e-6)
        
        # Combined quality score
        quality = (periodicity * 0.4 + stationarity * 0.3 + spectral_concentration * 0.3)
        return float(np.clip(quality, 0, 1))

    def _generate_explanations(
        self,
        has_pulse: bool,
        signal_quality: float,
        snr: float,
        hr_bpm: Optional[float],
        hr_confidence: float,
        method: str,
        num_frames: int,
    ) -> List[Dict[str, Any]]:
        """Generate human-readable explanations."""
        explanations = []
        
        explanations.append({
            "type": "method",
            "message": f"PPG signal extracted using {method} method from {num_frames} frames",
            "severity": "info",
            "details": {
                "method": method,
                "frames_analyzed": num_frames,
            }
        })
        
        if has_pulse:
            explanations.append({
                "type": "pulse_detected",
                "message": f"Physiological pulse detected at {hr_bpm:.1f} BPM",
                "severity": "success",
                "details": {
                    "heart_rate_bpm": round(hr_bpm, 1),
                    "confidence": round(hr_confidence, 3),
                }
            })
            explanations.append({
                "type": "liveness_confirmed",
                "message": "Video shows biological liveness indicators consistent with a living human",
                "severity": "success",
            })
        else:
            explanations.append({
                "type": "no_pulse",
                "message": "No consistent physiological pulse detected in facial regions",
                "severity": "warning" if signal_quality > 0.2 else "error",
                "details": {
                    "signal_quality": round(signal_quality, 3),
                    "snr_db": round(snr, 2),
                    "interpretation": "Synthetic avatars typically lack subtle blood-flow color changes"
                }
            })
            
            if signal_quality < 0.2:
                explanations.append({
                    "type": "poor_signal",
                    "message": "Signal quality too low for reliable assessment - check lighting and face visibility",
                    "severity": "info",
                })
        
        explanations.append({
            "type": "snr",
            "message": f"Signal-to-Noise Ratio: {snr:.1f} dB",
            "severity": "info",
            "details": {
                "snr_db": round(snr, 1),
                "threshold": "3 dB minimum for reliable pulse detection"
            }
        })
        
        return explanations

    def _create_result(
        self,
        has_pulse: bool,
        confidence: float,
        heart_rate_bpm: Optional[float] = None,
        signal_quality: float = 0.0,
        snr_db: float = 0.0,
        explanations: List[Dict] = None,
        raw_signal: Optional[List[float]] = None,
        timestamps: Optional[List[float]] = None,
    ) -> Dict[str, Any]:
        return {
            "detector": "ppg_liveness",
            "has_pulse": has_pulse,
            "confidence": confidence,
            "heart_rate_bpm": heart_rate_bpm,
            "signal_quality": signal_quality,
            "snr_db": snr_db,
            "explanations": explanations or [],
            "raw_signal": raw_signal,
            "timestamps": timestamps,
        }