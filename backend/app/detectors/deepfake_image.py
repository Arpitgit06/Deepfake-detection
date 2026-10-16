import cv2
import numpy as np
import logging
import tempfile
import os
import asyncio
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from PIL import Image
import io

import torch
import torchvision.transforms as transforms
from torchvision.models import efficientnet_b0

from app.core.config import settings

logger = logging.getLogger(__name__)


@dataclass
class DeepfakeResult:
    is_deepfake: bool
    confidence: float
    heatmap: Optional[np.ndarray]
    explanations: List[Dict[str, Any]]
    frame_scores: Optional[List[float]] = None


class DeepfakeImageDetector:
    """
    Deepfake detection for images and video frames.

    Primary path: EfficientNet-B0 classifier with trained weights loaded from
    settings.DEEPFAKE_MODEL_WEIGHTS (state dict). If no trained weights file is
    present, the detector falls back to a transparent heuristic algorithm
    ensemble (FFT frequency analysis, Laplacian edge consistency, Sobel gradient
    grid-artifact detection, eye-region asymmetry) so scanning still works.

    Supports both single image and video frame analysis.
    """

    def __init__(self):
        self.model = None
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.transform = None
        self.face_detector = None
        self.model_available = False
        self._initialize_model()

    def _initialize_model(self):
        """Initialize the deepfake detection model."""
        # Image preprocessing
        self.transform = transforms.Compose([
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize(
                mean=[0.485, 0.456, 0.406],
                std=[0.229, 0.224, 0.225]
            ),
        ])

        # Load EfficientNet-B0 backbone with *trained* binary-classifier weights.
        # Without trained weights the classifier head is random and its output is
        # meaningless, so we only use the network when a weights file exists.
        weights_path = settings.DEEPFAKE_MODEL_WEIGHTS
        if weights_path and os.path.exists(weights_path):
            try:
                self.model = efficientnet_b0(weights=None)
                self.model.classifier[1] = torch.nn.Linear(
                    self.model.classifier[1].in_features, 2
                )
                state_dict = torch.load(weights_path, map_location=self.device)
                # Accept both full checkpoints and bare state dicts
                if isinstance(state_dict, dict) and "state_dict" in state_dict:
                    state_dict = state_dict["state_dict"]
                self.model.load_state_dict(state_dict)
                self.model.to(self.device)
                self.model.eval()
                self.model_available = True
                logger.info(
                    f"Deepfake model loaded from {weights_path} on {self.device}"
                )
            except Exception as e:
                logger.warning(f"Could not load deepfake weights '{weights_path}': {e}")
                self.model = None
                self.model_available = False
        else:
            logger.warning(
                f"No trained deepfake weights found at '{weights_path}'. "
                f"Using the heuristic algorithm ensemble for scanning."
            )

        # Initialize face detector (MediaPipe preferred, OpenCV fallback)
        try:
            import mediapipe as mp
            self.mp_face_detection = mp.solutions.face_detection.FaceDetection(
                model_selection=1, min_detection_confidence=0.5
            )
            self.use_mediapipe = True
            logger.info("MediaPipe face detection initialized for deepfake detector")
        except Exception as e:
            logger.warning(f"MediaPipe not available: {e}, using OpenCV")
            self.use_mediapipe = False
            cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
            self.face_cascade = cv2.CascadeClassifier(cascade_path)

    def _preprocess_face(self, face_img: np.ndarray) -> Optional[torch.Tensor]:
        """Preprocess face crop for model input."""
        try:
            # Convert BGR to RGB
            face_rgb = cv2.cvtColor(face_img, cv2.COLOR_BGR2RGB)
            pil_img = Image.fromarray(face_rgb)
            tensor = self.transform(pil_img).unsqueeze(0).to(self.device)
            return tensor
        except Exception as e:
            logger.error(f"Face preprocessing failed: {e}")
            return None

    def _detect_faces(self, frame: np.ndarray) -> List[Tuple[int, int, int, int]]:
        """Detect faces in frame, return list of (x, y, w, h)."""
        h, w = frame.shape[:2]
        faces = []

        if self.use_mediapipe:
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = self.mp_face_detection.process(rgb_frame)
            if results.detections:
                for detection in results.detections:
                    bbox = detection.location_data.relative_bounding_box
                    x = int(bbox.xmin * w)
                    y = int(bbox.ymin * h)
                    bw = int(bbox.width * w)
                    bh = int(bbox.height * h)
                    # Expand bbox slightly
                    x = max(0, x - int(bw * 0.1))
                    y = max(0, y - int(bh * 0.1))
                    bw = min(w - x, int(bw * 1.2))
                    bh = min(h - y, int(bh * 1.2))
                    faces.append((x, y, bw, bh))
        else:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            detected = self.face_cascade.detectMultiScale(
                gray, scaleFactor=1.1, minNeighbors=5, minSize=(80, 80)
            )
            for (x, y, bw, bh) in detected:
                faces.append((x, y, bw, bh))

        # Sort by area (largest first)
        faces.sort(key=lambda f: f[2] * f[3], reverse=True)
        return faces

    def _generate_heatmap(self, frame: np.ndarray, face_box: Tuple[int, int, int, int],
                          score: float) -> np.ndarray:
        """Generate attention heatmap overlay on the frame."""
        x, y, w, h = face_box
        heatmap = np.zeros((frame.shape[0], frame.shape[1]), dtype=np.float32)

        # Create Gaussian heatmap centered on face
        center_x, center_y = x + w // 2, y + h // 2
        sigma = max(w, h) / 4

        y_coords, x_coords = np.ogrid[:frame.shape[0], :frame.shape[1]]
        heatmap = np.exp(-((x_coords - center_x)**2 + (y_coords - center_y)**2) / (2 * sigma**2))

        # Normalize and apply score
        heatmap = heatmap / (heatmap.max() + 1e-6) * score

        return heatmap

    async def detect(
        self,
        image_bytes: bytes,
        sensitivity: float = 0.5,
        return_heatmap: bool = False,
    ) -> Dict[str, Any]:
        """
        Detect deepfake in a single image.
        """
        try:
            # Decode image
            nparr = np.frombuffer(image_bytes, np.uint8)
            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

            if frame is None:
                return self._create_result(
                    is_deepfake=False,
                    confidence=0.0,
                    explanations=[{
                        "type": "decode_error",
                        "message": "Could not decode image",
                        "severity": "error"
                    }]
                )

            # Detect faces
            faces = self._detect_faces(frame)

            if not faces:
                return self._create_result(
                    is_deepfake=None,
                    confidence=0.0,
                    explanations=[{
                        "type": "no_face",
                        "message": "Face-specific checks do not apply: no face detected. Whole-image AI analysis is reported separately.",
                        "severity": "info"
                    }],
                    status="not_applicable",
                )

            # Analyze each face (use largest)
            x, y, w, h = faces[0]
            face_crop = frame[y:y+h, x:x+w]

            # Preprocess
            input_tensor = self._preprocess_face(face_crop)
            if input_tensor is None:
                return self._create_result(
                    is_deepfake=False,
                    confidence=0.0,
                    explanations=[{
                        "type": "preprocess_error",
                        "message": "Failed to preprocess face",
                        "severity": "error"
                    }]
                )

            # Run inference
            heuristic_details = None
            if self.model is not None:
                with torch.no_grad():
                    outputs = self.model(input_tensor)
                    probs = torch.softmax(outputs, dim=1)
                    fake_prob = probs[0, 1].item()
                    real_prob = probs[0, 0].item()
            else:
                # Fallback: heuristic algorithm ensemble
                fake_prob, heuristic_details = self._heuristic_analysis(face_crop)
                real_prob = 1 - fake_prob

            # Apply sensitivity threshold adjustment
            threshold = settings.DEEPFAKE_THRESHOLD * (1.0 - sensitivity * 0.3)  # Lower sensitivity = higher threshold
            is_deepfake = fake_prob > threshold
            confidence = fake_prob if is_deepfake else real_prob

            # Generate heatmap if requested
            heatmap = None
            if return_heatmap:
                heatmap = self._generate_heatmap(frame, (x, y, w, h), fake_prob)
                heatmap = (heatmap * 255).astype(np.uint8)

            explanations = self._generate_explanations(
                is_deepfake, fake_prob, real_prob, len(faces), sensitivity
            )

            return self._create_result(
                is_deepfake=is_deepfake,
                confidence=round(confidence, 4),
                heatmap=heatmap,
                explanations=explanations,
                heuristic_details=heuristic_details,
            )

        except Exception as e:
            logger.error(f"Image deepfake detection failed: {e}")
            return self._create_result(
                is_deepfake=False,
                confidence=0.0,
                explanations=[{
                    "type": "processing_error",
                    "message": f"Analysis failed: {str(e)}",
                    "severity": "error"
                }]
            )

    async def detect_video_frames(
        self,
        video_bytes: bytes,
        sample_rate: int = 5,
        max_frames: int = 100,
    ) -> Dict[str, Any]:
        """
        Analyze video frames for deepfake indicators.
        """
        try:
            with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as tmp:
                tmp.write(video_bytes)
                tmp_path = tmp.name

            try:
                cap = cv2.VideoCapture(tmp_path)
                fps = cap.get(cv2.CAP_PROP_FPS)
                if fps <= 0:
                    fps = 30.0

                frame_interval = max(1, int(fps / sample_rate))
                frame_scores = []
                frame_explanations = []
                all_heatmaps = []
                frames_analyzed = 0

                frame_count = 0
                while frames_analyzed < max_frames:
                    ret, frame = cap.read()
                    if not ret:
                        break

                    if frame_count % frame_interval == 0:
                        faces = self._detect_faces(frame)
                        if faces:
                            x, y, w, h = faces[0]
                            face_crop = frame[y:y+h, x:x+w]
                            input_tensor = self._preprocess_face(face_crop)

                            if input_tensor is not None:
                                if self.model is not None:
                                    with torch.no_grad():
                                        outputs = self.model(input_tensor)
                                        probs = torch.softmax(outputs, dim=1)
                                        fake_prob = probs[0, 1].item()
                                else:
                                    fake_prob, _ = self._heuristic_analysis(face_crop)

                                frame_scores.append(fake_prob)
                                frames_analyzed += 1

                    frame_count += 1

                cap.release()

            finally:
                try:
                    os.unlink(tmp_path)
                except:
                    pass

            if not frame_scores:
                return self._create_result(
                    is_deepfake=False,
                    confidence=0.0,
                    explanations=[{
                        "type": "no_faces_in_video",
                        "message": "No faces detected in video frames",
                        "severity": "warning"
                    }]
                )

            # Aggregate frame scores
            mean_score = np.mean(frame_scores)
            max_score = np.max(frame_scores)
            std_score = np.std(frame_scores)

            # Video-level decision: use mean with consideration of consistency
            # High variance might indicate partial manipulation
            consistency = 1.0 - min(std_score * 2, 1.0)
            overall_score = mean_score * 0.7 + max_score * 0.3
            overall_score *= consistency

            threshold = settings.DEEPFAKE_THRESHOLD
            is_deepfake = overall_score > threshold
            confidence = overall_score if is_deepfake else (1 - overall_score)

            explanations = self._generate_video_explanations(
                is_deepfake, frame_scores, mean_score, max_score, std_score, frames_analyzed
            )

            return self._create_result(
                is_deepfake=is_deepfake,
                confidence=round(confidence, 4),
                explanations=explanations,
                frame_scores=[round(s, 4) for s in frame_scores],
            )

        except Exception as e:
            logger.error(f"Video frame deepfake detection failed: {e}")
            return self._create_result(
                is_deepfake=False,
                confidence=0.0,
                explanations=[{
                    "type": "processing_error",
                    "message": f"Video analysis failed: {str(e)}",
                    "severity": "error"
                }]
            )

    def _heuristic_analysis(self, face_crop: np.ndarray) -> Tuple[float, Dict[str, Any]]:
        """
        Heuristic deepfake analysis when no trained model is available.
        Checks for common artifacts: blending boundaries, frequency anomalies, etc.
        Returns (score, details) where details breaks down each algorithm's
        contribution so results can be explained to the user.
        """
        # Convert to grayscale
        gray = cv2.cvtColor(face_crop, cv2.COLOR_BGR2GRAY)
        h, w = gray.shape

        # Resize to standard size
        gray = cv2.resize(gray, (224, 224))

        score = 0.0
        details: Dict[str, Any] = {"algorithms": []}

        # 1. Frequency domain analysis (FFT)
        fft = np.fft.fft2(gray)
        fft_shift = np.fft.fftshift(fft)
        magnitude = np.log(np.abs(fft_shift) + 1)

        # Check for grid artifacts (common in GAN outputs)
        center_h, center_w = magnitude.shape[0] // 2, magnitude.shape[1] // 2
        # Look for periodic patterns
        radial_profile = self._radial_profile(magnitude, (center_h, center_w))
        # High frequency spikes can indicate artifacts
        hf_energy = np.sum(radial_profile[len(radial_profile)//2:])
        total_energy = np.sum(radial_profile)
        if total_energy > 0:
            hf_ratio = hf_energy / total_energy
            if hf_ratio > 0.15:  # Threshold for suspicious HF energy
                score += 0.2
                details["algorithms"].append("fft_high_frequency_anomaly")
            details["fft_hf_ratio"] = round(float(hf_ratio), 4)

        # 2. Edge consistency (Laplacian variance)
        laplacian = cv2.Laplacian(gray, cv2.CV_64F)
        edge_variance = laplacian.var()
        details["laplacian_variance"] = round(float(edge_variance), 2)
        # Very low variance = overly smooth (potential deepfake)
        # Very high variance = excessive sharpening artifacts
        if edge_variance < 50:
            score += 0.15
            details["algorithms"].append("overly_smooth_texture")
        elif edge_variance > 5000:
            score += 0.1
            details["algorithms"].append("sharpening_artifacts")

        # 3. Color space inconsistency (check for blending artifacts)
        lab = cv2.cvtColor(cv2.resize(face_crop, (224, 224)), cv2.COLOR_BGR2LAB)
        l_channel = lab[:, :, 0]
        # Check for unnatural transitions in L channel
        grad_x = cv2.Sobel(l_channel, cv2.CV_64F, 1, 0, ksize=3)
        grad_y = cv2.Sobel(l_channel, cv2.CV_64F, 0, 1, ksize=3)
        grad_mag = np.sqrt(grad_x**2 + grad_y**2)
        # Look for grid-like patterns in gradients
        if self._detect_grid_artifacts(grad_mag):
            score += 0.25
            details["algorithms"].append("grid_artifacts_in_gradients")

        # 4. Eye region consistency (deepfakes often struggle with eyes)
        eye_score = self._analyze_eye_region(gray)
        score += eye_score * 0.2
        details["eye_asymmetry_score"] = round(float(eye_score), 4)
        if eye_score > 0:
            details["algorithms"].append("eye_region_asymmetry")

        final_score = min(score, 1.0)
        details["heuristic_score"] = round(final_score, 4)
        return final_score, details

    def _radial_profile(self, image: np.ndarray, center: Tuple[int, int]) -> np.ndarray:
        """Compute radial profile of 2D image."""
        y, x = np.indices(image.shape)
        r = np.sqrt((x - center[1])**2 + (y - center[0])**2)
        r = r.astype(int)

        tbin = np.bincount(r.ravel(), image.ravel())
        nr = np.bincount(r.ravel())
        radial = tbin / (nr + 1e-6)
        return radial

    def _detect_grid_artifacts(self, grad_mag: np.ndarray) -> bool:
        """Detect grid-like artifacts in gradient magnitude."""
        # Check for periodic patterns in both directions
        h, w = grad_mag.shape
        # Horizontal profile
        h_profile = np.mean(grad_mag, axis=0)
        # Vertical profile
        v_profile = np.mean(grad_mag, axis=1)

        # FFT of profiles
        h_fft = np.abs(np.fft.fft(h_profile))
        v_fft = np.abs(np.fft.fft(v_profile))

        # Look for peaks at regular intervals (excluding DC)
        h_peaks = self._find_peaks(h_fft[1:w//4])
        v_peaks = self._find_peaks(v_fft[1:h//4])

        return len(h_peaks) > 2 or len(v_peaks) > 2

    def _find_peaks(self, signal: np.ndarray, prominence: float = 0.1) -> List[int]:
        """Simple peak detection."""
        peaks = []
        for i in range(1, len(signal) - 1):
            if signal[i] > signal[i-1] and signal[i] > signal[i+1]:
                if signal[i] > prominence * np.max(signal):
                    peaks.append(i)
        return peaks

    def _analyze_eye_region(self, gray: np.ndarray) -> float:
        """Analyze eye region for deepfake artifacts."""
        h, w = gray.shape
        # Approximate eye regions (upper third, left and right)
        eye_region = gray[h//6:h//2, w//4:3*w//4]
        if eye_region.size == 0:
            return 0.0

        # Check symmetry
        left_half = eye_region[:, :eye_region.shape[1]//2]
        right_half = cv2.flip(eye_region[:, eye_region.shape[1]//2:], 1)

        # Resize to match
        min_w = min(left_half.shape[1], right_half.shape[1])
        left_half = left_half[:, :min_w]
        right_half = right_half[:, :min_w]

        diff = np.abs(left_half.astype(float) - right_half.astype(float))
        asymmetry = np.mean(diff) / 255.0

        # High asymmetry can indicate deepfake (but some asymmetry is natural)
        if asymmetry > 0.15:
            return 0.5
        elif asymmetry > 0.1:
            return 0.2
        return 0.0

    def _generate_explanations(
        self,
        is_deepfake: bool,
        fake_prob: float,
        real_prob: float,
        num_faces: int,
        sensitivity: float,
    ) -> List[Dict[str, Any]]:
        explanations = []

        explanations.append({
            "type": "analysis_summary",
            "message": (
                f"Analyzed {num_faces} face(s) with sensitivity {sensitivity:.1f} "
                f"using {'EfficientNet-B0 model' if self.model is not None else 'heuristic algorithm ensemble'}"
            ),
            "severity": "info",
            "details": {
                "faces_detected": num_faces,
                "fake_probability": round(fake_prob, 4),
                "real_probability": round(real_prob, 4),
                "threshold": round(settings.DEEPFAKE_THRESHOLD * (1.0 - sensitivity * 0.3), 4),
                "model_used": "efficientnet_b0" if self.model is not None else "heuristic_ensemble",
                "model_available": self.model_available,
            }
        })

        if is_deepfake:
            explanations.append({
                "type": "deepfake_detected",
                "message": f"Deepfake indicators detected (confidence: {fake_prob:.1%})",
                "severity": "error",
                "details": {
                    "confidence": round(fake_prob, 4),
                    "indicators": [
                        "Unnatural facial texture patterns",
                        "Inconsistent lighting/shadows",
                        "Possible blending artifacts",
                    ]
                }
            })
        else:
            explanations.append({
                "type": "clean",
                "message": f"Image appears authentic (confidence: {real_prob:.1%})",
                "severity": "success",
                "details": {
                    "confidence": round(real_prob, 4),
                }
            })

        return explanations

    def _generate_video_explanations(
        self,
        is_deepfake: bool,
        frame_scores: List[float],
        mean_score: float,
        max_score: float,
        std_score: float,
        frames_analyzed: int,
    ) -> List[Dict[str, Any]]:
        explanations = []

        explanations.append({
            "type": "video_analysis_summary",
            "message": f"Analyzed {frames_analyzed} frames at {len(frame_scores)} samples",
            "severity": "info",
            "details": {
                "frames_analyzed": frames_analyzed,
                "mean_score": round(mean_score, 4),
                "max_score": round(max_score, 4),
                "std_score": round(std_score, 4),
                "consistency": round(1.0 - min(std_score * 2, 1.0), 4),
            }
        })

        if is_deepfake:
            explanations.append({
                "type": "video_deepfake_detected",
                "message": f"Deepfake indicators in video (avg confidence: {mean_score:.1%})",
                "severity": "error",
                "details": {
                    "mean_confidence": round(mean_score, 4),
                    "peak_confidence": round(max_score, 4),
                    "temporal_consistency": round(1.0 - min(std_score * 2, 1.0), 4),
                }
            })

            # Check for frame-level inconsistencies
            if std_score > 0.2:
                explanations.append({
                    "type": "temporal_inconsistency",
                    "message": "High frame-to-frame variation suggests partial manipulation",
                    "severity": "warning",
                    "details": {
                        "score_variance": round(std_score, 4),
                    }
                })
        else:
            explanations.append({
                "type": "video_clean",
                "message": f"Video appears authentic (avg confidence: {1-mean_score:.1%})",
                "severity": "success",
                "details": {
                    "confidence": round(1 - mean_score, 4),
                }
            })

        return explanations

    def _create_result(
        self,
        is_deepfake: bool,
        confidence: float,
        heatmap: Optional[np.ndarray] = None,
        explanations: List[Dict] = None,
        frame_scores: Optional[List[float]] = None,
        heuristic_details: Optional[Dict[str, Any]] = None,
        status: Optional[str] = None,
    ) -> Dict[str, Any]:
        explanations = explanations or []
        if status is None:
            types = {item.get('type') for item in explanations}
            if types & {'decode_error', 'processing_error', 'preprocess_error'}:
                status = 'error'
            elif 'no_faces_in_video' in types:
                status = 'not_applicable'
            elif self.model is None:
                status = 'inconclusive'
                explanations = [item for item in explanations if item.get('type') not in
                                {'clean', 'deepfake_detected', 'video_clean', 'video_deepfake_detected'}]
                explanations.append({'type': 'face_model_unavailable', 'severity': 'warning',
                    'message': 'Trained face-manipulation weights are unavailable. Facial heuristic checks cannot establish authenticity.'})
            else:
                status = 'suspicious' if is_deepfake else 'clean'
        if status in ('error', 'not_applicable', 'inconclusive'):
            is_deepfake = None
            confidence = 0.0
        result = {
            "detector": "deepfake_image",
            "status": status,
            "is_deepfake": is_deepfake,
            "confidence": confidence,
            "explanations": explanations,
            # Transparency: tell the client what actually produced the verdict
            "model_available": self.model_available,
            "model_used": "efficientnet_b0" if self.model is not None else "heuristic_ensemble",
        }

        if heuristic_details is not None:
            result["heuristic_details"] = heuristic_details

        if heatmap is not None:
            # Encode heatmap as base64 for JSON transport
            import base64
            _, buffer = cv2.imencode('.png', heatmap)
            result["heatmap_base64"] = base64.b64encode(buffer).decode('utf-8')

        if frame_scores is not None:
            result["frame_scores"] = frame_scores

        return result
