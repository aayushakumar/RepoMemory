.PHONY: install dev dev-frontend dev-all test test-frontend test-all lint index bench clean

install:
	cd backend && pip install -e ".[dev]"
	cd frontend && npm install

dev:
	cd backend && uvicorn repomemory.api.app:app --reload --host 0.0.0.0 --port 8000

dev-frontend:
	cd frontend && npm run dev

dev-all:
	@echo "Starting backend on :8000 and frontend on :5173..."
	@cd backend && uvicorn repomemory.api.app:app --reload --host 0.0.0.0 --port 8000 &
	@cd frontend && npm run dev

test:
	cd backend && python -m pytest tests/ -v

test-frontend:
	cd frontend && npm test

test-all:
	cd backend && python -m pytest tests/ -v
	cd frontend && npm test

lint:
	cd backend && ruff check src/ tests/
	cd backend && ruff format --check src/ tests/

format:
	cd backend && ruff format src/ tests/

index:
	@if [ -z "$(REPO)" ]; then echo "Usage: make index REPO=/path/to/repo"; exit 1; fi
	cd backend && python -m repomemory.cli index "$(REPO)"

bench:
	cd backend && python -m repomemory.evaluation.benchmark

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	rm -rf backend/.pytest_cache
