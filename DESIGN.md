# Thunai — UI/UX Design Specification

This document specifies five surfaces, each built around one primary workflow:

| Surface | Route | Primary user | Primary job |
|---|---|---|---|
| Teller console | `/teller` | Teller (P3) | Recognise a coerced customer at the counter and respond correctly |
| Ops dashboard | `/ops`, `/ops/holds/:id`, `/ops/customers/:id` | Officer (P4) | Work the queue of holds and watch-listed customers, then decide |
| Customer app simulator | `/customer` | Protected customer (P1) | See a warning or hold in their own language, and call 1930 |
| Trusted-contact page | `/t/:token` | Trusted contact (P2) | Understand in 10 seconds, call the customer, and respond |
| Demo control | `/demo` | Presenter (ADMIN) | Reset, run scenarios and show the simulated clock |

The dashboard is **action-oriented**. Every number on it links to a queue item. There are no decorative charts.

---

## 1. Design principles

1. **Protect, don't accuse.** All copy says the transfer is *paused for your safety*. It never says the customer is a victim, a suspect or "fraud". The payee is never called a fraudster in the UI. The wording is "unverified new payee".
2. **Reasons before scores.** Plain-language reasons are the headline. The numeric score is secondary, and tiers are always text plus an icon, never colour alone.
3. **One next action.** Each screen has one obvious primary action: Call 1930, Respond, Apply checklist, Release/Cancel.
4. **Senior-first for customer surfaces.** Large type, high contrast, Tamil first when that is the preferred language, and no jargon.
5. **Honest demo.** Simulated data and signals carry a visible `SIMULATED` chip when `THUNAI_DEMO_MODE=true`.
6. **Fast under pressure.** Tellers and officers can work entirely from the keyboard. The critical information is above the fold at 1366×768.

## 2. Personas and accessibility needs

| Persona | Device | Needs | Design response |
|---|---|---|---|
| P1 Customer (72, Tamil) | Phone (simulated in a 390×844 frame) | Reduced vision, anxiety, possibly being watched on a video call | Body text ≥ 18 px and headline ≥ 24 px. 1930 button ≥ 56 px tall. Tamil first. Short sentences. No timers that create panic |
| P2 Trusted contact | Phone browser, possibly a slow network | Understand instantly, act in one tap | Three large stacked buttons. Page weight < 150 KB excluding fonts. Works without JS hydration delays (keep it simple) |
| P3 Teller | Desktop 1366×768+ | Speed, a non-confrontational script | Alert banner. Checklist toggles with keys 1–4. Script panel |
| P4 Officer | Desktop 1440+ | Evidence, accountability | Reason list with evidence, a multi-day timeline, a mandatory note |

Accessibility target: **WCAG 2.1 AA** across the app, and checked manually on the customer and trusted-contact pages (NFR-06). Requirements:
- Contrast ≥ 4.5:1 for text and ≥ 3:1 for UI components.
- Visible focus rings (2 px `--color-focus`).
- Every interactive element is reachable by keyboard, in a logical order.
- `aria-live="polite"` for queue updates and `assertive` for new VERY_HIGH holds on the teller console.
- `lang="ta"` on Tamil text nodes.
- Touch targets ≥ 44×44 px (56 px on customer and contact pages).
- No information conveyed by colour alone.
- Respect `prefers-reduced-motion`.

## 3. Information architecture and navigation

```text
/login
/ops                       Ops dashboard (queue)            OFFICER, ADMIN
  /ops/holds/:holdId       Hold detail (decision screen)    OFFICER, ADMIN
  /ops/customers/:id       Customer risk view               OFFICER, ADMIN (TELLER read)
/teller                    Teller console                   TELLER, OFFICER
  /teller/holds/:holdId    Case at counter                  TELLER, OFFICER
/customer                  Customer app simulator           CUSTOMER
/t/:token                  Trusted-contact page             public (token)
/demo                      Demo control                     ADMIN
```

- **Staff top bar** (all staff routes): Thunai logo · links allowed by role (Ops, Teller, Demo) · `DemoClockBar` (demo mode only: simulated date/time, speed, running scenario) · user menu (name, role, Logout).
- **After login**, users land on TELLER → `/teller`, OFFICER → `/ops`, ADMIN → `/demo`, CUSTOMER → `/customer`.
- **Unauthorised route:** show a 403 page with a "Go to your home" link.

