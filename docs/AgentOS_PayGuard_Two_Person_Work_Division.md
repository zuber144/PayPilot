PAYPAL AGENTOS + PAYGUARD AI

Two-Person Work Division

Person 1 owns the complete backend. Person 2 owns the complete frontend. Files, behaviour, screens, schedule and hand-offs.

| Area | Selected technology (unchanged from the architecture proposal) |
|---|---|
| Backend (Person 1) | Python 3.11, FastAPI, LangGraph, OpenAI API, Pydantic v2, SQLAlchemy 2, PostgreSQL, Docker Compose, pytest |
| Frontend (Person 2) | React + Vite + TypeScript, Tailwind CSS, React Router, TanStack Query |
| Payments | PayPal Orders API v2 (Sandbox only) |
| Shared | Git + GitHub, API contract (schemas.py mirrored in types.ts), Postman |

Companion to: PayPal_AgentOS_PayGuard_AI_Updated_Architecture.docx. Nothing here changes the architecture; it only assigns it to two people and adds the build-level detail each person needs.

# 1. How the Work Is Divided

|  | Person 1 - Backend | Person 2 - Frontend |
|---|---|---|
| Owns | Everything under backend/, docker-compose.yml, seed data, all tests | Everything under frontend/, mock layer, Postman collection, README, demo recording |
| Delivers | Working API, LangGraph workflow, 5 agents, PayGuard, PayPal Sandbox payment, database | Complete dashboard: goal entry, live agent timeline, offers, PayGuard verdict, approval, PayPal redirect, receipt, history |
| Is the source of truth for | Money amounts, plan state, verdicts, payment status | How all of that is shown. Never computes or sends a trusted amount or verdict |
| Blocked by the other? | No. Tests with pytest, curl and Postman | No. Builds against mock JSON until the real API is ready (VITE_USE_MOCKS) |
| Share of effort | About 60 to 65% | About 35 to 40%, plus the extra tasks in 1.1 |

## 1.1 Extra tasks given to Person 2 to balance the load

- Postman collection covering all 10 routes, with example requests and the four demo scenarios.

- docs/ folder: architecture diagram, screenshots, API cheat sheet.

- README.md: setup for both halves, environment variables, how to run the demo.

- Demo script, rehearsal and screen recording (section 6).

- Contract watch: on every backend change, diff schemas.py against types.ts and raise mismatches the same day.

## 1.2 Ground rules

- Day 1, first 90 minutes: freeze the contract together (section 2). Changes after that need both people to agree.

- The backend never trusts the browser: the payment amount and verdict are always read from the stored plan.

- The frontend never calls PayPal or the LLM directly. It only talks to FastAPI.

- Money is always integer minor units (paise) in JSON. Only money.ts on the frontend formats it for display.

- Every merge to main must start with docker compose up and the app loading with no console errors.

- Seeded provider data and Sandbox payments must be labelled as a demo in the UI.

# 2. The Shared Contract (Frozen on Day 1)

This is the only thing the two halves share. Person 1 writes it as Pydantic models in schemas.py. Person 2 mirrors it as TypeScript types in src/api/types.ts and as mock fixtures. Base path for all routes: /api/v1.

## 2.1 Routes

| Method and route | Used by screen | Behaviour |
|---|---|---|
| POST /goals | Dashboard | Body: raw_text, budget_minor, currency. Creates the goal, starts the LangGraph run in the background, returns {id, status: RUNNING} immediately. |
| GET /goals/{id} | Execution | Returns status, parsed requirements, trace[] and, when ready, plan_id. Polled every 1.5 s while RUNNING. |
| GET /goals/{id}/offers | Execution / Offers | Offers grouped by need, with every negotiation round. |
| GET /plans/{id} | Plan, Payment | Plan items, total, rationale, status and the latest PayGuard result. |
| POST /plans/{id}/payguard | Plan | Re-runs PayGuard on the stored plan and returns the new result. |
| POST /plans/{id}/approve | Payment | Body: acknowledged_flags[]. Records explicit approval. Rejected if verdict is BLOCKED or a REVIEW flag is not acknowledged. |
| POST /plans/{id}/pay | Payment | No amount in body. Re-checks policy, creates or reuses the PayPal order, returns approval_url. |
| POST /payments/capture | Return | Body: paypal_order_id. Captures after buyer return, stores the result, returns the receipt. |
| GET /transactions | Transactions | List of transactions, newest first. |
| GET /providers | Dashboard (info panel) | The seeded provider catalogue, flagged as demo data. |

## 2.2 Enums both sides must use exactly

