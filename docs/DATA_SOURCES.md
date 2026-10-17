# Thunai — Data Sources, Provenance and Licensing

## 1. Summary

| Data | Real or synthetic | Source | Licence / terms | Used for |
|---|---|---|---|---|
| Customers, accounts, transactions, payees | **Synthetic** | `backend/sim/generator.py` (ours) | Same licence as this repo | Demo and evaluation |
| Scenario families P1–P7, N1–N6 | **Synthetic**, *patterned on* public reports | `backend/sim/scenarios/*.yaml` (ours), with the grounding in §3 | Same licence as this repo. The news reports are cited, not copied | Demo and evaluation |
| DoT FRI ratings | **Simulated** | The `fri_mock_ratings` table, seeded by us | — | The FRI signal in the demo |
| Phone call-risk flag | **Simulated** | The replayer posts it to `/signals/call` | — | The call signal in the demo |
| Fictional names | Synthetic | A hand-written list in `sim/names.py`, each with a "(fictional)" suffix | — | Display |
| Statistics in the pitch and PRD | Real, secondary | News and legal reporting (§2) | Cited with a link. No content is reproduced beyond short quotes | Problem evidence |
| Tamil UI copy | Original (team-written and reviewed) | — | Repo licence | UI |

**No personal data from real people is used.** Do not add screenshots of real victims, real phone numbers or real account details, even from news articles.

## 2. Problem-evidence sources (checked on 2026-10-17; re-check before quoting)

