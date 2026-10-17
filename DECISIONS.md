# Thunai — Architecture Decision Records

Format: **Context → Decision → Alternatives → Consequences**. Status is `Accepted`, `Proposed`, `Superseded by ADR-xxx` or `Open`. Add new ADRs at the end. Never delete one; supersede it instead.

---

## ADR-001 Modular monolith — Accepted (2026-10-17)
- **Context:** 50 synthetic customers, one branch, a 24–48 h build, 5–6 developers.
- **Decision:** One FastAPI process with strict internal layers (api → services → domain, with repositories and integrations), one Postgres instance, one SPA. The simulator is a separate process that uses HTTP only.
- **Alternatives:** Microservices (ingest, scoring, notification): deployment overhead and distributed failure modes with no benefit at this scale. Serverless: cold starts and harder local and offline demos.
- **Consequences:** Simple to run offline. Boundaries are enforced by an architecture test instead of a network. It can be split later along the service boundaries.

## ADR-002 Explainable additive scoring with hand-set weights — Accepted
- **Context:** No real labelled coercion data is public. Holds must be explainable to customers, officers and regulators. Synthetic labels come from our own generator.
- **Decision:** An additive points model over stage, signal and teller features with dampeners, tier thresholds and deterministic overrides. The weights are in a versioned YAML file. The reasons always sum to the score.
- **Alternatives:** Gradient boosting or a neural network trained on synthetic data, which would learn the generator and is hard to explain. An isolation-forest anomaly score, which catches "unusual" but not "coerced", and is opaque.
- **Consequences:** It is transparent and testable, and it fits the accountability expectations. Its accuracy on real data is unknown. FR-26 (a calibration experiment) and a real-data pilot are the path to learned weights behind the same reason contract.
- **Weight rationale (v1):** stage points reflect how specific each stage is to coercion in the reported cases. A new payee less than 2 h old and a ≥ 100× amount are the strongest behavioural signals (20 each). FRI is strong but external, so it gets 10–30 depending on rating. The sequence bonus is modest (8–10), so the sequence can't dominate alone. The dampeners (−25/−15) reflect positive evidence of an established relationship. The tier boundaries (30/55/75) were chosen so that: (a) the hero is VERY_HIGH even without simulated signals; (b) N1 is LOW; (c) one strong signal alone can reach at most MEDIUM, except FRI VERY_HIGH through its override.

## ADR-003 PostgreSQL over SQLite — Accepted
- **Context:** The simulator, the API, the UI polling and the tests all run concurrently. We need a partial unique index (one open episode), JSONB and `FOR UPDATE`.
- **Decision:** PostgreSQL 16 via Docker Compose, locally and in hosting.
- **Alternatives:** SQLite (zero setup, but write locking and fewer features); MongoDB (weaker relational constraints for money and state machines).
- **Consequences:** Requires Docker on every machine (TECH_STACK §1).

## ADR-004 Polling instead of SSE/WebSockets for the MVP — Accepted
- **Decision:** TanStack Query `refetchInterval: 2000` on the queues and hold detail.
- **Alternatives:** SSE, which can't send auth headers via `EventSource` and so needs a ticket scheme. WebSockets, which add more moving parts.
- **Consequences:** Up to 2 s of latency and a little extra load, both fine at demo scale. SSE is FR-25 (Could).

## ADR-005 Synthetic data with a published generator — Accepted
- **Decision:** All data is generated from scenario families grounded in public case reports, with hard negatives. Seed splits are used for tuning versus evaluation, and some families are held out entirely.
- **Consequences:** Honest but limited evidence. Every metric carries the "synthetic" label.

## ADR-006 Notification abstraction with a console fallback — Accepted
- **Context:** Indian domestic SMS needs DLT registration, which can't be done in 48 h. Twilio's guidance says its international route to India doesn't need DLT (unverified for trial accounts).
- **Decision:** A `Notifier` protocol with Console (always available), Twilio and Telegram implementations, selected by env. A failed delivery falls back to console automatically.
- **Consequences:** The demo never depends on a third party. The real-phone moment is attempted, but it is not required.

## ADR-007 LLM only for report narrative — Accepted
- **Decision:** Claude drafts only the free-text incident paragraph, from pseudonymised facts. A deterministic validator and a template fallback apply. It is off by default and never on the decision path.
- **Alternatives:** An LLM explaining or deciding the risk, which is unverifiable and would hallucinate reasons. LLM-generated Tamil warnings, which risk mistranslated legal claims.
- **Consequences:** The "AI" story centres on the engine. The LLM is a productivity aid.

## ADR-008 Injectable simulated clock — Accepted
- **Decision:** A `Clock` protocol. In demo mode `SimClock` reads `sim_state.sim_now`. Wall clock is used only for token TTLs, rate limits and created/received timestamps.
- **Consequences:** Three days run in about 60 s, and tests are deterministic. A future bug class (mixing clocks) is mitigated by the architecture test and golden tests (R-07).

