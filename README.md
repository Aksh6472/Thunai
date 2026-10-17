# Thunai

*Hackathon: Theme 1, Real-Time AI for Critical Decisions · Category: Citizen scam/fraud defense.*

**A coercion-risk engine for banks.** It protects genuine customers who are being pressured, by "digital arrest" and impersonation scammers, into transferring their own savings.

> **Status (2026-10-17): MVP built and tested end to end.** Backend, risk engine, simulator, evaluation harness and all five UI surfaces work against the real API; the hero scenario passes headless and in a browser. All data is **synthetic and fictional**. The DoT FRI and phone call signals are **simulated**. The engine is deterministic and hand-weighted, **not trained**. See [Current implementation status](#current-implementation-status) for what is and isn't verified.

---

## The problem

In a "digital arrest" scam, criminals posing as police, CBI or court officials keep a victim, often a senior citizen, on video calls for days. Under that pressure, the victim breaks fixed deposits, consolidates their money and transfers it to a "verification account". The customer is genuine and authenticates perfectly, so impostor-focused fraud controls see little wrong. Today, the transfer is stopped only if a bank employee happens to notice. In one reported case, an SBI branch in Hyderabad stopped a ₹46 lakh RTGS in November 2024 this way. The Supreme Court issued nationwide directions in August 2026, asking RBI for an SOP on bank safeguards. Evidence and sources are in [PRD.md](PRD.md) §2 and [docs/DATA_SOURCES.md](docs/DATA_SOURCES.md).

## Target users

| User | Need |
|---|---|
| Protected customer (often a senior) | A clear warning in their language, and a pause plus a trusted person when it matters |
| Trusted contact (family) | To be asked before the money leaves, and to respond in one tap |
| Branch teller | A structured alert, a one-tap checklist, a non-accusatory script (Tamil/English) |
| Branch officer / fraud operations | An explained queue of holds, accountable decisions, a pre-filled 1930 report |

## Core features (MVP)

1. **Customer baseline.** Learns each customer's usual amounts, payees and FD habits.
2. **Multi-day stage tracker** (the core idea). Scores the *sequence* FD broken early → money pooled → new payee → large RTGS within hours, across a 7-day window.
3. **Signal fusion.** Adds a DoT FRI rating of the payee-linked number *(simulated)*, an optional consented "long call with an unknown caller" flag *(simulated, no audio ever)* and a teller checklist.
4. **Tiered response:**

   | Tier | Action |
   |---|---|
   | Low | Allow |
   | Medium | Bilingual warning ("There is no digital arrest in Indian law") with a 1930 button |
   | High | Cooling-off hold, released when the pre-registered trusted contact confirms (or by an officer) |
   | Very high | Hold, plus a guided teller script, a pre-filled 1930 / cybercrime.gov.in report and officer review |

5. **Explainable alerts.** Every hold lists its reasons with points that sum to the score, e.g. "₹46,00,000 is 115× usual · FD broken · payee added 2 hours ago · on an unknown video call for 3+ hours".
6. **Evaluation harness.** Measures interception and false holds on held-out synthetic scenarios built from public case patterns.

## Architecture overview

This is a modular monolith: a FastAPI backend with a pure-Python domain layer, PostgreSQL, and a React SPA with five surfaces (Ops dashboard, Teller console, Customer app simulator, Trusted-contact page, Demo control). A separate simulator plays the bank's core system and talks to the API over HTTP only. Details and diagrams are in [ARCHITECTURE.md](ARCHITECTURE.md).

```text
Simulator (core banking + device) ──HTTP──▶ FastAPI [api → services → domain] ──▶ PostgreSQL
React SPA (ops / teller / customer / contact / demo) ──HTTP──▶ FastAPI ──▶ Notifier (console | SMS | Telegram), LLM (optional)
```

## Technology stack

Python 3.12 · FastAPI · Pydantic 2 · SQLAlchemy 2 · Alembic · PostgreSQL 16 · React 19 · TypeScript · Vite · TanStack Query · Tailwind 4 · Recharts · pytest · Vitest · Playwright. Optional: Claude (report narrative only), Twilio/Telegram. Rationale is in [TECH_STACK.md](TECH_STACK.md).

## Prerequisites

Python 3.12 with [uv](https://docs.astral.sh/uv/), Node.js 22 LTS, Docker with Compose v2, and Git. The project folder path must contain **no spaces** (rename it to `thunai`).

## Installation and local development

```bash
git clone <repo-url> thunai && cd thunai
cp .env.example .env          # generate secrets: see ENVIRONMENT.md §3
make db                       # Postgres in Docker
make migrate                  # Alembic migrations
make seed                     # 50 synthetic customers, seed 42
make dev                      # API http://localhost:8000 · UI http://localhost:5173
```

Demo logins: `teller.priya`, `officer.rao`, `admin.demo`, `cust.kamala`, `cust.iqbal`, `cust.meena`. The password for all of them is the value of `THUNAI_SEED_PASSWORD` in your `.env`.

**Run the demo.** Sign in as `admin.demo` → `/demo` → **Run P1** (classic digital arrest) and watch `/ops`, `/teller` and the console message / QR code for the trusted-contact link. Or from a terminal with the API running: `make replay SCENARIO=P1 SPEED=4320`. `make demo-reset` restores seed 42 in about half a second. To browse with every screen populated, run `make demo-data` (API running): it resets, then replays all 13 synthetic scenario families, ending on P1. The full script is [DEMO_SCRIPT.md](DEMO_SCRIPT.md).

## Environment configuration

See [ENVIRONMENT.md](ENVIRONMENT.md) and [.env.example](.env.example). Never commit `.env`.

## Testing

```bash
make lint          # ruff, mypy, oxlint, tsc, prettier
make test          # pytest (backend) + vitest (frontend)
make e2e           # Playwright: hero, app warning, HIGH release, genuine (uses installed Chrome)
make eval          # synthetic evaluation on held-out seeds 100–299 → reports/eval/
make bench         # NFR-01 latency check against the running API
make security      # pip-audit, npm audit, gitleaks
```

The strategy and release gates are in [TESTING.md](TESTING.md). `make test`, `make e2e` and `make eval` all use the `thunai_test` database, so run them one at a time.

## Deployment

The primary demo runs locally (`make demo`) and works offline. The optional hosting is Render (API + Postgres) plus Vercel (SPA). See [DEPLOYMENT.md](DEPLOYMENT.md).

## Current implementation status

| Area | Status (2026-10-17) |
|---|---|
| Risk engine (baseline, stages, episodes, scoring, policy) | Done. Golden examples pass exactly: hero raw 115 → VERY_HIGH; behaviour-only 80; N1 = 5 → ALLOW; N4 = 60 → HIGH. Domain coverage 99% |
| API (ingestion, assessment, holds, trusted contact, teller, reports, dashboard, demo) | Done. 42 routes; authorisation matrix tested for every route × role |
| Simulator | 13 scenario families (P1–P7, N1–N6), 50-customer generator, replayer, in-app demo runner |
| UI | Ops dashboard, hold detail, customer view, teller console, customer app, trusted-contact page, demo panel. Playwright J1–J4 pass on two consecutive runs |
| Performance | `make bench`: p95 **55.2 ms**, p50 36.9 ms for 499 assessments at concurrency 10 on the dev laptop (NFR-01 target 300 ms) |
| Security checks | pip-audit, npm audit and gitleaks clean; checklist in [reports/security/2026-10-17.md](reports/security/2026-10-17.md) |
| Evaluation results (**synthetic**, held-out seeds 100–299, [reports/eval/20261017T141000Z.md](reports/eval/20261017T141000Z.md)) | Interception **96.9%** (1357/1400; 95% CI 95.9–97.7%), target ≥ 90%: **met**. False hold on genuine ≥ ₹2 L **30.8%** (367/1190; 95% CI 28.3–33.5%), target ≤ 5%: **missed**, almost entirely the expected-friction families N4 wedding (87.0%) and N5 tuition (96.5%, held out); N1, N2, N3, N6 and background 0%. Genuine warning rate 17.0%. Modelled added delay for genuine holds: median 11.3 min (a model, not a measurement). Explanation coverage 100%. *Synthetic data generated from public case patterns. Not evidence of real-world performance.* No weights were changed after viewing these seeds |
| LLM report narrative (FR-21, optional) | Built behind `THUNAI_LLM_ENABLED` (off by default) with a deterministic validator and template fallback; tested only with fakes. The live-model evaluation (AI_DESIGN §12.6) has **not** been run |

**Not done (needs people or accounts):** native-speaker review of the Tamil strings (T-038; every Tamil string is a draft), real SMS/Telegram to a phone (T-041), hosted deployment (T-048), rehearsals, backup video and slides (T-050), and GitHub branch protection.

## Limitations and future work

- **Synthetic data only.** There is no real bank data and no bank validation.
- **The FRI and call signals are simulated.** FRI number availability for RTGS payees is an open assumption (A-03), and so is phone-call detection feasibility (A-04).
- **Hand-set scoring weights**, deliberately explainable. A learned model needs real labelled cases.
- **Expected false holds** on some genuine life events (weddings, tuition), disclosed per family.
- The legal basis for holds depends on the RBI SOP and bank terms (A-02).
- Single instance, polling, no outbox, no SSO. See the post-hackathon items in [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md) §5 and [ROADMAP.md](ROADMAP.md) §4.

## Documentation map

| Doc | Purpose |
|---|---|
| [PRD.md](PRD.md) | Problem, personas, requirements, acceptance criteria |
| [AI_DESIGN.md](AI_DESIGN.md) | Engine design, scoring table, evaluation, LLM use |
| [ARCHITECTURE.md](ARCHITECTURE.md) · [API_SPEC.md](API_SPEC.md) · [DATABASE_SCHEMA.md](DATABASE_SCHEMA.md) | System design and contracts |
| [DESIGN.md](DESIGN.md) | UI/UX specification |
| [SECURITY.md](SECURITY.md) | Threat model, privacy, responsible use, regulation |
| [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md) · [TASKS.md](TASKS.md) · [ROADMAP.md](ROADMAP.md) · [docs/MILESTONES.md](docs/MILESTONES.md) | Delivery plan |
| [TESTING.md](TESTING.md) · [DEPLOYMENT.md](DEPLOYMENT.md) · [ENVIRONMENT.md](ENVIRONMENT.md) | Quality and operations |
| [DEMO_SCRIPT.md](DEMO_SCRIPT.md) · [JUDGING_STRATEGY.md](JUDGING_STRATEGY.md) | Hackathon presentation |
| [RISK_REGISTER.md](RISK_REGISTER.md) · [DECISIONS.md](DECISIONS.md) | Risks and ADRs |
| [CONTRIBUTING.md](CONTRIBUTING.md) · [CLAUDE.md](CLAUDE.md) | How we work |
| [docs/USER_FLOWS.md](docs/USER_FLOWS.md) · [docs/DATA_SOURCES.md](docs/DATA_SOURCES.md) · [docs/COMPETITOR_ANALYSIS.md](docs/COMPETITOR_ANALYSIS.md) | Supporting analysis |
