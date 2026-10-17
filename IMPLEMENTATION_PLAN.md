# Thunai — Implementation Plan

> **Timing basis.** The team reported a 24–48 h hackathon. **The exact deadline is not yet confirmed.** All times below are hours from kickoff (H+0). The plan makes the **MVP complete and frozen by H+20**, so it fits a 24 h event. If the event is 48 h, the extra time goes to Should Have items ([ROADMAP.md](ROADMAP.md) §3), not to scope creep.

## 1. Strategy

1. **Freeze the contracts first (H+0–2).** The API ([API_SPEC.md](API_SPEC.md)), the schema ([DATABASE_SCHEMA.md](DATABASE_SCHEMA.md)) and the scoring table ([AI_DESIGN.md](AI_DESIGN.md) §6) are agreed before parallel work starts. Then the frontend can build against the OpenAPI output while the backend fills in the logic.
2. **Get the headless hero working by H+12.** The hero scenario P1 and the hard negative N1 must run end to end through the API with curl or tests before any UI polish.
3. **Golden tests drive the engine.** The worked examples in AI_DESIGN §6.4 are written as failing tests first (T-028).
4. **Every UI surface is driven by the real API.** No hard-coded demo screens.

## 2. Workstreams (assign names at kickoff)

| WS | Name | Owns | Suggested skills |
|---|---|---|---|
| WS1 | Data & Simulation | Generator, scenarios, replayer, evaluation, seed | Python, data (Big Data background) |
| WS2 | Risk Engine | `app/domain/*`, scoring config, reasons and i18n text, the LLM narrative | Python, careful logic |
| WS3 | Backend Platform | FastAPI app, DB, auth, services, notifier, API tests | Python, SQL |
| WS4 | Staff Frontend | Ops dashboard, hold detail, teller console, component library | React/TS |
| WS5 | Customer & Contact Frontend | Customer app simulator, trusted-contact page, i18n, demo panel | React/TS, Tamil reviewer |
| WS6 | Product, QA & Delivery | Repo/CI, E2E, security checks, deployment, demo script, pitch | Generalist / team lead |

With 5 people, merge WS5 into WS4 and WS6 into the team lead's role.

## 3. Phases and tasks

**Fields:** Objective · Files · Depends on · Steps · Acceptance · Tests · DoD · Priority · Effort · Owner.

**Priorities:** **P0** is on the critical path to the hero demo. **P1** is MVP Must. **P2** is Should. **P3** is Could.

**Owners** shown here are defaults. [TASKS.md](TASKS.md) holds the rebalanced, live assignments (see §4).

**Generic DoD** (applies to every task, from [CLAUDE.md](CLAUDE.md) §13): the code is merged to `main` through a PR, lint, types and tests pass, the docs touched by the change are updated, and there is no TODO without a task id.

### Phase 1 — Project initialisation

**T-001 Repository bootstrap**
- *Objective:* A clean repo that tooling can handle.
- *Files:* the root folder, `.gitignore`, `.gitattributes`, `Makefile`, `docker-compose.yml` (stub), `backend/`, `frontend/`, `reports/.gitkeep`.
- *Depends on:* none.
- *Steps:*
  1. **Rename the project folder to `thunai`.** The original name `Kaaval ` contained a trailing space, which breaks unquoted shell paths, Docker volume mounts and some tools. *(Done 2026-10-17: renamed to `kaaval-ai`, then to `thunai` with the product rename, ADR-019.)*
  2. `git init -b main`, add the docs, make the first commit.
  3. Create the GitHub repo and branch protection on `main` (PR required, one review).
  4. Write a `.gitignore` covering `.env`, `.venv`, `node_modules`, `dist`, `reports/eval/*.json` (keep `.md`), `playwright-report`, `__pycache__`.
  5. Write `Makefile` targets that call the subprojects: `dev`, `db`, `migrate`, `seed`, `test`, `lint`, `eval`, `demo-reset`, `e2e`.
- *Acceptance:* a fresh clone plus `make db` starts Postgres.
- *Tests:* none (infrastructure).
- *DoD:* the repo URL is shared and everyone has cloned it.
- *Priority / Effort / Owner:* P0 · 0.5 h · WS6.

**T-002 Backend scaffold**
- *Objective:* A runnable FastAPI app with quality tooling.
- *Files:* `backend/pyproject.toml`, `backend/app/main.py`, `backend/app/api/v1/health.py`, `backend/tests/test_health.py`, ruff/mypy configuration in `pyproject.toml`.
- *Depends on:* T-001.
- *Steps:* `uv init --app`, add the dependencies ([TECH_STACK.md](TECH_STACK.md) §10), create the app factory `create_app()`, mount `/api/v1`, add `/healthz`, configure ruff (rules `E,F,I,B,UP,S`), mypy (strict for `app.domain`) and pytest.
- *Acceptance:* `uv run uvicorn app.main:app` serves `GET /api/v1/healthz` with a 200 response.
- *Tests:* `test_health.py`.
- *DoD:* generic. `make lint test` is green.
- *Priority / Effort / Owner:* P0 · 1 h · WS3.

**T-003 Frontend scaffold**
- *Objective:* A Vite + React + TS app shell with routes, providers, Tailwind and tokens.
- *Files:* `frontend/` (from Vite), `src/app/routes.tsx`, `src/app/providers.tsx`, `src/styles/tokens.css`, `src/i18n/{en,ta}.json`, `src/i18n/t.ts`, ESLint and Prettier configs, `vitest.config.ts`.
- *Depends on:* T-001.
- *Steps:* scaffold the app, add the dependencies, set up a TanStack Query provider (default `retry: 2`), create placeholder routes for every path in [DESIGN.md](DESIGN.md) §3, add the tokens from DESIGN §7, configure the fonts via `@fontsource`.
- *Acceptance:* `npm run dev` shows the route placeholders. `npm run build`, `lint` and `typecheck` pass.
- *Tests:* one smoke test that renders `/login`.
- *DoD:* generic.
- *Priority / Effort / Owner:* P0 · 1.5 h · WS4.

