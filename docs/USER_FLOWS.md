# Thunai — User Flows and Edge Cases

The screens are in [DESIGN.md](../DESIGN.md) §5, the endpoints in [API_SPEC.md](../API_SPEC.md) and the states in [DATABASE_SCHEMA.md](../DATABASE_SCHEMA.md) §3.13.

## J1 — Hero: coerced customer at the branch (VERY_HIGH)

```mermaid
sequenceDiagram
  autonumber
  participant SIM as Core-banking sim
  participant K as Thunai API
  participant OPS as Officer (/ops)
  participant TEL as Teller (/teller)
  participant TC as Trusted contact (phone)
  SIM->>K: Day 1 FD_CLOSED (premature) → S1, watch 15
  SIM->>K: Day 2 INTERNAL_TRANSFER_IN ×2 → S2; CALL_RISK 190 min → watch 40 (watchlist)
  K-->>OPS: Watchlist row appears (MEDIUM)
  SIM->>K: Day 3 PAYEE_ADDED → S3, watch 63
  SIM->>K: Day 3 +2h transfers/assess ₹46L RTGS BRANCH
  K-->>SIM: HOLD VERY_HIGH (status AWAITING_OFFICER)
  K-)TC: SMS/Telegram link (contact is active)
  K-->>TEL: Queue: VERY_HIGH alert
  TEL->>K: checklist [ON_CALL, MENTIONS_AUTHORITY] → re-score (escalate-only)
  TEL->>K: GET script?lang=ta
  TC->>K: GET /trusted/{token} → POST REPORT_SUSPICIOUS
  K-->>OPS: Hold shows contact response
  TEL->>K: POST /holds/{id}/report (draft)
  OPS->>K: officer-decision CANCEL_TRANSFER + note
  K-->>SIM: transfer CANCELLED; episode CLOSED_CONFIRMED_RISK
```

**Edge cases:**

| Case | Expected behaviour |
|---|---|
| The customer insists on proceeding | The teller cannot release it. Only the officer can, with a note. The script says to escalate calmly to the branch manager |
| The customer leaves the branch | The hold stays AWAITING_OFFICER. The officer can contact the trusted contact or the customer. The customer can cancel through the app |
| The contact confirms "genuine" on a VERY_HIGH hold | Recorded only. The officer still decides (ADR-012) |
| The contact link has expired | The contact sees the 410 page with a bank and 1930 helpline. Staff use **Resend** (max 3 per hour) |
| The teller ticks items after a decision is final | 409, plus the UI message "Transfer already completed/cancelled" |
| Two tellers open the same case | Both see the same state. Checklist submissions are additive, and the last re-score wins. Escalation is monotonic, so there is no conflict |

## J2 — App transfer with a warning (MEDIUM)

1. The customer logs into `/customer` and chooses Send money: an existing payee, ₹3,00,000 IMPS.
2. The assessment returns WARN and the warning screen appears (Tamil first if the customer prefers it).
3. The customer either:
   - **a.** taps **Call 1930**, which opens the phone dialer (`tel:1930`). The transfer stays WARNED until the customer returns;
   - **b.** taps **Cancel**, and the transfer becomes CANCELLED; or
   - **c.** waits 3 s and taps **Continue**, and the transfer becomes EXECUTED, with the acknowledgement audited.

| Edge case | Behaviour |
|---|---|
| The customer closes the app on the warning | The transfer stays WARNED. [Prod] it auto-expires after 30 min (not built; WARNED transfers are listed on the dashboard) |
| A network error on Continue | An inline error with Retry. Idempotent: the server returns the current status |
| The amount is above the balance | Client validation, and a server 422 `INSUFFICIENT_BALANCE` |

## J3 — HIGH hold released by the trusted contact

1. The app transfer assessment returns HOLD HIGH, and the hold status is AWAITING_CONTACT.
2. The customer screen says "Paused for your safety — we've messaged Arun".
3. Arun opens the link, calls his mother (outside the system), then taps **I spoke to them — it's genuine** and confirms.
4. The hold becomes RELEASED, the transfer EXECUTED and the episode CLOSED_BENIGN. The customer screen polls and shows "Released".

| Edge case | Behaviour |
|---|---|
| Arun taps **I can't reach them** | The hold moves to AWAITING_OFFICER. The customer screen says "A bank officer will contact you" |
| Arun never responds | When the cooling-off period ends (240 min of sim time), the next read moves the hold to AWAITING_OFFICER |
| No trusted contact is registered | The hold starts in AWAITING_OFFICER (override `NO_ACTIVE_TRUSTED_CONTACT`) |
| The contact was registered < 72 h ago | No notification is sent. The officer queue shows the reason `TRUSTED_CONTACT_RECENTLY_CHANGED` (AC-12) |
| The customer cancels while waiting | The hold and transfer become CANCELLED. Any later contact response gets 409 "already resolved" |
| SMS delivery fails | `delivery_status=FAILED`. The console message is available. The officer sees "SMS failed" and can resend or phone the contact |
| The contact taps a button twice | The second request gets 410, and the UI shows the first result |

## J4 — Genuine large payment (ALLOW)

The N1 scenario: an FD is broken and funds are pooled, then ₹40 L goes to a builder the customer has paid quarterly for 2 years. The score is 5 (LOW), the decision ALLOW and the transfer EXECUTED. Nothing appears in the alert queue. The episode remains OPEN, with a watch score from S1+S2 of 25 (LOW). It isn't on the watchlist.

| Edge case | Behaviour |
|---|---|
| Same customer, but to a **new** payee | It scores normally. Behaviour, not the customer's identity, determines the result |

## J5 — Officer works the queue

1. `/ops` shows the KPI strip and a queue sorted VERY_HIGH first, then by time left on the cooling-off period.
2. The officer opens a hold and reads the reasons, the timeline and the contact status.
3. The officer chooses **Release** (for example, after speaking to the customer and family), **Cancel** or **Keep holding**. A note of at least 10 characters is required, followed by confirmation.
4. The result is audited, and the queue updates.

| Edge case | Behaviour |
|---|---|
| Two officers decide at the same time | The first succeeds. The second gets 409 `INVALID_STATE_TRANSITION`, and the UI refreshes |
| An ADMIN tries to resolve a hold | 403 (separation of duties) |

## J6 — Customer registers a trusted contact (Should, FR-23/24)

1. In `/customer`, under Settings, the customer adds a contact (name, relationship, phone, language). The response is PENDING_ACTIVATION with "Active from <+72 h>".
2. They grant the TRUSTED_CONTACT_SHARING consent, after reading the consent text (`trusted_contact_sharing_v1`).

| Edge case | Behaviour |
|---|---|
| Replacing an existing contact | The old one is REVOKED and the new one is pending for 72 h. During the gap, holds route to the officer |
| An invalid phone number | 422, shown inline as "Enter a valid mobile number with country code" |

## J7 — Presenter runs the demo

Go to `/demo` → **Reset** (confirm) → choose a speed → **Run P1** → navigate the tabs → **Run N1**. If something gets stuck: Reset, and run again.

## Cross-cutting edge cases

| Situation | Behaviour |
|---|---|
| A JWT expires mid-session | The API returns 401, and the client redirects to `/login?next=<path>` |
| The API is unreachable | The ErrorBanner appears, the last data is kept and dimmed, and polling backs off |
| Assessment returns 503 | The customer app shows "We couldn't complete this right now. Please try again or visit your branch." The transfer is **not** executed |
| Duplicate submissions | Idempotent by `event_id` and `transfer_ref` |
| A low-confidence baseline (new customer) | Population defaults are used. The officer sees the info reason "Limited history (<30 days)" |
