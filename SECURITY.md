# Thunai — Security, Privacy and Responsible-Use

Thunai makes **consequential decisions about people's money**. It can delay a transfer, involve a family member and prepare a cybercrime report. This document treats both security (protecting the system) and safety (protecting the people affected by the system) as requirements.

> **MVP scope reminder.** The hackathon build uses only synthetic, fictional data. The controls marked **[MVP]** are implemented and tested. Those marked **[Prod]** are documented requirements for a real deployment and are not built.

---

## 1. Assets

| Asset | Sensitivity |
|---|---|
| Customer financial behaviour (transactions, balances, payees) | High |
| Trusted-contact phone numbers | High (personal data) |
| Call-risk flags (on a call, duration) | High (behavioural, consent-based) |
| Hold decisions and officer notes | High (consequential, auditable) |
| Contact tokens, JWTs, the service key, encryption and HMAC keys | Critical |
| Scoring config (weights, thresholds) | Medium. Integrity matters more than confidentiality |
| Fraud report drafts | High |

## 2. Threat model

### 2.1 Adversaries

| ID | Adversary | Goal |
|---|---|---|
| ADV-1 | **The scammer** controlling the victim (on a video call) | Get the money out despite Thunai: coach answers, swap the trusted contact, rush the release, impersonate the bank or a relative |
| ADV-2 | An external attacker on the internet | Read or alter data, forge contact responses, abuse the API |
| ADV-3 | A malicious or careless insider (teller/officer) | Release a hold improperly, snoop on customers |
| ADV-4 | A compromised dependency or leaked secret | Code execution, token forgery |

### 2.2 Threats and controls

| ID | Threat (STRIDE) | Adversary | Control | Status |
|---|---|---|---|---|
| T-01 | Scammer coaches the victim to give a cover story ("property purchase") | ADV-1 | The teller "customer said" text is **never scored**. Scoring uses behaviour only (A-07). Scenario P5 tests it | [MVP] |
| T-02 | Scammer makes the victim replace the trusted contact with the scammer's number (**Spoofing**) | ADV-1 | A new or changed contact becomes effective only after **72 h**. A change within 7 days adds `TRUSTED_CONTACT_RECENTLY_CHANGED` (+10). A contact inside the activation window is never notified, and the hold goes to an officer (AC-12) | [MVP] |
| T-03 | Scammer phones the trusted contact pretending to be the bank, or sends a fake link | ADV-1 | The message tells the contact to call the customer **on a number they already know**. The contact page shows no payee or reason details that could be exploited. [Prod]: a sender ID registered through DLT and a fixed short domain | [MVP] copy / [Prod] sender |
| T-04 | Forged or replayed trusted-contact response (**Spoofing/Tampering**) | ADV-2 | 32-byte random token, SHA-256 at rest, 30 min TTL, single use (a conditional UPDATE), rate-limited, uniform 404/410 timing, no token in logs | [MVP] |
| T-05 | A trusted contact (or someone holding their phone) releases a VERY_HIGH hold | ADV-1 | VERY_HIGH needs officer review. Contact confirmation is only recorded | [MVP] |
| T-06 | Insider releases a hold without justification (**Repudiation/Elevation**) | ADV-3 | OFFICER role only, mandatory note, an append-only audit entry with actor, time and request id. [Prod]: four-eyes approval for VERY_HIGH, and an alert when a hold is released within 5 min of creation | [MVP] note+audit / [Prod] four-eyes |
| T-07 | Broken object-level authorisation, e.g., a customer reads another customer's transfer (**Information disclosure**) | ADV-2 | Ownership checks in the services. 404 for objects the caller doesn't own. Tests for every customer and teller endpoint (T-043) | [MVP] |
| T-08 | Mass assignment, e.g., a client sets `status=EXECUTED` | ADV-2 | Pydantic request models with `extra="forbid"`. State changes happen only through explicit service methods with a transition table | [MVP] |
| T-09 | Injection (SQL, log, header) | ADV-2 | SQLAlchemy parameterised queries only, structured JSON logs (no string interpolation of user input into log format strings), no raw SQL from input | [MVP] |
| T-10 | XSS through names, notes or narratives | ADV-2 | React escaping and no `dangerouslySetInnerHTML`. LLM output is rendered as plain text. CSP header `default-src 'self'` on the built SPA [MVP: set in `vite preview` / hosting config] | [MVP] |
| T-11 | JWT forgery or theft | ADV-2/4 | HS256 with a ≥ 32-byte secret from env and a 60 min expiry. The algorithm is pinned on decode. The MVP stores the token in memory plus `sessionStorage` (an accepted demo risk). [Prod]: HttpOnly SameSite cookies, refresh rotation and an IdP (bank SSO) | [MVP] / [Prod] |
| T-12 | Credential stuffing on login | ADV-2 | argon2id, 10/min/IP and 5 failures/15 min/username, a generic error message. [Prod]: MFA for staff | [MVP] |
| T-13 | Service key leaked, so fake events are injected (**Tampering**) | ADV-4 | Key from env, constant-time compare, service routes are separate. [Prod]: mTLS between CBS and Thunai, key rotation, IP allow-list | [MVP] / [Prod] |
| T-14 | Simulated FRI or demo endpoints reachable in production | ADV-2 | `/demo/*` returns 403 unless `THUNAI_DEMO_MODE=true`. Startup **refuses** `DEMO_MODE=true` when `THUNAI_ENV=production` | [MVP] |
| T-15 | Engine failure becomes a silent ALLOW (**Denial of service → fail-open**) | ADV-2 | Errors return 503. The caller's documented fallback is manual review for ≥ ₹2 L | [MVP] |
| T-16 | Tampering with scoring weights | ADV-3/4 | Config in the repo (reviewed by PR), validated at startup, and its `config_version` stored on every assessment. No runtime edit endpoint in the MVP (FR-28 is Could) | [MVP] |
| T-17 | Leaking data to the LLM provider | — | Off by default. Pseudonymised facts only, with no names, phones or full account numbers ([AI_DESIGN.md](AI_DESIGN.md) §12.3). [Prod]: a bank-approved deployment or no LLM | [MVP] |
| T-18 | Prompt injection via customer-reported text in the narrative | ADV-1/2 | Customer-reported text is passed as quoted data in `<facts>`. The deterministic validator rejects facts that aren't in the input. Output is plain text and never executed. An officer reviews it | [MVP] |
| T-19 | A scammer watching over video reads the reasons on the customer's screen and adapts | ADV-1 | The customer screen shows one generic line. Detailed reasons go to staff only | [MVP] |
| T-20 | Vulnerable dependency | ADV-4 | Lockfiles, `pip-audit`, `npm audit`, minimal dependencies, gitleaks | [MVP] |