## 4. Key user journeys

These are summarised here. Full flows and edge cases are in [docs/USER_FLOWS.md](docs/USER_FLOWS.md).

1. **J1 Hero (branch).** Watch score climbs on `/ops` over 3 simulated days → the branch RTGS is HELD → a VERY_HIGH alert appears on `/teller` → teller applies the checklist → script → report draft → the trusted contact responds on their phone → the officer cancels on `/ops/holds/:id`.
2. **J2 App warning.** A MEDIUM transfer in `/customer` → warning screen → *Call 1930* or *Cancel* or *Continue*.
3. **J3 HIGH hold released.** The `/customer` hold screen shows "Waiting for Arun" → the contact confirms → the customer screen shows "Released".
4. **J4 Genuine large payment.** The N1 scenario runs → ALLOW → the ops queue shows nothing new. The presenter points out that there was no friction.

## 5. Screen inventory and layouts

### 5.1 Login (`/login`)
- A centred card, 400 px wide: logo, the title "Thunai", username and password fields, a primary button "Sign in".
- In demo mode, a helper panel lists the demo accounts (usernames only; passwords come from the README/env).
- Errors: an inline banner, "Username or password is incorrect" (generic).
- Loading: a button spinner with the button disabled.

### 5.2 Ops dashboard (`/ops`)

```text
┌ Top bar ───────────────────────────────────────────────────────────────────────┐
├ KPI strip (each is a filter button) ───────────────────────────────────────────┤
│ [Awaiting officer 2] [Awaiting contact 1] [Warnings today 4] [Watchlist 3]      │
│ Amount on hold: ₹52,40,000 (SYNTHETIC)                                          │
├ Queue (left, 60%) ──────────────────────────┬ Preview (right, 40%) ────────────┤
│ Tabs: All | Holds | Warnings | Watchlist    │ Selected item summary:            │
│ Row: TierBadge · Customer · ₹ amount ·      │  - Top 3 reasons                  │
│      top reason · contact status ·          │  - Mini watch-score chart         │
│      cooling-off countdown · channel icon   │  - [Open case →]                  │
│ Sort: VERY_HIGH first, then time left       │                                   │
└─────────────────────────────────────────────┴───────────────────────────────────┘
```
- The queue polls every 2 s. New rows slide in with a highlight. Arrow keys move the selection and Enter opens the case.
- **Empty state:** "No customers need attention right now." with a secondary line: "Thunai is monitoring 50 customers (synthetic)."
- **Error state:** an inline banner "Can't reach Thunai server — retrying" while the last data stays visible and dimmed.

### 5.3 Hold detail / decision screen (`/ops/holds/:id`)

```text
┌ Header: TierBadge VERY_HIGH · "₹46,00,000 RTGS to unverified new payee" · status chip ┐
├ Left column (65%) ─────────────────────────────────────┬ Right column (35%) ─────────┤
│ WHY THIS WAS PAUSED (ReasonList, sorted by points)       │ DECISION PANEL              │
│  +20 Payee added 2 hours before this transfer   [S3]     │ Trusted contact: Arun (son) │
│  +20 ₹46,00,000 is 115× usual (₹40,000)         [S4]     │  ● SMS sent 11:21 · opened  │
│  +20 Payee number rated HIGH by DoT FRI [SIMULATED]      │  ● Response: "Looks like a  │
│  +15 FD closed early (₹35,00,000)               [S1]     │    scam" 11:29              │
│  +15 On unknown video call 190 min [SIMULATED]           │ Note (required) [textarea]  │
│  ...                                                     │ [Cancel transfer] (danger)  │
│ ScoreBreakdownBar (stacked by group)                     │ [Release transfer]          │
│                                                          │ [Keep holding]              │
│ EPISODE TIMELINE (3 day lanes)                           │ ─────────────────────────── │
│  Day 1 ●FD closed  Day 2 ●Pooled ●Call  Day 3 ●Payee ●RTGS│ REPORT                      │
│ WATCH SCORE CHART (step line with tier bands)            │ [Generate report draft]     │
│                                                          │ Status: Draft · Template    │
│ ASSESSMENT HISTORY (INITIAL → TELLER_CHECKLIST)          │ AUDIT (last 5 actions)      │
└──────────────────────────────────────────────────────────┴─────────────────────────────┘
```
- Release and Cancel are disabled until the note has ≥ 10 characters. A confirmation dialog repeats the action and the amount.
- After the decision, the hold shows as resolved, the panel turns read-only, and a toast says "Transfer cancelled. Report draft ready."

