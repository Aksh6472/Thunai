# Kaaval AI — Three-Minute Demo Script

**Honesty rules for this demo:**
- All customers, accounts and transactions are **synthetic and fictional**.
- The FRI rating and the phone call signal are **simulated** and carry a visible SIMULATED chip.
- The opening story is a **real, publicly reported case**, cited on the slide.
- Any metric shown must be copied from `reports/eval/<ts>.md` and labelled "synthetic evaluation". **If the evaluation hasn't run, show no numbers.**

## 1. Cast and setup

| Role | Who | Device |
|---|---|---|
| Presenter | Team member A | Demo laptop (mirrored to the projector) |
| "Arun", the trusted contact | Team member B, standing near the judges | Their real phone, with the SMS/Telegram channel set up, on the team hotspot |
| Backup operator | Team member C | Second laptop with the backup video, paused |

**Before going on stage:** complete the pre-flight checklist in [DEPLOYMENT.md](DEPLOYMENT.md) §7. Do `POST /demo/reset`. Arrange the browser tabs: ① `/demo` ② `/ops` ③ `/teller` ④ slides. Set the speed to **4320×**.

**Test data:** seed 42. Hero = `CUST-0007` "R. Kamala (fictional)", Tamil preference, trusted contact "Arun (son)" pointing at member B's phone. Genuine = `CUST-0012` "Mr. Iqbal (fictional)". The scenario files are `backend/sim/scenarios/P1_classic.yaml` and `N1_property.yaml`.

## 2. Script

| Time | On screen | Say (approximately) | Expected output |
|---|---|---|---|
| **0:00–0:20** | Slide 1: a photo-free title card with a news headline quote and its source | "In November 2024, a retired couple walked into an SBI branch in Hyderabad to send ₹46 lakh. For three days, scammers posing as CBI officers had kept them on video calls under so-called 'digital arrest'. They were saved because one bank employee noticed they looked anxious. That's the safety net today: luck." | — |
| **0:20–0:35** | Slide 2: "The customer is genuine. The pressure is the fraud." Four icons: FD broken → money pooled → new payee → large RTGS | "Bank fraud systems look for impostors or mule accounts. Here, the real customer authenticates perfectly. But coercion leaves a trail across *days*. Kaaval AI watches that sequence, and responds the way the best bank staff do: pause, bring in family, report to 1930." | — |
| **0:35–0:45** | Tab ①, `/demo`: click **Run P1 — Classic digital arrest** | "This is a simulated bank with 50 synthetic customers. I'll fast-forward three days of Kamala's activity into a minute." | The clock starts moving. "Day 1" appears |
| **0:45–1:30** | Tab ②, `/ops`: watch the Watchlist and the row for Kamala | **Day 1:** "She breaks a ₹35 lakh FD early. Unusual, but alone it's nothing: score 15." **Day 2:** "Money is pooled into one account, and her phone reports, with her prior consent, that she has been on a video call with an unknown number for over three hours. We get only that flag, never the audio. Now 40: she's on the watchlist." **Day 3:** "A new payee is added. Two hours later she's at the branch asking for a ₹46 lakh RTGS." | The watch score chart steps 15 → 40 → 63. Then a **VERY_HIGH HOLD** row appears at the top with "₹46,00,000" |
| **1:30–1:50** | Click the row, then the hold detail. Point at the ReasonList | "Every hold is explained. ₹46 lakh is 115 times her usual transfer. The payee is 2 hours old. The FD was broken. Funds were pooled. Each line has its points, and they add up to the score. No black box. Two signals are simulated here, the DoT fraud-risk rating and the call flag. **Take them away and she still scores 80. She's held on her behaviour alone.**" | Eight reasons, SIMULATED chips on the FRI and call reasons, score 100 |
| **1:50–2:15** | Tab ③, `/teller`: the alert banner. Press **1** (on a call) and **4** (mentions CBI), then **Apply**. Toggle the script to **தமிழ்** | "At the counter, the teller taps what she sees. Kaaval adds it instantly. And she gets a script, in Tamil for Kamala, telling her there is no such thing as a digital arrest. As Bengaluru's police commissioner put it, 'there is no concept of digital arrest in our legal statutes'." | Reasons update within 2 s. The Tamil script renders |
| **2:15–2:35** | `/demo` → Console messages shows a **QR code**. Member B scans it with their phone *(the default; use the real SMS/Telegram only if it was delivered 3/3 in rehearsal)* | "Meanwhile, Kamala's son Arun, her pre-registered trusted contact, gets this link." (B opens it and taps **This looks like a scam**.) | The phone shows the contact page. On the laptop, the hold detail shows "Response: This looks like a scam" |
| **2:35–2:45** | Hold detail: **Generate report draft**. **Pause on it for 3 seconds** so the "1930" and "cybercrime.gov.in" fields are readable. Then type a note and **Cancel transfer** | "This is the report for the 1930 helpline and cybercrime.gov.in, pre-filled: amount, timeline, beneficiary bank. The officer cancels with a note, and it's all audited. The ₹46 lakh never left." | The report draft shows its structured fields, including helpline 1930 and the portal link. Status: **Cancelled** |
| **2:45–2:55** | `/demo`: **Run N1 — Property instalment** (completes in about 3 s), then `/ops` | "Same size of payment, but Mr. Iqbal has paid this builder every quarter for two years. Allowed. No hold, no questions." | No new alert. N1's transfer shows EXECUTED in the Demo panel log |
| **2:55–3:00** | Slide 3: the evaluation results (synthetic) plus the ask | "On held-out synthetic scenarios built from public case patterns: [interception X%, false holds Y%, read from the report]. Kaaval AI: protect the customer, not just the account." | — |