## 3. Authentication and authorisation

| Role | Can |
|---|---|
| CUSTOMER | Read their own overview and transfers, initiate transfers, respond to warnings, cancel their own held transfers, manage their own consents and trusted contact |
| TELLER | Read the branch queue and holds, submit the checklist, view the script, create and edit report drafts, resend the contact message |
| OFFICER | Everything TELLER can, plus resolve holds, mark reports filed, read the dashboard, customers and audit |
| ADMIN | Read everything, plus demo control and the FRI simulator (demo mode only). **Cannot resolve holds** (separation of duties) |
| Service key | `/events`, `/signals/call`, `/transfers/assess`, `GET /transfers/{ref}` |
| Contact token | `GET`/`POST /trusted/{token}` for its own request only |

The enforcement layers are (1) FastAPI route dependencies `require_roles(...)` and (2) service-level ownership and branch checks. The full matrix is in [DATABASE_SCHEMA.md](DATABASE_SCHEMA.md) §6. Every endpoint has a test for 401, 403 and an allowed role (T-043).

## 4. Input validation

- All bodies are Pydantic models with `extra="forbid"`, explicit length limits, enums, regexes (IFSC, E.164, refs) and numeric bounds (amount 1 to 10¹³ paise).
- Path and query parameters are typed. Pagination is capped at a `limit` of 100.
- `/signals/call` **rejects** any unknown field. This is a structural guarantee that no call content can be submitted.
- Free-text fields (notes, customer said, narrative) are length-capped, stored as-is, and rendered as text.
- The request body size limit is 64 KB (middleware).

## 5. Secrets management

