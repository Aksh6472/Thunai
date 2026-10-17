# Kaaval AI — Deployment and Operations

> **Status:** nothing has been deployed yet. The commands below are the **target** procedure. They become valid once T-001 to T-005 and T-047 are done. Update this file if the real commands differ.

**Primary demo = the local laptop** (works offline, no cold starts). The hosted deployment is a Should Have (FR-29) so judges can try it later. Never depend on it on stage.

## 1. Local development setup

Prerequisites are in [TECH_STACK.md](TECH_STACK.md) §1 (Python 3.12, uv, Node 22, Docker).

```bash
git clone <repo-url> kaaval-ai && cd kaaval-ai     # folder name must have no spaces
cp .env.example .env                               # then generate secrets (ENVIRONMENT.md §3)
make db                                            # docker compose up -d db   (waits for healthcheck)
make migrate                                       # cd backend && uv sync && uv run alembic upgrade head
make seed                                          # cd backend && uv run python -m sim.seed --seed 42
make dev                                           # API on :8000 (uvicorn --reload) + Vite on :5173
```

Open:

| URL | What it is |
|---|---|
| http://localhost:5173/login | The app (users `teller.priya`, `officer.rao`, `admin.demo`, `cust.kamala`, `cust.iqbal`, all with password `$KAAVAL_SEED_PASSWORD`) |
| http://localhost:8000/docs | OpenAPI UI |
| http://localhost:8000/api/v1/readyz | Readiness check |

## 2. Environment variables

The full reference is [ENVIRONMENT.md](ENVIRONMENT.md), and the template is [.env.example](.env.example).

## 3. Database initialisation and migrations

| Action | Command |
|---|---|
| Apply migrations | `cd backend && uv run alembic upgrade head` |
| New migration | `uv run alembic revision --autogenerate -m "add x"`, then **review it by hand** (CHECKs and partial indexes) |
| Roll back one migration | `uv run alembic downgrade -1` |
| Seed demo data | `uv run python -m sim.seed --seed 42` (idempotent: it truncates, then inserts) |
| Reset everything during the demo | `make demo-reset` or **Reset** in `/demo` (calls `POST /demo/reset`) |
| Snapshot for backup | `docker compose exec db pg_dump -U kaaval kaaval > reports/demo-snapshot.sql` (synthetic data only) |
| Restore the snapshot | `docker compose exec -T db psql -U kaaval kaaval < reports/demo-snapshot.sql` |

## 4. Build commands

```bash
cd frontend && npm ci && npm run build          # → frontend/dist
cd backend && uv sync --frozen                  # reproducible env
```

Demo-day "production-like" local run (no reload, built SPA):
```bash
make demo
# = docker compose up -d db
#   (cd backend && uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1)
#   (cd frontend && npm run build && npm run preview -- --host 0.0.0.0 --port 5173)
```

`--host 0.0.0.0` lets the trusted contact's phone on the same hotspot reach the laptop. **Single worker only**, because the rate limiter and the console notifier buffer are in-memory.

## 5. Making the trusted-contact link reachable from a real phone

| Option | Steps | When to use |
|---|---|---|
| **A. Same hotspot (preferred)** | The laptop and phone join the team's phone hotspot. Set `KAAVAL_PUBLIC_WEB_URL=http://<laptop-LAN-IP>:5173` and `VITE_API_BASE_URL=http://<laptop-LAN-IP>:8000/api/v1`, add the LAN origin to `KAAVAL_CORS_ORIGINS`, then rebuild the frontend | No internet needed between the devices |
| **B. Tunnel** | `cloudflared tunnel --url http://localhost:5173` (and a second one for :8000). Set the URLs to the tunnel hosts | Venue Wi-Fi blocks peer traffic |
| **C. Fallback** | Open `/demo` → Console messages → show the QR code to the phone, or read the message on screen | SMS or network fails |

SMS delivery uses `KAAVAL_NOTIFIER=twilio` or `telegram`, with the teammate's number or chat id in `.env` ([ENVIRONMENT.md](ENVIRONMENT.md)). Test it by H+2 (T-041).

## 6. Hosted deployment (Should, T-048)