**T-004 Local Postgres and env loading**
- *Objective:* `docker compose up -d db` gives a working database, and the backend reads `.env`.
- *Files:* `docker-compose.yml` (the `postgres:16-alpine` service, a healthcheck, the `thunai_test` DB created by an init script `infra/db/init.sql`), `.env.example` (already exists; keep it in sync).
- *Depends on:* T-001.
- *Steps:* write the compose service with a named volume, an init script that creates `thunai_test`, and port 5432.
- *Acceptance:* `psql` connects to both databases.
- *Tests:* `/readyz` reports `db: ok` after T-005.
- *DoD:* generic.
- *Priority / Effort / Owner:* P0 · 0.5 h · WS3.

### Phase 2 — Architecture and configuration

**T-005 Settings, logging and error envelope**
- *Objective:* Cross-cutting backend infrastructure.
- *Files:* `app/core/settings.py` (pydantic-settings, every variable in [ENVIRONMENT.md](ENVIRONMENT.md)), `app/core/logging.py` (JSON logs, request-id middleware, PII masking filter), `app/core/errors.py` (the `ThunaiError` hierarchy and handlers that produce the API_SPEC §2.1 envelope), `app/api/v1/health.py` (`/readyz`), body size limit middleware.
- *Depends on:* T-002, T-004.
- *Steps:*
  1. Define a typed `Settings` class.
  2. Validate at startup: required secrets present, placeholder secrets refused in production, and `DEMO_MODE` refused in production.
  3. Add the request-id middleware.
  4. Add the exception handlers, so that no stack trace is ever returned.
- *Acceptance:* a missing `THUNAI_JWT_SECRET` makes startup fail with a clear message. A 404 route returns the envelope.
- *Tests:* `tests/unit/test_settings.py`, `tests/integration/test_errors.py`, a log-masking test.
- *DoD:* generic.
- *Priority / Effort / Owner:* P0 · 2 h · WS3.

**T-006 Scoring config schema and loader**
- *Objective:* A versioned, validated `scoring_v1.yaml`.
- *Files:* `backend/config/scoring_v1.yaml`, `app/domain/config.py` (Pydantic model `ScoringConfig`).
- *Depends on:* T-002.
- *Steps:* encode AI_DESIGN §6.1–6.3 exactly: points, bands, tiers, overrides, the teller cap, windows (7 d episode, 72 h pooling), `min_high_value_paise=20000000`, `hold_floor_paise=5000000`. Compute `config_version = "<name>@<date>"`. Validate that thresholds increase monotonically.
- *Acceptance:* the loader rejects a config whose tier thresholds aren't increasing.
- *Tests:* `tests/unit/test_scoring_config.py`.
- *DoD:* generic. AI_DESIGN and the YAML match (reviewed by WS2 and WS6).
- *Priority / Effort / Owner:* P0 · 1 h · WS2.

**T-007 Clock abstraction**
- *Objective:* Injectable time, so multi-day scenarios can run in seconds.
- *Files:* `app/core/clock.py` (`Clock` Protocol, `RealClock`, `SimClock` backed by `sim_state`), a dependency in `app/api/deps.py`.
- *Depends on:* T-005, T-008 (for `sim_state`).
- *Steps:* `SimClock.now()` reads `sim_state.sim_now`. The replayer advances it via an internal service function. In demo mode the clock is selected by `THUNAI_DEMO_MODE`.
- *Acceptance:* the domain never calls `datetime.now()` (grep test).
- *Tests:* `tests/unit/test_clock.py`. The architecture test asserts there is no `datetime.now(` in `app/domain`.
- *DoD:* generic.
- *Priority / Effort / Owner:* P0 · 1 h · WS2.

### Phase 3 — Database and data model

**T-008 ORM models and initial migration**
- *Objective:* All tables in DATABASE_SCHEMA §3.
- *Files:* `app/models/*.py`, `app/db.py` (engine and session factory), `alembic.ini`, `migrations/env.py`, `migrations/versions/0001_initial.py`.
- *Depends on:* T-004, T-005.
- *Steps:*
  1. Write the typed models.
  2. Autogenerate the migration, then **add by hand** the CHECK constraints and partial unique indexes (`one open episode`, `one non-revoked trusted contact`) and the composite indexes.
  3. Write `downgrade()`.
- *Acceptance:* `alembic upgrade head`, then `alembic downgrade base`, then `upgrade head` all succeed.
- *Tests:* `tests/integration/test_migrations.py`. Constraint tests: inserting a second OPEN episode fails, and a negative amount fails.
- *DoD:* generic. The schema doc is updated if anything changed.
- *Priority / Effort / Owner:* P0 · 3 h · WS3.

**T-009 Staff and demo-customer seed**
- *Objective:* Seeded logins for every role.
- *Files:* `backend/sim/seed.py` (the staff part).
- *Depends on:* T-008, T-010 (for the password hasher).
- *Steps:*
  1. Create `teller.priya` (TELLER), `officer.rao` (OFFICER) and `admin.demo` (ADMIN), plus customer logins `cust.kamala` and `cust.iqbal`, all with the password from `THUNAI_SEED_PASSWORD`.
  2. Make the seed idempotent.
- *Acceptance:* every user can log in.
- *Tests:* covered by the T-010 tests.
- *DoD:* generic.
- *Priority / Effort / Owner:* P0 · 0.5 h · WS3.

### Phase 4 — Authentication and authorisation

**T-010 Auth: login, JWT, RBAC, service key**
- *Objective:* FR-19.
- *Files:* `app/core/security.py`, `app/api/v1/auth.py`, `app/api/deps.py` (`current_user`, `require_roles`, `require_service_key`), `app/core/rate_limit.py`.
- *Depends on:* T-005, T-008.
- *Steps:*
  1. Hash and verify with argon2id.
  2. Encode and decode JWTs with the algorithm pinned.
  3. Compare the service key in constant time (`hmac.compare_digest`).
  4. Add a fixed-window rate limiter keyed by IP, username or token.
  5. Write audit entries for `LOGIN_SUCCEEDED` / `LOGIN_FAILED`.
