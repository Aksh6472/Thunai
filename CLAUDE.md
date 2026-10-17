# CLAUDE.md — Thunai Engineering Guide

This file is the persistent instruction set for Claude Code (and humans) working in this repo. Read it at the start of every session. If anything here conflicts with a request, say so before acting.

## 0. The rule

**Inspect → Plan → Implement → Test → Verify → Document.**

1. **Inspect:** read the relevant code, tests and docs before editing. Search for an existing implementation (`grep -rn`) before writing a new one. Understand callers and dependencies before changing a function.
2. **Plan:** state which task ID (from [TASKS.md](TASKS.md)) and which FR/AC IDs this serves, the files you'll touch, and how you'll test. For changes over about 50 lines or touching a boundary, show the plan first.
3. **Implement:** make the smallest change that meets the acceptance criteria, in the style of the surrounding code.
4. **Test:** add or extend tests that would fail if the change were broken. Run them.
5. **Verify:** run the commands in §11 and report their **actual output**. Exercise the feature (curl, the UI, or the scenario replay) when it's user-facing.
6. **Document:** update every doc whose contract changed (§12).

**Never claim a feature works without running the relevant tests.** If you couldn't run something (no DB, no network, missing key), say exactly what wasn't verified. **Never overwrite working functionality without understanding its dependencies.** Read the callers and run the existing tests first.

## 1. Project purpose and scope

Thunai is a bank-side **coercion-risk engine**. It detects when a *genuine* customer is being pressured (for example, by "digital arrest" scammers) into transferring their savings. It tracks behaviour across days (FD broken → funds pooled → new payee → large transfer), fuses this with signals (simulated DoT FRI, a consented call flag, a teller checklist), and responds in tiers (allow / warn / cooling-off hold released by a trusted contact or an officer / hold plus teller script plus pre-filled 1930 report). Every decision is explained.

- **MVP scope:** [PRD.md](PRD.md) §6 (Must items) and §8. **Out of scope:** PRD §11. Do not build out-of-scope features. If a request implies one, point it out and ask.
- **Hackathon status:** documentation phase complete, implementation not started (as of 2026-10-17). Check [TASKS.md](TASKS.md) for the current state.

## 2. Repository structure (target; created by T-001 to T-003)

```text
thunai/
├── backend/
│   ├── pyproject.toml, uv.lock, alembic.ini
│   ├── config/scoring_v1.yaml        # versioned weights/thresholds (AI_DESIGN §6)
│   ├── migrations/                   # Alembic
│   ├── app/
│   │   ├── main.py                   # create_app()
│   │   ├── core/                     # settings, logging, errors, security, clock, rate_limit
│   │   ├── api/deps.py               # current_user, require_roles, require_service_key, get_clock, get_db
│   │   ├── api/v1/                   # routers: auth, events, signals, transfers, customer, holds, teller, reports, trusted, alerts, dashboard, customers, demo, health
│   │   ├── schemas/                  # Pydantic DTOs (source of OpenAPI)
│   │   ├── services/                 # ingest, assessment, baseline, hold, contact, report, audit
│   │   ├── domain/                   # PURE: baseline, stages, episodes, signals, scoring, policy, reasons, config, i18n/
│   │   ├── repositories/             # all SQL
│   │   ├── models/                   # SQLAlchemy ORM
│   │   └── integrations/             # fri/, notifier/, llm/
│   ├── sim/                          # generator, scenarios/*.yaml, replay, runner, seed, evaluate, metrics, bench
│   └── tests/                        # unit/, integration/, scenarios/, sim/, test_architecture.py
├── frontend/
│   ├── src/app/ (router, providers, auth) · src/api/ (client, schema.d.ts, hooks/)
│   ├── src/components/ · src/features/{ops,teller,customer,trusted,demo,auth}/
│   ├── src/i18n/{en,ta}.json · src/styles/tokens.css · src/lib/format.ts
│   └── e2e/                          # Playwright
├── infra/db/init.sql                 # creates thunai_test
├── reports/eval/                     # evaluation outputs (md committed, json ignored)
├── docs/                             # USER_FLOWS, DATA_SOURCES, COMPETITOR_ANALYSIS, MILESTONES
├── docker-compose.yml · Makefile · .env.example
└── *.md                              # PRD, ARCHITECTURE, API_SPEC, … (this set)
```