| Enum | Values |
|---|---|
| goal.status | RUNNING, NEEDS_INPUT, PLAN_READY, FAILED |
| plan.status | DRAFT, CHECKED, USER_APPROVED, PAYING, PAID, FAILED |
| payguard.verdict | APPROVED, REVIEW, BLOCKED |
| rule.result | PASS, REVIEW, BLOCK |
| offer.status | OPEN, COUNTERED, ACCEPTED, REJECTED, SELECTED |
| trace.status | OK, RETRY, FALLBACK, ERROR |
| trace.node | orchestrator, goal, discovery, provider, negotiation, planning, payguard |

## 2.3 The three JSON shapes the UI depends on most

### Trace event (one per agent action)

{ "seq": 4, "ts": "2026-11-10T10:21:07Z", "node": "orchestrator",

"action": "retry_discovery", "status": "RETRY",

"summary": "Only 1 verified photographer found",

"reason": "Coverage < 2 for need 'photographer'; retry 1 of 2",

"duration_ms": 412, "data": { "relaxed": ["min_rating"] } }

### Plan

{ "id": 7, "goal_id": 3, "status": "CHECKED", "currency": "INR",

"total_minor": 4100000, "budget_minor": 5000000, "rationale": "...",

"items": [ { "need_key": "catering", "provider_id": 1,

"provider_name": "ABC Catering", "price_minor": 2500000,

"timeline_days": 7, "verified": true } ],

"payguard": { "verdict": "APPROVED", "risk_score": 0.18,

"ai_ok": true, "flags": [],

"rules": [ { "id": "BUDGET_CAP", "result": "PASS", "detail": "..." } ] } }

### Error envelope (all non-2xx responses)

{ "error": { "code": "PLAN_NOT_APPROVED", "message": "Plan is BLOCKED" } }

The frontend shows error.message directly and switches on error.code only for PLAN_NOT_APPROVED, DUPLICATE_PAYMENT, PAYPAL_ERROR and VALIDATION_ERROR.

# 3. Person 1 - Complete Backend

## 3.1 What you deliver

- A FastAPI service with the 10 routes in section 2, validation and the error envelope.

- A LangGraph workflow: Goal, Discovery, Provider, Negotiation and Planning nodes with an orchestrator that picks permitted next actions.

- PayGuard: AI risk analysis plus a deterministic policy engine with veto power.

- PayPal Sandbox integration: create order, redirect URL, capture, idempotency.

- PostgreSQL schema, seed data for 4 demo scenarios, Docker Compose.

- pytest suite proving each claim in section 15 of the architecture document.

## 3.2 Files to create

agentos/backend/

|-- app/

|   |-- main.py              FastAPI app, CORS, router mounting, error handlers

|   |-- config.py            Settings from env (pydantic-settings), thresholds

|   |-- db.py                Engine, SessionLocal, get_db dependency

|   |-- models.py            SQLAlchemy tables (section 3.8)

|   |-- schemas.py           Pydantic request/response models = the contract

|   |-- llm.py               OpenAI wrapper: call_json(), timeout, retry, fallback

|   |-- orchestration/

|   |   |-- state.py         AgentState TypedDict + trace helper

|   |   |-- graph.py         LangGraph nodes, edges, conditional routing

|   |   |-- router.py        allowed_actions(state), choose_action()

|   |   `-- tools.py         Permitted tools the router may select

|   |-- agents/

|   |   |-- goal_agent.py        free text -> structured needs

|   |   |-- discovery_agent.py   filter + rank providers

|   |   |-- provider_agent.py    build offers (price from rules)

|   |   |-- negotiation_agent.py bounded rounds, never below min_price

|   |   `-- planning_agent.py    pick best combination, write rationale

|   |-- payguard/

|   |   |-- risk.py          LLM risk score + flags

|   |   |-- policy.py        10 deterministic rules

|   |   `-- engine.py        combine -> APPROVED / REVIEW / BLOCKED

|   |-- payments/

|   |   |-- paypal.py        OAuth token cache, create order, capture, get order

|   |   `-- service.py       pay/capture business logic + idempotency

|   `-- routers/

|       |-- goals.py   plans.py   payments.py   providers.py

|-- tests/               one file per area (section 3.9)

|-- seed.py              providers + demo user, idempotent

|-- requirements.txt

`-- .env.example         OPENAI_API_KEY, DATABASE_URL, PAYPAL_CLIENT_ID,

PAYPAL_CLIENT_SECRET, PAYPAL_BASE_URL, FRONTEND_URL

agentos/docker-compose.yml   postgres:16 with a named volume

## 3.3 How the backend works, end to end