- All secrets come from the environment ([ENVIRONMENT.md](ENVIRONMENT.md)). `.env` is git-ignored, and only `.env.example` (with placeholders) is committed.
- Required secrets are `THUNAI_JWT_SECRET`, `THUNAI_SERVICE_API_KEY`, `THUNAI_PII_ENCRYPTION_KEY` and `THUNAI_HMAC_KEY`. Optional ones are `TWILIO_*`, `TELEGRAM_*` and `ANTHROPIC_API_KEY`.
- Startup fails if a required secret is missing, or if it still equals its `.env.example` placeholder while `THUNAI_ENV=production`.
- Seeded demo passwords come from `THUNAI_SEED_PASSWORD` and are never hard-coded.
- gitleaks runs before every push (T-045). If a secret is committed: rotate it immediately (§10). Rewriting history isn't enough.

## 6. Data minimisation (what we deliberately do **not** collect)

- No call audio, transcripts, caller numbers, contact lists or app names. The call signal is a consented boolean-like flag plus duration (NFR-08).
- No date of birth, gender, address, Aadhaar/PAN or religion. Age appears only in fictional scenario narratives.
- Payee-linked phone numbers are stored only as HMAC plus last 4 digits.
- The trusted-contact page shows only the customer's first name, the amount and the channel.
- Logs never contain tokens, full phone numbers, passwords or full account numbers. A logging filter masks `\+?\d{10,}` patterns (T-005).

## 7. Encryption

| Data | In transit | At rest |
|---|---|---|
| All API traffic | [MVP local]: HTTP on localhost/LAN (accepted demo risk). [Hosted/Prod]: HTTPS only, plus HSTS | — |
| Trusted-contact phone, Telegram chat id | — | Fernet (AES-128-CBC + HMAC-SHA256) with `THUNAI_PII_ENCRYPTION_KEY` [MVP] |
| Payee-linked numbers | — | HMAC-SHA256 (not reversible) [MVP] |
| Passwords | — | argon2id [MVP] |
| Contact tokens | — | SHA-256 hash [MVP] |
| Database volume | — | [Prod] managed-DB encryption, plus KMS-managed keys and key rotation |

## 8. Rate limiting and abuse prevention

The limits are in [API_SPEC.md](API_SPEC.md) §2.4. They are in-memory, which is valid for a single process (`uvicorn --workers 1`). Contact-message resends are limited to 3 per hold per hour, to prevent harassing the contact. A trusted contact can only respond. They cannot initiate anything.

## 9. Logging and audit

- **Application logs:** structured JSON with `timestamp, level, request_id, route, status, latency_ms, actor_type, actor_id`, and no personal data. Domain events are logged by code (`assessment.created tier=VERY_HIGH decision=HOLD`).
- **Audit log** (`audit_log` table): append-only, covering every assessment, hold transition, contact request (sent, opened, responded), officer decision, report change, login success or failure, and consent change. Rows are never updated or deleted by the application (enforced by test).
- **Reproducibility:** every assessment stores `input_snapshot` and `config_version` (NFR-09).

## 10. Incident response (hackathon-scale runbook)