- *Acceptance:* AC-13. A wrong password gets a generic 401. The sixth failed attempt gets 429.
- *Tests:* `tests/integration/test_auth.py`, covering valid, invalid, expired, a wrong algorithm (`none`) and rate limiting.
- *DoD:* generic.
- *Priority / Effort / Owner:* P0 · 2.5 h · WS3.

**T-011 Frontend auth**
- *Objective:* The login page, token handling and route guards.
- *Files:* `src/app/auth.tsx` (context), `src/features/auth/LoginPage.tsx`, `src/api/client.ts` (fetch wrapper adding the bearer token, mapping the error envelope, logging out on 401).
- *Depends on:* T-003, T-010, T-032 (Button, inputs).
- *Steps:*
  1. Keep the token in memory and in `sessionStorage`.
  2. Guard routes by role.
  3. Redirect to the role's home after login.
- *Acceptance:* the TELLER lands on `/teller`. Visiting `/ops` as TELLER shows the 403 page.
- *Tests:* Vitest component tests for the guard. Login is covered by Playwright later.
- *DoD:* generic.
- *Priority / Effort / Owner:* P0 · 2 h · WS4.

### Phase 5 — Core backend

**T-012 Event and call-signal ingestion**
- *Objective:* FR-03, FR-06(b), NFR-08.
- *Files:* `app/api/v1/events.py`, `app/api/v1/signals.py`, `app/schemas/events.py` (a discriminated union by `event_type`, `extra="forbid"`), `app/services/ingest_service.py`, `app/repositories/events.py`.
- *Depends on:* T-008, T-010, T-026 (stage detection; stub it until ready).
- *Steps:*
  1. Insert idempotently on `event_id`.
  2. HMAC `linked_msisdn` and Fernet-encrypt the trusted-contact phone on receipt.
  3. Call stage detection and the episode update under `SELECT … FOR UPDATE`.
  4. For call signals, check consent, then store the signal and update the watch score.
  5. Return the API_SPEC response.
- *Acceptance:* AC-11 and AC-15 (events). Unknown fields on `/signals/call` get 422.
- *Tests:* `tests/integration/test_events.py`, `test_signals.py`.
- *DoD:* generic.
- *Priority / Effort / Owner:* P0 · 3 h · WS3.

**T-013 Transfer assessment orchestration**
- *Objective:* FR-09, NFR-09.
- *Files:* `app/api/v1/transfers.py`, `app/api/v1/customer.py` (`POST /customer/transfers`), `app/services/assessment_service.py`, `app/repositories/transfers.py`, `app/integrations/fri/{base,mock}.py`.
- *Depends on:* T-012, T-025, T-026, T-028, T-029.
- *Steps:*
  1. Run the idempotency check.
  2. Build `AssessmentInput` (baseline, episode, payee facts, signals, FRI with a 300 ms timeout).
  3. Score, then decide.
  4. Persist the transfer, the assessment (with `input_snapshot`) and the audit entry.
  5. Branch on the decision: ALLOW → EXECUTED, WARN → WARNED, HOLD → `hold_service.create_hold`.
  6. Return 503 on an unexpected error. Never fail open.
- *Acceptance:* AC-01 (decision part), AC-02, AC-03, AC-15 (transfers).
- *Tests:* `tests/integration/test_assess.py`, including the hero, N1, idempotent replay, a 409 conflict, an FRI timeout (mock raising) and the 503 path.
- *DoD:* generic.
- *Priority / Effort / Owner:* P0 · 3 h · WS3 with WS2.

**T-014 Hold lifecycle and officer decision**
- *Objective:* FR-11, FR-13.
- *Files:* `app/services/hold_service.py` (an explicit transition table, lazy cooling-off expiry, escalation only), `app/api/v1/holds.py`, `app/api/v1/customer.py` (cancel, warning-response).
- *Depends on:* T-013.
- *Steps:*
  1. Create the hold with its initial status per the DATABASE_SCHEMA §3.13 state machine.
  2. Resolve holds with officer decisions, with the note required.
  3. Let the customer cancel.
  4. Implement the warning response (continue or cancel).
  5. Move expired AWAITING_CONTACT holds to AWAITING_OFFICER whenever holds are read.
  6. On release, close the episode as benign. On an officer cancel, close it as confirmed risk.
- *Acceptance:* AC-06, AC-07, AC-10, plus 409 on an invalid transition.
- *Tests:* `tests/unit/test_hold_transitions.py` (table-driven), `tests/integration/test_holds.py`.
- *DoD:* generic.
- *Priority / Effort / Owner:* P0 · 3 h · WS3.

**T-015 Trusted-contact requests and responses**
- *Objective:* FR-12, plus the FR-24 backend rule.
- *Files:* `app/services/contact_service.py`, `app/api/v1/trusted.py`, `app/api/v1/customer.py` (trusted-contact registration).
- *Depends on:* T-014, T-016.
- *Steps:*
  1. Generate a token with `secrets.token_urlsafe(32)` and store its SHA-256.
  2. Build the link from `THUNAI_PUBLIC_WEB_URL/t/{token}`.
  3. Implement the activation check (`effective_from <= clock.now()`).
  4. Consume tokens with a conditional UPDATE.
  5. Apply the response matrix (API_SPEC §9).
  6. Return uniform 404/410 responses.
  7. Rate-limit, with a maximum of 3 resends per hour.
- *Acceptance:* AC-04, AC-05, AC-06, AC-07, AC-12.
- *Tests:* `tests/integration/test_trusted_contact.py`, covering expired, reused, a double-submit race (two concurrent POSTs → one 200 and one 410), and a contact inside the activation delay.
- *DoD:* generic.
- *Priority / Effort / Owner:* P0 · 3 h · WS3.

**T-016 Notifier abstraction**
- *Objective:* The FR-12 delivery mechanism (the console notifier is Must; real channels are FR-22).
- *Files:* `app/integrations/notifier/{base,console,twilio,telegram}.py`, `app/api/v1/demo.py` (`console-messages`).
- *Depends on:* T-005.
- *Steps:*
  1. Define a `Notifier.send(to, text) -> DeliveryResult` Protocol.
  2. Write `ConsoleNotifier`, which stores messages in memory (a ring buffer of 50) and logs a masked line.
  3. Write `TwilioNotifier` (httpx POST to the Messages API with a 5 s timeout).
  4. Write `TelegramNotifier` (`sendMessage`).
  5. Select with `THUNAI_NOTIFIER`. If a real channel fails, fall back to console and set `delivery_status=FAILED` with the error code.
