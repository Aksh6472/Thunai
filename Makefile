# Thunai — developer commands (CLAUDE.md §11). Run from the repo root.
# Ports come from .env (THUNAI_API_PORT / THUNAI_DB_PORT) so they can avoid clashes with other projects.

SHELL := /bin/bash
envval = $(shell grep -E '^$(1)=' .env 2>/dev/null | head -1 | cut -d= -f2- | sed -E 's/[[:space:]]+\#.*$$//; s/[[:space:]]+$$//')
API_PORT := $(or $(call envval,THUNAI_API_PORT),8000)

.PHONY: help db db-down dev frontend-env test test-backend test-frontend lint format \
        migrate seed demo demo-reset replay bench eval e2e security

help:
	@echo "make db | db-down | migrate | seed | dev | demo-reset | replay | test | lint | format"
	@echo "make demo | e2e | eval | bench | security"

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

migrate:
	cd backend && uv sync && uv run alembic upgrade head

seed:
	cd backend && uv run python -m sim.seed --seed 42

demo-reset:  # needs the API running (make dev / make demo)
	cd backend && uv run python -m sim.demo_reset

replay:  # make replay SCENARIO=P1 SPEED=4320 (API running)
	cd backend && uv run python -m sim.replay --scenario $(or $(SCENARIO),P1) --speed $(or $(SPEED),4320)

bench:  # NFR-01 latency check against the running API (make dev / make demo)
	cd backend && uv run python -m sim.bench --n 500 --concurrency 10

eval:  # synthetic evaluation on held-out seeds 100–299 → reports/eval/ (uses TEST_DATABASE_URL)
	cd backend && uv run python -m sim.evaluate --seeds 100-299 --out ../reports/eval/

lint:
	cd backend && uv run ruff check . && uv run ruff format --check . && uv run mypy
	cd frontend && npm run -s lint && npm run -s typecheck && npm run -s format:check

format:
	cd backend && uv run ruff format . && uv run ruff check --fix .
	cd frontend && npm run -s format

# ---- Added by later tasks; fail loudly until then (CLAUDE.md §11) ----
demo: frontend-env  # production-like local run (DEPLOYMENT.md §4): built SPA, 1 API worker, LAN-reachable
	docker compose up -d --wait db
	cd backend && uv run alembic upgrade head
	cd frontend && npm run build
	@trap 'kill 0' EXIT; \
	(cd backend && uv run uvicorn app.main:app --host 0.0.0.0 --port $(API_PORT) --workers 1) & \
	(cd frontend && npx vite preview --host 0.0.0.0 --port 5173) & \
	wait
e2e:  # Playwright against a test-DB stack on ports 8020/5180 (installed Chrome; PW_CHANNEL=chromium to override)
	cd frontend && npx playwright test
security:  # pip-audit, npm audit (prod deps), gitleaks over git history (Docker image, pinned)
	cd backend && uv run pip-audit
	cd frontend && npm audit --omit=dev
	docker run --rm -v "$(CURDIR):/repo" zricethezav/gitleaks:v8.24.3 git /repo --no-banner --redact
