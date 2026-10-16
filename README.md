# TruthLens AI - Deepfake & Scam Detection
# 
# A cutting-edge platform for detecting manipulated media and fraudulent communications
# using advanced AI techniques including biological liveness detection, cross-modal
# synchronization analysis, and financial threat intelligence.

## 🏆 Winning Differentiators

1. **Biological Liveness Detection (PPG)** - Detects human pulse via micro-color variations in skin
2. **Cross-Modal Phoneme-Viseme Synchronization** - Validates audio-visual physics consistency
3. **Financial Threat Graphing** - Specialized financial scam pattern recognition

## 🏗️ Architecture

```
TruthLens AI/
├── frontend/                 # React + TypeScript + Vite
│   ├── src/
│   │   ├── components/       # Reusable UI components
│   │   ├── pages/           # Page components
│   │   ├── hooks/           # Custom React hooks
│   │   ├── services/        # API services
│   │   ├── store/           # State management (Zustand)
│   │   ├── types/           # TypeScript types
│   │   └── lib/             # Utility functions
│   └── package.json
├── backend/                  # Python FastAPI
│   ├── app/
│   │   ├── api/             # API routes
│   │   ├── core/            # Core configuration
│   │   ├── detectors/       # Detection modules
│   │   ├── services/        # Business logic
│   │   └── utils/           # Utility functions
│   └── requirements.txt
├── docker-compose.yml        # Container orchestration
└── README.md
```

## 🚀 Quick Start

### Prerequisites
- Node.js 18+
- Python 3.10+
- Docker (optional, for containerized deployment)
- NVIDIA GPU (recommended for ML inference)

### Option 1: Docker (Recommended)

```bash
# Clone the repository
git clone <repository-url>
cd TruthLens-AI

# Copy environment file
cp .env.example .env

# Start all services
docker-compose up -d

# Access the application
# Frontend: http://localhost:5173
# Backend API: http://localhost:8000
# API Docs: http://localhost:8000/docs
```

### Option 2: Local Development

#### Backend
```bash
cd backend

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Download spaCy model (for NLP)
python -m spacy download en_core_web_sm

# Run server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

#### Frontend
```bash
cd frontend

# Install dependencies
npm install

# Run development server
npm run dev
```

## 🔬 Detection Modules

### 1. PPG Liveness Detection
- Extracts subtle color changes from facial regions (forehead, cheeks)
- Computes pulse signal using CHROM/POS algorithms
- Bandpass filters for heart rate range (0.7-4 Hz = 42-240 BPM)
- Detects absence of physiological pulse in synthetic avatars
- **Output**: Heart rate (BPM), signal quality, SNR, confidence score

### 2. Phoneme-Viseme Synchronization
- ASR extracts phonemes from audio track (Wav2Vec2)
- MediaPipe FaceMesh tracks visemes (mouth shapes) in video
- 16 viseme categories mapped to phoneme groups
- DTW alignment validates temporal consistency
- Flags lip-sync mismatches as deepfake indicators
- **Output**: Sync score, phoneme-viseme pairs, mismatch details

### 3. Financial Threat Graphing
- NER extracts entities: phones, crypto addresses, URLs, IBANs, SWIFT/BIC, credit cards
- Regex patterns for 10+ financial entity types
- 10 psychological tactic classifications (urgency, authority, fear, greed, etc.)
- Threat intelligence cross-referencing (VirusTotal, AbuseIPDB, custom feeds)
- Luhn algorithm validation for credit cards
- **Output**: Risk score, threat level, detected entities, tactics, recommendations

### 4. Deepfake Image/Video Detection
- EfficientNet-B0 backbone with binary classification head
- Face detection via MediaPipe, crops with padding
- Attention heatmap generation for explainability
- Video frame sampling with temporal consistency scoring
- Heuristic fallback: FFT analysis, edge consistency, gradient artifacts, eye symmetry
- **Output**: Deepfake probability, confidence, heatmap (base64), frame scores

## 📊 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/analyze/image` | POST | Analyze image for manipulation |
| `/api/v1/analyze/video` | POST | Analyze video with PPG + Phoneme-Viseme |
| `/api/v1/analyze/text` | POST | Analyze text for financial scams |
| `/api/v1/analyze/multimodal` | POST | Combined analysis |
| `/api/v1/analyze/{id}/status` | GET | Get analysis job status |
| `/api/v1/analyze/{id}/report` | GET | Get detailed report |
| `/api/v1/health` | GET | Health check |
| `/api/v1/health/detailed` | GET | Detailed system info |

### Example Requests

**Analyze Image:**
```bash
curl -X POST http://localhost:8000/api/v1/analyze/image \
  -F "file=@photo.jpg" \
  -F "return_heatmap=true" \
  -F "sensitivity=0.7"
```

**Analyze Video:**
```bash
curl -X POST http://localhost:8000/api/v1/analyze/video \
  -F "file=@video.mp4" \
  -F "enable_ppg=true" \
  -F "enable_phoneme_viseme=true" \
  -F "sample_rate=5"
```

**Analyze Text:**
```bash
curl -X POST http://localhost:8000/api/v1/analyze/text \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Urgent: Your account is compromised. Verify now at bit.ly/scam",
    "extract_entities": true,
    "check_threat_intel": true
  }'
```

**Multimodal:**
```bash
curl -X POST http://localhost:8000/api/v1/analyze/multimodal \
  -F "image=@photo.jpg" \
  -F "video=@video.mp4" \
  -F "text_content=Suspicious message text"
```

