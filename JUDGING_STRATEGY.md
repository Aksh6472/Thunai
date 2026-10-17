# Kaaval AI — Judging Strategy

> **Theme 1: Real-Time AI for Critical Decisions. Category: Citizen scam/fraud defense** (protect people and route reports to 1930 / cybercrime.gov.in).
> The weights below are the **team's planning weights**. The official rubric is not confirmed yet (A-08). When it arrives, re-map this table. Nothing here guarantees a result.

## 1. Rubric mapping (planning weights)

| Criterion | Weight | Our evidence | Demo moment ([DEMO_SCRIPT.md](DEMO_SCRIPT.md)) | Risk |
|---|---|---|---|---|
| **Importance** | 20 | A national issue: the Supreme Court's Aug 2026 directions and the RBI SOP, the I4C complaint figures, named public cases. It fits the theme: a *critical, real-time decision* (hold or allow) at the moment of payment | 0:00–0:20 opening case | Judges have seen many "fraud" pitches. Lead with *coercion of a genuine customer* |
| **Originality** | 20 | It watches the **victim's own money movement across days**, while the tools we reviewed watch the scammer's number, the receiving account or the call. It adds the trusted-contact release and branch parity | 0:45–1:30 watch score climbing over 3 days | A judge who knows BioCatch Scams360. Differentiate honestly (§3). Never say "nobody does this" |
| **Feasibility** | 15 | It runs live on real APIs, offline-capable. The hero case is **held on behaviour alone (score 80)**, so FRI is optional, not a dependency | 1:30–1:50 reasons, plus the "80 without simulated signals" line | Simulated FRI and call signals. Disclose them up front |
| **Technical depth** | 15 | Ingestion, per-customer baselines, a stage state machine, explainable scoring with an invariant (the points sum to the score), a hold state machine, single-use contact tokens, RBAC, audit, an evaluation harness with held-out families | Show `scoring_v1.yaml` on request | "Where's the AI?" (§5 Q1) |
| **Impact** | 10 | Money held before it leaves. The **1930 / cybercrime.gov.in report path** (required by the category brief) is pre-filled. Synthetic interception and false-hold metrics | 2:35–2:45 report draft on screen | Never extrapolate synthetic results to national savings |
| **Demo** | 10 | A real phone moment, Tamil script, a genuine payment passing | 2:15–2:55 | Network on stage. The QR fallback is the default |
| **Scalability** | 10 | The domain layer is pure and in-process. Partition by customer at bank scale (ARCHITECTURE §7) | Q&A only | p95 not measured until T-046 |

**Weight-driven emphasis:** about 40% of the planning weight is Importance plus Originality. Spend the first 45 seconds on the problem and the "victim's own behaviour across days" insight. Feasibility plus Technical depth is 30%: show the reasons and the behaviour-alone score, and keep code ready. The 1930 report must appear on screen, because the category brief asks for it.

**Responsible AI** isn't a separate criterion here, but it supports Feasibility and Importance: no audio, consent-based flags, no accusations, mandatory human review, per-family false-hold disclosure.

## 2. Demonstration strategy

1. **Open with a real case** (cited), not statistics.
2. **Make the multi-day climb visible.** That's the novelty, and the watch-score chart shows it.
3. **A real phone in a judge's line of sight.** The physical moment is memorable.
4. **Show the genuine case passing.** It pre-empts the "false positives" objection.
5. **End with measured numbers or none at all.** Never use invented numbers.
6. Keep `scoring.py` and `scoring_v1.yaml` open for technical judges.

## 3. Differentiation, honestly stated

| Existing approach | What it does well | What Kaaval adds |
|---|---|---|
| Bank FRM / transaction monitoring (FICO, Feedzai, Clari5, etc.) | Real-time anomaly scoring at scale | Coercion-specific **sequence** logic across days, and an explained, **intervention-oriented** workflow (cooling-off plus trusted contact plus teller script). *Many vendors may have APP-scam models. We claim focus, not invention* |
| BioCatch Scams360 (2025) | Behavioural biometrics in digital sessions, including active-call detection | **Branch counter parity**, **multi-day financial staging**, a **family release** loop and India-specific **1930/FRI** steps. Kaaval is complementary and could consume such a signal |
| RBI MuleHunter.AI | Detects mule (receiver) accounts | Kaaval protects the **sender at the moment of payment**. The two are complementary |
| DoT FRI / PhonePe Protect | Number-level risk, UPI blocking | Kaaval fuses FRI with behaviour, so it isn't a single-signal block |
| Truecaller Family Protection, Android scam detection | Phone-side call alerts to family | Kaaval sees the **money movement** and acts at the bank |
| Manual staff intervention | Works when someone notices | Makes noticing consistent, structured and auditable |

Our claim is: *"In our research we did not find a product that publicly combines these five elements for Indian banks."* We **don't** claim "nobody does this".

## 4. Impact measurement

- **Built and measurable now (synthetic):** interception rate, false-hold rate per family, explanation coverage, latency.
- **Proposed for a pilot:** release time for genuine holds, teller checklist adoption, customer satisfaction after a hold, rupees protected per 10,000 customers, and complaint-to-report time.
- **Don't** extrapolate national savings from synthetic results.