- *Acceptance:* with `THUNAI_NOTIFIER=console`, the hero hold produces a message containing a working link.
- *Tests:* unit tests with httpx `MockTransport` for Twilio and Telegram (success, 4xx, timeout).
- *DoD:* generic.
- *Priority / Effort / Owner:* P0 (console) / P2 (real) · 2 h · WS3.

**T-017 Teller endpoints**
- *Objective:* FR-14, FR-06(c).
- *Files:* `app/api/v1/teller.py`, `app/domain/i18n/scripts.yaml`, `app/services/assessment_service.py` (`rescore`).
- *Depends on:* T-013, T-014.
- *Steps:*
  1. Build the queue query.
  2. Accept the checklist: store the signal, then re-score with `trigger=TELLER_CHECKLIST`.
  3. Apply escalation only: WARN → HOLD creates a hold, and HIGH → VERY_HIGH updates the hold tier and status to AWAITING_OFFICER.
  4. Serve the script by language.
- *Acceptance:* AC-08, plus the script half of AC-09.
- *Tests:* `tests/integration/test_teller.py`, covering escalation, a 409 after EXECUTED, and that `customer_said` doesn't change the score.
- *DoD:* generic. The Tamil script is reviewed (T-038).
- *Priority / Effort / Owner:* P0 · 2.5 h · WS3.

**T-018 Report draft (template)**
- *Objective:* FR-15.
- *Files:* `app/services/report_service.py`, `app/api/v1/reports.py`, `app/integrations/llm/template.py`.
- *Depends on:* T-014.
- *Steps:*
  1. Build the structured fields deterministically from the hold, transfer, payee and episode.
  2. Render the template narrative.
  3. Support PATCH for customer-reported fields and edits.
  4. Implement mark-filed.
- *Acceptance:* AC-09 (report part). The draft never contains a full account number.
- *Tests:* `tests/integration/test_reports.py`, plus a snapshot-free assertion that specific fields equal the DB values.
- *DoD:* generic.
- *Priority / Effort / Owner:* P1 · 2 h · WS3.

**T-019 Read APIs: alerts, dashboard, customers**
- *Objective:* FR-16 data.
- *Files:* `app/api/v1/{alerts,dashboard,customers}.py`, `app/repositories/queries.py`.
- *Depends on:* T-013, T-014.
- *Steps:*
  1. Implement cursor pagination.
  2. Build the unified alert queue (holds, warnings, and watchlist episodes with watch tier MEDIUM or above), sorted by urgency.
  3. Compute the summary counts.
  4. Build the customer risk and timeline views.
  5. Keep each endpoint at 5 queries or fewer (no N+1; use `selectinload`).
- *Acceptance:* the queue ordering matches DESIGN §5.2. Pagination is stable.
- *Tests:* `tests/integration/test_read_apis.py`.
- *DoD:* generic.
- *Priority / Effort / Owner:* P1 · 2.5 h · WS3.

**T-020 Audit log writer**
- *Objective:* FR-20.
- *Files:* `app/services/audit_service.py`.
- *Depends on:* T-008.
- *Steps:*
  1. Write `audit(action, entity, actor, details)` inside the caller's transaction.
  2. Scrub `details` with a deny-list (token, password, phone).
- *Acceptance:* every action listed in SECURITY §9 writes a row.
- *Tests:* `tests/integration/test_audit.py`, including the "no update or delete path exists" test.
- *DoD:* generic.
- *Priority / Effort / Owner:* P1 · 1 h · WS3.

**T-021 Demo control endpoints**
- *Objective:* FR-17 backend.
- *Files:* `app/api/v1/demo.py`, `sim/runner.py` (an asyncio task that drives the replayer).
- *Depends on:* T-024, T-007.
- *Steps:*
  1. Add the demo-mode guard.
  2. Reset: truncate the transactional tables in FK order, then run `seed(seed=42)` and reset `sim_state`.
  3. Implement run, the clock endpoint, the FRI upsert and console messages.
- *Acceptance:* AC-16.
- *Tests:* `tests/integration/test_demo.py`, including a 403 when demo mode is off.
- *DoD:* generic.
- *Priority / Effort / Owner:* P0 · 2 h · WS1.

### Phase 6 — Risk engine, data and AI

**T-022 Synthetic customer and history generator**
- *Objective:* FR-01 (background population).
- *Files:* `sim/generator.py`, `sim/models.py` (dataclasses), `sim/seed.py` (the population part).
- *Depends on:* T-008.
- *Steps:*
  1. Generate 50 customers with fictional names from a fixed list, accounts (SAVINGS and sometimes FD/RD/CURRENT), payees (2–12 each, with tenure) and 20–365 days of routine events (salary or pension credits, utility bills, family transfers), using a log-normal amount distribution per customer.
  2. Use `random.Random(seed)` everywhere and never the global RNG.
  3. Write the data directly to the DB (fast) and compute the baselines.
- *Acceptance:* seed 42 gives identical output on every run (hash of a canonical dump). It finishes in ≤ 10 s.
- *Tests:* `tests/sim/test_generator_determinism.py`.
- *DoD:* generic. The provenance is noted in [docs/DATA_SOURCES.md](docs/DATA_SOURCES.md).
- *Priority / Effort / Owner:* P0 · 3 h · WS1.

**T-023 Scenario families**
- *Objective:* FR-01 (labelled episodes P1–P7, N1–N6).
- *Files:* `sim/scenarios/P1_classic.yaml` … `N6_business.yaml`, `sim/scenarios/schema.py`.
- *Depends on:* T-022.
- *Steps:*
  1. Define each family as a list of steps `{day_offset, time, kind, params}`, plus randomisation ranges and the `expected` decision for golden seeds.
  2. Make the hero P1 use customer `CUST-0007`, ₹35 L FD, ₹11 L pooled, payee added 09:12 on day 3, RTGS ₹46 L at 11:20 at the branch, a 190 min video call on day 2, and payee number `+919800000193` rated FRI HIGH (simulated).
  3. Make N1 use `CUST-0012` (Mr. Iqbal).
