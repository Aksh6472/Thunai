# Thunai — Technology Stack

**Selection principle:** use the smallest stack that (1) the team already knows (Python, SQL, React, Node), (2) can produce a reliable offline demo in 24–48 h, and (3) can grow into a production system without a rewrite. Nothing is here because it is popular.

> **Versions.** Majors are pinned below. At setup (T-002/T-003), install the latest patch of each major, then **commit the lockfiles** (`uv.lock`, `package-lock.json`). Nobody upgrades a major during the hackathon. If a listed major is unavailable or broken, record the substitute in [DECISIONS.md](DECISIONS.md).

## 1. Runtime requirements

| Tool | Version | Check |
|---|---|---|
| Python | 3.12.x, **managed by uv** (`uv python install 3.12`, pinned in `backend/.python-version`). The system Python version doesn't matter | `uv run python --version` |
| uv (Python package/venv manager) | ≥ 0.5 (verified with 0.13.1) | `uv --version` |
| Node.js | ≥ 22 (22 or 24 LTS recommended; verified with 26.8.1). Set in `frontend/package.json` `engines` | `node --version` |
| npm | Bundled with Node 22 | `npm --version` |
| Docker Desktop / Engine with Compose v2 | Current | `docker compose version` |
| Git | ≥ 2.40 | `git --version` |

Install (macOS):
```bash
brew install uv node@22 git
brew install --cask docker
```

## 2. Backend

| Concern | Choice | Version | Why | Alternatives considered | Trade-off |
|---|---|---|---|---|---|
| Language | Python | 3.12 | The team knows it. Good for data, scoring and simulation. Pydantic gives type safety | Node/TypeScript (one language end to end, but weaker data tooling); Java/Spring (slow to scaffold) | Two languages in the repo |
| Web framework | FastAPI | 0.115+ (latest 0.x) | Async, Pydantic-native validation, automatic OpenAPI (which drives frontend types), dependency injection for auth | Flask (no built-in validation or OpenAPI); Django (heavier, its ORM conflicts with our layering) | Pre-1.0 versioning, so pin it |
| Validation / settings | Pydantic v2, pydantic-settings | 2.x | One schema system for API, config and simulator payloads | marshmallow | — |
| ORM | SQLAlchemy | 2.0.x | Typed `Mapped[]`, explicit SQL control, `FOR UPDATE` support | SQLModel (thinner but less mature); raw SQL (no migrations story) | Verbose models |
| Migrations | Alembic | 1.x | The standard for SQLAlchemy | — | Autogenerate misses CHECK constraints, so review by hand |
| DB driver | psycopg | 3.x (`psycopg[binary]`) | Modern, sync and async, works well with SQLAlchemy 2 | asyncpg (async only, more complex sessions) | Sync sessions in a threadpool, which is fine at this scale |
| ASGI server | uvicorn | latest | Standard | gunicorn+uvicorn workers (not needed) | Run a single worker, because the in-memory rate limiter assumes one |
| Auth | PyJWT plus argon2-cffi | latest | HS256 JWTs and argon2id password hashes. No external IdP is needed for a demo | Auth0 / Keycloak / Supabase Auth (network dependency and setup time); FastAPI-Users (more than we need) | We own the token logic, so test it (T-010) |
| PII encryption | `cryptography` (Fernet) | latest | Encrypts trusted-contact phone numbers at rest | pgcrypto (moves keys into SQL) | Key management is via environment variables in the MVP |
| HTTP client | httpx | latest | Simulator, Twilio/Telegram, tests (`ASGITransport`) | requests (sync only) | — |
| YAML | PyYAML | latest | Scoring config, scenarios, scripts | TOML (less readable for nested tables) | Always use `safe_load` |
| LLM SDK (optional) | anthropic (official Python SDK) | latest | FR-21 narrative drafting. Structured outputs | Other providers (not needed) | External dependency. It is behind a flag with a template fallback |
| Notifications (optional) | Twilio REST via httpx. Telegram Bot API via httpx | — | Twilio's own guidance says international-route SMS to India does not need DLT (to be verified with a trial). Telegram is free and instant | Indian SMS gateways (MSG91, Fast2SMS) need DLT template registration, which can't be done in 48 h | Trial limits: Twilio sends only to verified numbers. Telegram needs the contact to start the bot first |

**Deliberately not used:** Celery/RQ/Redis (no queue needed, see ARCHITECTURE §6), Kafka (no streaming volume), pandas in the request path (pure Python is faster for small per-customer data; pandas is fine in `sim/evaluate.py`), scikit-learn in the MVP (only for FR-26, Could Have).

## 3. Frontend

| Concern | Choice | Version | Why | Alternatives | Trade-off |
|---|---|---|---|---|---|
| Framework | React | 19.x | The team knows it | Vue/Svelte (relearning) | — |
| Language | TypeScript | 5.9.x, `strict: true`. **Pinned below 6**, because openapi-typescript 7 requires TS 5 (ADR-017) | Type safety, plus types generated from OpenAPI | JS | Small setup cost |
| Build/dev | Vite | latest major at setup (`npm create vite@latest`, template `react-ts`) | Fast HMR, simple config | Next.js (SSR not needed; adds server concerns) | SPA only |
| Routing | React Router | 8.x (library mode: `createBrowserRouter`) | Standard | TanStack Router | — |
| Server state | TanStack Query | 5.x | Polling (`refetchInterval`), caching, retries, loading and error states for free | SWR; hand-rolled fetch | — |
| API types | openapi-typescript (dev dependency) | 7.x | `src/api/schema.d.ts` generated from `/openapi.json`, which prevents contract drift | Hand-written types | Regenerate after any API change |
| Styling | Tailwind CSS | 4.x with CSS-variable design tokens | Fast to build. Tokens in `src/styles/tokens.css` ([DESIGN.md](DESIGN.md) §7) | CSS modules; MUI (heavy, generic look) | Utility-class noise |
| Components | Our own small primitives (Button, Badge, Card, Dialog, Toast…) | — | Avoids a big UI dependency. About 12 components | shadcn/ui (acceptable if the team prefers; copy only what we need) | Some build time |
| Charts | Recharts | 3.x | Score-history step line and stage timeline | Chart.js, visx | Bundle size, which is fine |
| i18n | Our own `t(key)` with `en.json` / `ta.json` | — | Two languages and fewer than 200 strings | i18next (more than we need) | No pluralisation engine |
| Fonts | Inter and Noto Sans Tamil (self-hosted via `@fontsource`) | latest | Offline-safe and proper Tamil rendering | Google Fonts CDN (breaks offline) | — |