## 3. Technology stack and version constraints

These come from [TECH_STACK.md](TECH_STACK.md). **Do not change a major version, or add a framework, without an ADR in [DECISIONS.md](DECISIONS.md).**

- **Backend:** Python 3.12, uv, FastAPI 0.115+, Pydantic 2, SQLAlchemy 2.0 (typed `Mapped[]`), Alembic, psycopg 3, PyJWT, argon2-cffi, cryptography (Fernet), httpx, PyYAML (`safe_load` only).
- **DB:** PostgreSQL 16.
- **Frontend:** Node ≥ 22, React 19, TypeScript 5.9 (`strict`; pinned below 6 for openapi-typescript), Vite 8, React Router 8, TanStack Query 5, Tailwind 4 plus CSS-variable tokens, Recharts 3 (ADR-017), openapi-typescript. i18n is our own small `t()` function.
- **Tests:** pytest, Vitest + RTL, Playwright. **Quality:** ruff, mypy, oxlint, Prettier.
- **Optional:** the `anthropic` SDK (FR-21, model `claude-opus-5-5` via `THUNAI_LLM_MODEL`). Twilio and Telegram through httpx.

## 4. Coding conventions

**Python**
- Type hints everywhere. `mypy --strict` must pass for `app/domain`.
- Domain functions are pure: inputs in, dataclasses or Pydantic models out. No I/O, no `datetime.now()`, no globals, no randomness.
- Use `StrEnum` for every enum, with values identical to the DB CHECK values.
- Money is an `int` in paise (`amount_paise`). Never use `float` for money. Format only at the edges.
- Time is always timezone-aware and stored in UTC. Get "now" from the injected `Clock`.
- Keep functions short. Use early returns. No mutable default arguments.
- Use `logger = logging.getLogger(__name__)` and structured `extra={...}`. Never use `print` in `app/`.

**TypeScript / React**
- Function components and hooks only. One component per file in `components/`.
- All server data goes through TanStack Query hooks in `src/api/hooks/`. Components never call `fetch` directly.
- Use the generated types from `src/api/schema.d.ts`. Never hand-write API types.
- No business logic in the UI. Tiers, decisions and reasons come from the API. The UI only formats them.
- Every user-visible string goes through `t()`, with keys present in both `en.json` and `ta.json`.
- Use Tailwind with token-based classes. No hard-coded hex colours outside `tokens.css`.

**Product and bank names (ADR-015):** never hard-code "Thunai" or "Example Bank" in user-facing text. Use `PRODUCT_NAME` / `BANK_NAME` from `backend/app/core/branding.py` or `frontend/src/config/brand.ts`, or `{product}` / `{bank}` placeholders in i18n strings. The bank is always the fictional "Example Bank". The product was renamed from "Kaaval AI" to Thunai on 2026-10-17 (ADR-019), to avoid confusion with the TN Police "Kaaval Uthavi" app.

## 5. Naming conventions

| Thing | Convention | Example |
|---|---|---|
| Python modules, functions, variables | snake_case | `compute_baseline`, `amount_paise` |
| Python classes | PascalCase | `AssessmentService`, `ScoringConfig` |
| Enum values | UPPER_SNAKE | `VERY_HIGH`, `S3_NEW_PAYEE` |
| Reason codes | UPPER_SNAKE, stable forever | `NEW_PAYEE`, `FRI_RISK` |
| DB tables / columns | snake_case, plural tables | `risk_assessments.config_version` |
| API paths | kebab-case nouns, plural collections | `/holds/{id}/officer-decision` |
| JSON fields | snake_case | `transfer_ref`, `cooling_off_until` |
| React components / files | PascalCase | `ReasonList.tsx` |
| Hooks | `useX` | `useAlerts` |
| i18n keys | dot.separated | `warn.no_digital_arrest` |
| Branches | `<ws>/<task-id>-<slug>` | `ws2/T-028-scoring` |
| Task / requirement IDs | `T-NNN`, `FR-NN`, `AC-NN`, `ADR-NNN`, `R-NN` | |

## 6. Architectural boundaries (enforced by `tests/test_architecture.py`)