- *Acceptance:* every family loads and validates. The golden expectations match AI_DESIGN §6.4.
- *Tests:* `tests/sim/test_scenarios_load.py`.
- *DoD:* generic. Every family cites its grounding in DATA_SOURCES.
- *Priority / Effort / Owner:* P0 (P1, N1) / P1 (others) · 3 h · WS1.

**T-024 Scenario replayer**
- *Objective:* FR-02.
- *Files:* `sim/replay.py` (CLI `python -m sim.replay --scenario P1 --speed 4320`), `sim/client.py` (an httpx client with the service key).
- *Depends on:* T-012, T-013, T-023.
- *Steps:*
  1. Merge the scenario steps with background noise in time order.
  2. Advance the sim clock, sleeping `Δsim / speed`.
  3. POST events, signals and transfers.
  4. For WARN in app scenarios, auto-respond according to the scenario script (coerced customers "continue").
  5. Retry idempotently on network errors with a maximum of 3 attempts.
  6. Print a progress line for each step.
- *Acceptance:* P1 at speed 4320 completes in about 60 s and ends in a VERY_HIGH hold.
- *Tests:* `tests/sim/test_replay.py` runs against the app via `ASGITransport` at infinite speed.
- *DoD:* generic.
- *Priority / Effort / Owner:* P0 · 2.5 h · WS1.

**T-025 Baseline computation**
- *Objective:* FR-04.
- *Files:* `app/domain/baseline.py`, `app/services/baseline_service.py`.
- *Depends on:* T-006.
- *Steps:* implement AI_DESIGN §4 exactly as a pure function `compute_baseline(transfers, fd_events, now, cfg)`. The service loads the inputs and upserts `customer_baselines`. Recompute it after each EXECUTED transfer.
- *Acceptance:* the median and P95 match numpy on random inputs. Low confidence is triggered below 30 days or with fewer than 5 qualifying transfers.
- *Tests:* `tests/unit/test_baseline.py`, including a property test with seeded random lists.
- *DoD:* generic.
- *Priority / Effort / Owner:* P0 · 1.5 h · WS2.

**T-026 Stage tracker and episodes**
- *Objective:* FR-05.
- *Files:* `app/domain/stages.py`, `app/domain/episodes.py`.
- *Depends on:* T-006, T-025.
- *Steps:*
  1. Write `detect_stage(event, baseline, recent_events, cfg)`.
  2. Write `update_episode(episode|None, stage_event, now, cfg) -> Episode`, covering open, extend and expire.
  3. Write `watch_score(episode, signals, cfg) -> (score, tier, reasons)` following the AI_DESIGN §5.2 definition.
  4. Track the canonical-order count.
- *Acceptance:* the hero's watch scores are 15 / 40 / 63 on days 1–3. A maturity FD closure is not an S1. An episode expires after 7 quiet days.
- *Tests:* `tests/unit/test_stages.py`, `test_episodes.py`, `test_watch_score.py`.
- *DoD:* generic.
- *Priority / Effort / Owner:* P0 · 3 h · WS2.

**T-027 Signal adapters**
- *Objective:* FR-06.
- *Files:* `app/integrations/fri/mock.py`, `app/domain/signals.py` (call freshness and duration bands, the teller cap).
- *Depends on:* T-006.
- *Steps:*
  1. `MockFriClient.rating(hmac)` reads `fri_mock_ratings` with a configurable artificial latency to test the timeout.
  2. Write pure functions that map signals to reasons.
  3. Tag every simulated reason with `evidence.source = "SIMULATED"`.
- *Acceptance:* a call signal more than 30 min after the call ended is ignored. Teller points are capped at 30.
- *Tests:* `tests/unit/test_signals.py`.
- *DoD:* generic.
- *Priority / Effort / Owner:* P0 · 1.5 h · WS2.

**T-028 Scoring and reasons (EN/TA)**
- *Objective:* FR-07, FR-08, NFR-02, NFR-03.
- *Files:* `app/domain/scoring.py`, `app/domain/reasons.py`, `app/domain/i18n/reasons.yaml` (EN/TA templates per reason code).
- *Depends on:* T-006, T-026, T-027.
- *Steps:*
  1. **Write the golden tests first** from AI_DESIGN §6.4 (hero = 115 raw, N1 = 5, N4 = 60).
  2. Implement `score(input, cfg) -> Assessment`.
  3. Render the reason text with Indian number formatting (`₹46,00,000`).
  4. Assert the sum invariant inside `score()` itself, raising if it is violated.
- *Acceptance:* the golden tests pass. Every reason code has EN and TA text (a test checks the YAML for completeness).
- *Tests:* `tests/unit/test_scoring_golden.py`, `test_reasons_i18n.py`, `test_scoring_invariants.py` (randomised inputs: sum equals raw, 0 ≤ score ≤ 100), `test_no_protected_features.py`.
- *DoD:* generic. Domain coverage ≥ 85%.
- *Priority / Effort / Owner:* P0 · 3 h · WS2.

**T-029 Policy and overrides**
- *Objective:* FR-07 (decision mapping) and FR-11 (initial hold status).
- *Files:* `app/domain/policy.py`.
- *Depends on:* T-028.
- *Steps:* write `decide(tier, amount, fri, active_contact) -> Decision(decision, overrides, initial_hold_status)` per AI_DESIGN §6.2–6.3.
- *Acceptance:* the FRI VERY_HIGH floor, the below-floor no-hold rule, and the no-active-contact route to the officer all work.
- *Tests:* `tests/unit/test_policy.py` (table-driven).
- *DoD:* generic.
- *Priority / Effort / Owner:* P0 · 1 h · WS2.

**T-030 Evaluation harness**
- *Objective:* FR-18.
- *Files:* `sim/evaluate.py` (CLI `python -m sim.evaluate --seeds 100-299 --out reports/eval/`), `sim/metrics.py`.
- *Depends on:* T-024, T-013.
- *Steps:*
  1. For each seed, reset an isolated DB schema or the `thunai_test` DB.
  2. Run every family at infinite speed through `ASGITransport` (no network).
  3. Read the decisions and the `scenario_label`.
  4. Compute the PRD §9 metrics, Wilson intervals, per-family tables and the modelled contact delay (AI_DESIGN §8).
  5. Write the Markdown and JSON reports with the disclaimer, config version and git SHA.
