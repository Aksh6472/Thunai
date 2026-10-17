# Thunai — Task Backlog

The full specification of each task (steps, acceptance, tests) is in [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md) §3. This file is the **live tracker**. Update `Status` and `Assignee` as work moves.

**Status:** `todo` · `doing` · `review` · `done` · `cut`
**Priority:** P0 (critical path) · P1 (MVP) · P2 (Should) · P3 (Could)

## 1. MVP backlog (in recommended order)

| ID | Task | WS | Pri | Est (h) | Depends on | Milestone | Assignee | Status |
|---|---|---|---|---|---|---|---|---|
| T-001 | Repo bootstrap (rename folder, git, Makefile) | WS6 | P0 | 0.5 | — | M0 | Claude | done — pushed to github.com/Aksh6472/Thunai; branch protection not set up yet |
| T-002 | Backend scaffold | WS3 | P0 | 1 | T-001 | M0 | Claude | done |
| T-003 | Frontend scaffold | WS4 | P0 | 1.5 | T-001 | M0 | Claude | done (ADR-017) |
| T-004 | Local Postgres and env | WS3 | P0 | 0.5 | T-001 | M0 | Claude | done — `make db` healthy on port 5433; `thunai` and `thunai_test` reachable via psycopg |
| T-006 | Scoring config YAML and loader | WS2 | P0 | 1 | T-002 | M0 | Claude | done — loader in `app/core/scoring_config.py` (domain stays I/O-free); not yet wired into startup (T-005) |
| T-005 | Settings, logging, error envelope, `/readyz` | WS3 | P0 | 2 | T-002, T-004 | M1 | Claude | done — startup now loads the scoring config (fail closed) |
| T-008 | ORM models and migration 0001 | WS3 | P0 | 3 | T-004, T-005 | M1 | Claude | done — adds `request_hash` columns and account/payee indexes (DATABASE_SCHEMA updated) |
| T-007 | Clock abstraction | WS2 | P0 | 1 | T-005, T-008 | M1 | Claude | done — SimClock keeps time in memory (single worker), persisted to `sim_state` |
| T-025 | Baseline computation | WS2 | P0 | 1.5 | T-006 | M1 | Claude | done — `compute_baseline`; the DB service comes with T-013 |
| T-027 | Signal adapters (FRI mock, call, teller cap) | WS2 | P0 | 1.5 | T-006 | M1 | Claude | done — domain adapters; `MockFriClient` lands with T-013 |
| T-026 | Stage tracker, episodes, watch score | WS2 | P0 | 3 | T-006, T-025 | M1 | Claude | done — hero watch 15/40/63 verified |
| T-028 | Scoring and reasons EN/TA (golden tests first) | WS2 | P0 | 3 | T-026, T-027 | M1 | Claude | done — golden 115/80/5/60 pass; domain coverage 99% |
| T-029 | Policy and overrides | WS2 | P0 | 1 | T-028 | M1 | Claude | done |
| T-010 | Auth: login, JWT, RBAC, service key, rate limit | WS3 | P0 | 2.5 | T-005, T-008 | M1 | Claude | done — argon2id, HS256 pinned, RBAC deps, in-memory limiter, login audit |
| T-009 | Staff and demo-customer seed | WS3 | P0 | 0.5 | T-008, T-010 | M1 | Claude | done — staff + cust.kamala/iqbal/meena; idempotent (truncate, insert) |
| T-022 | Synthetic population generator | WS1 | P0 | 3 | T-008 | M1 | Claude | done — 50 customers, seed 42 deterministic (hash test), seeds in ~0.5 s |
| T-023 | Scenario families (P1 and N1 first) | WS1 | P0 | 3 | T-022 | M1→M2 | Claude | done — 13 families; all seed-42 expectations pass through the API |
| T-032 | Design tokens and core components | WS4 | P0 | 3 | T-003 | M1 | | todo |
| T-011 | Frontend auth | WS4 | P0 | 2 | T-003, T-010, T-032 | M1 | | todo |
| T-012 | Event and call-signal ingestion | WS3 | P0 | 3 | T-008, T-010, T-026 | M2 | Claude | done — idempotent, per-customer lock, HMAC/Fernet on receipt; hero watch 15→40→63 via API |
| T-013 | Transfer assessment orchestration | WS3+WS2 | P0 | 3 | T-012, T-025–T-029 | M2 | Claude | done — fail-closed 503, idempotent, FRI timeout → info reason, snapshot replay test |
| T-014 | Hold lifecycle and officer decision | WS3 | P0 | 3 | T-013 | M2 | Claude | done — transition table, officer decision (note 10–1000), lazy cooling-off expiry |
| T-016 | Notifier (console Must; Twilio/Telegram Should) | WS5 | P0 | 2 | T-005 | M2 | Claude | done — console always + Twilio/Telegram via httpx, FAILED → console fallback |
| T-015 | Trusted-contact requests and responses | WS3 | P0 | 3 | T-014, T-016 | M2 | Claude | done — single-use SHA-256 tokens, concurrent double submit → one 200 / one 410 |
| T-024 | Scenario replayer | WS1 | P0 | 2.5 | T-012, T-013, T-023 | M2 | Claude | done — CLI + in-process runner; P1 at 100000× replays in ~2 s |
| T-021 | Demo control endpoints | WS1 | P0 | 2 | T-024, T-007 | M2 | Claude | done — reset ~0.5 s, run, runs log, clock, FRI, console messages |
| T-017 | Teller endpoints (checklist, script) | WS3 | P0 | 2.5 | T-013, T-014 | M2 | Claude | done — escalate-only re-score, customer_said never scored, EN/TA script (TA pending review) |
| T-018 | Report draft (template) | WS6 | P1 | 2 | T-014 | M2 | Claude | done — template narrative; structured fields from DB; mark-filed OFFICER only |
| T-020 | Audit log writer | WS6 | P1 | 1 | T-008 | M2 | Claude | done — `audit()` with scrub; append-only enforced by test |
| T-019 | Read APIs: alerts, dashboard, customers | WS1 | P1 | 2.5 | T-013, T-014 | M2 | Claude | done — unified alert queue, summary, customers; ≤ 5 queries per list request (tested) |
| T-040a | **Headless hero gate** (API-level P1 and N1) | All | P0 | 1.5 | T-012–T-029 | **M2** | Claude | done — AC-01..AC-10 and N1 pass headless (tests/scenarios) |
| T-033 | Ops dashboard queue | WS4 | P0 | 3 | T-032, T-019, T-011 | M3 | | todo |
| T-035 | Teller console | WS4 | P0 | 3 | T-032, T-017 | M3 | | todo |
| T-034 | Hold detail and officer decision UI | WS4 | P0 | 4 | T-033, T-014, T-018 | M3 | | todo |
| T-036 | Customer app simulator | WS5 | P0 | 4 | T-032, T-013, T-014 | M3 | | todo |
| T-037 | Trusted-contact page | WS5 | P0 | 2.5 | T-032, T-015 | M3 | | todo |
| T-039 | Demo control panel | WS5 | P1 | 2 | T-021, T-032 | M3 | | todo |
| T-038 | i18n and native Tamil review | WS5 | P1 | 2 | T-028, T-017, T-036, T-037 | M3 | | todo |
| T-040b | **UI hero gate** (DEMO_SCRIPT run-through) | All | P0 | 1.5 | M3 tasks | **M3** | | todo |
| T-042 | Engine test hardening (determinism, coverage) | WS2 | P1 | 1.5 | T-028 | M4 | | todo |
| T-043 | API authorisation matrix and migration test | WS3 | P1 | 2 | T-010–T-021 | M4 | | todo |
| T-044 | Playwright E2E (J1, J2, J4) | WS6 | P1 | 3 | T-040b | M4 | | todo |
| T-045 | Security checks | WS6 | P1 | 1.5 | T-043 | M4 | | todo |
| T-046 | Performance check (NFR-01) | WS3 | P1 | 1 | T-013 | M4 | | todo |
| T-030 | Evaluation harness | WS1 | P1 | 3 | T-024, T-013 | M4 | | todo |
| T-049 | Run the evaluation and record the results | WS1 | P1 | 1 | T-030, M3 | M4 | | todo |
| T-047 | Local demo runbook and snapshot | WS6 | P0 | 1.5 | T-040b | M4 | | todo |
| T-050 | Rehearsals, backup video, slides, submission | WS6+All | P0 | 3 | T-047, T-049 | M5 | | todo |