- `api` → `services` → `domain`. `services` → `repositories`, `integrations`, `core`.
- `app/domain/**` must **not** import `sqlalchemy`, `fastapi`, `httpx`, `anthropic`, `os`, `app.services`, `app.repositories`, `app.models` or `app.integrations`, and must not call `datetime.now`.
- `app/api/**` must not import `app.repositories` or `app.models` directly. Go through the services.
- `sim/**` talks to the app **only over HTTP** (`sim/client.py`). The exceptions are `sim/seed.py`, which may import `app.models`, `app.core.settings` and `app.core.security` to bulk-insert, and `sim/evaluate.py`, which may use `ASGITransport(app=create_app())`, which is still HTTP semantics. `sim/**` must never import `app.domain` or `app.services`.
- **The engine never reads `transfers.scenario_label`.** It exists only for evaluation.
- No microservices, queues or caches without an ADR.

## 7. API and database conventions

- The contract is [API_SPEC.md](API_SPEC.md). The error envelope, pagination, idempotency and rate limits are defined in §2. **Change the spec and the code in the same PR.** Then run `npm run gen:api` and commit the regenerated `schema.d.ts`.
- All request models use `model_config = ConfigDict(extra="forbid")`, with explicit length and range limits.
- Every list endpoint is paginated (max limit 100) and sorted deterministically.
- The schema is [DATABASE_SCHEMA.md](DATABASE_SCHEMA.md). **Every schema change is an Alembic migration** with a working `downgrade()`. Autogenerated output must be reviewed: add the CHECK constraints and partial indexes by hand. Never edit an applied migration.
- State changes (transfer and hold status) happen **only** through service methods that check an explicit transition table.
- Keep it to 5 queries or fewer per request on read endpoints. Use `selectinload`, not lazy loading in loops.

## 8. Dependencies

- **Before adding a dependency:** check whether the stack already does the job, check the package is maintained (a release in the last 12 months), and add a one-line justification in the PR. Prefer the standard library.
- **Never** add: a second HTTP client, a second state-management library, a UI kit, Redis, Celery or Kafka, an ORM besides SQLAlchemy, or an i18n framework, without an ADR.
- Don't duplicate implementations. If a helper exists (`format.ts`, `audit_service`, `Clock`), use it.
- Don't refactor unrelated code in a feature PR. Note it as a follow-up task instead.

## 9. Error handling and logging

- Raise typed errors from `app/core/errors.py` (`NotFound`, `Forbidden`, `InvalidStateTransition`, `ConsentRequired`, `DependencyUnavailable`, …). The handlers map them to the envelope. **Never return stack traces or SQL to clients.**
- No bare `except:`. Catch specific exceptions, then log, then either re-raise a typed error or apply the documented fallback (AI_DESIGN §11).
- **Fail closed:** any unexpected error in the assessment path returns 503 `ASSESSMENT_UNAVAILABLE`. Never ALLOW by default.
- External calls (FRI, Twilio, Telegram, Anthropic) **always** have explicit timeouts and documented fallbacks.
- Logs are JSON with `request_id`. **Never log** tokens, passwords, full phone numbers, full account numbers, the Fernet/HMAC/JWT keys or LLM prompt contents. The masking filter is a backstop, not a licence.
- Write `audit_log` entries for every action listed in [SECURITY.md](SECURITY.md) §9, in the same transaction as the change.

## 10. Authentication, authorisation, security and privacy rules

- Roles: CUSTOMER, TELLER, OFFICER, ADMIN, plus the service key, plus single-use contact tokens. The matrix is in SECURITY §3 and DATABASE_SCHEMA §6.
- Every route declares its auth dependency (`require_roles(...)`, `require_service_key`, or is explicitly public). **No route without an explicit decision.**
- Object ownership and branch checks live **in services**. Respond with 404, not 403, for objects the caller doesn't own.
- ADMIN can't resolve holds. VERY_HIGH holds can't be released by a trusted contact.
- Contact tokens: `secrets.token_urlsafe(32)`, SHA-256 at rest, consumed with a conditional `UPDATE … WHERE responded_at IS NULL AND expires_at > now()`.
- **Privacy rules (non-negotiable):**
  - Never collect call audio, content, caller numbers or app names. `/signals/call` rejects extra fields.
  - Never use age, gender, religion, caste, location or language as scoring inputs.
  - Customer screens show one generic reason. Staff screens show all of them.
  - No accusatory copy ("victim", "fraudster", "blocked").
  - No real personal data, anywhere, ever. Fictional names carry the "(fictional)" suffix.
  - Label simulated signals and synthetic data visibly.
