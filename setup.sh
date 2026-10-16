#!/bin/bash
# ============================================================================
# TruthLens AI - Project Setup Script (Linux/macOS)
# ============================================================================
# This script sets up the complete TruthLens AI development environment
# Run with: bash setup.sh
# ============================================================================

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
RESET='\033[0m'

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$PROJECT_ROOT/backend"
FRONTEND_DIR="$PROJECT_ROOT/frontend"
VENV_DIR="$BACKEND_DIR/venv"
MODELS_DIR="$BACKEND_DIR/models"

print_info() { echo -e "${BLUE}[INFO]${RESET} $1"; }
print_ok() { echo -e "${GREEN}[OK]${RESET} $1"; }
print_warn() { echo -e "${YELLOW}[WARN]${RESET} $1"; }
print_error() { echo -e "${RED}[ERROR]${RESET} $1"; }
print_step() { echo -e "\n${CYAN}=====================================================================${RESET}"; echo -e "${CYAN}  $1${RESET}"; echo -e "${CYAN}=====================================================================${RESET}\n"; }

# Header
echo -e "${CYAN}"
cat << 'EOF'
╔═══════════════════════════════════════════════════════════════════════════╗
║                    TruthLens AI - Project Setup                          ║
║              Deepfake & Scam Detection Platform                          ║
╚═══════════════════════════════════════════════════════════════════════════╝
EOF
echo -e "${RESET}"

print_info "Project root: $PROJECT_ROOT"

# ============================================================================
# Check Prerequisites
# ============================================================================
print_step "Checking Prerequisites"

check_command() {
    local cmd="$1"
    local name="$2"
    local version_var="$3"
    local version=""
    
    if command -v "$cmd" >/dev/null 2>&1; then
        case "$cmd" in
            python3|python) version=$($cmd --version 2>&1) ;;
            node) version=$($cmd --version 2>&1) ;;
            npm) version=$($cmd --version 2>&1) ;;
            git) version=$($cmd --version 2>&1) ;;
            docker) version=$($cmd --version 2>&1) ;;
            docker-compose) version=$($cmd --version 2>&1) ;;
            ffmpeg) version=$($cmd -version 2>&1 | head -1) ;;
            *) version="found" ;;
        esac
        print_ok "$name found: $version"
        eval "$version_var='$version'"
        return 0
    else
        eval "$version_var=''"
        return 1
    fi
}

PYTHON_CMD=""
if check_command python3 "Python" PYTHON_VERSION; then
    PYTHON_CMD="python3"
elif check_command python "Python" PYTHON_VERSION; then
    PYTHON_CMD="python"
else
    print_error "Python not found! Please install Python 3.10+"
    exit 1
fi

check_command node "Node.js" NODE_VERSION || { print_error "Node.js not found! Install from https://nodejs.org"; exit 1; }
check_command npm "npm" NPM_VERSION || { print_error "npm not found!"; exit 1; }
check_command git "Git" GIT_VERSION || print_warn "Git not found - some features may not work"
check_command docker "Docker" DOCKER_VERSION || print_warn "Docker not found - containerized deployment unavailable"
check_command docker-compose "Docker Compose" COMPOSE_VERSION || print_warn "Docker Compose not found"
check_command ffmpeg "FFmpeg" FFMPEG_VERSION || print_warn "FFmpeg not found - video processing may fail (install from https://ffmpeg.org)"

# ============================================================================
# Environment File
# ============================================================================
print_step "Setting Up Environment Configuration"

if [[ ! -f "$PROJECT_ROOT/.env" ]]; then
    if [[ -f "$PROJECT_ROOT/.env.example" ]]; then
        cp "$PROJECT_ROOT/.env.example" "$PROJECT_ROOT/.env"
        print_ok "Created .env from .env.example"
    else
        print_warn ".env.example not found, creating basic .env"
        cat > "$PROJECT_ROOT/.env" << 'ENVEOF'
# TruthLens AI Environment Configuration
DEBUG=true
APP_NAME="TruthLens AI"
APP_VERSION="1.0.0"
HOST=0.0.0.0
PORT=8000
CORS_ORIGINS=["http://localhost:3000","http://localhost:5173"]
MODEL_DIR=./models
REDIS_URL=redis://localhost:6379/0
LOG_LEVEL=INFO
ENVEOF
        print_ok "Created basic .env"
    fi
else
    print_info ".env already exists, skipping"
fi

# ============================================================================
# Backend Setup
# ============================================================================
print_step "Setting Up Backend (Python/FastAPI)"

cd "$BACKEND_DIR"

if [[ ! -d "$VENV_DIR" ]]; then
    print_info "Creating Python virtual environment..."
    $PYTHON_CMD -m venv "$VENV_DIR"
    print_ok "Virtual environment created"
else
    print_info "Virtual environment already exists"