- POST /goals validates input, inserts a goals row with status RUNNING, starts the graph with FastAPI BackgroundTasks and returns at once.

- Goal Agent sends the text to the LLM with a strict JSON schema and validates the result with Pydantic. Output: needs[] (category, quantity, must-haves), deadline_days, currency. If the JSON is invalid after one retry, status becomes NEEDS_INPUT with a clarification question.

- Discovery Agent queries providers by category, drops anything unverified, applies preference filters (min rating, max turnaround, price ceiling), ranks the rest and returns candidates per need. It also returns a coverage report such as {photographer: 1 verified, required: 2}.

- Orchestrator decision: reads the coverage report. If coverage is below 2 per need and discovery retries are under the limit, it chooses retry_discovery, which relaxes only preference filters. Verification is never relaxed.

- Provider Agent creates one opening offer per candidate. Price is base_price_minor from the provider row. The LLM only writes the scope and pitch text.

- Negotiation Agent runs up to 3 rounds: our counter is 90% of the current price. The provider concedes by concession_rate per round but never below min_price_minor. All arithmetic is code. The LLM may phrase the messages.

- Planning Agent enumerates one offer per need with itertools.product, discards any total above budget, scores the rest (lowest total, then highest rating, then shortest turnaround) and picks the best. The LLM writes the rationale only and never touches numbers.

- Orchestrator decision: if no combination fits the budget, it chooses revise_plan (one extra negotiation round) or ask_user (status NEEDS_INPUT).

- PayGuard runs on the chosen plan. Risk layer plus policy engine produce the verdict (section 3.5). The plan row is saved with status CHECKED.

- Graph ends with goal status PLAN_READY. Every node wrote a trace event to goals.trace as it finished, so the UI timeline updates live.

- POST /plans/{id}/approve records the human approval. POST /plans/{id}/pay re-runs PayGuard, creates the PayPal order and returns approval_url. POST /payments/capture finishes the payment (section 3.6).

### Orchestrator design

The orchestrator is bounded. Code computes the list of allowed actions from the state, the LLM may pick one, and code validates the pick. If the LLM output is invalid, times out or is not in the allowed list, the router falls back to the default action and records a FALLBACK trace event.

| State situation | Allowed actions | Default action |
|---|---|---|
| After goal parsed | discover, ask_user | discover |
| Coverage below required | retry_discovery (if retries < 2), continue_with_minimum (only if minimum met), ask_user | retry_discovery |
| Offers ready | negotiate (if rounds < 3), plan | negotiate |
| No plan within budget | revise_plan (if revisions < 1), ask_user | revise_plan |
| Plan ready | payguard | payguard |

class AgentState(TypedDict):

goal_id: int; raw_text: str; budget_minor: int; currency: str

needs: list[Need]; filters: dict          # filters may be relaxed

candidates: dict[str, list[Provider]]; offers: list[Offer]

plan: Plan | None; payguard: PayGuardResult | None

retries: dict   # {discovery: 0, negotiation: 0, plan_revision: 0}

trace: list[TraceEvent]; status: str; next_action: str | None

| Limit (in config.py) | Value |
|---|---|
| MAX_DISCOVERY_RETRIES | 2 |
| MAX_NEGOTIATION_ROUNDS | 3 |
| MAX_PLAN_REVISIONS | 1 |
| MAX_GRAPH_STEPS (hard stop) | 25 |
| LLM_TIMEOUT_SECONDS / LLM_RETRIES | 20 / 1 |

## 3.4 llm.py: the single gateway to the model

- One function, call_json(system, user, schema_model), returns a validated Pydantic object or raises LLMFailure.

- Uses JSON mode, a 20 second timeout and one retry on invalid JSON.

- Every caller handles LLMFailure with a deterministic fallback: Goal Agent asks the user, Router uses the default action, Provider and Planning use template text, and PayGuard risk caps the verdict at REVIEW.

- Each fallback writes a trace event with status FALLBACK so it is visible in the UI and the demo.

- Never log the API key. Read it only from environment variables.

## 3.5 PayGuard

PayGuard runs after planning and again inside /pay. The AI layer can add flags or raise severity but can never override a deterministic failure.

