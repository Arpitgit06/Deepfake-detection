#!/bin/bash
# ============================================================================
# TruthLens AI - Project Launch Script (Linux/macOS)
# ============================================================================
# This script launches the TruthLens AI development servers
# Run with: bash run.sh [options]
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

print_info() { echo -e "${BLUE}[INFO]${RESET} $1"; }
print_ok() { echo -e "${GREEN}[OK]${RESET} $1"; }
print_warn() { echo -e "${YELLOW}[WARN]${RESET} $1"; }
print_error() { echo -e "${RED}[ERROR]${RESET} $1"; }
print_step() { echo -e "\n${MAGENTA}=====================================================================${RESET}"; echo -e "${MAGENTA}  $1${RESET}"; echo -e "${MAGENTA}=====================================================================${RESET}\n"; }

# Default options
MODE="dev"
USE_DOCKER=false
BACKEND_ONLY=false
FRONTEND_ONLY=false
SKIP_HEALTH_CHECK=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --docker) USE_DOCKER=true; shift ;;
        --prod) MODE="prod"; shift ;;
        --backend-only) BACKEND_ONLY=true; shift ;;
        --frontend-only) FRONTEND_ONLY=true; shift ;;
        --skip-health) SKIP_HEALTH_CHECK=true; shift ;;
        --help)
            echo "Usage: $0 [options]"
            echo ""
            echo "Options:"
            echo "  --docker            Run using Docker Compose"
            echo "  --prod              Run in production mode (with Docker)"
            echo "  --backend-only      Run only the backend server"
            echo "  --frontend-only     Run only the frontend server"
            echo "  --skip-health       Skip backend health check"
            echo "  --help              Show this help"
            echo ""
            echo "Examples:"
            echo "  $0                       # Runs both frontend and backend in dev mode"
            echo "  $0 --docker              # Runs with Docker Compose (dev)"
            echo "  $0 --docker --prod       # Runs production stack with Docker"
            echo "  $0 --backend-only        # Runs only backend API"
            exit 0
            ;;
        *) print_error "Unknown option: $1"; exit 1 ;;
    esac
done

# Header
echo -e "${CYAN}"
cat << 'EOF'
╔═══════════════════════════════════════════════════════════════════════════╗
║                    TruthLens AI - Launch                                 ║
║              Deepfake & Scam Detection Platform                          ║
╚═══════════════════════════════════════════════════════════════════════════╝
EOF
echo -e "${RESET}"

# ============================================================================
# Docker Mode
# ============================================================================
if [[ "$USE_DOCKER" == "true" ]]; then
    print_step "Starting with Docker Compose"
    
    if [[ "$MODE" == "prod" ]]; then
        print_info "Starting production stack..."
        docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
    else
        print_info "Starting development stack..."
        docker-compose up -d --build
    fi
    
    if [[ $? -ne 0 ]]; then
        print_error "Docker Compose failed"
        exit 1
    fi
    
    print_ok "Docker services started"
    echo
    echo "Services running:"
    echo "  - Frontend: http://localhost:5173"
    echo "  - Backend:  http://localhost:8000"
    echo "  - API Docs: http://localhost:8000/docs"
    echo "  - Redis:    localhost:6379"
    echo
    echo "View logs: docker-compose logs -f"
    echo "Stop:      docker-compose down"
    exit 0
fi

# ============================================================================
# Local Development Mode
# ============================================================================
print_step "Starting Local Development Servers"

# Check virtual environment
if [[ ! -d "$VENV_DIR" ]]; then
    print_error "Virtual environment not found! Run ./setup.sh first"
    exit 1
fi

# Check frontend dependencies
if [[ ! -d "$FRONTEND_DIR/node_modules" ]]; then
    print_error "Frontend dependencies not installed! Run ./setup.sh first"
    exit 1
fi

# Function to check if port is in use
check_port() {
    local port=$1
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
        print_warn "Port $port is already in use"
        return 1
    fi
    return 0
}