## 5. Q&A drill (likely objections and honest answers)

| # | Question | Answer |
|---|---|---|
| Q1 | "Where's the AI? This is rules." | "Kaaval learns each customer's normal behaviour, and the scoring is relative to *their* baseline. It recognises a multi-day sequence and fuses several signals. We deliberately kept the fusion weights transparent, because a bank must explain every hold and real labelled coercion data isn't public. Training on our synthetic data would mostly learn our generator. The reason contract lets a learned model drop in once a bank provides labelled cases." |
| Q2 | "Your data is synthetic. How do we know it works?" | "Correct, and we label it everywhere. The scenarios come from publicly reported case patterns, including hard negatives. We tuned on one set of seeds and report on separate held-out seeds and two held-out families. That shows the engine behaves as designed, not real-world accuracy. The next step is shadow mode on a bank's anonymised data." |
| Q3 | "How do you get the payee's phone number for FRI on an RTGS?" | "You often can't for account-to-account transfers, so FRI is an **optional** signal in Kaaval, not a dependency. Where a number is available (UPI/VPA payees, intra-bank beneficiaries, DIP-side mapping), it adds points. Without it, the hero case still scores 80 and is **held on behaviour alone**." **Say this proactively in the pitch** (DEMO_SCRIPT 1:30–1:50) |
| Q4 | "Can a bank legally hold a customer's money?" | "That's the key open question. The Supreme Court asked RBI in Aug 2026 for an SOP that reportedly includes temporary debit holds. Our hold is short, explained, cancellable by the customer and reviewed by a human. We'd align with the final SOP." *(Background only, not on slides unless the primary sources have been opened and confirmed: US FINRA Rule 2165 and Georgia HB 945 trusted-contact hold regimes.)* |
| Q5 | "Scammers will tell victims to say it's for property." | "That's why the score ignores what the customer *says*. The teller's note is recorded but never scored. One of our test families is exactly this cover story." |
| Q6 | "Scammers will make the victim change the trusted contact." | "A new contact only becomes active after 72 hours, and a recent change itself raises the risk." |
| Q7 | "What about false positives, like weddings?" | "We show them. Our evaluation reports per-family false holds, including weddings and tuition, which we expect to hold sometimes. The trusted contact can release a HIGH hold in minutes." |
| Q8 | "How do you detect a video call without spying?" | "We don't access audio or content. The bank app would share one consented flag: on a call with an unknown number, and for how long. In this demo that signal is simulated, and its feasibility on Android and iOS is an assumption we've listed." |
| Q9 | "What if the trusted contact is the scammer or is complicit?" | "VERY_HIGH holds need an officer regardless of what the contact says. The contact can't move money, only confirm or flag." |
| Q10 | "Latency? Scale?" | "Scoring is in-process and takes a few indexed queries. Our target is p95 under 300 ms [quote the measured value from T-046, or say 'not yet measured']. At bank scale, events would be partitioned by customer. The domain logic is pure, so it scales horizontally without changes." |
| Q11 | "Why would a bank adopt this?" | "Regulatory pressure after the SC directions, liability and compensation exposure, and reputation. And it formalises what their best staff already do." |
| Q12 | "Isn't the LLM risky?" | "The LLM only drafts report prose. It never decides anything. It's checked against the facts, falls back to a template and is reviewed by an officer. It's off by default." |
| Q13 | "Bias against elderly customers?" | "Age isn't a feature at all. We score behaviour. We can't measure demographic fairness on synthetic data. In a pilot we'd audit outcomes by age band without using it as an input." |
| Q14 | "What did you actually build in the hackathon?" | Point to the repo: "Everything you saw runs live: the engine, the API, four interfaces and the evaluation harness. The simulated parts are FRI, the phone signal and the bank itself." |

## 6. Limitations to disclose proactively (honesty slide)

1. Synthetic data only. No real bank data or bank validation.
2. The FRI and phone call signals are simulated. The FRI number availability for RTGS payees is unproven (A-03).
3. Hand-set weights. No trained model.
4. Expected false holds on some genuine life events (weddings, tuition), disclosed per family.
5. The legal authority for holds depends on the RBI SOP and bank T&Cs (A-02).
6. Tamil copy reviewed by a team member, not a professional translator.
7. Single branch, single instance. Not production-hardened (no SSO, no outbox).

## 7. Ways to strengthen competitiveness (in order of value and effort)

1. A **real phone moment** that works reliably (T-041). Rehearse it three times.
2. An **evaluation report with held-out families**, shown on one slide. Credibility beats claims.
3. **A short quote from a bank employee or a senior citizen** about the problem, if anyone on the team can legitimately get one before judging. Never fabricate it.
4. **Code a small library of public cases** (10+) into the stage model, as a table in [docs/DATA_SOURCES.md](docs/DATA_SOURCES.md) §3. It shows that the stage pattern is grounded.
5. Map the slides explicitly to the official rubric once it arrives.
