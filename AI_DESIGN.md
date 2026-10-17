# Thunai — AI and Risk-Engine Design

> **Honesty statement.** As of this document, **no model has been trained, validated or deployed.** The MVP risk engine is a **deterministic, explainable scoring system**. It sits on top of **per-customer statistical baselines** and a **multi-day sequence (stage) tracker**, and its weights are set by hand from documented case patterns. All evaluation numbers will come from **synthetic data**. They show that the engine behaves as designed on documented patterns. They are **not** evidence of real-world accuracy. The only generative-AI component (FR-21) drafts report text. It **never** makes or influences a decision.

---

## 1. The precise task

Given a customer's account history, the current risk episode, external signals and a pending outbound transfer, the engine must:

1. Decide **before execution** whether the transfer should be ALLOWED, WARNED or HELD.
2. Explain the decision as a list of human-readable reasons whose points add up to the score.

The engine targets **coercion of a genuine sender**. That is an *authorised* payment made under duress. It does not target account takeover or the fraudulent receiver.

## 2. Why "AI", and which kind

| Component | Kind | Learned from data? | Why this choice |
|---|---|---|---|
| Customer baseline | Statistical profiling (median, P95, payee tenure, FD habit) | **Yes**, per customer, from their own history (unsupervised) | "120× usual" only makes sense relative to *this* customer |
| Stage tracker | Deterministic state machine over a 7-day rolling window | No | Coercion unfolds over days. A single-transaction anomaly score misses the build-up |
| Signal fusion and scoring | Weighted additive model with tier thresholds | No (hand-set weights, `scoring_v1.yaml`). The FR-26 experiment fits a logistic regression on synthetic data | Weights you can audit and explain suit RBI/SC accountability expectations. There is no real labelled data to train on, and training on synthetic data mostly learns the generator |
| Policy | Deterministic rules mapping tier to action, with overrides | No | Consequential actions must be predictable and reviewable |
| Report narrative (FR-21) | LLM (Claude) | Pre-trained, used for inference only | Saves officer time on prose. It is validated against facts and has a template fallback |

**What we will say to judges:** "Thunai learns each customer's normal behaviour and detects a multi-day coercion *sequence*. Today it fuses signals with transparent, hand-set weights, because a bank must explain every hold and real labelled coercion data is not public. The architecture lets us swap in a learned model once a bank provides labelled cases, behind the same explanation contract."

## 3. Inputs and outputs

### 3.1 Inputs (internal schema; field names match [DATABASE_SCHEMA.md](DATABASE_SCHEMA.md))

```jsonc
// AssessmentInput (built by assessment_service, consumed by app/domain/scoring.py)
{
  "customer_id": "uuid",
  "now": "2026-10-03T11:20:00+05:30",            // from the Clock (simulated in demo mode)
  "baseline": {
    "history_days": 180,
    "median_outbound_paise": 4000000,              // ₹40,000
    "p95_outbound_paise": 25000000,
    "premature_fd_closures_365d": 0,
    "confidence": "OK"                              // OK | LOW (<30 days)
  },
  "episode": {
    "opened_at": "2026-10-01T10:05:00+05:30",
    "stages": [                                     // ordered by occurred_at
      {"stage": "S1_LIQUIDATION", "event_id": "...", "occurred_at": "...", "amount_paise": 3500000000},
      {"stage": "S2_POOLING",     "event_id": "...", "occurred_at": "...", "amount_paise": 1100000000},
      {"stage": "S3_NEW_PAYEE",   "event_id": "...", "occurred_at": "...", "payee_id": "..."}
    ]
  },
  "transfer": {
    "transfer_ref": "TRF-2026-000913",
    "amount_paise": 460000000,                      // ₹46,00,000
    "rail": "RTGS",
    "channel": "BRANCH",
    "payee": {"payee_id": "...", "added_at": "...", "prior_successful_transfers": 0,
              "recurring_amount_paise": null, "linked_msisdn_hmac": "..."},
    "source_account_balance_paise": 470000000
  },
  "signals": {
    "fri_rating": "HIGH",                           // null | MEDIUM | HIGH | VERY_HIGH  (SIMULATED)
    "call_risk": {"active_or_ended_within_min": 0, "duration_min": 190, "caller_known": false}, // null if no consent
    "teller_checklist": ["ON_CALL", "DISTRESSED"],  // [] if not a branch visit or not yet filled
    "trusted_contact_changed_within_days": null
  }
}
```