| Rule | Passes when | On failure | Where |
|---|---|---|---|
| BUDGET_CAP | total <= goal budget | BLOCK | policy.py |
| TXN_LIMIT | total <= MAX_TXN_MINOR (config) | BLOCK | policy.py |
| VERIFIED_PROVIDER | every selected provider has verified = true | BLOCK | policy.py |
| CURRENCY_MATCH | all items and the goal share one supported currency | BLOCK | policy.py |
| NO_DUPLICATE | no other plan for this goal is PAYING or PAID | BLOCK | policy.py |
| PRICE_FLOOR | each price >= provider min_price_minor | BLOCK | policy.py |
| TOTAL_INTEGRITY | total == sum(items) | BLOCK | policy.py |
| AI_RISK_HIGH | risk_score < HIGH_THRESHOLD (0.7) | BLOCK | engine.py |
| AI_RISK_MEDIUM | risk_score < MEDIUM_THRESHOLD (0.4) | REVIEW | engine.py |
| SINGLE_VENDOR_SHARE | no provider above 70% of total | REVIEW | policy.py |

- Verdict: any BLOCK gives BLOCKED. Otherwise any REVIEW gives REVIEW. Otherwise APPROVED.

- If the AI risk call fails, ai_ok is false and the verdict is capped at REVIEW.

- Policy functions are pure: they take (plan, goal, providers, existing_plans) and return a list of RuleResult. This makes them trivial to test.

- risk.py asks the LLM for {risk_score 0-1, flags[]} with short plain-language reasons, validated by Pydantic.

- REVIEW flags must be acknowledged by the user in /approve, listed by flag id.

## 3.6 PayPal Sandbox payment (payments/)

- Setup: create a PayPal Developer account, a Sandbox REST app, one Sandbox business account and one personal buyer account. Put the keys in .env only.

- paypal.py: get_access_token() with in-memory caching until expiry; create_order(amount_str, currency, return_url, cancel_url, request_id); capture_order(order_id); get_order(order_id).

- Amount: read plan.total_minor from the database and convert to a string such as 41000.00. Nothing from the request body is used.

- Idempotency: send a PayPal-Request-Id header derived from the plan id. The transactions table has a unique constraint on paypal_order_id. If /pay is called twice for a PAYING plan, return the existing approval_url.

- /pay: require plan.status = USER_APPROVED, re-run PayGuard, reject unless verdict is not BLOCKED, create the order with intent CAPTURE, insert the transaction as CREATED, set the plan to PAYING, return approval_url.

- /capture: confirm the order id belongs to a PAYING plan, call capture, store capture_id, amount, status and the raw response, set the plan to PAID. If called again for a captured order, return the stored receipt.

- Missed return: a reconcile helper calls get_order and completes the capture if the buyer approved but the browser never returned.

Verify on Day 1: confirm the Sandbox accepts your currency. If INR is rejected, run the entire demo in USD (seed prices, goal budget and UI labels) rather than converting.

## 3.7 Seed data and the four demo scenarios (seed.py)

All values are demo data. Tune base_price, min_price and concession_rate so the clean scenario lands close to INR 25,000 + INR 16,000 = INR 41,000.

| Provider | Category | Base (INR) | Min (INR) | Rating | Turnaround | Verified |
|---|---|---|---|---|---|---|
| ABC Catering | catering | 28,000 | 24,000 | 4.6 | 7 days | Yes |
| Spice Route Caterers | catering | 32,000 | 27,000 | 4.4 | 6 days | Yes |
| QuickBites Co | catering | 22,000 | 20,000 | 4.1 | 5 days | No |
| Studio X | photography | 18,000 | 15,000 | 4.7 | 4 days | Yes |
| LensCraft | photography | 21,000 | 17,500 | 4.2 | 9 days | Yes |
| PixelNest | photography | 14,000 | 12,000 | 4.5 | 3 days | No |

| Scenario | What it must show |
|---|---|
| 1. Clean | Catering for 100 plus photographer, budget INR 50,000. Verified providers only, plan within budget, verdict APPROVED, payment succeeds. |
| 2. Retry | Strict first pass (min rating 4.5, max turnaround 5 days) finds only Studio X. Orchestrator retries with relaxed preference filters, LensCraft appears, flow continues. Trace shows the retry. |
| 3. Blocked | Budget low enough that the cheapest valid combination needs an unverified provider (PixelNest or QuickBites). VERIFIED_PROVIDER fails, verdict BLOCKED, payment unavailable. |
| 4. Review | Plan where one vendor holds more than 70% of the total. SINGLE_VENDOR_SHARE returns REVIEW, user must acknowledge the flag to continue. |

Provide a way to trigger each scenario: the dashboard sends a scenario hint such as scenario: "retry" in the goal body, which the Discovery Agent reads to start with the strict filters. Document this in the API cheat sheet.

## 3.8 Database (models.py)