- *Acceptance:* AC-14. 200 seeds finish in ≤ 10 min on a laptop.
- *Tests:* `tests/sim/test_metrics.py` (hand-computed small cases).
- *DoD:* generic. **Results are not quoted anywhere until this has run** (T-049).
- *Priority / Effort / Owner:* P1 · 3 h · WS1.

**T-031 LLM narrative (Should)**
- *Objective:* FR-21.
- *Files:* `app/integrations/llm/{base,claude,template,validator}.py`, `app/integrations/llm/prompts/report_narrative_v1.md`.
- *Depends on:* T-018.
- *Steps:*
  1. Pseudonymise the facts.
  2. Call the Anthropic SDK with structured output and a timeout, **following the current SDK docs** (see AI_DESIGN §12.2).
  3. Run the validator (numbers and dates must be in the facts, the deny-list).
  4. Re-identify locally.
  5. Fall back to the template on any failure.
  6. Set the header `X-Thunai-LLM-Fallback`.
- *Acceptance:* with the LLM disabled, behaviour is identical to T-018. With a mocked client returning a fabricated amount, the validator rejects it and the template is used.
- *Tests:* `tests/unit/test_llm_validator.py`, `tests/integration/test_report_llm_fallback.py` (mocked; **no real API calls in tests**).
- *DoD:* generic. The LLM evaluation (AI_DESIGN §12.6) has run, or is listed as not run.
- *Priority / Effort / Owner:* P2 · 3 h · WS2.

### Phase 7 — Frontend

**T-032 Design tokens and core components**
- *Objective:* The DESIGN §7–9 foundation.
- *Files:* `src/styles/tokens.css`, `src/components/*` (Button, TierBadge, SimulatedChip, ReasonList, ScoreBreakdownBar, HoldStatusChip, EmptyState, ErrorBanner, Skeleton, Toast, Dialog, LanguageToggle), `src/lib/format.ts` (INR and IST formatting).
- *Depends on:* T-003.
- *Steps:*
  1. Implement the tokens and components with stories in a `/_components` dev-only route.
  2. Write the formatting helpers and their tests.
- *Acceptance:* `formatINR(460000000)` returns `₹46,00,000`. The tier contrast pairs are ≥ 4.5:1 (checked with a small script or a manual table).
- *Tests:* Vitest for the format helpers and ReasonList sorting (including negative points).
- *DoD:* generic.
- *Priority / Effort / Owner:* P0 · 3 h · WS4.

**T-033 Ops dashboard queue**
- *Objective:* FR-16 (queue and KPIs).
- *Files:* `src/features/ops/OpsDashboard.tsx`, `src/api/hooks/useAlerts.ts`, `useSummary.ts`.
- *Depends on:* T-032, T-019, T-011.
- *Steps:*
  1. Build the KPI filter buttons.
  2. Build the tabs and the queue with 2 s polling.
  3. Build the preview panel.
  4. Add keyboard navigation.
  5. Implement the empty, error and loading states.
- *Acceptance:* the hero hold appears within 4 s of the assessment.
- *Tests:* a Vitest render with MSW-free mocked fetch (inject a fake client).
- *DoD:* generic.
- *Priority / Effort / Owner:* P0 · 3 h · WS4.

**T-034 Hold detail and officer decision**
- *Objective:* FR-13, FR-16 (detail), FR-15 (UI).
- *Files:* `src/features/ops/HoldDetail.tsx`, `EpisodeTimeline.tsx`, `WatchScoreChart.tsx`, `DecisionPanel.tsx`, `ReportDraft.tsx`.
- *Depends on:* T-033, T-014, T-018.
- *Steps:*
  1. Lay out the screen per DESIGN §5.3.
  2. Add the note validation and the confirmation dialog.
  3. Show the contact delivery and response status.
  4. Add report generation and editing.
- *Acceptance:* the officer can cancel the hero transfer with a note. The decision panel turns read-only afterwards.
- *Tests:* a Vitest test that the decision button is disabled until the note is valid.
- *DoD:* generic.
- *Priority / Effort / Owner:* P0 · 4 h · WS4.

**T-035 Teller console**
- *Objective:* FR-14.
- *Files:* `src/features/teller/TellerConsole.tsx`, `ChecklistToggle.tsx`, `ScriptPanel.tsx`.
- *Depends on:* T-032, T-017.
- *Steps:*
  1. Build the queue and the alert banner, with an assertive live region for VERY_HIGH.
  2. Build the checklist toggles with hotkeys 1–4.
  3. Show the re-scored reasons when the checklist is applied.
  4. Build the script panel with a language toggle.
  5. Add a "Generate report draft" button that links to the report.
- *Acceptance:* AC-08 is visible in the UI within 2 s.
- *Tests:* a Vitest test for the hotkeys toggling `aria-pressed`.
- *DoD:* generic.
- *Priority / Effort / Owner:* P0 · 3 h · WS4.

**T-036 Customer app simulator**
- *Objective:* FR-10, plus the customer views for FR-11.
- *Files:* `src/features/customer/*` (PhoneFrame, Home, SendMoney, WarningScreen, HoldScreen, ResultScreen).
- *Depends on:* T-032, T-013, T-014.
- *Steps:*
  1. Build the screens per DESIGN §5.6.
  2. Add the 3 s delay before "continue" is enabled.
  3. Make the 1930 button an `<a href="tel:1930">`.
  4. Poll the transfer status every 2 s while it is held.
  5. Use Tamil first when the customer's `preferred_language` is `ta`.
- *Acceptance:* the J2 and J3 journeys work against the API.
- *Tests:* Vitest tests for the warning screen buttons and the countdown.
- *DoD:* generic.
- *Priority / Effort / Owner:* P0 · 4 h · WS5.

