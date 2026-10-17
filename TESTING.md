# Kaaval AI — Testing Strategy

**What we test hardest:** the parts that decide people's money (scoring, policy, hold transitions, contact tokens, authorisation) and the parts the demo depends on (hero flow end to end). We do not chase a coverage number outside `app/domain/`.

> **Status:** no tests exist yet. Every result in this document is a **gate to meet**, not a result achieved.

## 1. Test pyramid and locations

| Layer | Tool | Location | Runs against |
|---|---|---|---|
| Unit (pure domain, simulator, frontend helpers) | pytest, Vitest | `backend/tests/unit/`, `backend/tests/sim/`, `frontend/src/**/*.test.ts(x)` | No DB, no network |
| Integration / API | pytest + httpx `ASGITransport` | `backend/tests/integration/` | The real Postgres `kaaval_test` DB |
| Scenario (golden end-to-end at the API level) | pytest | `backend/tests/scenarios/` | The real DB, with replay at infinite speed |
| Architecture / policy | pytest (`ast` import inspection) | `backend/tests/test_architecture.py`, `test_no_protected_features.py` | Source code |
| Frontend component | Vitest + React Testing Library | `frontend/src/**` | A fake API client |
| E2E | Playwright | `frontend/e2e/` | The full stack (the backend in demo mode) |
| AI evaluation | `python -m sim.evaluate` | `backend/sim/evaluate.py` → `reports/eval/` | An isolated DB |
| Security | pip-audit, npm audit, gitleaks, authorisation-matrix tests | CI and `make security` | — |
| Performance | `python -m sim.bench` | `backend/sim/bench.py` | A local server |

## 2. Unit tests (must exist)

| Area | Test file | Key cases |
|---|---|---|
| Scoring golden | `test_scoring_golden.py` | Hero P1 raw 115 / score 100 / VERY_HIGH. Hero without FRI and the call gives 80 / VERY_HIGH. N1 gives 5 / LOW. N4 gives 60 / HIGH |
| Scoring invariants | `test_scoring_invariants.py` | 1,000 seeded random inputs: the reason sum equals `raw_score`, the score is between 0 and 100, the tier is consistent with the thresholds, and the decision is consistent with the tier and policy |
| Reasons i18n | `test_reasons_i18n.py` | Every reason code in the config has `text_en` and `text_ta`. Formatting gives `₹46,00,000` |
| Baseline | `test_baseline.py` | Median and P95 against `statistics`/numpy. LOW confidence below 30 days or with fewer than 5 transfers. Own-account transfers are excluded |
| Stages | `test_stages.py` | A premature FD closure is S1 and a maturity closure is not. Pooling has a 72 h window with both thresholds. Canonical-order counting allows gaps |
| Episodes | `test_episodes.py` | Opens, extends, expires after 7 days, closes benign or confirmed. One open episode per customer |
| Watch score | `test_watch_score.py` | The hero day sequence 15 / 40 / 63 |
| Signals | `test_signals.py` | Call freshness of 30 min. Duration bands. Teller cap of 30. FRI mapping |
| Policy | `test_policy.py` | Table-driven: the FRI VERY_HIGH floor, the below-floor no-hold rule, routing with no active contact, the initial hold status |
| Hold transitions | `test_hold_transitions.py` | Every (state, event) pair: an allowed transition produces the right next state, and a disallowed one raises `InvalidStateTransition` |
| Config | `test_scoring_config.py` | Thresholds that aren't monotonic are rejected. An unknown key is rejected |
| Settings | `test_settings.py` | Missing secrets fail. A placeholder secret in production fails. DEMO_MODE in production fails |
| Log masking | `test_logging.py` | Phone numbers and tokens are masked |
| LLM validator (S) | `test_llm_validator.py` | A fabricated amount, date or name is rejected. A clean narrative passes |
| Generator | `tests/sim/test_generator_determinism.py` | Seed 42 run twice gives an identical canonical hash |
| Metrics | `tests/sim/test_metrics.py` | A small hand-computed confusion table and Wilson interval |
| Frontend format | `src/lib/format.test.ts` | INR grouping, IST formatting |
| Frontend i18n | `src/i18n/parity.test.ts` | Same keys in `en.json` and `ta.json` |

## 3. Integration and API tests

