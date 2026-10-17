# Kaaval AI — Competitor and Alternatives Analysis

> Researched on 2026-10-17 from public sources. Vendor performance figures are **vendor claims**, not independent validation. Items marked *(verify)* still need a primary source.

## 1. Landscape

| Category | Example | Where it acts | What it detects | Covers coerced sender? | Multi-day sequence? | Branch counter? | Family loop? | India 1930/FRI? |
|---|---|---|---|---|---|---|---|---|
| Session behavioural biometrics | **BioCatch Scams360** (launched July 2025) | Digital banking session | Manipulation cues: hesitation, typing, **active phone call**, malicious apps. Up to 3,000 data points (vendor) | **Yes** (APP/social-engineering focus) | Not described publicly *(verify)* | No (digital) | Not described | Not described |
| Bank FRM / transaction monitoring | FICO Falcon, Feedzai, Featurespace (Visa), NICE Actimize, Clari5 (widely used in India) *(verify specifics)* | Payment processing | Transaction anomalies, rules, ML risk scores. Several market APP-scam capabilities | Partly | Varies | Sometimes via the core system | Generally not | Integration-dependent |
| Receiver / mule detection | **RBI MuleHunter.AI** (RBIH; piloted 2024, reported live in 26 banks) | Beneficiary accounts | Mule-account patterns (19 patterns analysed) | No (receiver side) | n/a | n/a | n/a | n/a |
| Telecom number risk | **DoT FRI** (May 2025), shared via DIP | Number-level | Mobile numbers linked to fraud complaints, rated M/H/VH | Indirect | No | No | No | It *is* the Indian signal |
| Payment app protection | **PhonePe Protect** (uses FRI) | UPI app | Blocks or warns on payments to risky numbers | Partly | No | No | No | Yes (FRI) |
| Phone-side scam call protection | **Truecaller Family Protection** (2026: an admin can see flagged calls and hang up remotely); Android scam detection for calls | The phone | Suspicious calls (content or number) | Partly (calls only) | No | No | **Yes** (family admin) | No |
| Call-content AI | DeepVerif.AI (an open-source project), ORACLE (arXiv), Turkish scam-call detection *(verify details)* | Call audio and transcripts | Scam conversation patterns | Yes | No | No | No | No |
| Human safeguards | Alert bank staff (SBI Hyderabad, Mangaluru, Navi Mumbai cases) | Branch | Intuition | Yes | Informal | **Yes** | Ad hoc ("come back with a family member") | Ad hoc 1930 calls |
| Regulatory precedents (**background only; keep off slides unless the primary sources are opened and confirmed**) | FINRA Rule 2165 / 4512 (US: trusted contact person and temporary holds); Georgia HB 945 (2026: bank holds for 65+ with trusted-contact notice); UK proposals for payment delays | Policy | — | Yes | — | — | **Yes** (trusted contact) | — |

**Framing for the pitch:** the victim is a genuine customer, so login, device and OTP checks all pass. The Indian tools we reviewed watch the **scammer's number** (FRI), the **receiving account** (MuleHunter.AI) or the **call** (Truecaller, Google, DeepVerif.AI). Kaaval watches the **victim's own abnormal money movement across days**. Say: *"we did not find a tool that does this"*. Don't say "nobody does", because BioCatch Scams360 targets authorised-push-payment scams within digital sessions.

## 2. Gaps Kaaval targets

1. **Cross-day financial staging.** The public material we reviewed for session biometrics focuses on in-session behaviour, and transaction monitoring focuses on per-transaction anomaly. Kaaval scores the *liquidate → pool → new payee → transfer* sequence explicitly.
2. **Branch parity.** Many of the reported saves happened at the counter, through staff intuition. Kaaval gives tellers a structured signal and a script.
3. **An automated human intervention.** A cooling-off hold plus a pre-registered trusted contact mirrors what worked in practice ("come back with a family member"). The US trusted-contact regimes are a precedent.
4. **India-specific steps.** FRI as a fused signal, and a pre-filled 1930 / cybercrime.gov.in report.
5. **Privacy posture.** No call audio, unlike call-content approaches, which conflict with Android's restrictions on call recording and with privacy expectations.

## 3. Where competitors are stronger (be honest)

- BioCatch and the FRM vendors are proven at bank scale, with real data, device intelligence and consortium networks. Kaaval is a prototype on synthetic data.
- Phone-side tools act *before* the victim reaches the bank, which can be earlier than Kaaval.
- MuleHunter-class tools can stop money at the receiving end, even after Kaaval misses.

**Positioning:** Kaaval is a **coercion-specific decision and intervention layer** that can sit on top of a bank's existing FRM. It consumes signals (FRI, device call flags, even BioCatch-type scores) and owns the *workflow*: hold, family, teller, report.

## 4. Sources

- BioCatch Scams360: [press release](https://www.biocatch.com/press-release/biocatch-delivers-scams360), [Finextra](https://www.finextra.com/pressarticle/106386/biocatch-takes-on-social-engineering-scam-market), [BioCatch blog on APP fraud](https://www.biocatch.com/blog/authorized-push-payment-fraud-how-digital-behavior-can-uncover-social-engineering-scams)
- MuleHunter.AI: [FinTech Futures](https://www.fintechfutures.com/ai-in-fintech/reserve-bank-of-india-pilots-new-mulehunter-ai-solution-to-help-identify-mule-accounts), [Business Standard explainer](https://www.business-standard.com/amp/finance/news/what-is-mulehunter-ai-rbi-s-latest-tool-against-financial-fraud-explained-124120600865_1.html), [Inc42](https://inc42.com/buzz/rbi-rolls-out-ai-to-detect-mule-accounts)
- DoT FRI / PhonePe: [Voice&Data](https://www.voicendata.com/news/dot-launches-financial-fraud-risk-indicator-to-curb-cybercrime-in-digital-payments-9149405), [Business Standard](https://www.business-standard.com/industry/news/dot-launches-financial-fraud-risk-indicator-to-aid-cybercrime-detection-125052101912_1.html)
- Truecaller Family Protection: [TechCrunch (Mar 2026)](https://techcrunch.com/2026/03/12/truecallers-now-lets-you-hang-up-on-scammers-on-behalf-of-your-family/), [ETV Bharat](https://www.etvbharat.com/en/technology/truecaller-launches-family-protection-feature-in-india-what-is-it-key-features-enn26031304993)
- Trusted-contact and hold precedents: [Stop Senior Fraud Act summary (PDF)](https://dondavis.house.gov/sites/evo-subsites/dondavis.house.gov/files/evo-media-document/stop-senior-fraud-act.pdf), [Transparency Taskforce APP paper (PDF)](https://transparencytaskforce.org/wp-content/uploads/2021/09/Richard-Emerys-thoughts-on-Protecting-the-Vulnerable-from-Authorised-Push-Payment.pdf). For FINRA Rules 2165 and 4512, cite finra.org directly *(verify)*. For Georgia HB 945, cite the Georgia General Assembly page *(verify)*
- The DeepVerif.AI, ORACLE and Turkish scam-call items come from the founding brief. **Find the primary links before citing them**