1. **Detect:** gitleaks alert, unexpected audit entries, or an error spike in the logs.
2. **Contain:** rotate the affected secret (JWT secret → all sessions invalidated; service key → update the simulator env; PII key → requires re-encryption, so **don't** rotate casually; use a key-versioned Fernet `MultiFernet` [Prod]). Take the hosted demo offline if needed (Render "suspend").
3. **Assess:** query the `audit_log` for the affected window.
4. **Recover:** redeploy from the last known good commit ([DEPLOYMENT.md](DEPLOYMENT.md) §8).
5. **Record:** add a dated entry to `DECISIONS.md`, "Incidents".

[Prod]: follow the bank's incident policy, report to CERT-In within the mandated window (CERT-In Directions 2022: 6 hours for specified incidents), and meet RBI cyber-incident reporting requirements.

## 11. Responsible use: false positives, false negatives, bias and human oversight

### 11.1 Who can be harmed

| Affected person | Possible harm | Mitigation |
|---|---|---|
| A genuine customer (false positive) | A delayed time-critical payment (hospital, property registration), embarrassment, a feeling of being distrusted | Holds only at HIGH and above. Fast release by the trusted contact. An officer release path. The customer can always cancel. Polite non-accusatory copy. False-hold rates disclosed per family. A "planned large payment" pre-registration as future work (with care, because scammers could coach it) |
| A coerced customer (false negative) | Loss of life savings | Multi-signal fusion. The teller checklist as a human safety net. Warnings at MEDIUM. Disclosure that the system is not a guarantee |
| The trusted contact | Distress, being drawn into a scam, privacy exposure | Minimal information. Clear instructions. Never asked to pay or share an OTP |
| The payee (who may be an innocent account holder) | Being labelled a criminal | Thunai **does not** label or act on the payee. FRI is a third-party signal shown as "rated by DoT FRI", not an accusation. Report drafts say "beneficiary account" and never "fraudster" |
| Tellers and officers | Blame for misses or false holds | Decision support with recorded reasons. Final responsibility follows bank policy |

### 11.2 Prohibited designs (enforced in review)

- No automated accusation of anyone. No account freezing or permanent block. No action against the payee.
- No decision based **solely** on one external signal. FRI raises the score, and only FRI = VERY_HIGH sets a floor of HIGH (a temporary hold that is reviewable).
- No identification of individuals from call data. No surveillance of the call content.
- No use of protected attributes (age, gender, religion, caste, location, language) as scoring features. `preferred_language` is used **only** to choose the display language (enforced by `tests/test_no_protected_features.py`, which checks the scoring input schema).

### 11.3 Bias monitoring

- In the MVP, the evaluation report breaks down hold rates by scenario family. Synthetic customers have no demographic attributes, so demographic fairness **cannot be measured** in the MVP. We say so.
- [Prod]: monitor hold and false-hold rates by branch, channel and (where lawfully held) age band, as an *outcome audit*, not as a feature. Run a quarterly review of weights with a fraud and compliance committee.

### 11.4 Human oversight

The officer reviews every VERY_HIGH hold. Every hold has an officer path. Release decisions need a note. Overrides of the model are expected and audited. They are not penalised.

## 12. Dependency security

- Keep dependencies minimal ([TECH_STACK.md](TECH_STACK.md)), with committed lockfiles.
- `uv run pip-audit` and `npm audit --omit=dev` run in the release gate. High or critical findings block the release unless an exception is documented with its rationale.
- No packages with post-install scripts unless they are well known (the Vite/Playwright toolchain).
- Python YAML is parsed with `safe_load` only.

## 13. Legal and regulatory considerations (not legal advice; validate with counsel)

| Area | Relevance | Status |
|---|---|---|
| **Digital Personal Data Protection Act 2023 (DPDP)** and Rules | Consent for the call signal and trusted-contact sharing, purpose limitation, retention, data-principal rights (access, correction, erasure, grievance) | The design has consent records, minimisation and retention ([DATABASE_SCHEMA.md](DATABASE_SCHEMA.md) §5). Check which Rules provisions are in force at deployment |
| **Supreme Court directions (Aug 2026) and RBI SOP** on digital-arrest scams | Expected to cover bank safeguards, including temporary debit holds and grievance or restoration mechanisms | Thunai is designed to be explainable and auditable to fit this. **The final SOP text has not been reviewed.** Update this row when the SOP is published |
| **RBI Master Directions on Fraud Risk Management** (2024) and customer-protection circulars | Fraud monitoring, reporting and customer liability | Officer workflow and reporting drafts align. Verify the specific clauses |
| **Authority to delay a customer-authorised payment** | The bank's T&Cs, payment-system rules (RTGS/NEFT) and the SOP | **Open legal question (A-02).** Background only, not yet confirmed from primary sources: FINRA Rule 2165 (US brokerages, temporary holds for suspected exploitation of specified adults), Georgia HB 945 (2026, bank holds for adults 65+ with trusted-contact notification) |
| **Telecom / DoT FRI** | Use of FRI data under DoT/DIP terms | Simulated only. A real use requires DIP onboarding |
| **SMS rules (TRAI TCCCPR, DLT)** | Commercial SMS in India needs DLT registration | The demo uses Twilio's international route (DLT not required per Twilio's guidance; verify) or Telegram. [Prod]: a bank DLT sender and templates |
| **IT Act 2000 and CERT-In Directions** | Security practices and incident reporting | §10 |
| **PMLA** record keeping | Retention of transaction records | §5 of the schema doc |

## 14. Data deletion

- [MVP] `POST /demo/reset` truncates all transactional tables. Synthetic data only.
- [Prod] Erasure requests: delete or anonymise the trusted-contact phone and consents, subject to legally required retention for transactions, assessments and audit (retained with access restricted). Call-risk signals are purged after 90 days by a scheduled job.

## 15. Reporting a vulnerability

During the hackathon, tell the team lead directly. Don't open a public issue with exploit details.
