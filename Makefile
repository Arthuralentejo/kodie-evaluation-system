SHELL := /bin/bash

BACKEND_DIR := backend
FRONTEND_DIR := frontend

.PHONY: help install install-backend install-frontend dev-backend dev-frontend dev build build-backend build-frontend test test-backend test-frontend etl clean clean-backend clean-frontend

help:
	@echo "Available targets:"
	@echo "  install           Install backend + frontend dependencies"
	@echo "  install-backend   Install backend dependencies via Poetry"
	@echo "  install-frontend  Install frontend dependencies via npm"
	@echo "  dev-backend       Run FastAPI with reload on :8000"
	@echo "  dev-frontend      Run Vite dev server"
	@echo "  dev               Run backend + frontend in parallel"
	@echo "  build             Build backend package + frontend assets"
	@echo "  build-backend     Build backend wheel/sdist via Poetry"
	@echo "  build-frontend    Build frontend assets"
	@echo "  test              Run backend + frontend tests"
	@echo "  test-backend      Run backend pytest suite"
	@echo "  test-frontend     Run frontend tests if package script exists"
	@echo "  etl               Run extraction script (scripts/extract.py)"
	@echo "  clean             Remove generated caches/artifacts"

install: install-backend install-frontend

install-backend:
	cd $(BACKEND_DIR) && poetry install

install-frontend:
	cd $(FRONTEND_DIR) && npm install

dev-backend:
	cd $(BACKEND_DIR) && poetry run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

dev-frontend:
	cd $(FRONTEND_DIR) && npm run dev

dev:
	@set -e; \
	( cd $(BACKEND_DIR) && poetry run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 ) & \
	BACK_PID=$$!; \
	( cd $(FRONTEND_DIR) && npm run dev ) & \
	FRONT_PID=$$!; \
	trap 'kill $$BACK_PID $$FRONT_PID 2>/dev/null || true' INT TERM EXIT; \
	wait $$BACK_PID $$FRONT_PID

build: build-backend build-frontend

build-backend:
	cd $(BACKEND_DIR) && poetry build

build-frontend:
	cd $(FRONTEND_DIR) && npm run build

test: test-backend test-frontend

test-backend:
	cd $(BACKEND_DIR) && poetry run pytest

test-frontend:
	cd $(FRONTEND_DIR) && if npm run | grep -q " test"; then npm test; else echo "No frontend test script found, skipping."; fi

etl:
	cd $(BACKEND_DIR) && poetry run python ../scripts/extract.py

clean: clean-backend clean-frontend

clean-backend:
	cd $(BACKEND_DIR) && rm -rf .pytest_cache dist build *.egg-info

clean-frontend:
	cd $(FRONTEND_DIR) && rm -rf dist node_modules/.vite