## ADR-009 Money as integer paise — Accepted
- **Decision:** `BIGINT` paise everywhere, formatted only at the edges.
- **Consequences:** No float rounding errors. The UI needs formatting helpers.

## ADR-010 No protected attributes as scoring features — Accepted
- **Decision:** Age, gender, religion, caste, location and language are never inputs to scoring. `preferred_language` is used only for display. This is enforced by a test.
- **Alternatives:** An age-based vulnerability multiplier. Victims skew elderly, but it would be discriminatory and easy to criticise.
- **Consequences:** The scoring relies purely on behaviour. Fairness is audited by outcome in a pilot.

## ADR-011 Trusted contact activation delay (72 h) — Accepted
- **Context:** A scammer could coach the victim to register the scammer's number as the trusted contact.
- **Decision:** A new or changed contact becomes effective after 72 h. A recent change adds +10. A pending contact is never notified, and the hold routes to an officer.
- **Consequences:** Genuine customers who register a contact late get officer review instead of contact release for 3 days.

## ADR-012 VERY_HIGH holds require an officer — Accepted
- **Decision:** For VERY_HIGH holds, the trusted contact's response is recorded but cannot release the hold.
- **Consequences:** More officer workload in exchange for protection against a complicit or impersonated contact.

## ADR-013 Customer sees one generic reason, staff see all — Accepted
- **Context:** A scammer watching over video could coach around specific reasons.
- **Decision:** The customer hold screen shows only a generic line. Staff and the officer see the full reasons.
- **Consequences:** Slightly less transparency to the customer at that moment. The customer can get a full explanation at the branch.

## ADR-014 Fail closed on engine errors — Accepted
- **Decision:** Assessment errors return 503. The documented caller policy is manual review for ≥ ₹2 L. The engine never ALLOWs by default.

## ADR-015 Product name in one config constant — Accepted (2026-10-17)
- **Context:** the Tamil Nadu Police already publish an app called "Kaaval Uthavi", so the team may rename the product.
- **Decision:** the display name lives in one constant per side: `backend/app/core/branding.py` (`PRODUCT_NAME`, `BANK_NAME`) and `frontend/src/config/brand.ts` (`PRODUCT_NAME`, `BANK_NAME`). Never hard-code "Thunai" or "Example Bank" in UI copy, SMS templates, report drafts or API messages. Use the constant, or the `{product}` / `{bank}` placeholders in i18n strings. Internal identifiers (package names, env prefix `THUNAI_`, DB name) stay as they are. A rename changes the display only.
- **Consequences:** a rename is a two-line change plus a docs search-and-replace.

## ADR-016 FRI is an optional signal — Accepted (2026-10-17)
- **Context:** the payee's mobile number is often unavailable for account-to-account (RTGS/NEFT) transfers (A-03).
- **Decision:** FRI contributes points only when a payee-linked number exists. When it's missing, the reason is simply absent, with no penalty and no error. The pitch states that the hero case scores 80 and is held on behaviour alone.

## ADR-017 Frontend toolchain from the current Vite template — Accepted (2026-10-17, T-003)
- **Context:** `create-vite@9.2.1` (react-ts) now ships Vite 8, TypeScript 6 and **oxlint** instead of ESLint. npm resolved React Router **8** and Recharts **3**, which are newer than the TECH_STACK v1 majors (7 and 2). `openapi-typescript@7.13` (the latest) declares a peer of `typescript ^5`.
- **Decision:** keep Vite 8, oxlint, React Router 8 (same `createBrowserRouter`/`RouterProvider` API) and Recharts 3. **Pin TypeScript to ~5.9.3**, so that the generated API types (the guard against contract drift, R-08) keep working. Set `"strict": true` explicitly in both tsconfigs, because the template relied on TS 6 defaults. Use Vitest 5 with jsdom.
- **Alternatives:** forcing ESLint back in (more dependencies, for no gain at hackathon scale); TS 6 with `--legacy-peer-deps` (an unsupported combination); hand-written API types (drift risk).
- **Consequences:** revisit when openapi-typescript supports TS 6. npm 11 blocks dependency install scripts by default. `fsevents` (optional, macOS file watching) is left unapproved. The dev server started and served pages without it (`make dev`, 2026-10-17). Hot-reload performance without it has not been measured.

## ADR-018 Configurable host ports — Accepted (2026-10-17, T-004)
- **Context:** on the lead developer's machine, other projects already occupy 5432 (Postgres) and 8000 (API).
- **Decision:** `THUNAI_DB_PORT` (compose host port) and `THUNAI_API_PORT` (uvicorn) default to 5432 and 8000. Each developer may override them in their own `.env`. The URLs in `.env` must match.
- **Consequences:** the docs keep the default ports in their examples. A local `.env` may differ.