### 5.4 Customer risk view (`/ops/customers/:id`)
Header (name, masked accounts, language) · baseline card (median transfer, history days, confidence) · current episode (stages, watch score chart) · a 14-day timeline table (events, signals, transfers, decisions).

### 5.5 Teller console (`/teller`, `/teller/holds/:id`)

```text
┌ ALERT BANNER (VERY_HIGH, assertive live region) ─────────────────────────────────┐
│ ⚠ Pause before processing: R. Kamala — ₹46,00,000 RTGS is on safety hold         │
├ Left (55%) ───────────────────────────────────┬ Right (45%) ─────────────────────┤
│ WHAT THUNAI NOTICED (top 5 reasons, plain)     │ GUIDED SCRIPT   [தமிழ் | English] │
│                                                │ 1. Greet calmly…                  │
│ WHAT YOU OBSERVE (tap or press 1–4)            │ 2. "There is no 'digital arrest'  │
│ [1 On a call now] [2 Seems distressed]         │     in Indian law…"               │
│ [3 Following instructions] [4 Mentions police/ │ 3. Ask to call family together…   │
│                     CBI/court]                 │ 4. Offer to call 1930 together    │
│ Customer said (optional, not scored): [_____]  │ ✗ Do not: argue, accuse, or        │
│ [Apply observations]                           │   process the transfer             │
│ Score: 100 · VERY_HIGH (updated 2s ago)        │ [Generate report draft]           │
└────────────────────────────────────────────────┴──────────────────────────────────┘
```
- "What Thunai noticed" shows the top 5 engine reasons plus every applied teller observation.
- Toggles are `aria-pressed` buttons and keys 1–4 toggle them. "Apply" re-scores. While the call is in flight, the toggles are disabled and show a spinner. On success, the reasons list animates in the new items.
- A note under the "Customer said" field reads: "Recorded for the report. Thunai does not change the score based on what the customer says."
- With no active case, the queue list of branch WARN/HOLD items shows, or the empty state "No branch transfers need attention."

### 5.6 Customer app simulator (`/customer`)
It renders inside a `PhoneFrame` (390×844, with rounded bezel art) centred on a neutral background. Screens:

