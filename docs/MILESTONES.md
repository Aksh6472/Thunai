# Kaaval AI — Milestones and Completion Gates

A gate **passes only when every check is true and demonstrated**: on screen, by a command's output, or with a test run link. "It works on my machine" is not a pass. If a gate fails at its check-in, the team must either (a) cut scope from the list in §7 or (b) extend the window **by taking time from a later Should item**, never from M5.

## G0 — Contracts frozen (target H+2)

- [ ] The repo exists, everyone has pushed one commit, and `main` is protected.
- [ ] The project folder has been renamed to `kaaval-ai` (no trailing space).
- [ ] `make db` starts Postgres. `GET /api/v1/healthz` returns 200. The frontend `npm run dev` shows the route placeholders.
- [ ] The team has read and agreed [API_SPEC.md](../API_SPEC.md), [DATABASE_SCHEMA.md](../DATABASE_SCHEMA.md) and the [AI_DESIGN.md](../AI_DESIGN.md) §6 scoring table. Any changes have been made in the docs.
- [ ] `backend/config/scoring_v1.yaml` matches the AI_DESIGN §6 table.
- [ ] A Twilio trial and/or Telegram bot has been created, and a test message has been attempted to the teammate's phone. The result is recorded.
- [ ] Workstream owners have been assigned in [TASKS.md](../TASKS.md).

## G1 — Engine and core backend (target H+8)

- [ ] `uv run pytest tests/unit` is green, **including** `test_scoring_golden.py` (hero raw 115, N1 = 5, N4 = 60).
- [ ] The migration runs up, down and up again.
- [ ] Login works for every seeded role, and the authorisation tests for 401 and 403 pass.
- [ ] `python -m sim.seed --seed 42` creates 50 customers in ≤ 10 s, and running it twice is deterministic.
- [ ] The frontend login works against the real API, and the components page renders TierBadge, ReasonList and the others.

## G2 — Headless hero (target H+12)

- [ ] `uv run pytest tests/scenarios/test_hero_e2e_api.py` is green. It covers:
  - P1 watch scores 15 → 40 → 63, then HOLD VERY_HIGH, reasons summing to 115, a console message with a link, the contact response recorded, an officer cancel with a note, and a report draft with the correct structured fields.
  - N1 ALLOW.
- [ ] `python -m sim.replay --scenario P1 --speed 4320` against a running server completes in about 60 s.
- [ ] `POST /demo/reset` takes ≤ 10 s.

## G3 — UI hero (target H+17)

- [ ] The full [DEMO_SCRIPT.md](../DEMO_SCRIPT.md) runs from the Demo panel with no terminal commands and no manual DB edits.
- [ ] The trusted-contact link opens on a **real phone** (LAN or tunnel). The real SMS/Telegram arrives in ≤ 15 s, **or** the fallback QR from the console messages is rehearsed.
- [ ] The teller checklist re-scores in ≤ 2 s. The Tamil script displays correctly (no tofu boxes).
- [ ] The customer warning and hold screens work in Tamil and English.
- [ ] N1 shows ALLOW and no new alert.

## G4 — Hardened and frozen (target H+20)

- [ ] The release gates in [TESTING.md](../TESTING.md) §10 all pass (CI or a local run log is attached).
- [ ] `reports/eval/<ts>.md` exists, generated on seeds 100–299. Its numbers are copied verbatim into the README status section, with the synthetic label.
- [ ] Security checks (T-045) are done. There are no high or critical findings, or exceptions are documented.
- [ ] The demo snapshot and the runbook (T-047) exist. An offline run with Wi-Fi off passes.
- [ ] **Feature freeze is declared** in the team chat, with the time.

## G5 — Demo-ready (target H+24, or the submission deadline)

- [ ] Three timed rehearsals are each ≤ 3:00, recorded in a rehearsal log (date, time, issues).
- [ ] A backup video of a clean run is saved locally **and** in the cloud.
- [ ] The slides are final, including the "What's simulated" honesty slide.
- [ ] The Q&A drill in [JUDGING_STRATEGY.md](../JUDGING_STRATEGY.md) §5 has been done, and every team member can answer the top 5 questions.
- [ ] The submission form is complete (repo link, video, description). The README is accurate.

## 7. Scope-cut order (if a gate is at risk)

Cut from the top. Never cut anything below the line.

1. T-031 LLM narrative
2. T-048 hosted deployment
3. T-051 consent screens (consents are seeded instead)
4. T-041 real SMS (use the console messages and QR fallback)
5. Families P2–P7 and N2–N6 in the demo (keep them in the evaluation if the generator supports them, otherwise report fewer families **and say so**)
6. T-019 customer timeline view (keep the queue and hold detail)
7. T-039 demo panel polish (keep reset and run)

---- **never cut** ----
- The hero P1 and genuine N1 flows end to end
- Reasons that sum to the score, in EN and TA
- The trusted-contact page and the officer decision
- The evaluation report, even with fewer families
- Honest labelling of simulated and synthetic parts