| Component | Host | Settings |
|---|---|---|
| PostgreSQL | Render PostgreSQL (or Neon) | Copy the connection string into `DATABASE_URL` (driver `postgresql+psycopg://`) |
| Backend | Render Web Service, root `backend/` | Build: `pip install uv && uv sync --frozen`. Start: `uv run alembic upgrade head && uv run uvicorn app.main:app --host 0.0.0.0 --port $PORT --workers 1`. Health check path `/api/v1/healthz`. Set every env var from ENVIRONMENT.md with **fresh secrets** (never the local ones) |
| Frontend | Vercel, root `frontend/` | Build `npm run build`, output `dist`. Env `VITE_API_BASE_URL=https://<render-app>/api/v1`. Add an SPA rewrite to `/index.html` and security headers (CSP `default-src 'self'; connect-src 'self' https://<render-app>`) in `vercel.json` |

After deploying: run `POST /demo/reset` once, then smoke-test login, run P1 and check that the hold appears. Note that free tiers sleep, so the first request can take 30–60 s. Warm it up before sharing the link.

## 7. Demo-day pre-flight checklist (T-047)

- [ ] The laptop is on charge. Notifications and auto-updates are off. The display is mirrored and readable at the back of the room (browser zoom 125%).
- [ ] `make demo` is running. `/readyz` is green. `POST /demo/reset` has been done.
- [ ] The phone hotspot is on, and the phone opens `http://<LAN-IP>:5173/t/test` (the expected page is "link expired").
- [ ] A test hold has been sent to the teammate's phone and **arrived**. Then reset again.
- [ ] Browser tabs are open in order: `/demo`, `/ops`, `/teller`, `/customer` (logged in), and the slides.
- [ ] The backup video is open in a paused player. `reports/demo-snapshot.sql` is ready.
- [ ] Wi-Fi has been tested off: the demo still runs (console fallback).

## 8. Health checks, logs and monitoring

| Signal | Where |
|---|---|
| Liveness | `GET /api/v1/healthz` |
| Readiness (DB, config, notifier) | `GET /api/v1/readyz` |
| Logs | Backend stdout (JSON). Locally, `make dev` shows them. Render dashboard → Logs. Every response has an `X-Request-ID`, so search the logs for it |
| Key log events | `assessment.created`, `hold.created`, `contact.sent` / `contact.failed`, `hold.resolved`, `llm.fallback`, `auth.login_failed` |
| Audit trail | `audit_log` table (OFFICER UI on the hold detail page, or SQL) |

## 9. Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `connection refused` on 5432 | DB not up | `make db`, then `docker compose ps` |
| `port is already allocated` / an app is already on 5432 or 8000 | Another project's container or server | Set `KAAVAL_DB_PORT` / `KAAVAL_API_PORT` in `.env` and update the URLs (ADR-018). Don't stop other projects' containers |
| `docker compose up` hangs with the container stuck in `Created` (even `docker run alpine echo hi` hangs) | Docker Desktop engine wedged | Quit and restart Docker Desktop (this also restarts other projects' containers), then `make db` again |
| The app exits with "required secret missing" | `.env` is incomplete | Fill it in per ENVIRONMENT.md §3 |
| CORS error in the browser | The origin isn't in `KAAVAL_CORS_ORIGINS` | Add the exact origin (scheme, host, port) and restart the API |
| The phone can't open the link | Different network / AP isolation | Use the hotspot, or option B (tunnel) |
| Tamil shows as boxes | Font not loaded | Check that the `@fontsource/noto-sans-tamil` import is in `main.tsx` |
| The scenario doesn't climb over days | SimClock not active or the speed is wrong | Check `KAAVAL_DEMO_MODE=true` and `/demo/clock` |
| Twilio error 21608 | Trial, unverified number | Verify the number in the Twilio console, or switch to Telegram or the console |
| Assessment returns 503 | Engine exception | Check the logs by request id. The engine fails closed by design |
| Paths break in scripts or Docker | Folder name has a space | Rename the folder to `kaaval-ai` |

## 10. Rollback strategy

| Situation | Action |
|---|---|
| A bad commit before the demo | `git revert <sha>` (don't force-push `main`), then redeploy. Tag every known-good state: `git tag demo-ok-H17` |
| A bad migration | `uv run alembic downgrade -1`, fix it, then upgrade again. In the demo DB, `make demo-reset` is the simplest fix |
| Broken data during the live demo | `/demo` → Reset (≤ 10 s). If the API is down, restore `reports/demo-snapshot.sql` |
| Hosted deploy broken | Render → Deploys → "Rollback" to the previous deploy. Vercel → Promote the previous deployment |
| Everything fails on stage | Switch to the backup video ([DEMO_SCRIPT.md](DEMO_SCRIPT.md) §6) |