1. **Home:** balance cards (masked), a "Send money" button, the last 5 transfers (each opens its warning, hold or result screen) and a link to Safety settings (FR-23/24).
2. **Send money:** payee select (existing payees, plus the scenario's new payee), amount (₹ formatted with the Indian grouping `46,00,000`), rail, and a "Continue" button. Validation: amount > 0 and ≤ the balance, and a payee is selected. Errors appear inline under the field.
3. **Warning (MEDIUM):** see §6.3. Buttons stack in this order: **Call 1930** (primary, large), **Cancel transfer** (secondary), and **I understand, continue** (tertiary text button, which needs a 3-second read delay before it is enabled. That is a deliberate friction, and the countdown is shown).
4. **Hold (HIGH/VERY_HIGH):** "Your transfer is paused for your safety." Shows who has been asked ("We have messaged Arun (son)"), what happens next, Call 1930, and Cancel transfer. It **does not** show the score or detailed reasons, because a scammer watching over video could use them to coach. It shows *one* generic line: "This transfer looks like patterns used in phone scams."
5. **Released / Cancelled:** a clear success or neutral state.
6. **Language toggle** (தமிழ் / English) in the app header, defaulting to the customer's `preferred_language`.

### 5.7 Trusted-contact page (`/t/:token`) — mobile-first, standalone layout (no staff chrome)

```text
Thunai · [Bank name] safety check                         [தமிழ் | EN]
------------------------------------------------------------------
Kamala's transfer of ₹46,00,000 is paused for safety.
Please CALL HER NOW on the number you know (not a number anyone gives you).

[ ✓ I spoke to her — it's genuine ]        (green, 56px)
[ ⚠ This looks like a scam ]               (red, 56px)
[ ✗ I can't reach her ]                    (neutral, 56px)

Never share OTPs or PINs. The bank will never ask you to transfer money.
Questions? Call the bank: 1800-XXX-XXXX (fictional)
```
- Tapping a button opens a confirmation sheet ("Confirm: you spoke to Kamala and she is making this payment willingly?"), then submits.
- **Result screens:** "Thank you — the transfer has been released." Or: "Thank you — a bank officer will contact Kamala now. If you believe she is in danger, call 1930 or 112."
- **Expired or used link:** "This link has expired or was already used. If you're worried, call the bank or 1930." (The 410 state.)
- **Loading:** a skeleton. **Network error:** "Couldn't connect. Check your internet and tap Retry."

### 5.8 Demo control (`/demo`)
Simulated clock (large) · speed selector (1×, 60×, 1440×, 4320×) · scenario cards (ID, title, label chip COERCION/GENUINE, expected decision, [Run]) · [Reset demo] (with confirm) · "Console messages" panel (the fallback SMS feed, also openable as a QR code for the phone) · FRI simulator form · links that open Ops / Teller / Customer in new tabs.

## 6. Content and copy

### 6.1 Tone
Calm, respectful, short. Second person for customers, third person for staff. Never use "fraud victim", "suspect", "blocked" or "frozen". Use "paused", "safety check" and "unverified".

### 6.2 Tier labels (`TierBadge`)

| Tier | Label EN | Label TA (draft) | Icon |
|---|---|---|---|
| LOW | Low | குறைவு | ● (circle) |
| MEDIUM | Caution | எச்சரிக்கை | ▲ (triangle) |
| HIGH | Hold | நிறுத்தம் | ■ (square) |
| VERY_HIGH | Hold — urgent | அவசர நிறுத்தம் | ◆ (diamond) plus a bold border |

### 6.3 Key customer and contact strings — Tamil: **PENDING NATIVE REVIEW**

The English is the source. The Tamil column is a draft, **pending native review by the team** (owner: WS5, task T-038, NFR-07). Until a reviewer is named in the T-038 PR, treat every Tamil string as unapproved and set `reviewed_by_native_speaker: false`.

The `warn.no_digital_arrest` wording is supported by a quoted police statement. Bengaluru Police Commissioner B. Dayananda said "there is no concept of digital arrest in our legal statutes or Constitution" (PTI, 24 Dec 2024; see [docs/DATA_SOURCES.md](docs/DATA_SOURCES.md) §2). Keep the UI wording consistent with that statement.

| Key | English | Tamil (draft — pending native review) |
|---|---|---|
| `warn.title` | Please pause before you send this money | இந்தப் பணத்தை அனுப்பும் முன் சற்று நிதானியுங்கள் |
| `warn.no_digital_arrest` | There is no "digital arrest" in Indian law. Police, CBI or courts will never ask you to transfer money or stay on a video call. | இந்திய சட்டத்தில் "டிஜிட்டல் கைது" என்று எதுவும் இல்லை. காவல்துறை, சிபிஐ அல்லது நீதிமன்றம் ஒருபோதும் பணம் அனுப்பவோ வீடியோ அழைப்பில் இருக்கவோ சொல்லாது. |
| `warn.call_1930` | Call 1930 (Cyber Crime Helpline) | 1930-ஐ அழைக்கவும் (சைபர் குற்ற உதவி எண்) |
| `warn.cancel` | Cancel this transfer | இந்தப் பரிமாற்றத்தை ரத்து செய் |
| `warn.continue` | I understand, continue | புரிந்தது, தொடரவும் |
| `hold.title` | Your transfer is paused for your safety | உங்கள் பாதுகாப்பிற்காக உங்கள் பரிமாற்றம் தற்காலிகமாக நிறுத்தி வைக்கப்பட்டுள்ளது |
| `hold.generic_reason` | This transfer looks like patterns used in phone scams. | இந்தப் பரிமாற்றம் தொலைபேசி மோசடிகளில் காணப்படும் முறைகளைப் போல் உள்ளது. |
| `hold.contact_asked` | We have messaged {name} ({relationship}). | {name} ({relationship}) அவர்களுக்கு நாங்கள் செய்தி அனுப்பியுள்ளோம். |
| `contact.title` | {name}'s transfer of {amount} is paused for safety. | {name} அவர்களின் {amount} பரிமாற்றம் பாதுகாப்பிற்காக நிறுத்தி வைக்கப்பட்டுள்ளது. |
| `contact.call_now` | Please call them now on the number you know. | உங்களுக்குத் தெரிந்த எண்ணில் இப்போதே அவர்களை அழையுங்கள். |
| `contact.genuine` | I spoke to them — it's genuine | நான் பேசினேன் — இது உண்மையானது |
| `contact.scam` | This looks like a scam | இது மோசடி போல் தெரிகிறது |
| `contact.unreachable` | I can't reach them | அவர்களைத் தொடர்பு கொள்ள முடியவில்லை |

The SMS template (≤ 300 characters, so it fits in 2 segments) reads:
`[Bank] Safety check: {first_name}'s transfer of {amount} is paused. Call them on a number you know, then respond: {link} . We never ask for OTP/PIN.`
The text is written in English or Tamil based on the contact's `preferred_language`. Tamil SMS uses UCS-2, which means more segments. That is acceptable.

## 7. Visual design and tokens

Tokens are defined in `frontend/src/styles/tokens.css` as CSS variables and mapped into Tailwind's theme.

### 7.1 Color

| Token | Light | Dark | Use |
|---|---|---|---|
| `--color-bg` | `#F3F5F9` | `#0B1220` | Page background |
| `--color-surface` | `#FFFFFF` | `#121A2B` | Cards |
| `--color-surface-2` | `#F8FAFC` | `#172036` | Hover rows, inset panels |
| `--color-text` | `#0F172A` | `#E5E9F0` | Body text |
| `--color-text-muted` | `#475569` | `#9AA6B8` | Secondary text |
| `--color-border` | `#E2E8F0` | `#243049` | Dividers |
| `--color-primary` | `#2F5BEA` | `#6B8CFF` | Primary actions, links |
| `--color-primary-strong` | `#1E40AF` | `#93ABFF` | Primary hover, gradients |
| `--color-focus` | `#2563EB` | `#93C5FD` | Focus ring |
| `--color-brand` / `--color-brand-2` | `#0B1B33` / `#13294B` | `#070E1C` / `#0F1A30` | Staff header, login panel, customer app bar |
| `--color-brand-text` / `--color-brand-muted` | `#E6ECF5` / `#94A3B8` | same | Text on brand backgrounds |
| `--color-accent` | `#F5A524` | same | Logo tick, clock dot, avatar initials (never a status) |
| `--color-tier-low` | `#15803D` | `#4ADE80` | LOW |
| `--color-tier-medium` | `#B45309` | `#FBBF24` | MEDIUM |
| `--color-tier-high` | `#C2410C` | `#FB923C` | HIGH |
| `--color-tier-very-high` | `#B91C1C` | `#F87171` | VERY_HIGH, danger buttons |
| `--color-success` | `#15803D` | `#4ADE80` | Released / confirmed |
| `--color-simulated` | `#6D28D9` | `#C4B5FD` | SIMULATED chip |

Tier backgrounds use a 10% tint of the tier color, with the text in the full tier color. Every pair must be checked for ≥ 4.5:1 contrast (T-032 includes a contrast check).

### 7.2 Typography
- **Families:** `Inter` for Latin and `Noto Sans Tamil` for Tamil. Font stack: `"Inter","Noto Sans Tamil",system-ui,sans-serif`.
- **Staff scale (px):** 12 caption · 14 body-sm · 16 body · 20 h3 · 24 h2 · 30 h1. Line height 1.5 for body and 1.25 for headings.
- **Customer and contact scale:** 18 body · 22 emphasis · 28 headline. Tamil line height 1.7 (the script needs room).
- Numbers use `font-variant-numeric: tabular-nums` and Indian grouping via `Intl.NumberFormat('en-IN', {style:'currency', currency:'INR', maximumFractionDigits:0})`.

### 7.3 Spacing, radius, elevation
- The spacing scale is 4 px based: 4, 8, 12, 16, 24, 32, 48.
- Radius: 8 px (inputs and buttons), 14 px (cards), 28 px (phone frame).
- Elevation: cards use `--shadow-card` (`0 1px 2px` + `0 4px 16px` at 5% slate). The phone frame and dialogs use `--shadow-raised`.
- Staff screens sit under a dark brand header (logo, nav, simulated clock, user avatar). KPI tiles carry a tier-coloured edge and icon; queue rows carry a tier-coloured left edge. Colour is never the only signal: the tier badge text stays.

### 7.4 Motion
150–200 ms ease-out for highlights and toasts. New-row highlight: fade the background from tier tint to transparent over 2 s. Everything is disabled under `prefers-reduced-motion`.

## 8. Component library (`frontend/src/components/`)

| Component | Props (key) | Notes |
|---|---|---|
| `Button` | `variant: primary\|secondary\|danger\|ghost`, `size`, `loading` | `loading` disables the button and shows a spinner with `aria-busy` |
| `TierBadge` | `tier`, `size` | Icon, label and color. Never color only |
| `SimulatedChip` | — | Shown only in demo mode |
| `ReasonList` | `reasons: Reason[]`, `lang`, `max?` | Sorted by points descending. Shows `+N`, the text, a stage chip and SimulatedChip when `evidence.source==="SIMULATED"`. Negative points are styled green ("reduces risk") |
| `ScoreBreakdownBar` | `reasons` | A horizontal stacked bar by group (Stage, Signal, Teller, Dampener) |
| `EpisodeTimeline` | `stages`, `transfers`, `signals` | Day lanes in simulated time. Points get an icon plus a label |
| `WatchScoreChart` | `history` | A Recharts step line, y-axis 0–100, with tier bands as background areas and threshold lines at 30/55/75 |
| `HoldStatusChip` | `status`, `contactResponse` | — |
| `ChecklistToggle` | `item`, `pressed`, `hotkey` | `aria-pressed` |
| `ScriptPanel` | `steps`, `lang` | Numbered steps. The "Do not" block is styled as a caution |
| `DecisionPanel` | `hold`, `onDecide` | Mandatory note and confirmation dialog |
| `ReportDraft` | `report`, `onSave` | Structured fields are read-only, the narrative is editable, with copy-to-clipboard |
| `PhoneFrame` | `children` | Visual only |
| `LanguageToggle` | `value`, `onChange` | — |
| `DemoClockBar` | — | Polls `/demo/clock` |
| `KpiFilterButton` | `label`, `count`, `active` | — |
| `EmptyState`, `ErrorBanner`, `Skeleton`, `Toast`, `Dialog` | — | Shared states |

## 9. States (apply to every data view)

| State | Pattern |
|---|---|
| Loading (first) | Skeletons shaped like the content. Never a full-page spinner |
| Loading (refetch) | Silent. A subtle "Updated 2s ago" timestamp |
| Empty | `EmptyState` with an icon, one sentence and, optionally, the next step |
| Error (fetch) | Keep the stale data, dimmed, with an `ErrorBanner` and Retry. Polling backs off (2 s → 4 s → 8 s, max 30 s) |
| Error (mutation) | Inline error near the action, with the server `message`. The form state is preserved |
| Success (mutation) | A toast (4 s) and an updated view. Holds also get a status chip change |
| Permission | 403 page or inline "You don't have access to this action" |

## 10. Form validation

| Form | Field rules | When validated |
|---|---|---|
| Login | Both required | On submit |
| Send money (customer) | Payee required. Amount: an integer of rupees, 1 ≤ amount ≤ balance, displayed with Indian grouping | On blur and submit |
| Officer decision | Note 10–1000 characters | Live counter. The button stays disabled until valid |
| Checklist | Optional "customer said" ≤ 500 characters | Live counter |
| Report | Acknowledgement number 1–64 characters `[A-Za-z0-9/-]` | On submit |
| FRI simulator | E.164 `^\+[1-9]\d{7,14}$`, rating required | On submit |

Server 422 `details.fields` errors map to field messages.

## 11. Responsive behaviour

| Breakpoint | Ops / Teller | Customer / Contact |
|---|---|---|
| ≥ 1280 px | Two columns as drawn | Phone frame centred (customer). Contact page max width 480 px |
| 768–1279 px | Two columns with a narrower right column. The timeline scrolls horizontally inside its card | Same |
| < 768 px | Single column. The right column stacks below. The queue preview becomes a full screen on tap | The customer page drops the frame and goes full-bleed. The contact page is designed for 360 px width |

## 12. Data visualisation rules

- Use only two charts: `WatchScoreChart` (the trend matters, because it is the multi-day story) and `ScoreBreakdownBar` (composition). Everything else is a list or a timeline.
- Tier thresholds are drawn as labelled lines. The y-axis is always 0–100. There are no 3D effects or pie charts.
- Every chart has a text equivalent: the ReasonList and the timeline table, with `aria-describedby`.
- Amounts are always shown with ₹ and Indian grouping. Times are shown in IST, `DD MMM, HH:mm`, with a "Day N" label in demo mode.
