# PayPilot AgentOS + PayGuard AI

A hackathon-ready scaffold: AI agent pipeline finds providers, negotiates prices, generates spending plans, and runs them through a deterministic compliance engine before PayPal Sandbox payment.

---

## Quick Start

### Prerequisites
- Docker (for Postgres)
- Python 3.11+
- Node.js 20+

---

### 1. Start PostgreSQL

```bash
cd agentos
docker compose up -d
```

Postgres will be available at `localhost:5432`.

---

### 2. Backend Setup

The backend lives in `agentos/backend/`. Full instructions are in the root [`README.md`](../README.md).

```bash
cd agentos/backend

# Create virtualenv and install dependencies (Python 3.11)
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Mac/Linux:
source .venv/bin/activate
pip install -r requirements.txt

# Configure environment (offline mock mode by default)
cp .env.example .env

# Seed the database and start the API
python seed.py
uvicorn app.main:app --reload --port 8000
```

API available at: http://localhost:8000/api/v1
Interactive docs: http://localhost:8000/docs

---

### 3. Frontend Setup

```bash
cd agentos/frontend

# Install dependencies
npm install

# Configure environment (mocks are ON by default)
cp .env.example .env

# Start dev server
npm run dev
```

Frontend available at: http://localhost:5173

**To use real API:** Set `VITE_USE_MOCKS=false` in `frontend/.env`

---

### 4. Run Tests

```bash
cd agentos/backend
python -m pytest -q
python scripts/run_scenarios.py
```

---

## PayPal Sandbox Setup

### Create a PayPal Developer Account
1. Go to [developer.paypal.com](https://developer.paypal.com)
2. Log in with your PayPal account (or create one)
3. Navigate to **Apps & Credentials**

### Create a Sandbox App
1. Under **REST API apps**, click **Create App**
2. App name: `PayPilot-Dev`
3. App type: **Merchant**
4. Environment: **Sandbox**
5. Copy **Client ID** and **Client Secret** to `agentos/backend/.env` and set `PAYPAL_MODE=sandbox`

### Create Sandbox Accounts
1. Go to **Sandbox > Accounts**
2. Create a **Business** account (seller/merchant) — this is where payments go
3. Create a **Personal** account (buyer) — use this to approve payments in the checkout
4. Use the Personal account credentials to log in at the PayPal sandbox checkout

### Test the Payment Flow
1. Create a goal → let the pipeline run → run PayGuard → approve → pay
2. You'll be redirected to `sandbox.paypal.com` — log in with the **Personal** sandbox account
3. After approval, you're redirected back to `/payments/return` where capture happens

---

## Demo Goals (Seed Data)

| Goal ID | Description | Budget | Expected PayGuard Outcome |
|---------|-------------|--------|---------------------------|
| 1 | Website + copywriting | $2,000 | ✅ APPROVED |
| 2 | Logo design | $200 | ⚠️ REVIEW (vendor concentration) |
| 3 | Blog content writing | $250 | 🚫 BLOCKED (unverified provider) |

Run all three goals through the pipeline to see the three different outcomes.

---

## Module Status

| Module | File | Status | Owner TODO |
|--------|------|--------|------------|
| Config | `app/config.py` | ✅ Real | — |
| DB Models | `app/models.py` | ✅ Real | — |
| LLM Wrapper | `app/llm.py` | ⚠️ Stub | Implement real provider (OpenAI/Anthropic) |
| Goal Analyzer | `app/agents/goal_analyzer.py` | ⚠️ Stub | Replace keyword fallback with real LLM parse |
| Service Discovery | `app/agents/discovery.py` | ✅ Real | SQL-based, no changes needed |
| Provider Agents | `app/agents/provider_agent.py` | ⚠️ Stub | Replace canned pitch with real LLM call |
| Negotiation | `app/agents/negotiation.py` | ✅ Real | Deterministic — no changes needed |
| Plan Generator | `app/agents/plan_generator.py` | ⚠️ Stub | Replace template rationale with real LLM |
| Pipeline Runner | `app/agents/pipeline.py` | ✅ Real | — |
| PayGuard Policy | `app/payguard/policy.py` | ✅ Real | All 10 rules implemented |
| PayGuard Risk | `app/payguard/risk.py` | ⚠️ Stub | Replace with real AI risk assessment |
| PayGuard Engine | `app/payguard/engine.py` | ✅ Real | — |
| PayPal Integration | `app/payments/paypal.py` | ✅ Real | Needs real sandbox credentials |
| Payment Service | `app/payments/service.py` | ✅ Real | State machine fully implemented |
| API Routers | `app/routers/` | ✅ Real | — |

---

## Architecture

```
POST /goals
  → BackgroundTasks: PipelineRunner.run()
      Step 1: Goal Analyzer (LLM → ParsedGoal)
      Step 2: Service Discovery (SQL)
      Step 3: Provider Agents (price in code, LLM writes pitch)
      Step 4: Negotiation (deterministic, 2 rounds max)
      Step 5: Plan Generator (brute-force best combo, LLM writes rationale)
  → Plan saved as DRAFT

POST /plans/{id}/payguard
  → PayGuard Layer 1: AI Risk Assessment (stub)
  → PayGuard Layer 2: 10 deterministic rules
  → Verdict: APPROVED | REVIEW | BLOCKED
  → Plan → CHECKED or BLOCKED

POST /plans/{id}/approve  (requires flag acknowledgement if REVIEW)
  → Plan → APPROVED

POST /plans/{id}/pay  (idempotent)
  → Re-runs PayGuard
  → Creates PayPal order
  → Plan → PAYING
  → Returns approval_url for redirect

POST /payments/capture  (called from PaymentReturnPage)
  → Captures PayPal order
  → Plan → PAID
```

---

## Environment Variables

### Backend (`backend/.env`)

See [`backend/.env.example`](backend/.env.example) for the full, commented list. Defaults run fully offline
(`LLM_MODE=mock`, `PAYPAL_MODE=mock`, `SEARCH_MODE=mock`, SQLite). For live use set `LLM_MODE=live` with
`ANTHROPIC_API_KEY`, and `PAYPAL_MODE=sandbox` with `PAYPAL_CLIENT_ID` / `PAYPAL_CLIENT_SECRET`.

### Frontend (`frontend/.env`)

| Variable | Default | Description |
|----------|---------|-------------|
| `VITE_USE_MOCKS` | `true` | Use mock fixtures instead of real API |
| `VITE_API_BASE_URL` | `http://localhost:8000` | Backend base URL |
