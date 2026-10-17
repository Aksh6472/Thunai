# Thunai — Product Requirements Document

| Field | Value |
|---|---|
| Status | Draft v1 — awaiting team approval |
| Last updated | 2026-10-17 |
| Owner | Product lead (Workstream 6) |
| Related | [ARCHITECTURE.md](ARCHITECTURE.md), [AI_DESIGN.md](AI_DESIGN.md), [API_SPEC.md](API_SPEC.md), [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md) |

---

## 1. Executive summary

Thunai is a **bank-side coercion-risk engine**. It protects a *genuine* customer who is being pressured — typically by "digital arrest" scammers posing as police, CBI, customs or court officials — into moving their own savings to a criminal's account.

Existing fraud controls are built to catch an *impostor* (stolen credentials, account takeover) or a *mule receiver*. In a coercion scam, the real customer authenticates correctly, from their own device or in person at their own branch. Single-transaction anomaly checks often see nothing wrong.

Thunai looks at the **sequence of behaviour across several days**:

1. A fixed deposit is closed early,
2. money from several accounts is pooled,
3. a new payee is added,
4. a large RTGS/NEFT goes to that new payee within hours.

It combines this sequence with external risk signals: the DoT Financial Fraud Risk Indicator (simulated in the MVP), an optional consented "long call with an unknown caller" flag, and a one-tap teller checklist. It then applies a **tiered, explained response**: allow, warn, hold for a cooling-off period with release by a pre-registered trusted contact, or hold with a guided teller script and a pre-filled 1930 / cybercrime.gov.in report.

## 2. Problem statement

> A senior citizen receives a video call from someone in a police uniform who says they are under "digital arrest" for money laundering. Over three days, the caller keeps them on video and in isolation. Under instruction, they break a fixed deposit, consolidate their savings and add a "verification account" as a payee. Then they walk into their branch and ask for a ₹46 lakh RTGS. Today, whether that money is lost depends on whether one bank employee happens to notice.

### 2.1 Evidence (publicly reported; see [docs/DATA_SOURCES.md](docs/DATA_SOURCES.md) for links)

| Evidence | Source type | Confidence |
|---|---|---|
| I4C data cited in Parliament: about 1,23,672 digital-arrest complaints in 2024, with reported losses of about ₹1,935 crore | Parliamentary data via news reports | Medium — secondary reporting |
| Supreme Court suo motu directions (4 Aug 2026): RBI asked to frame an SOP for banks within 4 weeks, reportedly including temporary debit holds on suspicious amounts. The Court had earlier asked why banks failed to flag unusual transactions | Legal news (MediaNama, Bar & Bench, ANI, Vision IAS) | High that the directions exist. Final SOP content is **not yet verified** |
| SBI Chandrayangutta, Hyderabad (Nov 2024): staff noticed an anxious couple about to RTGS ₹46 lakh after 3 days of video "surveillance", escalated, and filed a complaint on 1930 | News (Telangana Today, Siasat) | Medium |
| A recurring case pattern: an FD is broken, then a large RTGS/NEFT goes to an unfamiliar account while the customer stays on a call. Bank staff who probed, delayed or involved family stopped the transfer (Navi Mumbai, Mangaluru, Hyderabad, Jodhpur). Losses occurred where nobody intervened (Mumbai Mulund ₹1.83 crore over Jan 14–31 2026; Moradabad; Jaipur) | News reports | Medium — individual reports, figures not independently verified |
| Victims are coached with cover stories (e.g., "buying land in Bengaluru", Mangaluru case) | News | Medium |
| DoT launched the Financial Fraud Risk Indicator (FRI) on 21 May 2025. It rates mobile numbers Medium / High / Very High risk and is shared with banks via the Digital Intelligence Platform | DoT / PIB / Business Standard | High |

### 2.2 Why existing approaches fall short (summary; details in [docs/COMPETITOR_ANALYSIS.md](docs/COMPETITOR_ANALYSIS.md))

