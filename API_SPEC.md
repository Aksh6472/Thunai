# Thunai — API Specification (v1)

- **Base URL:** `http://localhost:8000/api/v1` locally. The hosted URL is listed in [DEPLOYMENT.md](DEPLOYMENT.md).
- **Format:** JSON, UTF-8. Timestamps are ISO 8601 with offset. Money is integer **paise** (`*_paise`).
- **Machine-readable contract:** FastAPI generates `/openapi.json`, and the frontend types are generated from it (`npm run gen:api`). If this document and the OpenAPI output disagree, **fix both in the same PR**.

## 1. Authentication

| Caller | Mechanism | Header |
|---|---|---|
| Staff (TELLER, OFFICER, ADMIN) and demo customers (CUSTOMER) | `POST /auth/login` returns a JWT (HS256, 60 min, claims `sub`, `role`, `branch`, `exp`, `jti`) | `Authorization: Bearer <jwt>` |
| Core-banking simulator (service) | A static API key from `THUNAI_SERVICE_API_KEY`, compared in constant time | `X-Thunai-Service-Key: <key>` |
| Trusted contact | A single-use token in the URL path (32 random bytes, base64url, SHA-256 at rest, 30 min TTL) | — |
| Public | None (health endpoints only) | — |

Status codes: 401 means no or invalid credentials. 403 means the credentials are valid but the role or ownership doesn't permit the action.

## 2. Common conventions

### 2.1 Error envelope (every non-2xx response)

```json
{
  "error": {
    "code": "HOLD_NOT_FOUND",
    "message": "No hold with that id.",
    "details": {},
    "request_id": "req_01HZX3…"
  }
}
```

| HTTP | Typical `code`s |
|---|---|
| 400 | `BAD_REQUEST` |
| 401 | `UNAUTHENTICATED`, `INVALID_CREDENTIALS`, `TOKEN_EXPIRED` |
| 403 | `FORBIDDEN`, `CONSENT_REQUIRED`, `DEMO_MODE_DISABLED` |
| 404 | `<ENTITY>_NOT_FOUND` |
| 409 | `INVALID_STATE_TRANSITION`, `IDEMPOTENCY_CONFLICT` (same key, different body) |
| 410 | `CONTACT_LINK_EXPIRED` (used or expired) |
| 422 | `VALIDATION_ERROR` (`details.fields: [{loc, msg}]`), `INSUFFICIENT_BALANCE`, `NOTE_REQUIRED` |
| 429 | `RATE_LIMITED` (with a `Retry-After` header) |
| 503 | `ASSESSMENT_UNAVAILABLE`, `DEPENDENCY_UNAVAILABLE` |

Error messages never include stack traces, SQL, tokens or personal data. Every response carries an `X-Request-ID` header.

### 2.2 Pagination (list endpoints)

The API uses cursor pagination: `?limit=50&cursor=<opaque>`. The maximum `limit` is 100 and the default is 50. Responses look like `{"items": [...], "next_cursor": "…" | null}`. The cursor is a base64url-encoded `(sort_key, id)`.

### 2.3 Idempotency

- `POST /events` is keyed by `event_id`. `POST /transfers/assess` and `POST /customer/transfers` are keyed by `transfer_ref`.
- A repeat with an identical body returns `200` and the original result, with the header `Idempotent-Replay: true`.
- A repeat with a different body returns `409 IDEMPOTENCY_CONFLICT`.

### 2.4 Rate limits (in-memory, per process; a single instance is enough for the MVP)

| Scope | Limit |
|---|---|
| `POST /auth/login` | 10 / min / IP and 5 failures / 15 min / username |
| `/trusted/{token}*` | 10 / min / token and 30 / min / IP |
| Service-key endpoints | 1200 / min / key (the simulator runs at high speed) |
| Other authenticated endpoints | 300 / min / user |

Rate limiting is bypassed when `THUNAI_ENV=test` (unit and integration tests, and the evaluation harness running at infinite speed). The rate-limit tests turn it on explicitly with a fixture.

### 2.5 Shared schemas