| Table | Columns |
|---|---|
| users | id, name, email (one seeded demo user) |
| goals | id, user_id, raw_text, parsed JSONB, budget_minor, currency, status, trace JSONB, created_at |
| providers | id, name, category, base_price_minor, min_price_minor, concession_rate, rating, turnaround_days, verified, persona |
| offers | id, goal_id, provider_id, need_key, round, price_minor, scope, timeline_days, status |
| plans | id, goal_id, items JSONB, total_minor, currency, rationale, payguard_result JSONB, status, approved_at |
| transactions | id, plan_id, paypal_order_id (unique), capture_id, amount_minor, currency, status, raw JSONB, created_at |

Money columns are integers (paise). Create tables with SQLAlchemy metadata on startup for the hackathon; skip Alembic.

## 3.9 Tests (pytest)

| File | Test | Proves |
|---|---|---|
| test_orchestration.py | Retry when coverage is low; stops at max retries; invalid router output falls back | Bounded loop and conditional routing |
| test_negotiation.py | Price never goes below min_price | Pricing enforced by code |
| test_policy.py | Unverified provider, over budget, total mismatch, currency mismatch, duplicate | Each BLOCK rule |
| test_payguard.py | AI failure caps at REVIEW; AI cannot override a BLOCK | Deterministic veto |
| test_llm.py | Invalid JSON and timeout return fallback | Safe failure |
| test_payments.py | Duplicate /pay reuses order; client-sent amount ignored; non-approved plan rejected; PayPal calls mocked | Server-side integrity |
| test_e2e_sandbox.py | One real Sandbox create + capture (marked, run manually) | Integration works |

## 3.10 Backend definition of done

- docker compose up plus uvicorn starts everything; /docs shows all 10 routes.

- All four scenarios run from a clean database with seed.py.

- pytest passes; the Sandbox test has been run at least once with a recorded capture id.

- No secret in git; .env.example is complete.

- Every route returns the error envelope on failure.

# 4. Person 2 - Complete Frontend

## 4.1 What you deliver

- A React + Vite + TypeScript app with 7 screens and a persistent demo banner.

- A live agent timeline that updates by polling while the workflow runs.

- A mock layer with fixtures for all four scenarios so the UI works with no backend.

- PayGuard verdict, policy checklist and approval flow, PayPal redirect and receipt.

- Plus: Postman collection, README, docs/ and the demo recording.

## 4.2 Files to create

agentos/frontend/

|-- index.html   package.json   vite.config.ts   tailwind.config.js

|-- .env.example            VITE_API_BASE_URL, VITE_USE_MOCKS=true

`-- src/

|-- main.tsx            QueryClientProvider + RouterProvider

|-- App.tsx             route table (section 4.4)

|-- index.css           Tailwind layers + font import

|-- api/

|   |-- types.ts        mirrors backend schemas.py exactly

|   |-- client.ts       fetch wrapper, error envelope, mock switch

|   `-- hooks.ts        useGoal, useOffers, usePlan, usePayGuard, useApprove,

|                       usePay, useCapture, useTransactions, useProviders

|-- mocks/

|   |-- handlers.ts     returns fixtures; simulates timeline progress

|   `-- fixtures/       goal_running.json, goal_retry.json, plan_clean.json,

|                       plan_blocked.json, plan_review.json, offers.json,

|                       transactions.json, providers.json

|-- lib/

|   |-- money.ts        formatMinor(4100000,'INR') -> Rs 41,000.00

|   |-- time.ts         relative time, duration formatting

|   `-- constants.ts    status -> colour/label maps, route paths

|-- pages/

|   |-- GoalDashboard.tsx   GoalExecution.tsx   PlanPage.tsx

|   |-- PaymentPage.tsx     PaymentReturn.tsx   Transactions.tsx

|   `-- NotFound.tsx

`-- components/

|-- layout/   AppShell  NavBar  DemoBanner

|-- goal/     GoalForm  ScenarioChips  ProviderPanel

|-- trace/    AgentTimeline  TraceEvent  RetryChip

|-- offers/   OfferGroup  NegotiationRounds

|-- plan/     PlanSummary  BudgetBar  LineItemTable

|-- payguard/ VerdictBanner  RiskGauge  FlagList  PolicyChecklist

|-- payment/  ApprovalPanel  ReceiptCard  TransactionTable

