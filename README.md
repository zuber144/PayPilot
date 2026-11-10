# PayPal AgentOS + PayGuard AI

Bounded multi-agent purchasing workflow (LangGraph + FastAPI + SQLAlchemy 2 + PayGuard deterministic & AI safety engine + PayPal Orders API v2 Sandbox).

## Run the backend

### 1. Environment & dependencies

From `backend/`:

```powershell
# Create virtual environment (Python 3.11) and install dependencies
uv venv -p 3.11 .venv
uv pip install -p .venv -r requirements.txt

# Copy environment template
Copy-Item .env.example .env
```

By default, `.env.example` configures offline deterministic mode (`LLM_MODE=mock`, `PAYPAL_MODE=mock`, `DATABASE_URL=sqlite:///./agentos.db`) so the server, all 4 demo scenarios, and the test suite run offline without external credentials or Docker.

To use PostgreSQL 16 via Docker Compose instead of SQLite:

```powershell
# From repository root
docker compose up -d
# Then set DATABASE_URL=postgresql+psycopg://agentos:agentos@localhost:5432/agentos in backend/.env
```

To use the live LLM and PayPal Sandbox, set these in `backend/.env`:
- `LLM_MODE=live` with `LLM_PROVIDER=anthropic` (default model `claude-haiku-5-5`; the key comes from `ANTHROPIC_API_KEY` in `.env` or your shell). `LLM_PROVIDER=openai` with `OPENAI_API_KEY` is still supported. The provider in use is logged at startup.
- `PAYPAL_MODE=sandbox` with `PAYPAL_CLIENT_ID` and `PAYPAL_CLIENT_SECRET` from a **US** Sandbox app. The demo is USD-only because PayPal Sandbox rejects INR. Approve payments with a US *personal* Sandbox account.

Live tests are opt-in and never run with a plain `pytest`: `.venv\Scripts\python -m pytest -m live`. The PayPal one reads `PAYPAL_CLIENT_ID` and `PAYPAL_CLIENT_SECRET` from the shell environment.

To drive the 4 scenarios against a running server (for example on Postgres), start uvicorn with `LLM_MODE=mock PAYPAL_MODE=mock` on an empty database, then run `.venv\Scripts\python scriptsun_scenarios.py --base-url http://127.0.0.1:8000`.

### 2. Seed the database & start FastAPI

From `backend/`:

```powershell
.venv\Scripts\python seed.py
.venv\Scripts\python -m uvicorn app.main:app --reload --port 8000
```

- OpenAPI docs: `http://localhost:8000/docs`
- API base path: `http://localhost:8000/api/v1` (see [`docs/API_CHEATSHEET.md`](docs/API_CHEATSHEET.md))

### 3. Run lint, typecheck, tests & demo scenarios

From `backend/`:

```powershell
.venv\Scripts\python -m ruff check .
.venv\Scripts\python -m mypy app
.venv\Scripts\python -m pytest -q
.venv\Scripts\python scripts\run_scenarios.py
```

To run the live PayPal Sandbox end-to-end test once Sandbox credentials are set in `.env`:

```powershell
.venv\Scripts\python -m pytest -q -m live
```