- Don't design automated accusations, identification of individuals, or enforcement against payees.

## 11. Commands (valid after T-001 to T-004)

```bash
# setup
cp .env.example .env            # then generate secrets (ENVIRONMENT.md §3)
make db                         # docker compose up -d db
make migrate                    # alembic upgrade head
make seed                       # python -m sim.seed --seed 42

# run
make dev                        # API :8000 (reload) + Vite :5173
make demo                       # production-like local run (DEPLOYMENT.md §4)
cd backend && uv run python -m sim.replay --scenario P1 --speed 4320

# quality
make lint                       # ruff check, ruff format --check, mypy, oxlint, tsc --noEmit, prettier --check
make test                       # backend pytest + frontend vitest
cd backend && uv run pytest tests/unit -q                     # fast loop
cd backend && uv run pytest --cov=app/domain --cov-fail-under=85
cd frontend && npm run gen:api                                # after API changes (server running)
make e2e                        # Playwright
make eval                       # evaluation report → reports/eval/
make security                   # pip-audit, npm audit, gitleaks

# build
cd frontend && npm run build
```

If a command doesn't exist yet, create it as part of the relevant task. Don't silently use an ad-hoc substitute.

## 12. Documentation update rules

| If you change… | Update… |
|---|---|
| An endpoint, request or response, error code, auth rule | `API_SPEC.md` (+ `npm run gen:api`) |
| A table, column, constraint or index | `DATABASE_SCHEMA.md` + a migration |
| A scoring weight, threshold, reason code or override | `AI_DESIGN.md` §6, `config/scoring_v1.yaml` (bump the version), the golden tests, and a `DECISIONS.md` changelog row |
| A component boundary or flow | `ARCHITECTURE.md` |
| An environment variable | `.env.example`, `ENVIRONMENT.md`, `Settings` |
| A UI screen, state or copy | `DESIGN.md` (+ `en.json`/`ta.json`) |
| A security control | `SECURITY.md` |
| Commands or setup | `README.md`, `DEPLOYMENT.md`, this file §11 |
| Task status | `TASKS.md` |
| A significant choice | A new ADR in `DECISIONS.md` |

## 13. Definition of done (every feature)

- [ ] It meets the task's acceptance criteria in [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md), no more and no less.
- [ ] Tests were added or updated. They fail without the change and pass with it.
- [ ] `make lint` and `make test` are green locally, and the output was reported.
- [ ] Error, empty and loading states are handled (UI), and failure paths are tested (backend).
- [ ] Authorisation is declared and tested for any new route.
- [ ] No secrets, real personal data or debug prints.
- [ ] Docs are updated per §12. TASKS.md status is updated.
- [ ] The PR description lists what was verified and **what was not**.

## 14. Git and change management

Follow [CONTRIBUTING.md](CONTRIBUTING.md): feature branches, Conventional Commits, PRs to a protected `main`, a second-workstream review for the engine, security and migrations, and tags for known-good demo states. **Claude Code must not commit, push, tag or open PRs unless the user asks.** It must never force-push `main`, and never commit `.env` or the snapshot files.

## 15. Honesty rules for AI and metrics

- The MVP engine is deterministic and hand-weighted. **Don't describe it as "trained" or "ML-predicted"** anywhere, in code comments, docs or UI.
- Never fabricate datasets, metrics, benchmarks, testimonials or results. Numbers in the README and slides must come from `reports/eval/*.md` or `sim/bench.py` output, quoted with their source and the "synthetic" label.
- Tune only on seeds 0–99. Report on 100–299. Disclose any post-hoc change.
- The LLM (FR-21) is never on the decision path, and its output is validated against the facts.

## 16. When unsure

Ask a short, specific question instead of inventing requirements. Name the doc and section that is ambiguous, propose a default, and continue only if the user agrees or the task is clearly unblocked by the default.