**T-037 Trusted-contact page**
- *Objective:* FR-12 (UI).
- *Files:* `src/features/trusted/TrustedContactPage.tsx` (a standalone layout).
- *Depends on:* T-032, T-015.
- *Steps:*
  1. Build the page per DESIGN §5.7, with the confirmation sheet.
  2. Handle the 410 and 404 states.
  3. Respect the language.
  4. Keep the page light (lazy-load nothing heavy; no charts imported).
- *Acceptance:* it works on a real phone over the LAN or a tunnel. Its Lighthouse accessibility score is ≥ 95.
- *Tests:* a Vitest test of the response flow with a mocked client.
- *DoD:* generic. Tested on at least one Android and one iOS phone if available.
- *Priority / Effort / Owner:* P0 · 2.5 h · WS5.

**T-038 i18n strings and Tamil review**
- *Objective:* NFR-07.
- *Files:* `src/i18n/{en,ta}.json`, `app/domain/i18n/{reasons,scripts}.yaml`.
- *Depends on:* T-028, T-017, T-036, T-037.
- *Steps:*
  1. Extract every string.
  2. A native Tamil speaker on the team reviews every `ta` string (the drafts are in DESIGN §6.3).
  3. Mark the scripts `reviewed_by_native_speaker: true` only after the review.
- *Acceptance:* a key-parity test passes (every key exists in both languages). The reviewer is named in the PR.
- *Tests:* `src/i18n/parity.test.ts` and the backend YAML completeness test.
- *DoD:* generic.
- *Priority / Effort / Owner:* P1 · 2 h · WS5.

**T-039 Demo control panel**
- *Objective:* FR-17 (UI).
- *Files:* `src/features/demo/DemoPanel.tsx`, `DemoClockBar.tsx`.
- *Depends on:* T-021, T-032.
- *Steps:*
  1. Build the scenario cards, reset with a confirmation, and the speed selector.
  2. Show the clock and the console messages, with a QR code for the latest contact link (use a tiny QR library, or display the link in large text if no library is approved).
  3. Build the FRI form.
- *Acceptance:* the presenter can run the whole demo from this panel.
- *Tests:* a smoke render.
- *DoD:* generic.
- *Priority / Effort / Owner:* P1 · 2 h · WS5.

**T-051 Consent and trusted-contact screens in the customer app (Should)**
- *Objective:* FR-23, plus the FR-24 UI.
- *Files:* `src/features/customer/Settings.tsx`.
- *Depends on:* T-036.
- *Steps:*
  1. Add toggles for the CALL_SIGNAL and TRUSTED_CONTACT_SHARING consents, with the consent text versions.
  2. Build the trusted-contact form, which shows "Active from <time>".
- *Acceptance:* granting and revoking consent changes whether call signals are accepted.
- *Tests:* Vitest for the form validation.
- *DoD:* generic.
- *Priority / Effort / Owner:* P2 · 2 h · WS5.

### Phase 8 — Integration

**T-040 End-to-end hero integration (headless gate, then UI gate)**
- *Objective:* Prove J1 and J4 end to end.
- *Files:* `tests/scenarios/test_hero_e2e_api.py`, any fixes.
- *Depends on:* T-013–T-017, T-021–T-029 (headless). T-033–T-037 (UI).
- *Steps:*
  1. Headless: reset, replay P1, assert the watch scores and the hold, simulate the contact response, the officer cancel and the report draft.
  2. Do the same for N1 with an ALLOW result.
  3. UI: run the full demo manually against [DEMO_SCRIPT.md](DEMO_SCRIPT.md).
- *Acceptance:* AC-01 to AC-09 pass through the API. The demo script runs without manual DB edits.
- *Tests:* the test file above.
- *DoD:* the **M2 and M3 gates** in [docs/MILESTONES.md](docs/MILESTONES.md).
- *Priority / Effort / Owner:* P0 · 3 h · all (WS6 coordinates).

**T-041 Real phone notification (Should)**
- *Objective:* FR-22.
- *Files:* `.env` (local only), [DEPLOYMENT.md](DEPLOYMENT.md) §5 notes.
- *Depends on:* T-016, T-037.
- *Steps:*
  1. **By H+2**, create a Twilio trial and verify the teammate's number, then send a test SMS to the Indian number. In parallel, create a Telegram bot (@BotFather) and get the teammate's chat id.
  2. Pick whichever channel delivers reliably.
  3. Make the phone reach the link via the LAN IP or `cloudflared tunnel --url http://localhost:5173`.
- *Acceptance:* during rehearsal the hero hold reaches the teammate's phone in ≤ 15 s, three times in a row.
- *Tests:* manual. Record the results in the rehearsal log.
- *DoD:* the fallback (console messages and QR) is also rehearsed.
- *Priority / Effort / Owner:* P2 · 1.5 h · WS3.

### Phase 9 — Testing and bug fixing

**T-042 Engine test hardening** — Determinism test (NFR-03: the same seed twice gives identical assessments), coverage ≥ 85% on `app/domain`, and the architecture test. *Depends on:* T-028. · P1 · 1.5 h · WS2.

**T-043 API integration and authorisation matrix** — A parametrised test across every endpoint × role, expecting 401, 403 or 2xx per [SECURITY.md](SECURITY.md) §3. Also the migration up/down test. *Depends on:* T-010–T-021. · P1 · 2 h · WS3.

**T-044 Playwright E2E** — The J1 (hero), J2 and J4 flows across the staff, customer and contact pages, with a seeded reset before each. Run with `npx playwright test`. *Depends on:* T-040. · P1 · 3 h · WS6.

**T-045 Security checks** — `pip-audit`, `npm audit --omit=dev`, `gitleaks detect`, manual checks of the SECURITY §2 controls (T-04 token replay, T-07 BOLA, T-14 demo guard), and a CSP header check. *Depends on:* T-043. · P1 · 1.5 h · WS6.

**T-046 Performance check** — `sim/bench.py`: 500 assessments with concurrency 10 against a seeded DB, reporting p50/p95. It must meet NFR-01 or the gap is documented. *Depends on:* T-013. · P1 · 1 h · WS3.

### Phase 10 — Deployment

