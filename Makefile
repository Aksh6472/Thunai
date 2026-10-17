# Thunai — developer commands (CLAUDE.md §11). Run from the repo root.
# Ports come from .env (THUNAI_API_PORT / THUNAI_DB_PORT) so they can avoid clashes with other projects.

SHELL := /bin/bash
envval = $(shell grep -E '^$(1)=' .env 2>/dev/null | head -1 | cut -d= -f2- | sed -E 's/[[:space:]]+\#.*$$//; s/[[:space:]]+$$//')
API_PORT := $(or $(call envval,THUNAI_API_PORT),8000)

.PHONY: help db db-down dev frontend-env test test-backend test-frontend lint format \
        migrate seed demo demo-reset eval e2e security

help:
	@echo "make db | db-down | dev | test | lint | format    (available now)"
	@echo "make migrate | seed | demo | demo-reset | eval | e2e | security    (added by later tasks)"

db:
	docker compose up -d --wait db

db-down:
	docker compose down

frontend-env:
	@grep -E '^VITE_' .env > frontend/.env 2>/dev/null || (echo "Missing .env — run: cp .env.example .env" && exit 1)

dev: frontend-env
	@trap 'kill 0' EXIT; \
	(cd backend && uv run uvicorn app.main:app --reload --port $(API_PORT)) & \
	(cd frontend && npm run dev) & \
	wait

test: test-backend test-frontend

test-backend:
	cd backend && uv run pytest

test-frontend:
	cd frontend && npx vitest run

lint:
	cd backend && uv run ruff check . && uv run ruff format --check . && uv run mypy
	cd frontend && npm run -s lint && npm run -s typecheck && npm run -s format:check

format:
	cd backend && uv run ruff format . && uv run ruff check --fix .
	cd frontend && npm run -s format

# ---- Added by later tasks; fail loudly until then (CLAUDE.md §11) ----
migrate:
	@echo "Not implemented yet: T-008 (Alembic)"; exit 1
seed:
	@echo "Not implemented yet: T-009 / T-022 (sim.seed)"; exit 1
demo:
	@echo "Not implemented yet: T-047"; exit 1
demo-reset:
	@echo "Not implemented yet: T-021"; exit 1
eval:
	@echo "Not implemented yet: T-030"; exit 1
e2e:
	@echo "Not implemented yet: T-044"; exit 1
security:
	@echo "Not implemented yet: T-045"; exit 1