| Claim | Source |
|---|---|
| The Supreme Court (4 Aug 2026) directed RBI to frame an SOP within 4 weeks, reportedly including temporary debit holds. There are grievance and restoration mechanisms. The I4C status report says complaints fell from 1,23,672 (2024) to 58,249 (2025) | [MediaNama](https://www.medianama.com/2026/08/223-sc-rbi-sop-review-compensation-digital-arrests/), [Bar & Bench](https://www.barandbench.com/news/supreme-court-issues-directions-to-curb-digital-arrest-scams-asks-rbi-to-frame-sop-on-mule-accounts), [ANI](https://aninews.in/news/national/general-news/supreme-court-issues-nationwide-directions-to-curb-digital-arrest-scams20260804190532/), [Vision IAS](https://visionias.in/current-affairs/news-today/2026-08-05/security/supreme-court-mandates-sops-to-curb-digital-arrests-ensure-time-bound-refunds) |
| About ₹1,935 crore was lost to digital arrest in 2024 (parliamentary data, via secondary reporting) | [Digital Arrest Scams Explained (PDF)](https://frankonfraud.com/wp-content/uploads/2026/01/Digital-Arrest-Scams-Explained.pdf), [Wikipedia: Digital arrest scam](https://en.wikipedia.org/wiki/Digital_arrest_scam). **Prefer the original Lok Sabha/Rajya Sabha answer if it can be found** |
| Overall 2025 cyber-fraud losses of about ₹19,813 crore (I4C, via IANS). Other sources report higher figures, so quote with the source | [IANS](https://ianslive.in/indians-lose-over-rs-52976-crore-to-cyber-frauds-over-six-years-report--20260103154943), [Moneylife](https://moneylife.in/article/fraud-alert-india-is-losing-over-22000-crore-a-year-in-cyber-scams-and-the-worst-is-yet-to-come/80612.html) |
| DoT FRI (launched 21 May 2025), rated Medium / High / Very High and shared via DIP | [Sanchar Saathi PDF](https://www.sancharsaathi.gov.in/SancharSaathiDocuments/ImportantDocuments/DoT%20Introduces%20Financial%20Fraud%20Risk%20Indicator%20(FRI)%20to%20strengthen%20Cyber%20Fraud%20Prevention.pdf), [Business Standard](https://www.business-standard.com/industry/news/dot-launches-financial-fraud-risk-indicator-to-aid-cybercrime-detection-125052101912_1.html), [Voice&Data](https://www.voicendata.com/news/dot-launches-financial-fraud-risk-indicator-to-curb-cybercrime-in-digital-payments-9149405) |
| "There is no concept of digital arrest in our legal statutes or Constitution" and "there is no provision for digital arrest". Bengaluru Police Commissioner B. Dayananda, PTI, 24 Dec 2024. **Opened and confirmed on 2026-10-17.** This is the only source to quote on slides for this claim. Do not cite a government release unless it has been opened | [Siasat / PTI](https://www.siasat.com/digital-arrest-scam-bengaluru-police-appeals-to-public-to-stay-alert-3153633/). Similar statements, **not yet opened** (don't quote): Hyderabad CP VC Sajjanar ([Siasat](https://www.siasat.com/hyderabad-police-commissioner-cautions-against-digital-arrest-scam-3315060/amp/)), Mumbai Police ([Outlook Money](https://www.outlookmoney.com/news/no-such-concept-as-digital-arrest-exists-under-the-law-mumbai-police-launches-awareness-drive-for-senior-citizens)) |
| Twilio: international-route SMS to India doesn't need DLT | [Twilio India SMS guidelines](https://www.twilio.com/en-us/guidelines/in/sms) |

## 3. Case grounding for scenario families (to extend in T-023 / T-049)

Each row is a **publicly reported case**, coded into Thunai's stage model. Fill in more rows (target 10+). Record only what the article states. Don't invent details.

| # | Case (as reported) | Date | S1 liquidation | S2 pooling | S3 new payee | S4 large transfer | Call / isolation | Branch? | Outcome | Family | Source |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | Retired couple, SBI Chandrayangutta, Hyderabad, ₹46 L | Nov 2024 | not stated | not stated | ICICI Aurangabad account | RTGS ₹46 L | 3 days of video "surveillance" | Yes | Stopped by staff, 1930 complaint | P1/P7 | [Telangana Today](https://telanganatoday.com/hyderabad-alert-sbi-staff-avert-digital-arrest-scam-being-perpetrated-save-46-lakh-of-elderly-couple), [Siasat](https://www.siasat.com/sbi-official-thwarts-digital-arrest-scam-in-hyderabad-saves-rs-46-lakh-3136695/amp/) |
| 2 | 61-year-old, SBI AC Guards, Hyderabad, ₹13 L | see source | — | — | — | Withdrawal | Repeated visits | Yes | Staff delayed it and asked for a family member. Connected to 1930 on the 3rd visit | P7 | [Outlook Money](https://www.outlookmoney.com/news/sbi-hyderabad-saves-senior-citizen-from-rs-13-lakh-scam) |
| 3 | Elderly couple, Mangaluru, ₹84 L FD | see source | FD | — | — | Planned transfer | Cover story: land in Bengaluru | Yes | Manager suspicious, police foiled it | P5 | [Deccan Herald](https://www.deccanherald.com/india/karnataka/mangaluru/alert-bank-manager-mulki-police-foil-rs-84-lakh-digital-arrest-fraud-attempt-3820300) |
| 4 | Retired bank manager, Mulund, Mumbai, ~₹1.83 Cr | 14–31 Jan 2026 | — | — | — | Multiple RTGS over 17 days | Threats | — | Lost | P2 | [Free Press Journal](https://www.freepressjournal.in/mumbai/mumbai-cyber-fraud-62-year-old-retired-canara-bank-manager-duped-of-183-crore-in-digital-arrest-scam-case-registered) |
| 5 | 73-year-old retired LIC manager, Moradabad, ₹27 L | see source | FD broken | — | — | RTGS | Told to keep the phone on | — | Lost | P1 | [the420.in](https://the420.in/moradabad-digital-arrest-retired-lic-manager-27-lakh-fraud) |
| 6 | 80-year-old, Unity SFB, Navi Mumbai | see source | FD move attempted | — | Various banks | ₹21.94 L already sent | — | Yes | Partly stopped | P2/P7 | [Free Press Journal](https://www.freepressjournal.in/mumbai/navi-mumbai-alert-bank-manager-saves-80-year-old-man-from-losing-12-lakh-in-digital-arrest-scam) |
| 7 | Woman bank manager, Jaipur, ₹17 L | see source | FD broken | — | — | Transfers | 5 h video call | — | Lost | P4 | [hellobanker.in](https://hellobanker.in/bank-manager-held-hostage-on-video-call-in-jaipur) |
| 8 | Jodhpur, ₹1.85 Cr RTGS, then a ₹22 L NEFT flagged | Feb 2026 (article date) | — | — | — | RTGS and NEFT | Worried demeanour | Yes (PNB) | Partly recovered | P2 | [ETV Bharat](https://www.etvbharat.com/en/state/jodhpur-senior-citizen-duped-of-more-than-rs-1-dot-5-crore-through-digital-arrest-enn26022402537) |

**Caution:** these are news reports. The amounts and details are as reported, not verified. The scenario YAML files take *structure and timing patterns* from them, never personal details.

## 4. Hard-negative grounding

N1–N6 are common genuine high-value life events (property, FD maturity, medical, wedding, education, business). They are generated from plausible patterns, not from specific cases. Their parameters are documented in each YAML file.

## 5. Collection plan (post-hackathon)

| Data | Plan | Constraint |
|---|---|---|
| Real labelled coercion cases | A partnership with a bank fraud team. Anonymised case timelines | A DPDP-compliant data-sharing agreement |
| Interview data (A-05, A-06) | 5+ seniors, 5+ adult children, 2+ branch staff. Notes anonymised | Informed consent. No recordings without consent |
| FRI | DIP onboarding through a partner bank | DoT terms |
| Call signal | A bank app SDK prototype on test devices | Platform policies (Android/iOS) and consent |