# Check ports
BACKEND_PORT_FREE=0
FRONTEND_PORT_FREE=0
check_port 8000 || BACKEND_PORT_FREE=1
check_port 5173 || FRONTEND_PORT_FREE=1

if [[ $BACKEND_PORT_FREE -eq 1 && "$FRONTEND_ONLY" == "false" ]]; then
    print_warn "Backend port 8000 is busy. Backend may fail to start."
fi
if [[ $FRONTEND_PORT_FREE -eq 1 && "$BACKEND_ONLY" == "false" ]]; then
    print_warn "Frontend port 5173 is busy. Frontend may fail to start."
fi
echo

# Trap for cleanup
BACKEND_PID=""
FRONTEND_PID=""
cleanup() {
    echo -e "\n${YELLOW}[INFO] Shutting down servers...${RESET}"
    [[ -n "$BACKEND_PID" ]] && kill $BACKEND_PID 2>/dev/null || true
    [[ -n "$FRONTEND_PID" ]] && kill $FRONTEND_PID 2>/dev/null || true
    # Kill any child processes
    pkill -P $$ 2>/dev/null || true
    exit 0
}
trap cleanup INT TERM EXIT

# ============================================================================
# Start Backend
# ============================================================================
if [[ "$FRONTEND_ONLY" == "false" ]]; then
    print_step "Starting Backend (FastAPI)"
    
    cd "$BACKEND_DIR"
    source "$VENV_DIR/bin/activate"
    
    # Load environment variables
    if [[ -f "$PROJECT_ROOT/.env" ]]; then
        print_info "Loading environment variables..."
        set -a
        source "$PROJECT_ROOT/.env"
        set +a
    fi
    
    print_ok "Starting backend on http://localhost:8000"
    print_info "API docs available at http://localhost:8000/docs"
    echo
    
    uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 --log-level info &
    BACKEND_PID=$!
    
    deactivate
    cd "$PROJECT_ROOT"
    
    # Wait for backend to start
    print_info "Waiting for backend to start..."
    sleep 3
    
    # Health check
    if [[ "$SKIP_HEALTH_CHECK" == "false" ]]; then
        print_info "Checking backend health..."
        HEALTH_OK=false
        for i in {1..15}; do
            if curl -s -f http://localhost:8000/api/v1/health >/dev/null 2>&1; then
                HEALTH_OK=true
                break
            fi
            sleep 1
        done
        if [[ "$HEALTH_OK" == "true" ]]; then
            print_ok "Backend health check passed"
        else
            print_warn "Backend health check timeout (may still be starting)"
        fi
    fi
    echo
fi

# ============================================================================
# Start Frontend
# ============================================================================
if [[ "$BACKEND_ONLY" == "false" ]]; then
    print_step "Starting Frontend (Vite + React)"
    
    cd "$FRONTEND_DIR"
    
    print_ok "Starting frontend on http://localhost:5173"
    echo
    
    npm run dev -- --host 0.0.0.0 --port 5173 &
    FRONTEND_PID=$!
    
    cd "$PROJECT_ROOT"
    echo
fi

# ============================================================================
# Summary
# ============================================================================
echo -e "${CYAN}=====================================================================${RESET}"
echo -e "${CYAN}  Servers Started!${RESET}"
echo -e "${CYAN}=====================================================================${RESET}\n"

if [[ "$FRONTEND_ONLY" == "false" ]]; then
    echo "  Backend API:        http://localhost:8000"
    echo "  API Docs (Swagger): http://localhost:8000/docs"
    echo "  API Docs (ReDoc):   http://localhost:8000/redoc"
    echo "  Health Check:       http://localhost:8000/api/v1/health"
    echo
fi

if [[ "$BACKEND_ONLY" == "false" ]]; then
    echo "  Frontend App:       http://localhost:5173"
    echo
fi

echo -e "${YELLOW}Press Ctrl+C to stop all servers...${RESET}\n"

# Wait for processes
wait $BACKEND_PID $FRONTEND_PID