**The gap in one line:** the victim is a genuine customer, so login, device and OTP checks all pass. The public Indian tools we reviewed watch the **scammer's number** (DoT FRI), the **receiving account** (RBI MuleHunter.AI) or the **call** (Truecaller, Google's call scam detection, call-content research such as DeepVerif.AI). Thunai watches the **victim's own abnormal money movement across days**. That focus is our core differentiator. We state it as *"we did not find a tool that does this"*, not "nobody does this", because global vendors such as BioCatch Scams360 target authorised-push-payment scams within digital sessions (see below).

- **Receiver-side tools** (e.g., RBI's MuleHunter.AI) detect mule accounts. They are complementary, but they do not intervene with the coerced sender at the moment of payment.
- **Phone-side tools** (Truecaller Family Protection, Android scam detection) do not see the bank transactions.
- **Session-behaviour tools** (e.g., BioCatch Scams360, launched July 2025) detect manipulation in *digital* sessions, including active-call detection. Public material does not describe cross-day financial staging, the branch counter, or an India-specific 1930/FRI workflow. *This needs further verification.*
- **Manual staff intuition** works when it happens, but it is inconsistent and leaves no structured record.

## 3. Assumptions requiring validation

Each assumption has an ID referenced elsewhere. **None has been validated with a bank.**

| ID | Assumption | Why it matters | How to validate |
|---|---|---|---|
| A-01 | Coercion cases show a recognisable multi-day staging pattern (liquidate, then pool, then new payee, then large transfer) | Core detection premise | Code ≥20 public case reports into the stage model ([docs/DATA_SOURCES.md](docs/DATA_SOURCES.md) §3). Ask a bank fraud team |
| A-02 | A bank can lawfully apply a short cooling-off hold on a customer-authorised outbound transfer | The intervention depends on it | The SC-directed RBI SOP, bank T&Cs, and legal counsel. Precedents: US FINRA Rule 2165, Georgia HB 945 (2026) |
| A-03 | The remitting bank can obtain a mobile number linked to the payee for an FRI lookup | Needed for the FRI signal on RTGS/NEFT payees | Not generally present in RTGS/NEFT messages. It is feasible for UPI/VPA, intra-bank beneficiaries, or via DIP-side mapping. **Simulated in the MVP** |
| A-04 | A bank's mobile app can detect, with consent, that the device is on a long call with an unknown caller (telephony or VoIP), without accessing audio | Phone signal | Android `AudioManager` mode / telephony state research. BioCatch publicly claims active-call detection. **Simulated in the MVP** |
| A-05 | Customers will pre-register a trusted contact, and that contact responds within minutes | Release path and delay for genuine customers | User interviews (5+ seniors, 5+ adult children). Response times in the MVP are **modelled assumptions** |
| A-06 | Tellers will use a one-tap checklist during a busy branch visit | Branch signal | Interviews with 2+ bank staff |
| A-07 | Scoring behaviour, not stated reasons, resists coached cover stories | Robustness claim | Scenario family P5 in the synthetic evaluation. Real-world validation needed |
| A-08 | The working rubric weights (Importance 20, Originality 20, Feasibility 15, Technical depth 15, Impact 10, Demo 10, Scalability 10) match the official rubric | Pitch strategy | Theme confirmed: **Theme 1, Real-Time AI for Critical Decisions; category Citizen scam/fraud defense**. The weights are the team's planning assumption. **Confirm them against the official rubric** |
| A-09 | Tamil + English cover the primary demo audience | Localisation scope | Team decision |

## 4. User personas

| Persona | Description | Goals | Pain points |
|---|---|---|---|
| **P1 — Protected customer** ("Kamala", 72, fictional) | Retired teacher, Chennai. Savings in FDs. Uses the bank app lightly and prefers the branch. Prefers Tamil | Keep savings safe and keep control of her money | Scammers isolate and terrify her. She may hide the situation from staff and family because she was told to |
| **P2 — Trusted contact** ("Arun", 41, fictional) | Kamala's son, in another city, pre-registered as her trusted contact | Be told before money leaves, act fast, not be bothered for routine payments | Learns about the fraud only after the money is gone |
| **P3 — Branch teller** ("Priya", fictional) | Front-desk officer handling 80+ customers a day | Spot coercion without accusing customers, and follow a clear procedure | No structured signal and no script. Fear of offending genuine customers |
| **P4 — Branch officer / fraud-ops analyst** ("Mr. Rao", fictional) | Branch manager or central fraud operations | Review holds, release or cancel with accountability, file reports | Alert fatigue. Unexplained scores. Manual reporting to 1930 |
| **P5 — Genuine high-value customer** ("Mr. Iqbal", fictional) | Pays a builder in instalments and buys property | Large transfers go through without friction | False holds and embarrassing questioning |

Accessibility needs: P1 needs large type, high contrast, Tamil text and a one-tap call button. P2 uses a phone browser, possibly on poor connectivity. P3 and P4 use desktop browsers under time pressure, so they need keyboard operation and scannable reasons. Details are in [DESIGN.md](DESIGN.md) §2.

## 5. User stories

| ID | As a… | I want… | So that… | Req |
|---|---|---|---|---|
| US-01 | protected customer | a clear warning in my language before a risky transfer, with a one-tap call to 1930 | I learn that "digital arrest" does not exist before I pay | FR-10 |
| US-02 | protected customer | my large transfer to be paused briefly and my son to be asked | someone I trust can break the scammer's isolation | FR-11, FR-12 |
| US-03 | trusted contact | an SMS with a secure link that tells me what was paused and what to do | I can call my mother and confirm or stop the transfer within minutes | FR-12, FR-22 |
| US-04 | teller | a prominent alert with plain-language reasons when a held customer is at my counter | I know why and what to say | FR-08, FR-14 |
| US-05 | teller | one-tap checklist items (on a call, distressed, following instructions, mentions police/CBI) | what I observe updates the risk instantly | FR-06, FR-14 |
| US-06 | teller | a guided script in Tamil or English | I can talk to the customer without accusing them | FR-14 |
| US-07 | branch officer | to review a hold with every reason and the multi-day timeline, then release or cancel with a note | decisions are accountable and audited | FR-13, FR-16, FR-20 |
| US-08 | branch officer | a pre-filled 1930 / cybercrime.gov.in report draft | reporting takes minutes, not an hour | FR-15, FR-21 |
| US-09 | genuine customer | my regular large payment to an established payee to go through | I am not inconvenienced | FR-07 (dampeners) |
| US-10 | fraud-ops analyst | a queue of watch-listed customers and holds, sorted by urgency | I act on the most urgent case first | FR-16 |
| US-11 | team / judge | to replay a three-day scenario in about a minute and see the risk climb | the multi-day logic is visible | FR-02, FR-17 |
| US-12 | team / judge | an evaluation report on held-out synthetic scenarios | claims are measured, not asserted | FR-18 |
| US-13 | protected customer | changes to my trusted contact to take effect only after a delay | a scammer cannot make me swap in their own number | FR-24 |

## 6. Functional requirements

Priority: **M** = Must Have (MVP), **S** = Should Have, **C** = Could Have, **W** = Won't Have (this hackathon).

### 6.1 Data and simulation

| ID | Requirement | Pri |
|---|---|---|
| FR-01 | **Synthetic data generator.** Generates about 50 fictional customers with accounts and 180 days of routine history, plus labelled scenario episodes from documented coercion families (P1–P7) and hard-negative families (N1–N6) ([AI_DESIGN.md](AI_DESIGN.md) §7). Deterministic given `--seed`. The generator source is published with the project | M |
| FR-02 | **Scenario replay with a simulated clock.** Replays events to the API over HTTP in simulated time, with configurable compression (default: 3 simulated days in about 60 real seconds). Routine background activity for all customers streams concurrently | M |

### 6.2 Engine

| ID | Requirement | Pri |
|---|---|---|
| FR-03 | **Event ingestion.** Accepts account events (`FD_CLOSED`, `INTERNAL_TRANSFER_IN`, `PAYEE_ADDED`, `TRUSTED_CONTACT_CHANGED`, `ROUTINE_DEBIT`, `ROUTINE_CREDIT`) idempotently by `event_id` | M |
| FR-04 | **Customer baseline.** Per customer: median and P95 outbound transfer amount, known payees, premature FD closure history, typical channel, and history length. Low-confidence baselines (<30 days of history) fall back to population defaults and are flagged in the reasons | M |
| FR-05 | **Multi-day stage tracker.** Maintains a per-customer *risk episode* over a rolling 7-day window. It tracks stages S1 (premature FD closure or liquidation), S2 (pooling), S3 (new payee) and S4 (high-value outbound), plus their order. It computes a *watch score* on every event | M |
| FR-06 | **Signal fusion.** Adds (a) the FRI rating of a payee-linked number (simulated adapter), (b) a consented call-risk flag (simulated), and (c) the teller checklist. A signal without valid consent is rejected | M |
| FR-07 | **Risk scoring.** Additive, explained points clamped to 0–100. Tiers: LOW <30, MEDIUM 30–54, HIGH 55–74, VERY_HIGH ≥75. Weights, thresholds and overrides live in a versioned YAML config, and every assessment stores its `config_version` | M |
| FR-08 | **Explainable reasons.** Every non-zero contribution is a reason with a code, points, evidence and text in English and Tamil. The reasons always sum exactly to the score before clamping | M |
| FR-09 | **Transfer assessment.** `POST /transfers/assess` (service-to-service) and `POST /customer/transfers` (customer app) return ALLOW / WARN / HOLD *before* simulated execution. Both are idempotent by `transfer_ref` | M |

### 6.3 Interventions

| ID | Requirement | Pri |
|---|---|---|
| FR-10 | **Customer warning (MEDIUM).** Bilingual screen with the "There is no 'digital arrest' in Indian law" message and a `tel:1930` button. The customer chooses *Cancel* or *I understand, continue*. The acknowledgement is recorded | M |
| FR-11 | **Cooling-off hold (HIGH / VERY_HIGH).** The transfer is held. A HIGH hold is released by trusted-contact confirmation **or** officer review. A VERY_HIGH hold needs officer review, and the officer must see the trusted contact's response if one exists. Holds never auto-release. When the cooling-off period expires, the hold moves to an officer review queue. The customer can always cancel | M |
| FR-12 | **Trusted contact flow.** On a hold, notify the active trusted contact with a single-use link (token hashed at rest, 30-minute expiry). The page shows minimal, consented information and three options: *I spoke to them — it's genuine*, *This looks like a scam*, *I can't reach them*. The console notifier is always available as a fallback | M |
| FR-13 | **Officer review.** Release, cancel the transfer, or keep holding. A note is mandatory. The action is audited | M |
| FR-14 | **Teller console.** Shows the alert for a branch transfer, the reasons, the episode timeline, the one-tap checklist (which re-scores instantly) and the guided script in Tamil or English | M |
| FR-15 | **Report draft (template).** A pre-filled structured draft for 1930 / cybercrime.gov.in, built from hold facts, plus customer-reported details the teller enters. The teller can edit it and copy it out. The officer marks it "filed externally" and records the acknowledgement number. There is **no** automatic submission | M |
| FR-21 | **LLM narrative for the report.** Optional narrative drafted by Claude from pseudonymised facts. It is checked so that every number and date must appear in the facts, and it falls back to the template on any failure | S |
| FR-22 | **Real message delivery.** Twilio SMS and/or a Telegram bot to the trusted contact's real phone | S |
| FR-24 | **Trusted contact change delay.** A new or changed trusted contact becomes effective after 72 hours. A change within the last 7 days adds a risk reason | M (backend rule) / S (UI) |

### 6.4 Operations, platform and demo

| ID | Requirement | Pri |
|---|---|---|
| FR-16 | **Ops dashboard.** A queue of holds, warnings and watch-listed customers sorted by urgency. Alert detail shows the reasons, a score history chart, the multi-day episode timeline and officer actions. KPIs: active holds, awaiting contact, awaiting officer, warnings today | M |
| FR-17 | **Demo control panel.** List scenarios, reset to seed state, run a scenario at a chosen speed, and show the simulated clock. Available only when `THUNAI_DEMO_MODE=true` | M |
| FR-18 | **Evaluation harness.** A CLI that runs all scenario families on held-out seeds and writes a metrics report (§9). Results are labelled as synthetic | M |
| FR-19 | **Staff authentication and RBAC.** Roles TELLER, OFFICER, ADMIN, plus CUSTOMER (demo customers), plus a service API key for the simulator | M |
| FR-20 | **Audit log.** Append-only record of every assessment, hold transition, contact response, officer action, report change and login | M |
| FR-23 | **Consent screens** in the customer app, for the call signal and trusted-contact sharing | S |
| FR-29 | **Hosted demo deployment** so judges can try it after the event | S |
| FR-25 | Server-Sent Events for live updates (the MVP polls every 2 s) | C |
| FR-26 | An experiment that calibrates weights with logistic regression on the synthetic train split, compared against expert weights | C |
| FR-27 | Hindi localisation | C |
| FR-28 | An admin UI to view and edit the scoring config | C |

## 7. Non-functional requirements

| ID | Requirement | Measure |
|---|---|---|
| NFR-01 | Assessment latency | p95 ≤ 300 ms for `POST /transfers/assess` on a dev laptop with 50 customers and 180 days of history (to be measured, T-046) |
| NFR-02 | Explainability | 100% of WARN/HOLD decisions have ≥1 reason, and reason points sum to the raw score (enforced by test) |
| NFR-03 | Determinism | The same seed, config and event stream produce identical scores and decisions |
| NFR-04 | Offline demo | The full demo runs with no internet. Only the real SMS (FR-22) and the LLM (FR-21) need the network, and both have fallbacks |
| NFR-05 | Secrets | No secrets in the repository. Trusted contact phone numbers are encrypted at rest. Payee phone numbers are stored only as HMAC plus last 4 digits |
| NFR-06 | Accessibility | WCAG 2.1 AA for the customer warning and trusted contact pages. Body text ≥18 px on the customer warning |
| NFR-07 | Localisation | All customer-, contact- and teller-facing strings in English and Tamil, with the Tamil reviewed by a native speaker before the demo |
| NFR-08 | Privacy | No call audio, content or caller identity is collected. The call signal is a consented flag only |
| NFR-09 | Auditability | Every decision can be reproduced from stored inputs plus `config_version` |
| NFR-10 | Quality | `app/domain/` line coverage ≥ 85%. All release gates in [TESTING.md](TESTING.md) §10 pass |

## 8. MVP boundaries

**In:** everything marked M above, on synthetic data, with simulated FRI and call signals, running locally on one laptop, demonstrated through the four UI surfaces (Ops dashboard, Teller console, Customer app simulator, Trusted contact page) plus the Demo control panel.

**Not in:** real bank integration, real FRI/DIP access, real phone call detection, automatic submission to cybercrime.gov.in, production-grade identity verification, and multi-branch tenancy.

## 9. Success metrics

These are **targets**, not results. Results come only from `make eval` (T-049) and must be reported with the "synthetic data" label.

| Metric | Definition | Target |
|---|---|---|
| Coercion interception rate | Share of positive-family episodes where the first high-value transfer to a scammer payee is HELD before simulated execution | ≥ 90% |
| Amount-weighted protection | Rupees held before execution ÷ total rupees attempted in positive episodes | Reported (no target) |
| False hold rate | Share of genuine high-value transfers (≥ ₹2,00,000) that are HELD. Reported overall **and per family** | ≤ 5% overall. Per-family values are disclosed |
| Genuine warning rate | Share of genuine high-value transfers that receive a WARN | Reported (≤ 20% desired) |
| Added delay for genuine customers | Hold-to-release time for genuine held transfers, under the **modelled** trusted-contact response distribution ([AI_DESIGN.md](AI_DESIGN.md) §8) | Median ≤ 15 min (modelled) |
| Explanation coverage | WARN/HOLD decisions with complete reasons | 100% |
| Assessment latency | See NFR-01 | p95 ≤ 300 ms |

Demo-day product metric: the judge sees the hero scenario held, the trusted contact's real phone notified, and a genuine large payment allowed, all live.

## 10. Acceptance criteria (MVP)

| ID | Given / When / Then | Req |
|---|---|---|
| AC-01 | Given hero scenario P1 (seed 42), when it is replayed, then the watch score rises on each of days 1–3 and the ₹46,00,000 RTGS gets decision HOLD with tier VERY_HIGH | FR-02, FR-05, FR-07, FR-09 |
| AC-02 | Given any WARN/HOLD assessment, the response contains reasons whose `points` sum to `raw_score`, and each reason has `text_en` and `text_ta` | FR-08 |
| AC-03 | Given hard negative N1 (property instalment to an established payee), the transfer is ALLOWED | FR-07 |
| AC-04 | Given a HIGH hold and an active trusted contact, a notification is dispatched within 5 s, and a valid link opens the response page | FR-12 |
| AC-05 | Given a used or expired contact token, the response endpoint returns 410 and changes nothing | FR-12 |
| AC-06 | Given a HIGH hold, when the trusted contact confirms "genuine", then the hold is RELEASED and the transfer EXECUTED, with an audit entry | FR-11 |
| AC-07 | Given a VERY_HIGH hold, a trusted-contact confirmation alone does **not** release it. The status remains AWAITING_OFFICER and the response is recorded for the officer | FR-11 |
| AC-08 | Given a teller ticks "customer is on a call" and "mentions police/CBI", the assessment is re-scored and the new reasons show within 2 s | FR-14 |
| AC-09 | Given a VERY_HIGH hold, the teller can view the script in Tamil and English and generate a report draft with amount, date/time, payee bank/IFSC, masked account, and the episode timeline pre-filled | FR-14, FR-15 |
| AC-10 | Officer release/cancel without a note is rejected with 422 | FR-13 |
| AC-11 | A call signal for a customer without active CALL_SIGNAL consent is rejected with 403 `CONSENT_REQUIRED` | FR-06 |
| AC-12 | A trusted contact added less than 72 h ago is not notified. The hold goes to the officer queue with the reason `TRUSTED_CONTACT_RECENTLY_CHANGED` | FR-24 |
| AC-13 | A TELLER token calling an OFFICER-only endpoint gets 403. An unauthenticated call gets 401 | FR-19 |
| AC-14 | `make eval` produces `reports/eval/<timestamp>.md` with every §9 metric, per-family tables and the synthetic-data disclaimer | FR-18 |
| AC-15 | Re-posting the same `event_id` or `transfer_ref` returns the original result and creates no duplicates | FR-03, FR-09 |
| AC-16 | Demo reset restores the seed state in ≤ 10 s, and the hero scenario can be re-run immediately | FR-17 |

## 11. Out of scope (Won't Have this hackathon)

- Integration with real core banking, payment rails, DIP/FRI or I4C systems.
- Detection using call audio, transcripts or content. This is a deliberate privacy choice, not just a time constraint.
- Detecting or acting against the **receiver** (mule) account. That is the job of MuleHunter.AI-class tools.
- Automatic accusations, blocking a customer's account, or permanently blocking funds.
- Using age, gender, religion, caste, location or language as scoring features.
- A native mobile app. The customer app is a web simulator in a phone frame.
- Multi-tenant, multi-bank deployment.

## 12. Constraints and dependencies

| Type | Item |
|---|---|
| Hackathon | Theme 1: Real-Time AI for Critical Decisions. Category: Citizen scam/fraud defense, which asks for reports to be routed to 1930 / cybercrime.gov.in. So FR-15 is demo-critical |
| Time | Hackathon of 24–48 h (**exact deadline still to be filled in**). The plan is built so the MVP is complete by H+20 ([ROADMAP.md](ROADMAP.md)) |
| Team | 5–6 people, organised into 6 workstreams ([IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md) §2) |
| Data | No real bank data. Everything is synthetic and fictional ([docs/DATA_SOURCES.md](docs/DATA_SOURCES.md)) |
| External | Twilio trial (can send only to verified numbers) and/or a Telegram bot for FR-22. The Anthropic API for FR-21. Both are optional, with fallbacks |
| Regulatory | Holding customer funds depends on bank T&Cs and the RBI SOP (A-02). The DPDP Act 2023 applies to personal data ([SECURITY.md](SECURITY.md) §13) |
| Language | Tamil copy must be reviewed by a native speaker on the team before the demo |