> If any number on slide 3 isn't from the latest evaluation report, **delete it**. Say instead: "We measure interception and false-hold rate; the report is in the repo."

**Category check (Citizen scam/fraud defense):** the 1930 / cybercrime.gov.in report path must be visible on screen (2:35–2:45), and it must be shown on the warning screen as the 1930 button. Never skip it, even when running short of time on stage. Instead, shorten the N1 segment to running it and saying one sentence. The N1 flow itself is still built and shown.

**Slide rules:** the "no digital arrest" line may be quoted only as the Bengaluru Police Commissioner's statement (PTI, 24 Dec 2024). Keep FINRA/Georgia and any unopened government release off the slides.

## 3. Measurable benefit to state

- **Interception:** the share of coercion episodes held before money leaves (target ≥ 90%, synthetic).
- **Friction:** genuine high-value transfers held (target ≤ 5% overall), plus the per-family table, including the honest false holds on weddings and tuition.
- **Time:** the 1930 report draft is pre-filled in seconds instead of being typed by hand. Present this as a qualitative claim unless it is timed in rehearsal.

## 4. Differentiators to make visible

1. A **multi-day sequence**: the watch score climbs across three days.
2. It protects the **sender under coercion** and does not chase the receiver.
3. **The intervention is automated**: a cooling-off hold plus a trusted person, the human safeguard that works in practice.
4. It works the **same at the branch and in the app**, with no call audio needed.
5. **Every hold is explained**, with points that add up.

## 5. Likely failure points and live recovery

| What goes wrong | Recovery on stage (≤ 10 s) |
|---|---|
| The SMS/Telegram doesn't arrive (only if you chose the SMS path) | Presenter: "Network's slow, so here's the same link." Switch to the default **QR code** in `/demo` → Console messages. B scans it |
| Hotspot or venue Wi-Fi is down | The laptop demo is fully local. Read the console message aloud and click the link on the laptop in a mobile-size window |
| The scenario run stalls | `/demo` → Reset → Run again (the run takes ~60 s). If it's still stuck, restore the snapshot (pre-staged at day 3, just before the RTGS) |
| The browser or app crashes | Switch to the backup video at the matching timestamp, and keep narrating |
| A judge asks to see code | Open `backend/app/domain/scoring.py` and `config/scoring_v1.yaml` (keep them pinned in the IDE) |

## 6. Backup plan if an external API or the internet fails

- **The SMS provider fails:** use the console notifier (which needs no network), shown via the Demo panel or QR.
- **The LLM is unavailable:** the template narrative is the default. The demo doesn't depend on the LLM.
- **No internet at all:** the entire demo runs locally (NFR-04). Fonts are self-hosted.
- **The laptop dies:** the second laptop has the repo cloned and the snapshot. Otherwise play the **backup video** (≤ 3:00, recorded at G5, captioned "Recorded run of the live system").

## 7. Rehearsal log (fill in)

| # | Date/time | Duration | Issues | Fix |
|---|---|---|---|---|
| 1 | | | | |
| 2 | | | | |
| 3 | | | | |