```jsonc
// Reason
{"code": "NEW_PAYEE", "points": 20, "stage": "S3" | null,
 "evidence": {"payee_age_minutes": 128, "source": "SIMULATED"?},
 "text_en": "…", "text_ta": "…"}

// AssessmentResult
{"transfer_ref": "TRF-2026-000913", "transfer_status": "HELD",
 "decision": "ALLOW" | "WARN" | "HOLD",
 "tier": "LOW" | "MEDIUM" | "HIGH" | "VERY_HIGH",
 "score": 100, "raw_score": 115, "reasons": [Reason], "overrides_applied": ["FRI_VERY_HIGH_FLOOR"],
 "hold_id": "uuid" | null, "assessment_id": "uuid", "config_version": "scoring_v1@2026-10-17",
 "assessed_at": "…"}
```

Enum values are exactly those in [DATABASE_SCHEMA.md](DATABASE_SCHEMA.md).

---

## 3. Auth

### `POST /auth/login` (public, rate-limited)
Request `{"username": "teller.priya", "password": "…"}`. Both fields are required, 1–128 characters.

Response 200:
```json
{"access_token": "eyJ…", "token_type": "bearer", "expires_in": 3600,
 "user": {"id": "…", "role": "TELLER", "display_name": "Priya (fictional)", "branch_code": "CHN001"}}
```
For a CUSTOMER, `user` also carries `customer_ref` (e.g. `CUST-0007`); it is `null` for staff.

Errors: 401 `INVALID_CREDENTIALS`, which is the same message for an unknown user or a wrong password. 429 after 10 attempts per minute per IP, or after 5 failures in 15 minutes for one username (even with the right password).

A valid service key sent to a user route gets 403, and a valid JWT sent to a service route gets 403 (ARCHITECTURE §4.5). A wrong service key gets 401.

### `GET /auth/me` (any JWT)
Returns the `user` object.

---

## 4. Ingestion (service key)

### `POST /events`
```json
{
  "event_id": "EVT-7f3a91",
  "customer_ref": "CUST-0007",
  "event_type": "FD_CLOSED",
  "occurred_at": "2026-10-01T10:05:00+05:30",
  "account_ref": "XXXXXX7710",
  "amount_paise": 3500000000,
  "payload": {"maturity_date": "2027-04-01", "proceeds_to_account": "XXXXXX2201"}
}
```

`payload` is validated by `event_type`:

