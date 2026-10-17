# Thunai — Environment Configuration

## 1. Rules

1. Read all configuration from environment variables through `app/core/settings.py` (pydantic-settings). **Never** call `os.getenv` anywhere else in the backend.
2. `.env` is local and git-ignored. [.env.example](.env.example) is the committed template. **When you add a variable, update `.env.example`, this file and `Settings` in the same PR.**
3. Placeholder values that start with `change-me` are allowed only in `development` and `test`. Startup fails in `production` if any remain.
4. The frontend sees **only** `VITE_*` variables. They are bundled into public JS, so they must never hold secrets.
5. Never paste real keys into chat, issues, logs, screenshots or the slides.

## 2. Variable reference

| Variable | Required | Default | Description |
|---|---|---|---|
| `THUNAI_API_PORT` | no | `8000` | Host port for uvicorn (`make dev`). Change it if 8000 is taken, and update `THUNAI_API_BASE_URL` / `VITE_API_BASE_URL` to match (ADR-018) |
| `THUNAI_DB_PORT` | no | `5432` | Host port for the compose Postgres. Change it if 5432 is taken, and update `DATABASE_URL` / `TEST_DATABASE_URL` to match |
| `THUNAI_OPENAPI_URL` | no | `http://localhost:8000/openapi.json` | Read by `npm run gen:api` (shell env, not `.env`) |
| `THUNAI_ENV` | yes | `development` | `development` / `test` / `production` |
| `THUNAI_DEMO_MODE` | yes | `true` (dev) | Enables `/demo/*`, SimClock, `scenario_label` and the SIMULATED chips. **Refused** in production |
| `THUNAI_LOG_LEVEL` | no | `INFO` | Log level |
| `THUNAI_PUBLIC_WEB_URL` | yes | `http://localhost:5173` | Base URL in the trusted-contact links. For the phone demo, set the LAN IP (`http://192.168.x.y:5173`) or the tunnel URL |
| `THUNAI_CORS_ORIGINS` | yes | `http://localhost:5173` | Comma-separated allow-list. Wildcards are not allowed |
| `POSTGRES_USER` / `POSTGRES_PASSWORD` / `POSTGRES_DB` | yes (compose) | — | Used by the docker-compose Postgres |
| `DATABASE_URL` | yes | — | SQLAlchemy URL (`postgresql+psycopg://…`) |
| `TEST_DATABASE_URL` | tests | — | Separate DB, `thunai_test` |
| `THUNAI_JWT_SECRET` | yes | — | ≥ 32 bytes, random |
| `THUNAI_JWT_TTL_MINUTES` | no | `60` | Access token lifetime |
| `THUNAI_SERVICE_API_KEY` | yes | — | Simulator ↔ API key |
| `THUNAI_PII_ENCRYPTION_KEY` | yes | — | Fernet key (urlsafe base64, 32 bytes) |
| `THUNAI_HMAC_KEY` | yes | — | HMAC key for the payee-linked numbers |
| `THUNAI_SEED_PASSWORD` | dev | — | Password for all seeded demo users |
| `THUNAI_CONTACT_TOKEN_TTL_MINUTES` | no | `30` | Trusted-contact link lifetime (wall clock) |
| `THUNAI_SCORING_CONFIG_PATH` | no | `config/scoring_v1.yaml` | Relative to `backend/` |
| `THUNAI_COOLING_OFF_MINUTES` | no | `240` | Hold cooling-off (simulated clock in demo mode) |
| `THUNAI_TRUSTED_CONTACT_ACTIVATION_HOURS` | no | `72` | FR-24 delay |
| `THUNAI_FRI_TIMEOUT_MS` | no | `300` | FRI adapter timeout |
| `THUNAI_NOTIFIER` | no | `console` | `console` / `twilio` / `telegram` |
| `TWILIO_ACCOUNT_SID` / `TWILIO_AUTH_TOKEN` / `TWILIO_FROM_NUMBER` | if twilio | — | Twilio credentials. The trial sends only to verified numbers |
| `TELEGRAM_BOT_TOKEN` | if telegram | — | From @BotFather |
| `THUNAI_DEMO_CONTACT_PHONE_E164` | demo | — | The teammate's real number. The seed sets it as Kamala's trusted contact (encrypted) when present. **Local `.env` only** |
| `THUNAI_DEMO_CONTACT_TELEGRAM_CHAT_ID` | demo | — | The teammate's Telegram chat id |
| `THUNAI_LLM_ENABLED` | no | `false` | FR-21 switch |
| `ANTHROPIC_API_KEY` | if LLM | — | Anthropic API key |
| `THUNAI_LLM_MODEL` | no | `claude-opus-5-5` | Model id |
| `THUNAI_LLM_TIMEOUT_SECONDS` | no | `10` | Request timeout |
| `THUNAI_API_BASE_URL` | sim | `http://localhost:8000/api/v1` | Where the replayer sends requests |
| `THUNAI_SIM_DEFAULT_SPEED` | no | `4320` | Simulated seconds per real second |
| `VITE_API_BASE_URL` | frontend | `http://localhost:8000/api/v1` | API base for the SPA. For phone access, use the LAN IP |
| `VITE_DEMO_MODE` | frontend | `true` | Shows the demo bar and the SIMULATED chips |
| `VITE_DEMO_AUTOFILL_PASSWORD` | frontend | empty | Optional. When set (and demo mode is on), tapping a demo account on the login page also fills the password. **The one exception to rule 4:** it is bundled into public JS, so set it only to the synthetic seed password for local or LAN demos, never on a hosted deployment |

## 3. Generating secrets

```bash
openssl rand -hex 32        # THUNAI_JWT_SECRET, THUNAI_HMAC_KEY
openssl rand -hex 24        # THUNAI_SERVICE_API_KEY
uv run python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"   # THUNAI_PII_ENCRYPTION_KEY
```

Changing `THUNAI_PII_ENCRYPTION_KEY` or `THUNAI_HMAC_KEY` makes existing encrypted or hashed values unreadable or unmatched. In the demo, run `make demo-reset` afterwards.

## 4. Profiles

| Setting | development | test | production (hosted demo is still "development + DEMO_MODE") |
|---|---|---|---|
| `THUNAI_DEMO_MODE` | true | true | **false (enforced)** |
| Clock | SimClock | SimClock | RealClock |
| Notifier | console (or twilio/telegram) | console (fake) | twilio / bank gateway |
| LLM | off unless testing it | off (mocked) | bank decision |
| Log format | JSON (pretty with `THUNAI_LOG_LEVEL=DEBUG`) | JSON | JSON |
| CORS | localhost | n/a | Exact origins |

> The **hosted judge demo** (T-048) runs with `THUNAI_ENV=development` and `THUNAI_DEMO_MODE=true`, because it uses synthetic data and simulated signals by design. `production` is reserved for a future real deployment, where those guards apply.

## 5. Where each file lives

| File | Read by |
|---|---|
| `.env` (repo root) | docker compose, the backend (`Settings` with `env_file="../.env"` when run from `backend/`) and the simulator |
| `frontend/.env` | Vite (copy the `VITE_*` lines from the root `.env`, or symlink it). `make dev` copies them automatically |