| File | Covers |
|---|---|
| `test_migrations.py` | upgrade head, then downgrade base, then upgrade head. CHECK and partial-unique constraints are enforced |
| `test_auth.py` | Login success and failure, generic error, expired JWT, `alg=none` rejected, rate limit returns 429, audit rows |
| `test_authz_matrix.py` | **Parametrised over every route × {anonymous, CUSTOMER(own), CUSTOMER(other), TELLER, OFFICER, ADMIN, service key}**, with the expected 2xx/401/403/404 from [SECURITY.md](SECURITY.md) §3 |
| `test_events.py` | Idempotent replay, a conflicting replay returns 409, payload validation per type, the phone is HMAC'd and never stored raw |
| `test_signals.py` | Consent is required (403). Unknown fields return 422. The watch score updates |
| `test_assess.py` | Hero, N1, idempotency, 409 conflict, FRI timeout gives `FRI_UNAVAILABLE`, an engine exception gives 503 (never ALLOW), `input_snapshot` replays to the identical result |
| `test_holds.py` | Officer release, cancel and keep, the note being required, 409 on resolved holds, lazy cooling-off expiry |
| `test_trusted_contact.py` | Valid flow. Expired gives 410. Reused gives 410. A concurrent double submit gives exactly one 200. The activation delay goes to the officer route. The minimal fields are returned (no payee or reasons) |
| `test_teller.py` | The checklist escalates. `customer_said` doesn't change the score. 409 after EXECUTED |
| `test_reports.py` | Structured fields equal the DB values. There is no full account number. PATCH sets EDITED. Mark-filed validation |
| `test_read_apis.py` | Queue ordering, pagination stability, ≤ 5 queries per request (SQLAlchemy event counter) |
| `test_audit.py` | Each auditable action writes one row. No update or delete code path exists |
| `test_demo.py` | 403 when demo mode is off. Reset in ≤ 10 s. The scenario run returns 202 |

**Test DB strategy:** create the schema once per session with Alembic, then run each test in a transaction and roll it back (SAVEPOINT pattern). Concurrency tests (double submit) use real separate connections and clean up explicitly.

## 4. Frontend tests

- **Components:** ReasonList (sorting, negative points styled as reducing risk, SimulatedChip), TierBadge (has a text label), DecisionPanel (disabled until the note is ≥ 10 characters), ChecklistToggle (hotkeys and `aria-pressed`), WarningScreen (3 s continue delay, the `tel:1930` href), TrustedContactPage (the 410 state).
- **Approach:** inject a fake API client through context, so no network is needed. Don't snapshot whole pages. Assert on roles and text (`getByRole`).

## 5. End-to-end (Playwright)

| Spec | Journey |
|---|---|
| `e2e/hero.spec.ts` | Reset. Run P1 at max speed. The Ops queue shows the VERY_HIGH hold. The teller applies the checklist, the reasons update, and the script appears in Tamil. Generate the report draft. Open the contact link (taken from the console messages) in a mobile viewport and submit "This looks like a scam". The officer cancels with a note, and the status becomes Cancelled |
| `e2e/app-warning.spec.ts` | The customer logs in and sends a MEDIUM transfer. The warning appears and the Continue button is enabled after 3 s. Cancel gives Cancelled |
| `e2e/genuine.spec.ts` | Run N1. No new alert appears. The transfer status is EXECUTED |
| `e2e/high-release.spec.ts` | A HIGH scenario (N4 seed). The contact confirms, the customer screen shows Released |

Each spec starts with `POST /demo/reset`. Viewports: desktop 1366×768 and mobile 390×844 for the contact and customer pages.

## 6. AI evaluation

Defined in [AI_DESIGN.md](AI_DESIGN.md) §7. Command: `make eval` (seeds 100–299). Required outputs: the [PRD.md](PRD.md) §9 metrics with Wilson CIs, per-family tables, a tier confusion table, reason frequencies, the config version, git SHA, seeds and the synthetic disclaimer.

**Rules:**
- Tune only on seeds 0–99.
- Never change weights after looking at the 100–299 results without re-running and **disclosing** it in [DECISIONS.md](DECISIONS.md).
- P6 and N5 are held-out families.

The LLM narrative evaluation is in AI_DESIGN §12.6.

## 7. Security testing

- `test_authz_matrix.py` (BOLA, BFLA).
- Token tests in `test_trusted_contact.py`.
- Mass-assignment tests: POST bodies with an extra `status` or `score` field get 422.
- Injection smoke: names like `'; DROP TABLE` and `<script>` survive a round trip and render as text (E2E asserts no alert dialog).
- `uv run pip-audit`, `npm audit --omit=dev`, `gitleaks detect --no-banner`.
- A manual checklist against every SECURITY §2 control marked [MVP], recorded in the PR for T-045.