## 🧪 Testing

```bash
# Backend tests
cd backend
pytest -v

# Frontend tests
cd frontend
npm test
```

## 📦 Model Weights

Place model files in `backend/models/`:
- `ppg_liveness.onnx` - PPG liveness classifier (optional)
- `deepfake_detector.pt` - Trained EfficientNet-B0 deepfake classifier state dict (optional).
  Without it, image/video scanning uses the heuristic algorithm ensemble
  (FFT frequency analysis, Laplacian edge consistency, gradient grid-artifact
  detection, eye-region asymmetry) and reports `model_used: heuristic_ensemble`.
- `wav2vec2_phoneme/` - Wav2Vec2 phoneme model directory
- `viseme_classifier.onnx` - Viseme classifier (optional)
- `llm/Qwen3-4B-Instruct-2507-Q8_0.gguf` - Local Qwen3-4B LLM (downloaded
  automatically by `setup.bat` / `download_llm.py`, ~4 GB)

Models will use heuristic fallbacks if not present.

## 🧠 Local LLM (Qwen3-4B, Q8_0)

TruthLens ships with a **local Qwen3-4B-Instruct-2507** model (Q8_0 GGUF, ~4 GB)
served through llama.cpp. It fits in 8 GB VRAM and is managed by an
**LLM manager** (`backend/app/services/llm_manager.py`):

- **On-demand loading** - the model is loaded into VRAM (all layers offloaded
  to GPU) only when an LLM task starts
- **Automatic unload** - after each task completes, the model is destroyed and
  VRAM is fully released (~5 GB freed)
- **Graceful degradation** - if the model is missing or the backend is not
  installed, scanning continues without AI explanations

What it does:
- Writes a plain-language **AI Explanation** attached to every analysis
  (`llm_summary` field, shown in the web UI)
- Answers follow-up questions about an analysis via `POST /api/v1/llm/ask`
  (the "Ask AI" panel in the result view)

Setup (already handled by `setup.bat`):
```bash
# 1. Install the llama.cpp backend (CUDA build for VRAM offload)
pip install llama-cpp-python==0.3.36 --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cu124

# 2. Download the model into the project folder (~4 GB)
python backend/download_llm.py
```

LLM endpoints:
| Method | Path | Description |
| --- | --- | --- |
| GET | `/api/v1/llm/status` | Model presence, load state, VRAM usage |
| POST | `/api/v1/llm/load` | Load the model into VRAM |
| POST | `/api/v1/llm/unload` | Unload and release VRAM |
| POST | `/api/v1/llm/ask` | Ask a question (optionally about an analysis) |

LLM settings in `.env`:
```bash
LLM_ENABLED=true                 # master switch
LLM_MODEL_PATH=./models/llm/Qwen3-4B-Instruct-2507-Q8_0.gguf
LLM_N_GPU_LAYERS=-1              # all layers offloaded to GPU
LLM_REQUIRE_GPU=true             # reject CPU builds, partial offload, insufficient free VRAM
LLM_VERBOSE=false                # true prints native layer/buffer placement logs
LLM_IDLE_UNLOAD_SECONDS=0        # 0 = unload immediately after each task
```

The root `.env` is loaded regardless of the launch directory; `backend/.env`
overrides it if present. Relative model paths are resolved from `backend/`.
Qwen uses llama.cpp CUDA independently of PyTorch, so a CPU-only PyTorch build
does not prevent Qwen from using the GPU. `/api/v1/llm/status` reports
`gpu_offload_supported`, `gpu_required`, `loaded`, `execution_device`, and VRAM.
An unloaded model is normal with immediate unload enabled.

Verified on an RTX 4060 Laptop GPU (8 GB): 37/37 layers offloaded, 4076 MiB
CUDA model buffer, 576 MiB GPU KV cache, about 5162 MiB total device usage
while loaded, and successful text generation. The native runtime still needs
host memory (about 394 MiB of pinned model buffers plus Python and metadata);
GPU inference cannot mean zero system RAM. Memory mapping is disabled to avoid
retaining a full mapped GGUF in the process. Free VRAM is checked with conservative
headroom before loading; actual requirements vary with context and other apps.

Qwen provides text explanations and follow-up answers over detector outputs.
It does not replace trained deepfake classifier weights. Without
`backend/models/deepfake_detector.pt`, image scanning uses the labeled heuristic
ensemble. The optional phoneme ASR also uses its fallback if its dependencies
or weights are unavailable. These startup warnings do not prevent image uploads.

## 🔧 Configuration

Key settings in `.env`:
```bash
# Thresholds (0-1)
PPG_CONFIDENCE_THRESHOLD=0.75
PHONEME_VISEME_THRESHOLD=0.70
DEEPFAKE_THRESHOLD=0.65
FINANCIAL_THREAT_THRESHOLD=0.60

# External APIs for threat intelligence
VIRUSTOTAL_API_KEY=your_key
ABUSEIPDB_API_KEY=your_key
```

## 🐳 Production Deployment

```bash
# Build production images
docker-compose -f docker-compose.yml -f docker-compose.prod.yml build

# Deploy
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# Scale backend workers
docker-compose up -d --scale backend=3
```

## 📝 License

MIT License - Built for hackathon excellence

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests
5. Submit a pull request

## 🙏 Acknowledgments

- MediaPipe for face detection and landmarks
- Hugging Face Transformers for Wav2Vec2
- FastAPI for the excellent framework
- The open-source deepfake detection research community