fi

print_info "Activating virtual environment and upgrading pip..."
source "$VENV_DIR/bin/activate"
pip install --upgrade pip setuptools wheel >/dev/null
print_ok "Pip upgraded"

print_info "Installing backend dependencies..."
pip install -r requirements.txt
print_ok "Backend dependencies installed"

# Dev dependencies
read -p "Install development dependencies (pytest, black, mypy, etc.)? [y/N] " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    pip install -r requirements-dev.txt
    print_ok "Development dependencies installed"
fi

print_info "Downloading spaCy English model..."
python -m spacy download en_core_web_sm >/dev/null 2>&1 && print_ok "spaCy model downloaded" || print_warn "Failed to download spaCy model (will download on first use)"

mkdir -p "$MODELS_DIR"
print_ok "Models directory ready"

# ============================================================================
# LLM Setup (Qwen3-4B-Instruct-2507, Q8_0 GGUF via llama.cpp)
# ============================================================================
print_step "Setting Up Local LLM (Qwen3-4B Q8_0, ~4 GB)"

print_info "Installing llama-cpp-python (CUDA build when available)..."
CMAKE_ARGS="" pip install llama-cpp-python==0.3.36 --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cu124 >/dev/null 2>&1 \
    && print_ok "llama-cpp-python installed (CUDA)" \
    || {
        pip install llama-cpp-python >/dev/null 2>&1 \
            && print_ok "llama-cpp-python installed (CPU build)" \
            || print_warn "Failed to install llama-cpp-python - LLM features disabled"
    }

print_info "Downloading Qwen3-4B-Instruct-2507 Q8_0 into backend/models/llm/ ..."
python "$BACKEND_DIR/download_llm.py" \
    && print_ok "Qwen3-4B (Q8_0) ready in the project models folder" \
    || print_warn "LLM download incomplete - scanning still works without it. Re-run setup.sh later."

deactivate

# ============================================================================
# Frontend Setup
# ============================================================================
print_step "Setting Up Frontend (React/TypeScript/Vite)"

cd "$FRONTEND_DIR"

if [[ ! -d "node_modules" ]]; then
    print_info "Installing frontend dependencies..."
    npm install
    print_ok "Frontend dependencies installed"
else
    print_info "node_modules exists, updating..."
    npm install
    print_ok "Frontend dependencies up to date"
fi

print_info "Verifying frontend build..."
npm run build >/dev/null 2>&1 && print_ok "Frontend builds successfully" || print_warn "Frontend build check failed (may still work in dev mode)"

# ============================================================================
# Pre-commit Hooks
# ============================================================================
print_step "Setting Up Pre-commit Hooks"

cd "$BACKEND_DIR"
source "$VENV_DIR/bin/activate"
pip install pre-commit >/dev/null 2>&1 && pre-commit install >/dev/null 2>&1 && print_ok "Pre-commit hooks installed" || print_warn "Could not install pre-commit hooks"
deactivate

# ============================================================================
# Verification
# ============================================================================
print_step "Verifying Installation"

cd "$BACKEND_DIR"
source "$VENV_DIR/bin/activate"

print_info "Testing backend imports..."
python -c "
import fastapi, uvicorn, torch, cv2, numpy as np, mediapipe, transformers, spacy
print('All core imports successful')
print(f'PyTorch: {torch.__version__}')
print(f'OpenCV: {cv2.__version__}')
print(f'CUDA available: {torch.cuda.is_available()}')
if torch.cuda.is_available():
    print(f'GPU: {torch.cuda.get_device_name(0)}')
" && print_ok "Backend imports working" || print_error "Backend import test failed"

deactivate

# ============================================================================
# Summary
# ============================================================================
echo -e "\n${CYAN}=====================================================================${RESET}"
echo -e "${CYAN}  Setup Complete!${RESET}"
echo -e "${CYAN}=====================================================================${RESET}\n"

print_ok "TruthLens AI has been set up successfully!"
echo
echo "Next steps:"
echo "  1. Review configuration:    nano .env"
echo "  2. Run the project:         ./run.sh"
echo "  3. Or use Docker:           docker-compose up -d"
echo
echo "Access points (after running):"
echo "  - Frontend:                 http://localhost:5173"
echo "  - Backend API:              http://localhost:8000"
echo "  - API Documentation:        http://localhost:8000/docs"
echo "  - Health Check:             http://localhost:8000/api/v1/health"
echo
echo "Useful commands:"
echo "  - Backend tests:            cd backend && ../venv/bin/activate && pytest"
echo "  - Frontend tests:           cd frontend && npm test"
echo "  - Lint backend:             cd backend && ../venv/bin/activate && ruff check ."
echo "  - Format backend:           cd backend && ../venv/bin/activate && black ."
echo
echo -e "${CYAN}Happy detecting! 🔍${RESET}"