`-- ui/       Button  Card  Badge  Spinner  Skeleton  EmptyState

ErrorState  Toast

## 4.3 Look and feel

Clean fintech dashboard. Light theme, generous white space, one accent colour, and colour used only to carry status meaning. Desktop first for the demo laptop; layouts collapse to a single column on phones.

| Element | Specification |
|---|---|
| Palette | Navy #003087 (nav bar, headings), PayPal blue #0070BA (primary buttons, links), page background slate-50, cards white with slate-200 border |
| Status colours | APPROVED / PASS / PAID: green #16A34A. REVIEW / RETRY / FALLBACK: amber #D97706. BLOCKED / BLOCK / ERROR: red #DC2626. RUNNING: blue with a pulsing dot. Always pair colour with an icon and text, never colour alone. |
| Typography | Inter (system sans fallback). Page title 24 px semibold, section title 18 px semibold, body 14 px, captions 12 px slate-500. IDs, order numbers and trace data in a monospace face. |
| Cards | rounded-xl, 1 px border, shadow-sm, 24 px padding, 24 px gap between cards |
| Buttons | Primary: blue filled. Secondary: white with border. Danger: red outline. Disabled state is visibly greyed with a tooltip saying why (for example, 'Blocked by PayGuard'). |
| Layout | Fixed top NavBar (logo, Goals, Transactions). Content centred, max width 1152 px. A slim yellow DemoBanner under the nav on every page: 'Demo: seeded providers and PayPal Sandbox. No real money moves.' |
| Motion | Only functional: timeline items fade in as they arrive, progress dots pulse while RUNNING, no decorative animation |
| Money | Always through formatMinor. Right-aligned, tabular numerals, currency symbol shown |
| States | Every data component has loading (skeleton), empty and error (message + Retry button) states |

## 4.4 Screens

| Screen | Route | Purpose |
|---|---|---|
| Goal dashboard | / | Start a goal |
| Execution | /goals/:id | Watch agents work, see offers |
| Plan and PayGuard | /plans/:id | Review plan and safety verdict |
| Payment | /plans/:id/pay | Approve and go to PayPal |
| Return | /payments/return | Capture and show receipt |
| Transactions | /transactions | History |
| Not found | * | Friendly 404 with link home |

### Screen 1: Goal dashboard ( / )

- Layout: two columns on desktop. Left (about 60%): the goal card. Right: a 'How it works' card (5 steps) and a collapsed ProviderPanel listing the seeded providers tagged 'Demo data'.

- Goal card: large textarea with placeholder 'Describe what you need to buy...', budget input with currency selector, a row of ScenarioChips (Clean, Low coverage, Unverified provider, Needs review) that fill the form with the sample text and set the scenario hint, and a primary 'Start AgentOS' button.

- Behaviour: validates text length and budget above zero, calls POST /goals, then navigates to /goals/:id. Button shows a spinner and is disabled while submitting.

- Errors: inline field errors for validation, toast for server errors.

### Screen 2: Execution ( /goals/:id )

- Header: goal text, budget, a StatusBadge (RUNNING pulses blue) and elapsed time.

- Left, AgentTimeline: vertical stepper. Each TraceEvent row shows an icon per node, the node name, the one-line summary, duration, and an expand arrow revealing reason and data as formatted JSON. RETRY events show an amber RetryChip such as 'Retry 1 of 2' with the reason visible without expanding. FALLBACK events show a grey 'Fallback used' tag.

- Right, parsed requirements card: needs, quantities, deadline and currency as soon as the Goal Agent finishes.

- Below, Offers section: one OfferGroup per need. Each lists providers with a verified tick, opening price, a NegotiationRounds mini-table (round, our counter, their response, price) and the final price. The selected offer has a green outline.

- Data: poll GET /goals/:id every 1.5 s while status is RUNNING, stop on any other status. Append new trace events with a fade-in.

- End states: PLAN_READY shows a primary 'Review plan' button. NEEDS_INPUT shows the question in an amber card with an input to answer. FAILED shows an error card with 'Try again'.

### Screen 3: Plan and PayGuard ( /plans/:id )

- Top: full-width VerdictBanner. APPROVED is green with a check, REVIEW amber with a warning, BLOCKED red with a stop icon and the sentence 'Payment is not available for this plan'.

- Left, PlanSummary: LineItemTable (need, provider with verified badge, timeline, price), total, a BudgetBar showing spent versus budget and the remaining amount, and the rationale paragraph.

- Right, PayGuard card: RiskGauge (semicircle or bar 0 to 1 with the medium and high thresholds marked), FlagList with each AI flag and its reason, and the PolicyChecklist: all 10 rules, each with PASS / REVIEW / BLOCK icon, rule id, plain-English description and the detail text from the backend.

- Actions: 'Re-run PayGuard' (secondary) calls POST /plans/:id/payguard. 'Continue to payment' (primary) is enabled for APPROVED and REVIEW, disabled with a tooltip for BLOCKED.

- AI failure: if ai_ok is false, show a small amber note 'AI risk check unavailable, verdict limited to REVIEW'.

### Screen 4: Payment ( /plans/:id/pay )

- Final review card: read-only summary: items, total, provider names, currency.

- ApprovalPanel: for REVIEW verdicts, one checkbox per flag, each with its text. A final checkbox 'I authorise this Sandbox payment'. The 'Approve and pay with PayPal' button stays disabled until all boxes are ticked.

- Flow: on click call POST /plans/:id/approve with the acknowledged flag ids, then POST /plans/:id/pay, then set window.location to approval_url. No amount is ever sent.

- Errors: PLAN_NOT_APPROVED, DUPLICATE_PAYMENT and PAYPAL_ERROR show an error card with the backend message and a back link.

- Safety copy: 'You will be redirected to PayPal Sandbox. Use your Sandbox buyer account.'

### Screen 5: Return ( /payments/return )

- PayPal returns here with a token query parameter (the order id). On mount call POST /payments/capture once (guard against React double-invoke).

- While waiting: 'Confirming your payment...' with a spinner.

- Success: green ReceiptCard with plan summary, amount, currency, PayPal order id, capture id, status and time, plus buttons 'View transactions' and 'Start a new goal'.

- Failure or cancel: red card with the message and 'Back to plan'.

- Re-visiting the page must show the stored receipt, not an error.

### Screen 6: Transactions ( /transactions )

- TransactionTable: date, goal summary, amount, status badge (PAID green, CREATED grey, FAILED red), order id and capture id in monospace with a copy button.

- Empty state: 'No payments yet' with a link to start a goal.

## 4.5 Data layer and behaviour

- TanStack Query for all server state. Polling via refetchInterval that returns false once the goal is not RUNNING.

- client.ts reads VITE_USE_MOCKS. When true it calls mocks/handlers.ts instead of fetch. The handler simulates progress by revealing one more trace event every 1.2 s, so the live timeline can be built and demoed with no backend.

- Switching to the real API: set VITE_USE_MOCKS=false and VITE_API_BASE_URL. Nothing else changes. Switch one endpoint group at a time as Person 1 ships them.

- Never trust the client for money: no amount or verdict is ever put in a request body. Display values come from the last GET only.

- Errors: client.ts parses the error envelope into a typed ApiError. Pages render ErrorState with Retry.

- Accessibility basics: keyboard-focusable buttons, visible focus ring, aria-live on the status badge, text alternatives for icons, sufficient contrast.

- TypeScript: strict mode on. No any in api/types.ts.

## 4.6 Mock fixtures to prepare on Day 1

| Fixture | Content |
|---|---|
| goal_running.json | Clean scenario trace in 8 steps, ending PLAN_READY with plan_id |
| goal_retry.json | Same plus a RETRY event on discovery and the resulting extra provider |
| plan_clean.json | Verdict APPROVED, all 10 rules PASS, total 4,100,000 paise |
| plan_blocked.json | Verdict BLOCKED, VERIFIED_PROVIDER = BLOCK |
| plan_review.json | Verdict REVIEW, SINGLE_VENDOR_SHARE = REVIEW with one flag to acknowledge |
| offers.json, providers.json, transactions.json | Matching data with negotiation rounds, six seed providers, two sample transactions |

## 4.7 Frontend checks

| Check | Expected |
|---|---|
| BLOCKED plan | 'Continue to payment' disabled with tooltip; /plans/:id/pay shows backend error if opened directly |
| REVIEW plan | Cannot pay until every flag checkbox is ticked |
| Tampering | Editing the DOM or request in dev tools cannot change the charged amount (verify in Network tab that no amount is sent) |
| Double click on pay | Only one order is created (button disables; backend idempotent) |
| Page refresh on /goals/:id | Timeline reloads fully from GET /goals/:id |
| Return page refreshed | Shows the stored receipt, no second capture |
| Backend down | Every screen shows ErrorState with Retry, nothing crashes |
| Narrow window (about 400 px) | Single column, tables scroll horizontally, no clipped buttons |

## 4.8 Frontend definition of done

- All 7 routes work with mocks and with the real API.

- All four scenarios can be driven from the dashboard chips.

- No console errors; loading, empty and error states exist on every data component.

- Postman collection, README and docs/ are complete.

- Demo recorded: one clean run ending in a Sandbox payment, plus the blocked and retry cases.

# 5. Four-Day Schedule

| Day | Person 1 - Backend | Person 2 - Frontend | Exit check |
|---|---|---|---|
| Day 1 Foundation | Repo, Docker Compose, Postgresconfig.py, db.py, models.py, schemas.pyseed.py with 6 providersAgentState and tool contractsPayPal Sandbox app and accounts, currency check | Vite + TS + Tailwind scaffold, routes, AppShell, DemoBannertypes.ts mirroring schemas.pyAll fixtures and mock handlersmoney.ts, constants.ts, ui/ componentsGoal dashboard on mocks | POST /goals starts a run; UI renders mock data; Sandbox keys tested |
| Day 2 Agents | llm.py with fallbackGoal, Discovery, Provider, Negotiation, Planning agentsgraph.py + router.py with retry and limitsTrace events saved after every nodeGET /goals, /offers, /providers | AgentTimeline, TraceEvent, RetryChipExecution page with polling on mocksOfferGroup, NegotiationRoundsFlip goal and offers hooks to real API at midday if ready | Seeded goal makes a plan; retry visible in the UI |
| Day 3 Safety + Payment | policy.py, risk.py, engine.py/plans routes, approve, pay, capturepaypal.py, service.py, idempotencyTests for policy and payments | Plan page: VerdictBanner, RiskGauge, PolicyChecklist, FlagListPaymentPage, ApprovalPanel, Return, ReceiptCard, TransactionsSwitch everything to the real API by evening | One full Sandbox payment; BLOCKED and REVIEW work |
| Day 4 Test + Demo | Remaining pytest cases, failure pathsFix bugs reported by Person 2Freeze backend by midday | Frontend checks (4.7), polish, responsive fixesPostman collection, README, docs/Record demo, rehearse twice | Two repeatable end-to-end runs; recorded payment |

## 5.1 Sync points

| When | What happens |
|---|---|
| Day 1, first 90 min | Freeze routes, enums and the three JSON shapes (section 2). Both sign off. |
| Day 1 end | Person 1 shows /docs with stub endpoints returning fixture-shaped JSON. Person 2 shows the UI on mocks. |
| Day 2 midday | Person 1 ships real GET /goals/:id with trace. Person 2 flips the timeline to it. |
| Day 3 midday | Plan and PayGuard endpoints live. Person 2 flips plan and payment screens. |
| Day 3 evening (30 min) | Run the full flow together. Anything unfinished is cut, not carried into Day 4. |
| Day 4 midday | Backend feature freeze. Only bug fixes after this. |

# 6. Demo Plan

| # | Step | Screen | Presenter |
|---|---|---|---|
| 1 | Enter the corporate event goal; show the structured requirements | Dashboard, Execution | Person 2 |
| 2 | Explain the orchestrator choosing actions as the timeline fills | Execution | Person 1 |
| 3 | Low-coverage scenario: show the retry and why verification is never relaxed | Execution | Person 1 |
| 4 | Show offers, negotiation rounds and the floor price rule | Offers | Person 1 |
| 5 | Show the plan, total and remaining budget | Plan | Person 2 |
| 6 | Show PayGuard flags and the 10 rule outcomes | Plan | Person 1 |
| 7 | Blocked scenario: payment unavailable | Plan | Person 2 |
| 8 | Clean scenario: approve, PayPal Sandbox, receipt | Payment, Return | Person 2 |
| 9 | Transactions and the stored trace | Transactions | Person 2 |

Rehearse twice on Day 4. Keep the recorded video as a fallback if the network or Sandbox fails during judging.

# 7. Risks and Cut List

| Risk | Mitigation |
|---|---|
| Sandbox rejects INR | Check on Day 1. Fall back to USD across seed, goal and UI. |
| LLM slow or invalid output | 20 s timeout, one retry, deterministic fallbacks, trace shows FALLBACK. Keep one pre-recorded run. |
| Contract drift between halves | Person 2 diffs schemas.py and types.ts after every backend change. Version the fixtures. |
| Person 1 falls behind | Person 2 stays on mocks and finishes polish; cut order below. |
| PayPal return page missed | Reconcile helper (3.6) plus a stored receipt on revisit. |

Cut in this order if time runs short: (1) re-run PayGuard button and /payguard route, (2) transactions page filters, (3) NegotiationRounds detail table, (4) responsive polish, (5) the retry scenario live (show it from the recording). Never cut: PayGuard policy checks, human approval, server-side amount, Sandbox payment.

# 8. Day 0 Setup Checklist

| Person 1 | Person 2 |
|---|---|
| Python 3.11, Docker DesktopOpenAI API key and billing or credits checkedPayPal Developer account, Sandbox app, business and buyer accountsGitHub repo created, collaborator addedPostgres container runs | Node 20 LTS, pnpm or npmPostman installedFigma not required; follow section 4.3Cloned repo, Vite app bootsPayPal Sandbox buyer login tested in browser |