## 2. Should / Could backlog (only after the M3 gate)

| ID | Task | WS | Pri | Est (h) | Depends on | Status |
|---|---|---|---|---|---|---|
| T-041 | Real SMS / Telegram to the teammate's phone (**start the trial account at H+0**) | WS3 | P2 | 1.5 | T-016, T-037 | todo |
| T-051 | Consent and trusted-contact screens in the customer app | WS5 | P2 | 2 | T-036 | todo |
| T-031 | LLM narrative with validator and fallback | WS2 | P2 | 3 | T-018 | todo |
| T-048 | Hosted deployment (Render + Vercel) | WS6 | P2 | 2 | T-040b | todo |
| T-060 | SSE live updates (FR-25) | WS3/WS4 | P3 | 3 | M4 | todo |
| T-061 | Logistic-regression calibration experiment (FR-26), report only | WS1/WS2 | P3 | 3 | T-030 | todo |
| T-062 | Hindi strings (FR-27) | WS5 | P3 | 2 | T-038 | todo |
| T-063 | Scoring config viewer (FR-28, read-only) | WS4 | P3 | 2 | T-006 | todo |

## 3. Tasks that can run in parallel

| Time window | In parallel |
|---|---|
| H+0–2 | T-002 + T-004 (WS3) · T-003 (WS4) · T-006 (WS2) · scenario research for T-023 (WS1) · T-001, then the Twilio/Telegram trial for T-041 (WS6) |
| H+2–8 | WS2: T-025 → T-027 → T-026 → T-028 → T-029 · WS3: T-005 → T-008 → T-010 → T-009 · WS1: T-022 → T-023 · WS4: T-032 → T-011 · WS5: T-016 (console notifier), then mock-driven T-036 and T-037 layouts · WS6: T-020 |
| H+8–12 | WS3: T-012 → T-013 (with WS2) → T-014 → T-015 → T-017 · WS1: T-024 → T-021 → T-019 · WS6: T-018 · WS4/WS5: wire the screens to the real endpoints as they land |
| H+12–17 | WS4: T-033, T-034, T-035 · WS5: T-036, T-037, T-039, T-038 · WS1: T-030 · WS2: T-042 · WS3: T-043, T-046 · WS6: T-041, T-044 setup |
| H+17–20 | T-044, T-045, T-049, T-047, bug fixes |

**Rule for parallel frontend work before the endpoints exist:** build against the OpenAPI types (`npm run gen:api` as soon as T-002 serves the schemas) and a thin fake client in `src/api/fake.ts`. Delete the fake client once the endpoint is live. **No hard-coded demo data may ship.**

## 4. MVP completion criteria (all must be true)

1. The G4 gate in [docs/MILESTONES.md](docs/MILESTONES.md) passes.
2. AC-01 to AC-16 in [PRD.md](PRD.md) §10 pass (automated where marked).
3. [DEMO_SCRIPT.md](DEMO_SCRIPT.md) runs start to finish in ≤ 3 min on the demo laptop, three times in a row, **with Wi-Fi off** (using the console-notifier fallback).
4. The evaluation report exists, and its numbers in the README and slides match it exactly.
5. No P0/P1 task is in `todo`/`doing`, unless it is marked `cut` with a reason in [DECISIONS.md](DECISIONS.md).
