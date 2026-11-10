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

To use live OpenAI and PayPal Sandbox, set `LLM_MODE=live` (`OPENAI_API_KEY=...`) and `PAYPAL_MODE=sandbox` (`PAYPAL_CLIENT_ID=...`, `PAYPAL_CLIENT_SECRET=...`) in `backend/.env`.

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

