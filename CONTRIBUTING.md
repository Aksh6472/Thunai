# Contributing to Kaaval AI

## 1. Branching

- `main` is always demo-able. It is protected: changes go through a PR, with 1 approval and green checks.
- Use short-lived feature branches: `<ws>/<task-id>-<slug>`, e.g. `ws2/T-028-scoring`, `ws5/T-037-trusted-page`.
- Rebase onto `main` frequently. Keep a branch alive for at most about 4 hours during the hackathon.
- Use tags for known-good states: `demo-ok-H12`, `demo-ok-H17`, `submission`.
- **After the feature freeze (H+20 or H+40):** only `fix/<id>-<slug>` branches are allowed, each with a test.

## 2. Commit conventions (Conventional Commits)

```text
<type>(<scope>): <summary in imperative, ≤ 72 chars>

<why, if not obvious>
Refs: T-028
```

- **Types:** `feat`, `fix`, `test`, `docs`, `refactor`, `chore`, `perf`, `security`.
- **Scopes:** `engine`, `api`, `db`, `auth`, `sim`, `eval`, `ops-ui`, `teller-ui`, `customer-ui`, `contact-ui`, `demo`, `infra`, `docs`.
- One logical change per commit. Never commit `.env`, keys, real phone numbers or `reports/demo-snapshot.sql` containing anything except synthetic data.

## 3. Pull requests

Every PR description has:
1. **What and why** (link the task ID and the FR/AC IDs).
2. **How it was tested.** List the commands you ran and their results. Screenshots or GIFs for UI changes.
3. **Docs updated**: which of API_SPEC, DATABASE_SCHEMA, AI_DESIGN, ENVIRONMENT and so on, or "none needed" with the reason.
4. **Risk / rollback**: anything risky, such as a migration or a scoring change.

PR size: aim for fewer than 400 changed lines, excluding generated files (`schema.d.ts`, lockfiles).

## 4. Code review requirements

The reviewer checks:
- [ ] It matches the task's acceptance criteria and does not exceed them (no scope creep).
- [ ] Layering: no business logic in routers, no I/O in `app/domain`, and `sim/` doesn't import domain or services.
- [ ] Input validation (`extra="forbid"`, limits). Authorisation at both the role and ownership levels.
- [ ] Error paths return the envelope. No silent `except:`.
- [ ] Tests cover the behaviour, including at least one failure case. The tests would fail if the feature broke.
- [ ] No new dependency without a justification line.
- [ ] Copy follows DESIGN §6 (no "victim", "fraudster", "blocked").
- [ ] Any **scoring config change** has a DECISIONS changelog row and a re-run of the golden tests. Changes after viewing evaluation seeds 100–299 must be disclosed.

Mandatory second reviewer: changes to `app/domain/scoring.py`, `policy.py`, `hold_service.py`, `contact_service.py`, `core/security.py` or the migrations need **a review from a second workstream** as well.

## 5. Architecture decisions

Significant choices go in [DECISIONS.md](DECISIONS.md) as an ADR, in the same PR as the change. Significant means: a new dependency, a new table, a change to the auth model, a scoring change, or a change to any boundary rule.

## 6. Local quality checks before pushing

```bash
make lint && make test        # backend + frontend
gitleaks detect --no-banner   # secrets
```

## 7. Working with Claude Code

Follow [CLAUDE.md](CLAUDE.md). The short version: Inspect → Plan → Implement → Test → Verify → Document. Never claim something works without running its tests.