## ADR-019 Rename the product to Thunai (full rename) — Accepted (2026-10-17)
- **Context:** the working name "Kaaval AI" was close to the TN Police app "Kaaval Uthavi" (OD-6, R-27).
- **Decision:** the product is now **Thunai** (Tamil துணை, "companion, support"). The name reflects the trusted-contact idea: nobody faces a scammer alone. The team chose a **full rename**, not display-only. That covers the display name, the env prefix `KAAVAL_` → `THUNAI_`, the headers `X-Kaaval-*` → `X-Thunai-*`, the DB/user names `thunai` / `thunai_test`, the compose project `thunai`, the packages `thunai-backend` / `thunai-frontend`, and the repo folder `thunai`. This supersedes ADR-015's "internal identifiers stay as they are" clause. The single-constant rule for display names still applies.
- **Name check:** a quick web search (2026-10-17) found no fraud, banking or safety app called "Thunai". **This is not a trademark search.** Run one before any public launch.
- **Consequences:** the empty dev database volume `kaaval_pgdata` was deleted and recreated as `thunai_pgdata`. Every developer must rename their `.env` keys (`KAAVAL_*` → `THUNAI_*`) and run `docker compose down -v` on any old `kaaval` stack. Git history keeps the old name.

## ADR-020 Engine clarifications made during implementation — Accepted (2026-10-17, T-025..T-029)
- **Context:** the hero example has the payee added at 09:12 and the RTGS at 11:20 (128 minutes), yet AI_DESIGN §6.4 gives NEW_PAYEE 20 points ("< 2 h") and a raw total of 115. The reason text in DATABASE_SCHEMA §7 also says "added 2 hours before". A few other details were unspecified.
- **Decision:**
  1. **Payee age is compared in whole hours** (floor of minutes ÷ 60): ≤ 2 h → 20, ≤ 24 h → 15, ≤ 168 h → 8. So 128 minutes counts as 2 hours, which keeps every documented number (115, 80, 60) consistent. No weight or threshold changed.
  2. **Pooling evidence** shows only money moved in from the customer's own accounts (₹11 L for the hero). FD proceeds into the same account still count towards the "≥ 2 inbound transfers" rule.
  3. **Call freshness:** an active-call observation (no `ended_at`) is trusted for 30 minutes after `observed_at`; the device re-reports during a long call. Only the latest observation counts.
  4. **Teller cap:** when the four items exceed 30, the lowest-value items are trimmed last, so every observation stays visible and the reasons still sum exactly.
  5. **Reason texts** (EN/TA) live in `app/domain/i18n/reason_texts.py`, not YAML, so the domain stays free of file I/O (CLAUDE.md §6). The teller script stays YAML (loaded by a service).
  6. **Cooling-off and trusted-contact activation** are env settings only (`THUNAI_COOLING_OFF_MINUTES`, `THUNAI_TRUSTED_CONTACT_ACTIVATION_HOURS`), not keys in `scoring_v1.yaml`, so there is one source of truth.
- **Consequences:** effective NEW_PAYEE windows are < 3 h, < 25 h and < 169 h. This is disclosed here and in AI_DESIGN §6.1. Tuning seeds: none viewed.

**Team approval (2026-10-17):** ADR-002 (fixed points table, no trained model), ADR-010 (no age in scoring), ADR-011 (72 h activation), ADR-012 (officer-only release at VERY_HIGH) and ADR-013 (generic customer message) were explicitly approved by the team.

---

## Open decisions

| ID | Question | Owner | Needed by | Status |
|---|---|---|---|---|
| OD-1 | Official rubric and exact deadline. *The theme is decided: Theme 1, Real-Time AI for Critical Decisions; category Citizen scam/fraud defense. The planning weights are in JUDGING_STRATEGY §1* | Team lead | H+0 | Partly resolved |
| OD-2 | Real phone channel: Twilio SMS or Telegram, tested in the first 2 h. **The QR fallback is the demo default** | WS3 | H+2 | Open |
| OD-3 | Tamil review: the team will review it (T-038). The reviewer is still to be named in the PR | WS5 | H+6 | Resolved (owner) |
| OD-4 | Whether to attempt the hosted deployment (T-048) for a 24 h event | WS6 | H+17 | Open |
| OD-5 | Bank name in the UI: fictional "Example Bank" only | Team | — | **Resolved** |
| OD-6 | Product rename (possible conflict with "Kaaval Uthavi") | Team | Before submission | **Resolved**: renamed to Thunai (ADR-019) |

## Known limitations

These are recorded here and in [JUDGING_STRATEGY.md](JUDGING_STRATEGY.md) §6:
- Synthetic data.
- Simulated FRI and call signals.
- Hand-set weights.
- Single instance with in-memory rate limits.
- JWTs kept in `sessionStorage`.
- No outbox for notifications.
- Lazy cooling-off expiry.
- The hold legality depends on the SOP.

## Change log for scoring config

| Date | Version | Change | Seeds viewed before change |
|---|---|---|---|
| 2026-10-17 | scoring_v1 | Initial table (AI_DESIGN §6) | none |
| 2026-10-17 | scoring_v1 | Clarification only (ADR-020): payee age compared in whole hours; cooling-off/activation moved to env. No weight or threshold changed, version unchanged | none |

## Incidents

*(none)*