| event_type | Required payload |
|---|---|
| `FD_CLOSED` | `maturity_date`, `proceeds_to_account` |
| `INTERNAL_TRANSFER_IN` | `from_account`, `to_account` (both the customer's own) |
| `PAYEE_ADDED` | `payee_ref`, `display_name`, `bank_name`, `ifsc`, `masked_account`, `channel`, and optional `linked_msisdn` (E.164; HMAC'd on receipt, never stored raw) |
| `TRUSTED_CONTACT_CHANGED` | `display_name`, `relationship`, `phone_e164`, `preferred_language` (encrypted on receipt) |
| `ROUTINE_DEBIT` / `ROUTINE_CREDIT` | `counterparty`, optional `payee_ref` |

Response 202:
```json
{"event_id": "EVT-7f3a91", "stage_detected": "S1_LIQUIDATION",
 "episode": {"id": "…", "watch_score": 15, "watch_tier": "LOW"}}
```
Errors: 404 `CUSTOMER_NOT_FOUND`, 409, 422.

### `POST /signals/call`
```json
{"customer_ref": "CUST-0007", "call_type": "VIDEO", "caller_known": false,
 "duration_min": 190, "ended_at": null, "observed_at": "2026-10-02T18:40:00+05:30"}
```
- `call_type` must be one of `VOICE` or `VIDEO`.
- `duration_min` must be between 0 and 1440.
- The request is rejected with **403 `CONSENT_REQUIRED`** unless the latest `CALL_SIGNAL` consent is granted.
- **No caller number, app name, audio or content fields exist, and unknown fields are rejected with 422.**

Response 202 `{"accepted": true, "episode": {…watch…}}`.

### `POST /transfers/assess`
```json
{
  "transfer_ref": "TRF-2026-000913",
  "customer_ref": "CUST-0007",
  "from_account": "XXXXXX2201",
  "payee_ref": "PAY-0007-03",
  "amount_paise": 460000000,
  "rail": "RTGS",
  "channel": "BRANCH",
  "initiated_at": "2026-10-03T11:20:00+05:30",
  "scenario_label": "P1"
}
```
`scenario_label` is accepted only when `THUNAI_DEMO_MODE=true`. It is stored for evaluation and never read by the engine.

Response 200 `AssessmentResult`. Side effects:
- ALLOW: the transfer becomes `EXECUTED` (simulated).
- WARN: the transfer becomes `WARNED`, pending acknowledgement.
- HOLD: the transfer becomes `HELD`, a hold is created, and trusted-contact notification is enqueued.

Errors: 404 (customer, account or payee), 409, 422, 503 `ASSESSMENT_UNAVAILABLE`. The engine **never** silently allows when it fails.

### `GET /transfers/{transfer_ref}` (service key, or OFFICER/TELLER)
Returns the transfer status plus the latest `AssessmentResult`.

---

## 5. Customer app (role CUSTOMER; only the customer's own resources)

| Method & path | Purpose | Request → Response |
|---|---|---|
| `GET /customer/overview` | Accounts (masked) and payees | → `{accounts:[…], payees:[…], trusted_contact:{display_name, phone_last4, status, effective_from} \| null}` |
| `POST /customer/transfers` | Initiate a transfer from the app (channel APP) | Same body as `/transfers/assess` minus `customer_ref`/`channel`/`scenario_label` → `{transfer_ref, transfer_status, decision, hold_id?, message_key}`. This is a **customer-safe** response: no score, tier detail or reasons (ADR-013, SECURITY T-19). `message_key` selects the generic copy in [DESIGN.md](DESIGN.md) §6.3. The full `AssessmentResult` is still stored and visible to staff. 422 `INSUFFICIENT_BALANCE` if the amount exceeds the balance |
| `GET /customer/transfers/{transfer_ref}` | Poll status | → `{transfer_status, decision, hold_status?, message_key}` |
| `POST /customer/transfers/{transfer_ref}/warning-response` | Respond to a WARN | `{"action": "CONTINUE" \| "CANCEL"}` → 200 `{transfer_status}`. 409 if the transfer is not WARNED |
| `POST /customer/transfers/{transfer_ref}/cancel` | Cancel a held transfer | → 200 `{transfer_status: "CANCELLED"}` |
| `POST /customer/consents` | Grant or revoke a consent (FR-23) | `{"consent_type": "CALL_SIGNAL", "granted": true, "text_version": "call_signal_v1"}` → 201 |
| `POST /customer/trusted-contact` | Register or replace the trusted contact (FR-24) | `{"display_name", "relationship", "phone_e164", "preferred_language"}` → 201 `{status: "PENDING_ACTIVATION", effective_from}` |

---

## 6. Holds and officer review

### `GET /holds?status=AWAITING_OFFICER&tier=VERY_HIGH&limit=&cursor=` (TELLER, OFFICER, ADMIN)
Items:
```json
{"id": "…", "transfer_ref": "TRF-2026-000913", "customer": {"external_ref": "CUST-0007", "display_name": "R. Kamala (fictional)"},
 "amount_paise": 460000000, "tier": "VERY_HIGH", "status": "AWAITING_OFFICER",
 "contact_response": "REPORT_SUSPICIOUS", "top_reasons": [Reason, Reason, Reason],
 "created_at": "…", "cooling_off_until": "…"}
```
Sort: VERY_HIGH first, then `cooling_off_until` ascending.

### `GET /holds/{id}` (TELLER, OFFICER, ADMIN)
Returns the full hold plus `assessments: [AssessmentResult…]` (history), `episode` (stages and `watch_history`), `contact_requests: [{channel, delivery_status, sent_at, opened_at, responded_at, response}]` (never tokens), and `report_id | null`.

### `POST /holds/{id}/officer-decision` (OFFICER)
```json
{"decision": "RELEASE" | "CANCEL_TRANSFER" | "KEEP_HOLDING", "note": "Spoke with son and customer in person; genuine tuition payment."}
```
`note` is required (10–1000 characters). Without it the response is 422.

| Decision | Effect |
|---|---|
| RELEASE | The hold becomes `RELEASED` and the transfer `EXECUTED`. The episode becomes `CLOSED_BENIGN` |
| CANCEL_TRANSFER | The hold becomes `CANCELLED` and the transfer `CANCELLED`. The episode becomes `CLOSED_CONFIRMED_RISK` |
| KEEP_HOLDING | No state change. The note is audited |

Errors: 409 `INVALID_STATE_TRANSITION` if the hold is already resolved.

### `POST /holds/{id}/resend-contact` (TELLER, OFFICER)
Expires earlier links and sends a new one. Returns 409 if there is no active contact or the hold is resolved.

---

## 7. Teller

### `GET /teller/queue` (TELLER, OFFICER)
Branch-channel transfers that are WARNED or HELD, plus active branch holds. Same item shape as `/holds`, plus `channel`.

### `POST /teller/transfers/{transfer_ref}/checklist` (TELLER, OFFICER)
```json
{"items": ["ON_CALL", "DISTRESSED", "FOLLOWING_INSTRUCTIONS", "MENTIONS_AUTHORITY"], "customer_said": "Says it is for a property purchase."}
```
- `items` is a subset of the four values, and an empty list is allowed.
- `customer_said` is optional, free text, ≤ 500 characters. It is stored as a note and **never scored** (A-07).
- The call stores a `TELLER_CHECKLIST` signal and re-scores with `trigger=TELLER_CHECKLIST`. If the transfer was ALLOW-executed already, the response is 409.
- A re-score may **escalate** a decision (WARN → HOLD, HIGH → VERY_HIGH) but never de-escalates an existing hold.

Response 200: the new `AssessmentResult`.

### `GET /teller/holds/{id}/script?lang=ta|en` (TELLER, OFFICER)
```json
{"lang": "ta", "tier": "VERY_HIGH",
 "steps": [{"id": "greet", "text": "…"}, {"id": "no_digital_arrest", "text": "…"}, {"id": "ask_family", "text": "…"},
           {"id": "offer_1930", "text": "…"}, {"id": "do_not", "text": "…"}],
 "reviewed_by_native_speaker": true}
```
The content is fixed and reviewed (not generated). It is defined in `backend/app/domain/i18n/scripts.yaml`.

---

## 8. Reports (1930 / cybercrime.gov.in drafts)

### `POST /holds/{id}/report` (TELLER, OFFICER)
Creates or returns the draft. Request `{"use_llm": false}`. `true` is honoured only if `THUNAI_LLM_ENABLED=true`.

Response 201:
```json
{"id": "…", "status": "DRAFT",
 "structured_fields": {
   "incident_category": "Online Financial Fraud — impersonation / 'digital arrest' (suspected)",
   "transaction": {"amount_paise": 460000000, "rail": "RTGS", "initiated_at": "…", "status": "HELD — not executed",
                   "from_account_masked": "XXXXXX2201", "beneficiary_bank": "Example Bank",
                   "beneficiary_ifsc": "EXMP0001234", "beneficiary_account_masked": "XXXXXX4821"},
   "timeline": [{"at": "…", "what": "Fixed deposit closed before maturity"}],
   "helpline": "1930", "portal": "https://cybercrime.gov.in"},
 "customer_reported": {},
 "narrative_text": "…", "narrative_source": "TEMPLATE",
 "disclaimer": "Draft for officer review. Not submitted. File via 1930 or cybercrime.gov.in."}
```
If the LLM fails, the response is still 201 with `narrative_source: "TEMPLATE"` and the response header `X-Thunai-LLM-Fallback: <reason_code>`.

### `PATCH /reports/{id}` (TELLER, OFFICER)
`{"customer_reported": {"claimed_agency": "CBI", "scammer_numbers_given_by_customer": ["+91…"], "platform": "WhatsApp video"}, "narrative_text": "…", "status": "READY"}`. Editing `narrative_text` sets `narrative_source=EDITED`.

### `POST /reports/{id}/mark-filed` (OFFICER)
`{"acknowledgement_number": "…"}` (1–64 characters, `[A-Za-z0-9/-]`) sets the status to `FILED_EXTERNALLY`.

---

## 9. Trusted contact (public; the token is the credential)

### `GET /trusted/{token}`
It sets `opened_at`. Response 200 contains only consented, minimal data:
```json
{"customer_first_name": "Kamala", "amount_display": "₹46,00,000", "channel": "BRANCH",
 "held_at": "…", "bank_helpline": "1800-XXX-XXXX (fictional)", "language": "ta",
 "already_responded": false}
```
**Never returned:** payee details, reasons, scores, account numbers or the customer's phone number. The response is 410 `CONTACT_LINK_EXPIRED` if the link is used or expired, and 404 for an unknown token. The response time is uniform for 404 and 410 so tokens can't be enumerated.

### `POST /trusted/{token}/response`
`{"response": "CONFIRM_GENUINE" | "REPORT_SUSPICIOUS" | "CANNOT_REACH"}`

| Response | HIGH hold | VERY_HIGH hold |
|---|---|---|
| CONFIRM_GENUINE | RELEASED and EXECUTED | Recorded and stays AWAITING_OFFICER |
| REPORT_SUSPICIOUS | Moves to AWAITING_OFFICER, flagged | Recorded and flagged |
| CANNOT_REACH | Moves to AWAITING_OFFICER | Recorded |

The token is consumed (single use). Response 200 `{"result_key": "RELEASED" | "SENT_TO_OFFICER", "message": "…localised…"}`. Errors: 410, 404, 409 (hold already resolved), 429.

---

## 10. Ops dashboard (OFFICER, ADMIN; TELLER read-only where noted)

| Method & path | Purpose |
|---|---|
| `GET /dashboard/summary` | `{active_holds, awaiting_contact, awaiting_officer, warnings_today, watchlist_count, amount_on_hold_paise, data_label: "SYNTHETIC"}` |
| `GET /alerts?kind=HOLD\|WARN\|WATCH&tier=&limit=&cursor=` | A unified, urgency-sorted queue (TELLER can read) |
| `GET /customers?search=&limit=&cursor=` | Search by `external_ref` or display name |
| `GET /customers/{id}/risk` | The current episode (stages, watch score, `watch_history`), the baseline, and recent assessments (TELLER can read) |
| `GET /customers/{id}/timeline?days=14` | Events, signals, transfers and assessments in time order |

---

## 11. Demo control (ADMIN; only when `THUNAI_DEMO_MODE=true`, otherwise 403 `DEMO_MODE_DISABLED`)

| Method & path | Purpose |
|---|---|
| `GET /demo/scenarios` | `[{id: "P1", title, label, customer_ref, description, expected_decision}]` |
| `POST /demo/reset` | Truncate the transactional tables, re-seed (seed 42) and reset `sim_state`. Target ≤ 10 s |
| `POST /demo/scenarios/{id}/run` | `{"speed": 4320}`, in simulated seconds per real second. 4320 makes 3 days ≈ 60 s. The run happens in the background replayer. Returns 202 `{run_id}` |
| `GET /demo/clock` | `{sim_now, speed, running_scenario}` |
| `POST /demo/fri` | `{"linked_msisdn": "+91…", "rating": "HIGH"}`. Upserts a **simulated** FRI rating |
| `GET /demo/console-messages?limit=20` | Recent console-notifier messages (the fallback when SMS is unavailable) |

---

## 12. Health (public)

| Path | Response |
|---|---|
| `GET /healthz` | `200 {"status": "ok"}` if the process is alive |
| `GET /readyz` | `200 {"status": "ready", "db": "ok", "scoring_config": "scoring_v1@…", "notifier": "console"}`, or 503 with the failing component |

---

## 13. Example: hero flow

```bash
# 1. Simulator posts day-3 payee addition
curl -s -X POST localhost:8000/api/v1/events \
  -H "X-Thunai-Service-Key: $THUNAI_SERVICE_API_KEY" -H 'Content-Type: application/json' \
  -d '{"event_id":"EVT-P1-0007","customer_ref":"CUST-0007","event_type":"PAYEE_ADDED",
       "occurred_at":"2026-10-03T09:12:00+05:30",
       "payload":{"payee_ref":"PAY-0007-03","display_name":"Verification Account","bank_name":"Example Bank",
                  "ifsc":"EXMP0001234","masked_account":"XXXXXX4821","channel":"APP","linked_msisdn":"+919800000193"}}'
# → 202 {"event_id":"EVT-P1-0007","stage_detected":"S3_NEW_PAYEE","episode":{"watch_score":63,"watch_tier":"HIGH"}}

# 2. Branch RTGS assessment
curl -s -X POST localhost:8000/api/v1/transfers/assess -H "X-Thunai-Service-Key: $THUNAI_SERVICE_API_KEY" \
  -H 'Content-Type: application/json' \
  -d '{"transfer_ref":"TRF-P1-0001","customer_ref":"CUST-0007","from_account":"XXXXXX2201","payee_ref":"PAY-0007-03",
       "amount_paise":460000000,"rail":"RTGS","channel":"BRANCH","initiated_at":"2026-10-03T11:20:00+05:30"}'
# → 200 {"decision":"HOLD","tier":"VERY_HIGH","score":100,"raw_score":115,"hold_id":"…", "reasons":[…8 reasons…]}
```

These responses are the **specified expected outputs** (AC-01). They are not results yet.