**T-047 Local demo runbook and snapshot** — Write the `make demo` sequence, a `pg_dump` snapshot after seeding (`reports/demo-snapshot.sql`, which contains synthetic data only), a pre-flight checklist ([DEPLOYMENT.md](DEPLOYMENT.md) §7), and a check that the build works offline with Wi-Fi off. *Depends on:* T-040. · P0 · 1.5 h · WS6.

**T-048 Hosted deployment (Should)** — Render (API and Postgres) plus Vercel (SPA), with environment variables set, `THUNAI_DEMO_MODE=true` (the hosted instance is a demo), a CORS allow-list, and a smoke test. *Depends on:* T-040. · P2 · 2 h · WS6.

### Phase 11 — Demo preparation and final verification

**T-049 Run the evaluation and record the results** — Run `make eval` on seeds 100–299 and commit `reports/eval/<ts>.md`. Copy the numbers into the README "Status" section and the pitch **verbatim, with the synthetic label**. If a target is missed, say so. Do not retune on the evaluation seeds. *Depends on:* T-030, the M3 gate. · P1 · 1 h · WS1.

**T-050 Rehearsal, backup video and submission** — Do three full timed rehearsals with [DEMO_SCRIPT.md](DEMO_SCRIPT.md), record a backup screen capture of a clean run, prepare the slides (problem, insight, demo, results, honesty slide, ask), and walk through the [JUDGING_STRATEGY.md](JUDGING_STRATEGY.md) Q&A drill. *Depends on:* T-047, T-049. · P0 · 3 h · WS6 + all.

## 4. Effort summary (MVP P0+P1)

| WS | Tasks | Est. hours |
|---|---|---|
| WS1 | T-021, T-022, T-023, T-024, T-030, T-049 | 14.5 |
| WS2 | T-006, T-007, T-025, T-026, T-027, T-028, T-029, T-042 | 13.5 |
| WS3 | T-002, T-004, T-005, T-008, T-009, T-010, T-012–T-020, T-043, T-046 | 34.5 |
| WS4 | T-003, T-011, T-032, T-033, T-034, T-035 | 16.5 |
| WS5 | T-036, T-037, T-038, T-039 | 10.5 |
| WS6 | T-001, T-040 (coordination), T-044, T-045, T-047, T-050 | 12.5 |

WS3 is the bottleneck at about 34.5 h, which is more than one person can do in a 24 h event. **Required rebalancing at kickoff:** WS2 takes T-013 together with WS3 (−3 h). WS6 takes T-018 and T-020 (−3 h). WS1 takes T-019 after the generator is done (−2.5 h). WS5 takes T-016 (−2 h). That leaves WS3 at about 24 h. Re-check at the H+6 check-in. Rebalance at the H+6 check-in ([ROADMAP.md](ROADMAP.md)).

## 5. Post-hackathon improvements (not in the MVP)

| Item | Why |
|---|---|
| Outbox table and worker for notifications with retries | Delivery guarantees |
| Score decay instead of a hard 7-day window, and a cumulative episode amount | Catches slow burns and many small transfers (AI_DESIGN §14) |
| Logistic-regression or GBM calibration on **real** labelled bank cases, behind the same reason contract | Real-world accuracy |
| Real DIP/FRI integration, and a real device SDK for the call signal | Removes the simulations |
| Bank SSO, HttpOnly cookies, four-eyes VERY_HIGH release, MFA | Production auth |
| SSE/WebSocket push (FR-25), Hindi and more languages (FR-27), config admin UI (FR-28) | UX |
| A pilot with one branch: measure teller adoption, release times and customer satisfaction | Validates A-05 and A-06 |

## 6. Traceability: requirements → tasks → tests

| Req | Tasks | Key tests / AC |
|---|---|---|
| FR-01 | T-022, T-023 | test_generator_determinism, test_scenarios_load |
| FR-02 | T-007, T-024 | test_replay, AC-01 |
| FR-03 | T-012 | test_events, AC-15 |
| FR-04 | T-025 | test_baseline |
| FR-05 | T-026 | test_stages, test_watch_score, AC-01 |
| FR-06 | T-012, T-017, T-027 | test_signals, AC-08, AC-11 |
| FR-07 | T-006, T-028, T-029 | test_scoring_golden, test_policy, AC-01, AC-03 |
| FR-08 | T-028, T-038 | test_scoring_invariants, test_reasons_i18n, AC-02 |
| FR-09 | T-013 | test_assess, AC-15 |
| FR-10 | T-036 | WarningScreen tests, E2E J2 |
| FR-11 | T-014 | test_hold_transitions, AC-06, AC-07 |
| FR-12 | T-015, T-016, T-037 | test_trusted_contact, AC-04, AC-05 |
| FR-13 | T-014, T-034 | test_holds, AC-10 |
| FR-14 | T-017, T-035 | test_teller, AC-08, AC-09 |
| FR-15 | T-018, T-034 | test_reports, AC-09 |
| FR-16 | T-019, T-033, T-034 | test_read_apis, E2E J1 |
| FR-17 | T-021, T-039 | test_demo, AC-16 |
| FR-18 | T-030, T-049 | test_metrics, AC-14 |
| FR-19 | T-010, T-011, T-043 | test_auth, authorisation matrix, AC-13 |
| FR-20 | T-020 | test_audit |
| FR-21 (S) | T-031 | test_llm_validator, test_report_llm_fallback |
| FR-22 (S) | T-016, T-041 | notifier unit tests, rehearsal log |
| FR-23 (S) | T-051 | Settings tests |
| FR-24 | T-015 (backend), T-051 (UI) | AC-12 |
| FR-29 (S) | T-048 | Hosted smoke test |
| NFR-01 | T-046 | bench report |
| NFR-02/03 | T-028, T-042 | invariants, determinism |
| NFR-04 | T-047 | offline check |
| NFR-05 | T-005, T-010, T-012, T-045 | settings tests, gitleaks |
| NFR-06/07 | T-036–T-038, T-044 | Lighthouse, parity test |
| NFR-08 | T-012 | `/signals/call` extra-field 422 |
| NFR-09 | T-013 | input_snapshot replay test in test_assess |
| NFR-10 | T-042 | coverage report |
