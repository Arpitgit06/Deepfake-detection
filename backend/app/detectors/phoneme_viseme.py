import numpy as np
import cv2
import logging
import tempfile
import os
import asyncio
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from scipy.signal import resample
from scipy.spatial.distance import euclidean

try:
    from fastdtw import fastdtw
except ImportError:
    fastdtw = None

from app.core.config import settings

logger = logging.getLogger(__name__)


@dataclass
class PhonemeVisemeResult:
    is_synchronized: bool
    confidence: float
    sync_score: float
    phoneme_viseme_pairs: List[Dict[str, Any]]
    explanations: List[Dict[str, Any]]


class PhonemeVisemeDetector:
    """
    Cross-modal phoneme-viseme synchronization detection.
    Extracts phonemes from audio and visemes from video, then validates
    temporal alignment using Dynamic Time Warping (DTW).
    """

    # Viseme to phoneme mapping (simplified)
    VISEME_TO_PHONEMES = {
        0: ['sil', 'sp', 'pau'],  # silence
        1: ['aa', 'ao'],          # open mouth (ah, aw)
        2: ['ae', 'ah', 'ax'],    # wide open (ae, ah)
        3: ['ey', 'ay', 'oy'],    # wide to narrow (ay, oy)
        4: ['iy', 'ih', 'ix'],    # spread lips (ee, ih)
        5: ['uw', 'uh', 'ux'],    # rounded (oo, uh)
        6: ['ow', 'aw'],          # rounded to open
        7: ['w', 'r'],            # rounded consonants
        8: ['l', 'el'],           # tongue up
        9: ['th', 'dh'],          # tongue between teeth
        10: ['f', 'v'],           # lower lip to upper teeth
        11: ['s', 'z', 'sh', 'zh'], # teeth together
        12: ['m', 'n', 'ng'],     # lips closed (nasals)
        13: ['p', 'b'],           # lips closed (stops)
        14: ['t', 'd', 'k', 'g'], # tongue contact
        15: ['ch', 'jh'],         # affricates
    }

    PHONEME_TO_VISEME = {}
    for viseme, phonemes in VISEME_TO_PHONEMES.items():
        for p in phonemes:
            PHONEME_TO_VISEME[p] = viseme

    def __init__(self):
        self.face_mesh = None
        self.asr_model = None
        self.asr_processor = None
        self._initialize_models()

    def _initialize_models(self):
        """Initialize MediaPipe FaceMesh and ASR model with fallbacks."""
        # MediaPipe FaceMesh for viseme extraction
        try:
            import mediapipe as mp
            self.mp_face_mesh = mp.solutions.face_mesh.FaceMesh(
                static_image_mode=False,
                max_num_faces=1,
                refine_landmarks=True,
                min_detection_confidence=0.5,
                min_tracking_confidence=0.5,
            )
            self.use_mediapipe = True
            logger.info("MediaPipe FaceMesh initialized for viseme extraction")
        except Exception as e:
            logger.warning(f"MediaPipe not available: {e}")
            self.use_mediapipe = False

        # ASR model for phoneme extraction (optional, with fallback)
        try:
            from transformers import Wav2Vec2Processor, Wav2Vec2ForCTC
            import torch
            
            model_name = "facebook/wav2vec2-lv-60-espeak-cv-ft"
            self.asr_processor = Wav2Vec2Processor.from_pretrained(model_name)
            self.asr_model = Wav2Vec2ForCTC.from_pretrained(model_name)
            self.asr_model.eval()
            self.use_asr = True
            logger.info("Wav2Vec2 phoneme model loaded")
        except Exception as e:
            logger.warning(f"ASR model not available: {e}, using energy-based fallback")
            self.use_asr = False

    async def detect(self, video_bytes: bytes) -> Dict[str, Any]:
        """
        Detect phoneme-viseme synchronization from video.
        """
        try:
            # Extract audio and video frames
            audio_data, fps, video_frames = await self._extract_audio_video(video_bytes)
            
            if audio_data is None or len(video_frames) == 0:
                return self._create_result(
                    is_synchronized=False,
                    confidence=0.0,
                    explanations=[{
                        "type": "extraction_failed",
                        "message": "Could not extract audio or video frames",
                        "severity": "error"
                    }]
                )

            # Extract phonemes from audio
            phonemes, phoneme_times = await self._extract_phonemes(audio_data)
            
            # Extract visemes from video
            visemes, viseme_times = await self._extract_visemes(video_frames, fps)
            
            if len(phonemes) == 0 or len(visemes) == 0:
                return self._create_result(
                    is_synchronized=False,
                    confidence=0.0,
                    explanations=[{
                        "type": "no_speech",
                        "message": "No speech detected in audio or video",
                        "severity": "warning"
                    }]
                )

            # Align and compare using DTW
            sync_score, alignment = self._compute_sync_score(
                phonemes, phoneme_times, visemes, viseme_times
            )
            
            # Determine if synchronized
            is_synchronized = sync_score > settings.PHONEME_VISEME_THRESHOLD
            confidence = sync_score if is_synchronized else (1.0 - sync_score)
            
            # Generate detailed pair analysis
            pairs = self._generate_pair_analysis(phonemes, phoneme_times, visemes, viseme_times, alignment)
            
            explanations = self._generate_explanations(
                is_synchronized, sync_score, phonemes, visemes, pairs
            )

            return self._create_result(
                is_synchronized=is_synchronized,
                confidence=round(confidence, 4),
                sync_score=round(sync_score, 4),
                phoneme_viseme_pairs=pairs,
                explanations=explanations,
            )

        except Exception as e:
            logger.error(f"Phoneme-viseme detection failed: {e}")
            return self._create_result(
                is_synchronized=False,
                confidence=0.0,
                explanations=[{
                    "type": "processing_error",
                    "message": f"Analysis failed: {str(e)}",
                    "severity": "error"
                }]
            )

    async def _extract_audio_video(
        self, video_bytes: bytes
    ) -> Tuple[Optional[np.ndarray], float, List[np.ndarray]]:
        """Extract audio waveform and video frames."""
        with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as tmp:
            tmp.write(video_bytes)
            tmp_path = tmp.name
        
        try:
            # Extract audio using ffmpeg
            audio_path = tmp_path.replace('.mp4', '.wav')
            import subprocess
            result = subprocess.run([
                'ffmpeg', '-y', '-i', tmp_path,
                '-vn', '-acodec', 'pcm_s16le', '-ar', '16000', '-ac', '1',
                audio_path
            ], capture_output=True, timeout=30)
            
            audio_data = None
            if result.returncode == 0:
                import soundfile as sf
                audio_data, _ = sf.read(audio_path)
                audio_data = audio_data.astype(np.float32)
                try:
                    os.unlink(audio_path)
                except:
                    pass
            
            # Extract video frames
            cap = cv2.VideoCapture(tmp_path)
            fps = cap.get(cv2.CAP_PROP_FPS)
            if fps <= 0:
                fps = 30.0
                
            frames = []
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                frames.append(frame)
            cap.release()
            
            return audio_data, fps, frames
            
        except Exception as e:
            logger.error(f"Audio/video extraction failed: {e}")
            return None, 30.0, []
        finally:
            try:
                os.unlink(tmp_path)
            except:
                pass

    async def _extract_phonemes(
        self, audio_data: np.ndarray
    ) -> Tuple[List[str], List[float]]:
        """Extract phoneme sequence with timestamps from audio."""
        if self.use_asr and self.asr_model is not None:
            return await self._extract_phonemes_asr(audio_data)
        else:
            return self._extract_phonemes_energy(audio_data)

    async def _extract_phonemes_asr(
        self, audio_data: np.ndarray
    ) -> Tuple[List[str], List[float]]:
        """Extract phonemes using Wav2Vec2 ASR model."""
        import torch
        
        # Process in chunks for long audio
        chunk_size = 16000 * 10  # 10 seconds
        all_phonemes = []
        all_times = []
        
        for i in range(0, len(audio_data), chunk_size):
            chunk = audio_data[i:i+chunk_size]
            if len(chunk) < 1600:  # Skip very short chunks
                continue
                
            inputs = self.asr_processor(
                chunk, sampling_rate=16000, return_tensors="pt", padding=True
            )
            
            with torch.no_grad():
                logits = self.asr_model(inputs.input_values).logits
            
            predicted_ids = torch.argmax(logits, dim=-1)
            transcription = self.asr_processor.batch_decode(predicted_ids)[0]
            
            # Convert to phonemes (simplified - in practice use a phonemizer)
            # This is a placeholder; real implementation would use phonemizer
            phonemes = self._text_to_phonemes(transcription)
            
            # Estimate timestamps (simplified)
            chunk_duration = len(chunk) / 16000
            time_per_phoneme = chunk_duration / max(len(phonemes), 1)
            for j, ph in enumerate(phonemes):
                all_phonemes.append(ph)
                all_times.append(i / 16000 + j * time_per_phoneme)
        
        return all_phonemes, all_times

    def _extract_phonemes_energy(
        self, audio_data: np.ndarray
    ) -> Tuple[List[str], List[float]]:
        """Fallback: Extract speech segments using energy-based VAD."""
        # Simple energy-based voice activity detection
        frame_size = 320  # 20ms at 16kHz
        hop_size = 160    # 10ms
        
        energy = []
        times = []
        
        for i in range(0, len(audio_data) - frame_size, hop_size):
            frame = audio_data[i:i+frame_size]
            e = np.sum(frame**2)
            energy.append(e)
            times.append(i / 16000)
            
        energy = np.array(energy)
        if len(energy) == 0:
            return [], []
            
        # Threshold
        threshold = np.percentile(energy, 70)
        voiced = energy > threshold
        
        # Group into segments
        phonemes = []
        phoneme_times = []
        
        in_segment = False
        segment_start = 0
        
        for i, v in enumerate(voiced):
            if v and not in_segment:
                in_segment = True
                segment_start = i
            elif not v and in_segment:
                in_segment = False
                duration = (i - segment_start) * hop_size / 16000
                if duration > 0.05:  # Min 50ms
                    # Map to rough phoneme based on duration and position
                    phonemes.append(self._estimate_phoneme_from_context(duration))
                    phoneme_times.append(times[segment_start])
        
        if in_segment:
            duration = (len(voiced) - segment_start) * hop_size / 16000
            if duration > 0.05:
                phonemes.append(self._estimate_phoneme_from_context(duration))
                phoneme_times.append(times[segment_start])
        
        return phonemes, phoneme_times

    def _text_to_phonemes(self, text: str) -> List[str]:
        """Convert text to phonemes (simplified)."""
        # This is a very simplified version
        # Real implementation would use phonemizer library
        vowels = 'aeiouAEIOU'
        phonemes = []
        for word in text.split():
            for char in word:
                if char.lower() in vowels:
                    phonemes.append(char.lower())
                elif char.isalpha():
                    phonemes.append(char.lower())
        return phonemes if phonemes else ['sil']

    def _estimate_phoneme_from_context(self, duration: float) -> str:
        """Estimate phoneme type from segment duration."""
        if duration < 0.08:
            return 't'  # Short stop
        elif duration < 0.15:
            return 'n'  # Nasal
        elif duration < 0.3:
            return 'a'  # Vowel
        else:
            return 'aa'  # Long vowel

    async def _extract_visemes(
        self, frames: List[np.ndarray], fps: float
    ) -> Tuple[List[int], List[float]]:
        """Extract viseme sequence from video frames."""
        visemes = []
        viseme_times = []
        
        for i, frame in enumerate(frames):
            viseme = self._classify_viseme(frame)
            if viseme is not None:
                visemes.append(viseme)
                viseme_times.append(i / fps)
        
        # Smooth viseme sequence (median filter)
        if len(visemes) > 5:
            from scipy.ndimage import median_filter
            visemes = median_filter(visemes, size=3).astype(int).tolist()
        
        return visemes, viseme_times

    def _classify_viseme(self, frame: np.ndarray) -> Optional[int]:
        """Classify mouth shape into viseme category."""
        h, w = frame.shape[:2]
        
        if self.use_mediapipe:
            return self._classify_viseme_mediapipe(frame)
        else:
            return self._classify_viseme_opencv(frame)

    def _classify_viseme_mediapipe(self, frame: np.ndarray) -> Optional[int]:
        """Classify viseme using MediaPipe FaceMesh landmarks."""
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.mp_face_mesh.process(rgb)
        
        if not results.multi_face_landmarks:
            return None
            
        landmarks = results.multi_face_landmarks[0].landmark
        
        # Key mouth landmarks
        # Upper lip: 13, 14, 15, 16, 17
        # Lower lip: 14, 15, 16, 17, 18 (approximate)
        # Mouth corners: 61, 291
        # Upper inner: 13, 14
        # Lower inner: 14, 15
        
        # Get coordinates
        def get_point(idx):
            lm = landmarks[idx]
            return np.array([lm.x * w, lm.y * h])
        
        # Mouth opening (vertical distance between upper and lower lip)
        upper_lip = get_point(13)
        lower_lip = get_point(14)
        mouth_corner_left = get_point(61)
        mouth_corner_right = get_point(291)
        
        mouth_height = np.linalg.norm(upper_lip - lower_lip)
        mouth_width = np.linalg.norm(mouth_corner_left - mouth_corner_right)
        
        if mouth_width < 1e-6:
            return 0
            
        aspect_ratio = mouth_height / mouth_width
        
        # Lip protrusion (distance from mouth center to nose)
        nose_tip = get_point(1)
        mouth_center = (mouth_corner_left + mouth_corner_right) / 2
        protrusion = np.linalg.norm(nose_tip - mouth_center)
        
        # Classify based on aspect ratio and width
        return self._map_geometry_to_viseme(aspect_ratio, mouth_width, protrusion)

    def _classify_viseme_opencv(self, frame: np.ndarray) -> Optional[int]:
        """Fallback: Classify viseme using OpenCV mouth detection."""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # Use Haar cascade for mouth (if available) or approximate from face
        # This is a simplified fallback
        return None  # Would need mouth cascade

    def _map_geometry_to_viseme(
        self, aspect_ratio: float, mouth_width: float, protrusion: float
    ) -> int:
        """Map mouth geometry to viseme category."""
        # Normalize by face size (approximate)
        normalized_width = mouth_width / 100.0  # Rough normalization
        
        if aspect_ratio < 0.05:
            # Mouth nearly closed
            if normalized_width > 0.3:
                return 12  # m, n, ng (lips closed, wide)
            else:
                return 13  # p, b (lips closed, narrow)
        elif aspect_ratio < 0.15:
            # Slightly open
            if protrusion > 0.5:
                return 5  # uw, uh (rounded)
            else:
                return 4  # iy, ih (spread)
        elif aspect_ratio < 0.3:
            # Moderately open
            if protrusion > 0.5:
                return 6  # ow, aw
            else:
                return 3  # ey, ay
        else:
            # Wide open
            return 1 if protrusion < 0.3 else 2  # aa/ao vs ae/ah

    def _compute_sync_score(
        self,
        phonemes: List[str],
        phoneme_times: List[float],
        visemes: List[int],
        viseme_times: List[float],
    ) -> Tuple[float, List[Tuple[int, int]]]:
        """
        Compute synchronization score using DTW.
        Maps phonemes to expected visemes and compares with observed.
        """
        if len(phonemes) == 0 or len(visemes) == 0:
            return 0.0, []
        
        # Convert phonemes to expected visemes
        expected_visemes = [
            self.PHONEME_TO_VISEME.get(p.lower(), 0) for p in phonemes
        ]
        
        # Resample both sequences to same length for DTW
        # Or use DTW directly on sequences of different lengths
        if fastdtw is None:
            return self._fallback_sync_score(phonemes, phoneme_times, visemes, viseme_times)

        try:
            distance, path = fastdtw(expected_visemes, visemes, dist=euclidean)
            
            # Normalize score
            max_possible_dist = len(path) * 15  # Max viseme diff is ~15
            sync_score = 1.0 - (distance / max_possible_dist)
            sync_score = max(0.0, min(1.0, sync_score))
            
            return sync_score, path
        except Exception as e:
            logger.warning(f"DTW failed: {e}")
            # Fallback: simple correlation at aligned times
            return self._fallback_sync_score(phonemes, phoneme_times, visemes, viseme_times)

    def _fallback_sync_score(
        self,
        phonemes: List[str],
        phoneme_times: List[float],
        visemes: List[int],
        viseme_times: List[float],
    ) -> Tuple[float, List[Tuple[int, int]]]:
        """Fallback synchronization using temporal alignment."""
        if len(phonemes) == 0 or len(visemes) == 0:
            return 0.0, []
        
        # Interpolate visemes to phoneme times
        expected_visemes = [
            self.PHONEME_TO_VISEME.get(p.lower(), 0) for p in phonemes
        ]
        
        # Simple time alignment
        matches = 0
        total = 0
        path = []
        
        for i, (ph_time, exp_viseme) in enumerate(zip(phoneme_times, expected_visemes)):
            # Find closest viseme in time
            time_diffs = [abs(vt - ph_time) for vt in viseme_times]
            if time_diffs:
                closest_idx = np.argmin(time_diffs)
                if time_diffs[closest_idx] < 0.3:  # Within 300ms
                    total += 1
                    if visemes[closest_idx] == exp_viseme:
                        matches += 1
                    path.append((i, closest_idx))
        
        sync_score = matches / total if total > 0 else 0.0
        return sync_score, path

    def _generate_pair_analysis(
        self,
        phonemes: List[str],
        phoneme_times: List[float],
        visemes: List[int],
        viseme_times: List[float],
        alignment: List[Tuple[int, int]],
    ) -> List[Dict[str, Any]]:
        """Generate detailed phoneme-viseme pair analysis."""
        pairs = []
        
        for ph_idx, vis_idx in alignment[:50]:  # Limit to first 50
            if ph_idx < len(phonemes) and vis_idx < len(visemes):
                ph = phonemes[ph_idx]
                exp_viseme = self.PHONEME_TO_VISEME.get(ph.lower(), 0)
                obs_viseme = visemes[vis_idx]
                
                pairs.append({
                    "phoneme": ph,
                    "expected_viseme": exp_viseme,
                    "observed_viseme": obs_viseme,
                    "match": exp_viseme == obs_viseme,
                    "phoneme_time": round(phoneme_times[ph_idx], 3),
                    "viseme_time": round(viseme_times[vis_idx], 3),
                    "time_diff": round(abs(phoneme_times[ph_idx] - viseme_times[vis_idx]), 3),
                })
        
        return pairs

    def _generate_explanations(
        self,
        is_synchronized: bool,
        sync_score: float,
        phonemes: List[str],
        visemes: List[int],
        pairs: List[Dict],
    ) -> List[Dict[str, Any]]:
        explanations = []
        
        explanations.append({
            "type": "sync_analysis",
            "message": f"Analyzed {len(phonemes)} phonemes and {len(visemes)} visemes",
            "severity": "info",
            "details": {
                "phoneme_count": len(phonemes),
                "viseme_count": len(visemes),
                "sync_score": round(sync_score, 3),
            }
        })
        
        if is_synchronized:
            explanations.append({
                "type": "sync_confirmed",
                "message": "Audio and video are well synchronized - lip movements match speech sounds",
                "severity": "success",
            })
        else:
            # Count mismatches
            mismatches = sum(1 for p in pairs if not p["match"])
            total_pairs = len(pairs)
            
            explanations.append({
                "type": "sync_mismatch",
                "message": f"Lip-sync mismatch detected: {mismatches}/{total_pairs} phoneme-viseme pairs don't match",
                "severity": "error" if sync_score < 0.3 else "warning",
                "details": {
                    "mismatch_count": mismatches,
                    "total_pairs": total_pairs,
                    "sync_score": round(sync_score, 3),
                }
            })
            
            # Find specific mismatches
            mismatch_details = [p for p in pairs if not p["match"]][:5]
            if mismatch_details:
                explanations.append({
                    "type": "mismatch_examples",
                    "message": "Examples of mismatched phoneme-viseme pairs:",
                    "severity": "info",
                    "details": {
                        "examples": [
                            {
                                "phoneme": m["phoneme"],
                                "expected": self._viseme_name(m["expected_viseme"]),
                                "observed": self._viseme_name(m["observed_viseme"]),
                                "time_diff_ms": round(m["time_diff"] * 1000),
                            }
                            for m in mismatch_details
                        ]
                    }
                })
        
        return explanations

    def _viseme_name(self, viseme_id: int) -> str:
        names = {
            0: "silence", 1: "aa/ao", 2: "ae/ah", 3: "ey/ay/oy",
            4: "iy/ih", 5: "uw/uh", 6: "ow/aw", 7: "w/r",
            8: "l", 9: "th/dh", 10: "f/v", 11: "s/z/sh",
            12: "m/n/ng", 13: "p/b", 14: "t/d/k/g", 15: "ch/jh"
        }
        return names.get(viseme_id, f"viseme_{viseme_id}")

    def _create_result(
        self,
        is_synchronized: bool,
        confidence: float,
        sync_score: float,
        phoneme_viseme_pairs: List[Dict] = None,
        explanations: List[Dict] = None,
    ) -> Dict[str, Any]:
        return {
            "detector": "phoneme_viseme",
            "is_synchronized": is_synchronized,
            "confidence": confidence,
            "sync_score": sync_score,
            "phoneme_viseme_pairs": phoneme_viseme_pairs or [],
            "explanations": explanations or [],
        }