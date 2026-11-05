# TruthLens AI — Deepfake & Scam Detection

> A cutting-edge platform for detecting manipulated media and fraudulent communications using advanced AI techniques including biological liveness detection, cross-modal synchronization analysis, and financial threat intelligence.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-3776AB.svg)](https://www.python.org/)
[![React](https://img.shields.io/badge/React-18-61DAFB.svg)](https://react.dev/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100%2B-009688.svg)](https://fastapi.tiangolo.com/)

---

## 🏆 Winning Differentiators

| # | Feature | Highlight |
|---|---------|-----------|
| 1 | **Biological Liveness Detection (PPG)** | Detects human pulse via micro-color variations in skin |
| 2 | **Cross-Modal Phoneme-Viseme Sync** | Validates audio-visual physics consistency |
| 3 | **Financial Threat Graphing** | Specialized financial scam pattern recognition |

---

## 🗂️ Project Structure

```
TruthLens AI/
├── frontend/                 # React + TypeScript + Vite
│   ├── src/
│   │   ├── components/       # Reusable UI components
│   │   ├── pages/            # Page components
│   │   ├── services/         # API services
│   │   ├── store/            # State management (Zustand)
│   │   └── lib/              # Utility functions
│   └── package.json
├── backend/                  # Python FastAPI
│   ├── app/
│   │   ├── api/              # API routes
│   │   ├── core/             # Core configuration
│   │   ├── detectors/        # Detection modules
│   │   ├── services/         # Business logic
│   │   └── utils/            # Utility functions
│   └── requirements.txt
├── docker-compose.yml        # Container orchestration
├── LICENSE                   # MIT License
└── README.md
```

---

## 🚀 Quick Start

### Prerequisites

- **Node.js** 18+
- **Python** 3.10+
- **Docker** (optional, for containerized deployment)
- **NVIDIA GPU** (recommended for ML inference)

### Option 1 — Docker (Recommended)

```bash
# Clone the repository
git clone <repository-url>
cd TruthLens-AI

# Copy environment file
cp .env.example .env

# Start all services
docker-compose up -d
```

The app will be available at:

| Service | URL |
|---------|-----|
| Frontend | http://localhost:5173 |
| Backend API | http://localhost:8000 |
| API Docs (Swagger) | http://localhost:8000/docs |

### Option 2 — Local Development

#### Backend

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Download spaCy model
python -m spacy download en_core_web_sm

# Start server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

#### Frontend

```bash
cd frontend

# Install dependencies
npm install

# Start dev server
npm run dev
```

---

## 🔬 Detection Modules

### 1. PPG Liveness Detection

Extracts subtle color changes from facial regions (forehead, cheeks) to compute a pulse signal using CHROM/POS algorithms. A bandpass filter isolates heart-rate frequencies (0.7–4 Hz / 42–240 BPM). The absence of a physiological pulse flags synthetic avatars.

**Output:** Heart rate (BPM) · Signal quality · SNR · Confidence score

### 2. Phoneme-Viseme Synchronization

Uses Wav2Vec2 ASR to extract phonemes from the audio track and MediaPipe FaceMesh to track visemes (mouth shapes) in video. DTW alignment across 16 viseme categories validates temporal consistency; mismatches flag deepfake lip-sync errors.

**Output:** Sync score · Phoneme-viseme pairs · Mismatch details

### 3. Financial Threat Graphing

NER + regex patterns extract 10+ financial entity types (phones, crypto addresses, URLs, IBANs, SWIFT/BIC, credit cards). Ten psychological-tactic classifiers (urgency, authority, fear, greed, etc.) and threat-intelligence cross-referencing (VirusTotal, AbuseIPDB) provide a composite risk assessment.

**Output:** Risk score · Threat level · Detected entities · Tactics · Recommendations

### 4. Deepfake Image / Video Detection

EfficientNet-B0 classifier with face detection (MediaPipe), attention heatmaps for explainability, and temporal consistency scoring across sampled video frames. A heuristic fallback performs FFT analysis, edge consistency checks, gradient artifact detection, and eye symmetry validation.

**Output:** Deepfake probability · Confidence · Heatmap (base64) · Frame scores

---

## 📊 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/detect/image` | POST | Analyze an image for deepfake indicators |
| `/api/v1/detect/video` | POST | Analyze a video with multi-modal checks |
| `/api/v1/detect/text` | POST | Scan text for scam / phishing patterns |
| `/api/v1/detect/document` | POST | Analyze document authenticity |
| `/api/v1/health` | GET | Health check |

Full interactive docs at **http://localhost:8000/docs** when the backend is running.

---

## ⚙️ Configuration

Key settings in `.env` (see [`.env.example`](.env.example) for all options):

```bash
# Detection thresholds (0-1)
PPG_CONFIDENCE_THRESHOLD=0.75
PHONEME_VISEME_THRESHOLD=0.70
DEEPFAKE_THRESHOLD=0.65
FINANCIAL_THREAT_THRESHOLD=0.60

# External APIs for threat intelligence
VIRUSTOTAL_API_KEY=your_key
ABUSEIPDB_API_KEY=your_key
```

---

## 🐳 Production Deployment

```bash
# Build production images
docker-compose -f docker-compose.yml -f docker-compose.prod.yml build

# Deploy
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# Scale backend workers
docker-compose up -d --scale backend=3
```

---

## 🧪 Testing

```bash
# Backend tests
cd backend
pytest

# Frontend tests
cd frontend
npm test
```

---

## ⚠️ Disclaimers

- The AI-image classifier has **not** been independently validated or calibrated for uploaded phone photographs, documents, screenshots, or current generators. Its raw softmax activation is diagnostic only.
- Document-like layouts are always excluded from classifier authenticity verdicts.
- External threat intelligence is **not configured** by default; URL/keyword matches are local heuristics only.
- Structured IPTC XMP declarations of AI generation are shown as unsigned metadata evidence — they can be forged or removed.

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📄 License

This project is licensed under the **MIT License** — see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- [MediaPipe](https://mediapipe.dev/) — Face detection and landmarks
- [Hugging Face Transformers](https://huggingface.co/) — Wav2Vec2 ASR
- [FastAPI](https://fastapi.tiangolo.com/) — Backend framework
- [React](https://react.dev/) & [Vite](https://vitejs.dev/) — Frontend tooling
- [Recharts](https://recharts.org/) — Data visualization
- The open-source deepfake detection research community