## 8. Performance testing

`python -m sim.bench --n 500 --concurrency 10` sends 500 assessments against the seeded DB with uvicorn (1 worker) and reports p50/p95/max. Gate: **p95 ≤ 300 ms** (NFR-01). If it fails, record the measured value in the README and in [RISK_REGISTER.md](RISK_REGISTER.md), and profile the queries (expected cause: N+1 on signals or payees).

## 9. Test data strategy

- **Only synthetic, fictional data.** Names come from a fixed fictional list with a "(fictional)" suffix in display names. Phone numbers use the `+9198000xxxxx` pattern, plus the teammate's real number only in local `.env` for T-041 (never committed).
- Unit tests build inputs with **factory helpers** (`tests/factories.py`) rather than fixtures with hidden state.
- Golden scenarios use fixed seeds (42 for the demo).
- The evaluation uses the separate seed ranges in §6.
- Tests never call real Twilio, Telegram or Anthropic. Those clients are injected and replaced with fakes or httpx `MockTransport`.

## 10. Release gates (all must pass at G4)

| # | Gate | Command / evidence |
|---|---|---|
| RG-1 | Backend lint, format and types are clean | `make lint` (`ruff check`, `ruff format --check`, `mypy app sim`) |
| RG-2 | All backend tests pass | `make test-backend` |
| RG-3 | Domain coverage ≥ 85% | `uv run pytest --cov=app/domain --cov-fail-under=85` |
| RG-4 | Frontend lint, types and unit tests pass, and the build succeeds | `npm run lint && npm run typecheck && npm test -- --run && npm run build` |
| RG-5 | E2E: hero, app-warning, genuine and high-release pass, 2 consecutive runs | `npx playwright test --repeat-each=2` |
| RG-6 | Golden scenarios pass (AC-01 to AC-09) | `uv run pytest tests/scenarios` |
| RG-7 | Evaluation report generated, with numbers matching the README | `make eval`, then a diff check by WS6 |
| RG-8 | No high or critical vulnerabilities, no secrets | `make security` |
| RG-9 | Assessment p95 ≤ 300 ms, or the gap documented | `python -m sim.bench` output pasted in the PR |
| RG-10 | Offline demo works | Manual: Wi-Fi off, full DEMO_SCRIPT run with the console-notifier fallback |
| RG-11 | Tamil reviewed | T-038 PR names the reviewer |

## 11. Acceptance tests

The acceptance criteria AC-01 to AC-16 ([PRD.md](PRD.md) §10) map to automated tests as follows:

| AC | Test |
|---|---|
| AC-01 | `tests/scenarios/test_hero_e2e_api.py::test_p1_watch_and_hold` |
| AC-02 | `test_scoring_invariants.py`, `test_assess.py::test_reasons_sum` |
| AC-03 | `test_hero_e2e_api.py::test_n1_allowed` |
| AC-04/05 | `test_trusted_contact.py` |
| AC-06/07 | `test_holds.py`, `test_trusted_contact.py::test_very_high_not_released` |
| AC-08 | `test_teller.py::test_checklist_rescore` and `e2e/hero.spec.ts` |
| AC-09 | `test_teller.py::test_script_langs`, `test_reports.py` |
| AC-10 | `test_holds.py::test_note_required` |
| AC-11 | `test_signals.py::test_consent_required` |
| AC-12 | `test_trusted_contact.py::test_activation_delay` |
| AC-13 | `test_authz_matrix.py` |
| AC-14 | `tests/sim/test_evaluate_smoke.py` (a 2-seed run produces all sections) |
| AC-15 | `test_events.py::test_idempotent`, `test_assess.py::test_idempotent` |
| AC-16 | `test_demo.py::test_reset_time` |

## 12. Commands

```bash
make test             # backend + frontend unit/integration
make test-backend     # cd backend && uv run pytest
make test-frontend    # cd frontend && npm test -- --run
make e2e              # starts the stack in demo mode, then: cd frontend && npx playwright test
make eval             # cd backend && uv run python -m sim.evaluate --seeds 100-299 --out ../reports/eval/
make security         # pip-audit, npm audit, gitleaks
make lint             # ruff, mypy, oxlint, tsc, prettier
```