### 3.2 Output

```jsonc
// Assessment
{
  "raw_score": 120,             // sum of reason points (may exceed 100)
  "score": 100,                 // clamp(raw_score, 0, 100)
  "tier": "VERY_HIGH",
  "decision": "HOLD",
  "overrides_applied": [],
  "config_version": "scoring_v1@2026-10-17",
  "reasons": [
    {"code": "HIGH_VALUE_TO_PAYEE", "points": 20, "stage": "S4",
     "evidence": {"amount_paise": 460000000, "multiple_of_median": 115},
     "text_en": "₹46,00,000 is 115× this customer's usual transfer (₹40,000).",
     "text_ta": "₹46,00,000 என்பது இந்த வாடிக்கையாளரின் வழக்கமான பரிமாற்றத்தின் (₹40,000) 115 மடங்கு."}
  ]
}
```

Invariant (tested): `sum(r.points for r in reasons) == raw_score`, and every WARN/HOLD has ≥1 reason with non-zero points.

## 4. Baseline (`app/domain/baseline.py`)

These are computed from the last 180 days of *completed outbound transfers and debits ≥ ₹1,000* (excluding transfers to the customer's own accounts):

| Field | Definition |
|---|---|
| `median_outbound_paise` | Median amount. If there are fewer than 5 qualifying transfers, use the population default ₹25,000 and set `confidence=LOW` |
| `p95_outbound_paise` | 95th percentile (stored for display and analysis only, not scored in v1) |
| `premature_fd_closures_365d` | Count of FDs closed before maturity |
| `history_days` | Days since the first event |
| `confidence` | `LOW` if `history_days < 30` or there are fewer than 5 qualifying transfers |
| Payee facts (per payee) | `added_at`, `prior_successful_transfers`, `recurring_amount_paise` (median of ≥2 prior transfers, if any) |

The baseline is recomputed nightly in production. In the MVP it is recomputed **on seed** and **on demand after each executed transfer**. It is cheap at this scale. A low-confidence baseline adds an informational reason `BASELINE_LOW_CONFIDENCE` (0 points) so officers can see it.

## 5. Stage tracker (`app/domain/stages.py`)

### 5.1 Stage definitions

| Stage | Triggered by | Condition |
|---|---|---|
| **S1_LIQUIDATION** | `FD_CLOSED` | `closed_at < maturity_date` (premature). Normal maturity does **not** trigger it |
| **S2_POOLING** | `INTERNAL_TRANSFER_IN` | Within 72 h, ≥2 inbound transfers into one account from the customer's own accounts or FD proceeds, with a sum ≥ ₹1,00,000 **and** ≥ 5× `median_outbound` |
| **S3_NEW_PAYEE** | `PAYEE_ADDED` | Any new payee |
| **S4_HIGH_VALUE** | Transfer assessment | `amount ≥ min_high_value` (₹2,00,000) **and** `amount ≥ 10 × median_outbound` |

### 5.2 Episodes

- An episode **opens** on the first stage event when no episode is open.
- It **stays open** while stage events keep arriving, and **closes** 7 days after the last stage event (`EXPIRED`).
- It also closes when a hold in it is resolved as genuine by the trusted contact or an officer (`CLOSED_BENIGN`), or when a transfer is cancelled as suspected coercion (`CLOSED_CONFIRMED_RISK`). Closing as benign does **not** whitelist the customer. New stage events open a new episode.
- **Watch score:** a pre-transfer score recomputed on every event. It is defined as `FD_PREMATURE_CLOSURE` + `FUNDS_POOLED` + **15 if any S3 occurred in the episode** (a flat value, because no transfer exists yet) + `STAGE_SEQUENCE` (counting the stages so far, S1–S3) + `LONG_CALL_UNKNOWN` + `TRUSTED_CONTACT_RECENTLY_CHANGED`. Transfer-specific reasons (amount, balance drain, FRI of the payee, teller checklist, dampeners) are excluded. It uses the same tier thresholds. It is shown on the ops dashboard to make the multi-day climb visible, and it triggers **no customer-facing action**. A watch tier of MEDIUM or above puts the customer on the ops *watchlist*.

### 5.3 Sequence bonus

The stage tracker counts how many **distinct stages appear in canonical order** (S1 → S2 → S3 → S4) within the episode. Gaps are allowed, and the order is measured by the time each stage first occurred.

## 6. Scoring (`app/domain/scoring.py`, config `backend/config/scoring_v1.yaml`)

### 6.1 Points table (v1, hand-set, rationale in [DECISIONS.md](DECISIONS.md) ADR-002)

| Code | Group | Condition | Points |
|---|---|---|---|
| `FD_PREMATURE_CLOSURE` | Stage S1 | An S1 occurred in the episode | **15**. Only **5** if `premature_fd_closures_365d ≥ 2` (the customer's habit) |
| `FUNDS_POOLED` | Stage S2 | An S2 occurred in the episode | **10** |
| `NEW_PAYEE` | Stage S3 | The transfer payee was added < 2 h / < 24 h / < 7 d before | **20 / 15 / 8** |
| `HIGH_VALUE_TO_PAYEE` | Stage S4 | Amount ≥ ₹2,00,000 and multiple of median ≥ 10× / 50× / 100× | **10 / 15 / 20** |
| `BALANCE_DRAIN` | Stage S4 | Amount ≥ 70% of the source account balance | **5** |
| `STAGE_SEQUENCE` | Sequence | 3 / 4 distinct stages in order (including this transfer as S4) | **8 / 10** |
| `FRI_RISK` | Signal | Rating of the payee-linked number: MEDIUM / HIGH / VERY_HIGH (**simulated**) | **10 / 20 / 30** |
| `LONG_CALL_UNKNOWN` | Signal | Consented flag: unknown caller, call active or ended ≤30 min ago, duration 60–179 / ≥180 min | **8 / 15** |
| `TELLER_ON_CALL` | Teller | Customer is on a phone or video call while transacting | **8** |
| `TELLER_DISTRESSED` | Teller | Customer appears anxious, frightened or confused | **8** |
| `TELLER_FOLLOWING_INSTRUCTIONS` | Teller | Customer appears to follow someone else's instructions | **10** |
| `TELLER_MENTIONS_AUTHORITY` | Teller | Customer mentions police, CBI, ED, customs, court, "arrest" or "case" | **15** |
| *(teller cap)* | Teller | Sum of teller items is capped | **max 30** |
| `TRUSTED_CONTACT_RECENTLY_CHANGED` | Account | Trusted contact added or changed within 7 days | **10** |
| `ESTABLISHED_PAYEE` | Dampener | Payee ≥ 90 days old **and** ≥ 2 prior successful transfers | **−25** |
| `MATCHES_REGULAR_PATTERN` | Dampener | Payee has a recurring amount, and the transfer is ≤ 1.5× that amount | **−15** |
| `BASELINE_LOW_CONFIDENCE` | Info | Baseline confidence is LOW | **0** |

Payee age for `NEW_PAYEE` is measured in **whole hours** (128 minutes counts as 2 h), see ADR-020.

`score = clamp(sum(points), 0, 100)`

### 6.2 Tiers and decisions

| Tier | Score | Decision | Action |
|---|---|---|---|
| LOW | 0–29 | ALLOW | Execute |
| MEDIUM | 30–54 | WARN | Bilingual warning plus 1930 button. The customer may continue (acknowledgement recorded) or cancel. At the branch, the teller is shown the reasons |
| HIGH | 55–74 | HOLD | Cooling-off hold (default 240 min). Notify the trusted contact. Release by trusted-contact confirmation **or** officer review |
| VERY_HIGH | ≥75 | HOLD | Hold, plus teller script and report draft. Release **only** by officer review (which shows the trusted-contact response if one exists) |

### 6.3 Deterministic overrides (`app/domain/policy.py`)

| Override | Rule |
|---|---|
| `FRI_VERY_HIGH_FLOOR` | If FRI = VERY_HIGH, the tier is at least HIGH |
| `NO_ACTIVE_TRUSTED_CONTACT` | If HIGH but no *active* trusted contact exists (none registered, or still inside the 72 h activation delay), route to the officer review queue |
| `BELOW_FLOOR_NO_HOLD` | If amount < ₹50,000, the decision is at most WARN (holds are reserved for high-value transfers) |

### 6.4 Worked examples (these become golden tests in `tests/scenarios/`)

**Hero, P1 (Kamala, ₹46,00,000 RTGS at the branch, seed 42):**

| Reason | Points |
|---|---|
| FD_PREMATURE_CLOSURE (day 1) | 15 |
| FUNDS_POOLED (day 2) | 10 |
| NEW_PAYEE (< 2 h, day 3) | 20 |
| HIGH_VALUE_TO_PAYEE (115× median) | 20 |
| BALANCE_DRAIN (98%) | 5 |
| STAGE_SEQUENCE (4 stages) | 10 |
| LONG_CALL_UNKNOWN (190 min) | 15 |
| FRI_RISK (HIGH, simulated) | 20 |
| **Total** | **115 → score 100, VERY_HIGH, HOLD** |

Without FRI or the call signal, the score is 80, which is still VERY_HIGH. That supports the "behaviour alone is enough" story. The watch score climbs: day 1 → **15** (LOW: FD broken). Day 2 → **40** (MEDIUM, watchlist: +10 pooled, +15 long unknown call). Day 3 → **63** (HIGH watch: +15 new payee, +8 three-stage sequence). Tested in AC-01.

**Hard negative, N1 (Mr. Iqbal, ₹40,00,000 to a builder he has paid ₹5,00,000 quarterly for 2 years, median outbound ₹5,00,000):** S1 15 + S2 10 + HIGH_VALUE 0 (8× median, below 10×, so S4 is not reached) + BALANCE_DRAIN 5 + STAGE_SEQUENCE 0 (only S1 and S2) + ESTABLISHED_PAYEE −25 = **5 → LOW, ALLOW** (AC-03).

**Hard negative, N4 (wedding: FD broken, new jeweller payee, ₹8,00,000):** 15 + 10 + 15 + 10 + 0 + 10 = **60 → HIGH, HOLD**. This is an **expected false hold**. The trusted contact (family) knows about the wedding and releases it quickly. We disclose this rather than tune it away ([JUDGING_STRATEGY.md](JUDGING_STRATEGY.md) §6).

## 7. Data sources and the evaluation dataset

There is **no real bank data**. The synthetic generator (`backend/sim/generator.py`) and the scenario definitions (`backend/sim/scenarios/*.yaml`) are published in the repository. The provenance of each family is in [docs/DATA_SOURCES.md](docs/DATA_SOURCES.md).

### 7.1 Scenario families

| ID | Label | Pattern | Grounding |
|---|---|---|---|
| P1 | coercion | Classic: FD broken, pooled, new payee, RTGS within hours, over 3 days | Hyderabad SBI ₹46 L case and similar |
| P2 | coercion | Split: several transfers to 2–4 new payees across 5–17 days | Mumbai Mulund (Jan 14–31 2026) |
| P3 | coercion | No FD. Savings pooled from several accounts, new payee, NEFT | Generic pattern from reports |
| P4 | coercion | Compressed: all stages within one day | Several reports of same-day pressure |
| P5 | coercion | Cover story: the teller records "says it's for property". Behaviour is identical to P1 | Mangaluru (land-purchase story) |
| P6 | coercion | Pre-staged payee: the payee is added 3–6 days before the transfer | Generator variant (tests the "< 2 h" assumption) |
| P7 | coercion | Branch only, no app or call signal. Teller checklist is the only signal | Hyderabad, Navi Mumbai |
| N1 | genuine | Property instalment to an established builder payee | Hard negative |
| N2 | genuine | FD matures normally and is reinvested in the customer's own account | Hard negative |
| N3 | genuine | Medical emergency: new hospital payee, ₹2–5 L IMPS, no FD | Hard negative |
| N4 | genuine | Wedding: FD broken, several new merchant payees, ₹3–10 L | Hard negative (expected friction) |
| N5 | genuine | Child's overseas tuition: FD broken, new university payee, ₹10–30 L | Hard negative (expected friction) |
| N6 | genuine | Business current account with frequent large RTGS | Hard negative |

### 7.2 Splits (reducing circularity)

- Weights and thresholds may be tuned **only** on seeds `0–99`.
- Reported metrics come from seeds `100–299`. Each seed randomises amounts (×0.3–3), gaps between stages, number of accounts, history length (20–365 days) and background noise.
- Families **P6 and N5 are held out entirely** from tuning, as a within-synthetic generalisation check.
- The family mix in the evaluation is fixed and published (default: 1 episode per family per seed, plus 50 customers' routine background). False hold rates are reported **per family**, so the aggregate cannot be gamed through the mix.

### 7.3 Metrics

The definitions are in [PRD.md](PRD.md) §9. `make eval` writes `reports/eval/<timestamp>.md` and `.json`, containing:

1. Overall metrics plus 95% Wilson confidence intervals for rates.
2. A per-family table: n, ALLOW / WARN / HOLD counts, interception or false-hold rate.
3. A tier confusion table by label.
4. Distributions of reason-code frequency.
5. The config version, git commit, seeds, and the disclaimer: *"Synthetic data generated from public case patterns. Not evidence of real-world performance."*

## 8. Modelled trusted-contact response (for the "added delay" metric)

These are **assumptions** (A-05), not measurements. The response is drawn from a log-normal distribution with median 8 minutes and p90 25 minutes. There is a 15% chance of no response, in which case the hold goes to the officer review queue at the end of the cooling-off period (default 240 min). The report states these parameters next to the delay metric.

## 9. Confidence and uncertainty handling

- Thunai produces a **score and tier, not a probability**, so it never claims "93% likely coerced".
- A low-confidence baseline is surfaced as a reason. Officers see "limited history" next to the amount multiple.
- Simulated signals are tagged `source: "SIMULATED"` in evidence and shown with a "Simulated" chip in the UI whenever `THUNAI_DEMO_MODE=true`.
- Missing signals contribute 0, never negative points. Absence of evidence never lowers the risk, except through the two dampeners that rest on positive evidence of an established relationship.

## 10. Latency and cost

- Scoring is pure Python over in-memory structures. It loads the baseline, open episode, payee and signals in ≤ 5 indexed queries. Target p95 ≤ 300 ms end to end (NFR-01).
- There is no model-serving infrastructure. The marginal cost per assessment is about zero.
- The LLM narrative (FR-21) is requested only when an officer clicks *Generate report draft*. That is about 1.5k input and 600 output tokens, roughly **US$0.02 per report** on `claude-opus-5-5` (US$4 / US$20 per million tokens as of 2026-10). It is never on the decision path.

## 11. Failure handling and fallbacks

| Failure | Behaviour |
|---|---|
| Baseline missing | Use population defaults. Add `BASELINE_LOW_CONFIDENCE` |
| FRI adapter error or timeout (> 300 ms) | Treat as unknown (0 points). Add the info reason `FRI_UNAVAILABLE`. Log a warning |
| Call signal stale (> 30 min after the call ended) | Ignore it |
| Scoring config fails validation at startup | The app **refuses to start** (fail closed at deploy time, not at runtime) |
| Unhandled exception during assessment | Return 503 `ASSESSMENT_UNAVAILABLE`. The caller (core banking) applies its own fallback policy. The documented recommendation is "manual review for ≥ ₹2 L". Never silently ALLOW |
| LLM error, timeout, refusal or validation failure | Use the template narrative. `narrative_source = TEMPLATE`. The UI says "Drafted from template" |

## 12. The LLM component (FR-21, Should Have)

### 12.1 Scope

The LLM drafts **only** the free-text "incident description" section of the report draft. Structured fields (amounts, timestamps, payee bank, IFSC, masked account, UTR) are filled **deterministically** from the database and are never generated.

### 12.2 Provider and model

- Anthropic Claude via the official `anthropic` Python SDK. The default model is `claude-opus-5-5` (configurable through `THUNAI_LLM_MODEL`), with low effort because the task is short and templated.
- Timeout `THUNAI_LLM_TIMEOUT_SECONDS` (default 10), SDK `max_retries=1`.
- Use structured output (`output_config.format` with a JSON schema) so the response is guaranteed-valid JSON.
- Enable server-side refusal fallbacks as described in the SDK docs. **The implementer must follow the current SDK documentation and not guess parameter names.**
- Disabled by default: `THUNAI_LLM_ENABLED=false`. Tests never call the real API.

### 12.3 Privacy: pseudonymised input

The prompt never contains names, phone numbers, full account numbers or addresses. The service replaces them with placeholders (`[CUSTOMER]`, `[PAYEE_ACCOUNT_LAST4=4821]`) and re-inserts them locally after validation. In the MVP all data is fictional anyway. In production, sending data to an external LLM would need bank approval or a bank-approved deployment.

### 12.4 Prompt (v1, stored in `backend/app/integrations/llm/prompts/report_narrative_v1.md`)

```text
System:
You draft the incident-description paragraph of a cybercrime complaint for an Indian bank
officer to review. Use ONLY the facts provided in <facts>. Do not add, infer or estimate any
amount, date, time, name, phone number, account, organisation or claim that is not in <facts>.
If a detail is unknown, omit it. Write in plain, neutral English, past tense, 120–200 words.
Do not accuse any named person. Refer to the customer as [CUSTOMER].
Return JSON matching the schema.

User:
<facts>
{facts_json}
</facts>
```

Output schema: `{"narrative_en": string, "facts_used": [fact_id, ...]}`. A Tamil narrative is out of scope for the LLM. The Tamil teller script and warnings are fixed, reviewed strings.

### 12.5 Hallucination mitigation (deterministic validator)

1. Extract every number, ₹ amount, date and time from `narrative_en` using a regex.
2. Each one must normalise to a value present in `facts_json`. Otherwise reject.
3. Reject the output if it contains any of the deny-list terms (e.g., "confirmed fraudster", "criminal" followed by a name).
4. Every `facts_used` id must exist.
5. On rejection, fall back to the template and log `llm_validation_failed` with the reason (no content).
6. A human officer always reviews and edits before marking the report "filed externally".

### 12.6 Evaluation of the LLM component

Run 20 fixed fact sets (from P1–P7). Measure (a) the validator pass rate, (b) any fabricated facts the validator missed (manual check), and (c) officer edit distance (qualitative). Target: 0 fabricated facts reach the UI. The results go in `reports/llm-eval/`. **Not yet run.**

## 13. Human review

- Every hold is reviewable by an officer, with the full reasons and timeline.
- No automated action is taken against a customer beyond a **temporary** hold that the customer can cancel. Nothing is taken against a payee.
- The trusted contact can *release* a HIGH hold, but cannot move money and cannot extend a hold on their own. "This looks like a scam" moves the hold to officer review.
- The officer note is mandatory. Every action is in `audit_log`.

## 14. Known failure modes (disclosed)

| Mode | Example | Mitigation |
|---|---|---|
| False hold on a genuine life event | Wedding, tuition, medical (N3–N5) | Fast trusted-contact release, a polite non-accusatory script, per-family false-hold disclosure |
| Missed slow-burn coercion | A scammer spreads stages over more than 7 days | The window is configurable. Future work: decay instead of a hard window |
| Missed small repeated transfers | Many transfers below ₹2 L | Future work: cumulative episode amount (post-hackathon) |
| A scammer coaches the customer to add a payee days earlier | P6 | The NEW_PAYEE < 7 d tier and the FRI and call signals still contribute. Measured on the held-out family |
| A trusted contact who is complicit or unreachable | — | A VERY_HIGH hold needs an officer anyway. The 72 h activation delay and change reason apply. An unreachable contact routes to the officer |
| Weights that do not transfer to real data | — | That is why this is v1 and hand-set, with the logistic-regression calibration (FR-26) and real bank pilots as next steps |