## 4. Data and AI

| Concern | Choice | Why |
|---|---|---|
| Risk engine | Pure-Python domain module plus a YAML config | Explainable and deterministic ([AI_DESIGN.md](AI_DESIGN.md) §2) |
| Synthetic data | Python `random.Random(seed)` with scenario YAML | Reproducible and publishable |
| Evaluation | Python plus pandas (offline only), with a Markdown/JSON report | Familiar to the team (Big Data background) |
| LLM | Claude via the official SDK, `claude-opus-5-5` (configurable), off by default | Not on the decision path |
| Optional calibration (FR-26) | scikit-learn `LogisticRegression` | Only if time allows. Compared against the hand-set weights |

## 5. Database

PostgreSQL 16 in Docker (`postgres:16-alpine`). It provides JSONB for reasons and evidence, partial unique indexes (one open episode per customer), `FOR UPDATE`, and real concurrency for the parallel simulator, UI and tests. SQLite was rejected because of its concurrency limits and because it lacks partial-index and JSONB support at parity ([DECISIONS.md](DECISIONS.md) ADR-003).

## 6. Storage, background jobs and external integrations

| Concern | Decision |
|---|---|
| File / object storage | **None needed.** Reports are text in the DB, and the evaluation reports are files in `reports/` |
| Background jobs | FastAPI `BackgroundTasks` for notifications, plus an asyncio task for demo runs. No queue |
| DoT FRI | `MockFriClient` backed by the `fri_mock_ratings` table (**simulated**). A real integration would be through DIP, which is not publicly available |
| Phone call signal | Simulated by the replayer via `/signals/call` |
| 1930 / cybercrime.gov.in | **No API integration.** We produce a draft to copy, plus `tel:1930` and portal links |

## 7. Testing and quality

| Concern | Tool |
|---|---|
| Python tests | pytest 8, pytest-cov, httpx `ASGITransport` for API tests |
| Python lint/format | ruff (lint and format) |
| Python types | mypy (strict on `app/domain`, normal elsewhere) |
| Frontend unit/component | Vitest plus React Testing Library |
| Frontend lint/format | oxlint (ships with the Vite 8 template; replaces ESLint, see ADR-017) plus Prettier |
| E2E | Playwright (Chromium) |
| Dependency audit | `uv run pip-audit` and `npm audit --omit=dev` |
| Secret scanning | gitleaks (pre-commit or CI) |
| Load check | A small `httpx` async script (`sim/bench.py`) for NFR-01. No k6/Locust needed |

## 8. Deployment and monitoring

| Concern | Choice | Why |
|---|---|---|
| Primary demo | **Local laptop:** Docker Postgres, uvicorn and the Vite build served by `vite preview` | Works offline. No cold starts |
| Hosted (Should, FR-29) | Backend and Postgres on Render (or Railway), frontend on Vercel | Free or cheap tiers, git-based deploys. Expect cold starts, so never use it as the primary demo |
| Phone reachability for the trusted-contact link | Same Wi-Fi/hotspot LAN IP, or a `cloudflared` quick tunnel | No deploy needed for the demo |
| Logs | Structured JSON to stdout with a request id | Ready for any log drain |
| Monitoring | `/healthz` and `/readyz`. Platform metrics on Render | Enough for the hackathon |

## 9. Package management strategy

- **Python:** `uv` manages the virtualenv and lockfile. `uv add <pkg>` / `uv add --dev <pkg>`, and `uv sync --frozen` in CI and in Docker.
- **Node:** `npm`. `npm ci` in CI. No pnpm or yarn, to keep one less tool to learn.
- **New dependency rule:** before adding a package, check that the stack can't already do it, write one line in the PR saying why, and prefer packages with recent releases and no install scripts ([CLAUDE.md](CLAUDE.md) §8).

## 10. Installation commands (after scaffolding in T-001 to T-004)

```bash
# Backend
cd backend
uv sync
uv run alembic upgrade head

# Frontend
cd ../frontend
npm ci

# Initial scaffolding (only once, in T-002/T-003)
uv init --app backend && cd backend && \
  uv add fastapi "uvicorn[standard]" pydantic pydantic-settings "sqlalchemy>=2,<3" alembic "psycopg[binary]" \
         pyjwt argon2-cffi cryptography httpx pyyaml && \
  uv add --dev pytest pytest-cov ruff mypy pip-audit pandas types-PyYAML
uv add anthropic          # only when FR-21 starts

npm create vite@latest frontend -- --template react-ts && cd frontend && \
  npm i react-router @tanstack/react-query recharts @fontsource/inter @fontsource/noto-sans-tamil && \
  npm i -D tailwindcss @tailwindcss/vite openapi-typescript vitest @testing-library/react @testing-library/user-event jsdom \
           @playwright/test prettier      # oxlint comes with the template; pin typescript@~5.9.3
```
