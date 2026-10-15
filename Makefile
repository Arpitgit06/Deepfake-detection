# Makefile for TruthLens AI Development

.PHONY: help install dev test lint format clean docker-build docker-up docker-down

help: ## Show this help message
	@echo "TruthLens AI - Development Commands"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# Backend commands
backend-install: ## Install backend dependencies
	cd backend && pip install -r requirements.txt

backend-dev-install: ## Install backend with dev dependencies
	cd backend && pip install -e ".[dev]"

backend-test: ## Run backend tests
	cd backend && pytest -v

backend-test-cov: ## Run backend tests with coverage
	cd backend && pytest --cov=app --cov-report=html --cov-report=term

backend-lint: ## Run backend linting
	cd backend && ruff check . && black --check . && isort --check-only .

backend-format: ## Format backend code
	cd backend && black . && isort .

backend-serve: ## Run backend development server
	cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Frontend commands
frontend-install: ## Install frontend dependencies
	cd frontend && npm install

frontend-test: ## Run frontend tests
	cd frontend && npm test

frontend-test-ui: ## Run frontend tests with UI
	cd frontend && npm test -- --ui

frontend-lint: ## Run frontend linting
	cd frontend && npm run lint

frontend-format: ## Format frontend code
	cd frontend && npx prettier --write .

frontend-serve: ## Run frontend development server
	cd frontend && npm run dev

frontend-build: ## Build frontend for production
	cd frontend && npm run build

# Combined commands
install: backend-install frontend-install ## Install all dependencies

dev: ## Start both frontend and backend dev servers
	docker-compose up -d redis && \
	cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 & \
	cd frontend && npm run dev

test: backend-test frontend-test ## Run all tests

lint: backend-lint frontend-lint ## Run all linting

format: backend-format frontend-format ## Format all code

# Docker commands
docker-build: ## Build all Docker images
	docker-compose build

docker-build-nocache: ## Build Docker images without cache
	docker-compose build --no-cache

docker-up: ## Start all services
	docker-compose up -d

docker-down: ## Stop all services
	docker-compose down

docker-logs: ## View logs from all services
	docker-compose logs -f

docker-restart: ## Restart all services
	docker-compose restart

docker-clean: ## Clean up Docker resources
	docker-compose down -v --remove-orphans
	docker system prune -f

# Database/Model commands
download-models: ## Download required models (placeholder)
	@echo "Model download not implemented yet. Add your model download scripts here."

# Cleanup
clean: ## Clean build artifacts
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "node_modules" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "dist" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "build" -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true
	find . -name ".coverage" -delete 2>/dev/null || true

# Pre-commit
pre-commit-install: ## Install pre-commit hooks
	cd backend && pre-commit install

pre-commit-run: ## Run pre-commit on all files
	cd backend && pre-commit run --all-files