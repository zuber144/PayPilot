PAYPAL AGENTOS+ PAYGUARD AI

Updated Agentic Commerce Architecture & Implementation Plan

A bounded multi-agent purchasing workflow with independent payment safeguards

| Area | Selected technology |
|---|---|
| Agent orchestration | LangGraph |
| Backend and APIs | Python 3.11 + FastAPI |
| LLM intelligence | OpenAI API (or another compatible LLM provider) |
| Database | PostgreSQL + SQLAlchemy 2 |
| Frontend | React + Vite + TypeScript + Tailwind CSS |
| Payments | PayPal Orders API v2 – Sandbox |
| Testing and local environment | pytest + Docker Compose + Postman |

Prepared from the supplied 16-page architecture, with an expanded orchestration design.

# 1. Executive Summary

PayPal AgentOS + PayGuard AI is a prototype for goal-driven business purchasing. A user describes a purchasing goal and budget. A set of specialised agents interprets the goal, discovers suitable providers, obtains and negotiates offers, and prepares a purchase plan. PayGuard independently evaluates the proposed plan. A human must explicitly approve the purchase before the backend creates and captures a PayPal Sandbox payment.

The updated design introduces LangGraph as an orchestration layer. Rather than relying only on a strict sequence of functions, an orchestrator evaluates the shared workflow state and chooses among permitted next actions—for example, retrying provider discovery when too few verified providers are found, requesting another negotiation round, or asking the user to clarify a requirement.

This is best described as a bounded, LLM-assisted multi-agent workflow. It includes agentic behaviour through goal interpretation, tool use, conditional routing and feedback loops. It is not an unrestricted autonomous system: actions are constrained by backend validation, policy rules, iteration limits and human payment approval.

# 2. Project Goals and Scope

## Goals

- Convert a natural-language business goal into structured purchasing requirements.

- Find and rank suitable providers from a seeded provider catalogue.

- Generate offers and conduct bounded negotiation using provider pricing constraints.

- Select a purchase plan that satisfies the user's budget and requirements.

- Assess risk using AI-assisted analysis and deterministic policy checks.

- Require explicit human approval before any payment action.

- Create, capture and record test payments through PayPal Sandbox.

- Show the agent execution trace, decisions, risk verdict and payment result in a dashboard.

## Prototype boundaries

- Use seeded/demo provider records; do not imply that real vendor integrations exist.

- Use PayPal Sandbox and test accounts; do not process real customer funds.

- Use one demo user/session for the hackathon prototype.

- Do not implement refunds, multi-currency conversion, full user management or production-grade security hardening unless time permits.

- Do not allow an LLM or orchestrator to approve, alter or directly execute a payment.

# 3. Automation, AI Agents and the Proposed Design

| Concept | Meaning in this project |
|---|---|
| Traditional automation | Predefined rules and steps execute in a fixed order. |
| LLM-assisted automation | An LLM interprets text or generates content inside a mostly fixed workflow. |
| AI agent | A component uses a goal, context and permitted tools to decide what action to take next. |
| Multi-agent workflow | Specialised agents handle different responsibilities and share results through a common state. |
| Proposed system | A bounded multi-agent workflow: the orchestrator can select conditional actions, but backend rules and human approval constrain it. |

Using an LLM API alone does not make a system an agent. The agentic behaviour comes from the control loop: observe the current state, choose a permitted action, execute a tool, inspect the result and decide what to do next. LangGraph provides the graph/state orchestration mechanism; the application logic determines the actual autonomy.

# 4. Updated High-Level Architecture

The browser communicates with FastAPI. FastAPI starts and monitors a LangGraph workflow. The graph coordinates specialised agent nodes and application tools. PostgreSQL stores goals, providers, offers, plans, traces and transactions. The LLM provider and PayPal Sandbox are external services.

| Layer | Components | Responsibility |
|---|---|---|
| Frontend | React dashboard | Goal entry, execution timeline, offers, PayGuard result, approval and transaction history. |
| API/backend | FastAPI | Authentication/session handling for demo, API contracts, validation and workflow lifecycle. |
| Orchestration | LangGraph orchestrator + shared state | Selects permitted next actions, routes conditionally, tracks iterations and records trace events. |
| Agent nodes | Goal, Discovery, Provider, Negotiation, Planning | Interpret requirements, search providers, create offers, negotiate and optimise a plan. |
| Safety | PayGuard AI risk analysis + deterministic policy engine | Raise risk flags, enforce mandatory rules and veto unsafe plans. |
| Persistence | PostgreSQL + SQLAlchemy | Store structured entities and JSONB workflow outputs. |
| Payment | PayPal Orders API v2 Sandbox | Create order after approval, redirect buyer, capture after return and store transaction result. |

## 4.1 Workflow and conditional routing

- START: receive the user's goal and budget.

- Goal Agent: extract needs, constraints, currency and deadline.

- Discovery Agent: query the provider catalogue and rank candidates.

- Orchestrator decision: if provider coverage is insufficient, retry discovery with permitted alternative filters; otherwise continue.

- Provider/Negotiation Agents: create offers and run a limited number of negotiation rounds.

- Planning Agent: evaluate offer combinations and select a plan within budget.

- Orchestrator decision: if no valid plan exists, request a permitted revision or ask the user; otherwise continue.

- PayGuard: run AI risk analysis and deterministic policy checks.

- Human checkpoint: show the plan and verdict; require explicit user authorisation.

- Payment service: re-run policy checks server-side, create PayPal order, capture after buyer return and record the result.

# 5. Agent Responsibilities and Example

Example user request: “I am organising a corporate event in Bangalore. I need catering for 100 people and a photographer. My total budget is ₹50,000 and the event is in 10 days. Find suitable options and prepare a plan.”

| Agent / component | Inputs | Responsibilities and outputs |
|---|---|---|
| Goal Agent | Free-text goal and budget | Extract categories, quantities, must-have constraints, budget in minor units, currency and deadline. |
| Discovery Agent | Structured needs + provider catalogue | Filter by category, verification, price and fit; rank candidates; report insufficient coverage. |
| Provider Agent | Need + provider configuration | Create offer scope, timeline and explanatory pitch. Price is computed from provider rules, not invented by the LLM. |
| Negotiation Agent | Opening offers + provider limits | Generate bounded counteroffers and provider responses; never go below min_price. |
| Planning Agent | Final offers + goal | Evaluate combinations, select one offer per need and produce line items, total and rationale. |
| Orchestrator | Shared graph state + permitted tools | Choose the next node/action, handle conditional retries, stop conditions and user clarification. |
| PayGuard | Plan + goal + provider records | Return risk flags and score; independently apply deterministic policy rules and produce APPROVED, REVIEW or BLOCKED. |

## 5.1 Example of adaptive behaviour

Suppose Discovery finds only one verified photographer. It returns a structured result indicating insufficient verified coverage. The orchestrator reads that result and selects the permitted action “retry_discovery”. The Discovery Agent runs again with broader non-mandatory filters. If two suitable verified candidates are found, the graph continues to negotiation. If the retry limit is reached, the system asks the user to revise the requirement or proceeds only if the minimum requirements are satisfied. It must never relax mandatory provider verification.

Illustrative outcome: ABC Catering offers ₹25,000 and Studio X offers ₹16,000. The Planning Agent selects the ₹41,000 combination, leaving ₹9,000 of the ₹50,000 budget. These are sample demo values, not real vendor quotes.

# 6. Tools and Technologies We Will Use

| Tool / technology | Purpose | Cost / licensing note |
|---|---|---|
| Python 3.11 | Backend language and agent/tool implementation. | Free and open source. |
| FastAPI | REST API, request validation, workflow endpoints and payment routes. | Free and open source. |
| LangGraph | Stateful orchestration, graph nodes, conditional edges and human-in-the-loop checkpoints. | Open-source library is free; optional hosted products may cost extra. |
| OpenAI API (initial choice) | LLM reasoning for goal extraction, offer language, negotiation support and risk analysis. | Usage-based paid API; check current model pricing and any available credits. |
| Pydantic v2 | Typed request/response schemas and validation of LLM outputs. | Free and open source. |
| SQLAlchemy 2 | Python ORM and database access. | Free and open source. |
| PostgreSQL | Persistent storage for users, goals, providers, offers, plans and transactions. | Free and open source when self-hosted; managed hosting may cost extra. |
| React + Vite + TypeScript | Frontend application and typed UI. | Free and open source. |
| Tailwind CSS | Frontend styling and responsive layouts. | Free and open source. |
| React Router | Frontend routes for goals, plans, payment return and transactions. | Free and open source. |
| TanStack Query | Server-state fetching, caching and polling. | Free and open source. |
| PayPal Orders API v2 – Sandbox | Test order creation, buyer approval and capture. | Sandbox testing is free; live processing has commercial fees. |
| Docker Compose | Run PostgreSQL locally and standardise local setup. | Free for the intended local open-source workflow; check Docker Desktop terms for organisational use. |
| pytest | Unit and integration tests for agents, policy and payment flows. | Free and open source. |
| Postman | Manual API testing and endpoint collections. | Free tier available; paid plans are optional. |
| Git + GitHub | Version control and team collaboration. | Git is free; GitHub offers a free tier and optional paid features. |

Cost summary: most development frameworks and local tools are free. LLM API usage and any paid cloud hosting are the likely prototype costs. PayPal Sandbox is for testing and does not move real funds. Verify current vendor pricing and terms before deployment; prices and free-tier limits can change.

## 6.1 Why LangGraph?

- Represents the workflow as nodes connected by normal or conditional edges.

- Shares a typed state between agent nodes.

- Supports loops and conditional routing, such as retrying discovery or negotiation.

- Supports human-in-the-loop checkpoints for approval workflows.

- Can be used inside the existing FastAPI backend; it does not replace FastAPI, React or PostgreSQL.

CrewAI and the OpenAI Agents SDK are alternatives, not additional required dependencies. For this implementation, use LangGraph only to avoid introducing multiple orchestration frameworks.

# 7. PayGuard: Independent Payment Safety

PayGuard runs after a plan is generated and again immediately before payment order creation. The AI risk layer can add caution or raise severity, but it cannot override a deterministic policy failure.

| Rule | Pass condition | Failure result |
|---|---|---|
| BUDGET_CAP | Plan total is no greater than the user's budget. | BLOCK |
| TXN_LIMIT | Plan total is within configured transaction limit. | BLOCK |
| VERIFIED_PROVIDER | Every selected provider is verified. | BLOCK |
| CURRENCY_MATCH | All line items and the goal use a supported matching currency. | BLOCK |
| NO_DUPLICATE | No PAID or PAYING plan already exists for the goal. | BLOCK |
| PRICE_FLOOR | Each offer is at or above the provider's minimum price. | BLOCK |
| TOTAL_INTEGRITY | Plan total equals the sum of its line items. | BLOCK |
| AI_RISK_HIGH | Risk score is below the high-risk threshold. | BLOCK |
| AI_RISK_MEDIUM | Risk score is below the medium-risk threshold. | REVIEW |
| SINGLE_VENDOR_SHARE | No provider exceeds the configured share threshold. | REVIEW |

Verdict combination: any BLOCK result produces BLOCKED. If there is no BLOCK but at least one REVIEW, the result is REVIEW and the user must acknowledge each displayed flag. Otherwise the plan is APPROVED. If the AI risk call fails, the result must not be treated as a clean approval; cap the verdict at REVIEW or stricter according to policy.

Security boundary: the frontend cannot submit an amount or a trusted verdict. The payment endpoint reads the amount from the stored plan, re-runs policy checks on the server and rejects any plan not in the APPROVED state.

# 8. PayPal Sandbox Payment Flow

- Create a PayPal Developer account and a Sandbox REST application.

- Create one Sandbox business (merchant) account and one personal (buyer) account.

- Store PAYPAL_CLIENT_ID, PAYPAL_CLIENT_SECRET and PAYPAL_BASE_URL in backend environment variables; never commit secrets.

- After user approval, the backend obtains/caches an OAuth access token and creates an Orders API v2 order with intent CAPTURE.

- The amount is derived from the stored plan total and converted from integer minor units to a decimal currency string.

- Redirect the buyer to the PayPal approval URL.

- After the buyer returns, validate the order/plan relationship and capture the order on the backend.

- Persist the PayPal order ID, capture ID, amount, currency, status and relevant response data.

- Use idempotency controls so repeated requests do not create duplicate live payments; reconcile status if the browser return is missed.

Developer portal: https://developer.paypal.com/

# 9. Proposed API Contract

| Method and route | Purpose |
|---|---|
| POST /api/v1/goals | Create a goal and start the LangGraph workflow. |
| GET /api/v1/goals/{id} | Read goal status, parsed requirements and execution trace. |
| GET /api/v1/goals/{id}/offers | Retrieve offers grouped by need. |
| GET /api/v1/plans/{id} | Retrieve plan, line items and PayGuard result. |
| POST /api/v1/plans/{id}/payguard | Re-run PayGuard after plan edits. |
| POST /api/v1/plans/{id}/approve | Record explicit user authorisation and required acknowledgements. |
| POST /api/v1/plans/{id}/pay | Re-check policy and create/reuse PayPal order. |
| POST /api/v1/payments/capture | Capture the approved PayPal order after buyer return. |
| GET /api/v1/transactions | Retrieve transaction history. |
| GET /api/v1/providers | Retrieve the seeded provider catalogue. |

# 10. Database Design

| Table | Important fields / purpose |
|---|---|
| users | id, name, email; one seeded demo user. |
| goals | id, user_id, raw_text, parsed JSONB, budget_minor, currency, status, trace JSONB, created_at. |
| providers | id, name, category, base_price_minor, min_price_minor, concession_rate, rating, turnaround_days, verified, persona. |
| offers | id, goal_id, provider_id, need_key, round, price_minor, scope, timeline_days, status. |
| plans | id, goal_id, items JSONB, total_minor, currency, rationale, payguard_result JSONB, status, approved_at. |
| transactions | id, plan_id, paypal_order_id, capture_id, amount_minor, currency, status, raw JSONB, created_at. |

Store money as integer minor units (for example, paise for INR) rather than floating-point values. Add uniqueness constraints for PayPal order IDs and suitable transaction idempotency constraints.

# 11. Frontend Screens

| Screen | What it displays |
|---|---|
| Goal dashboard (/) | Natural-language goal form, budget and demo scenarios. |
| Execution (/goals/:id) | Agent timeline, current status, trace events, decisions and retries. |
| Offers (within goal view) | Providers, opening offers, counteroffers and final prices. |
| Plan and PayGuard (/plans/:id) | Purchase breakdown, rationale, risk score, flags, policy checklist and verdict. |
| Payment (/plans/:id/pay) | Final review, approval acknowledgement and PayPal redirect. |
| Return (/payments/return) | Capture/status confirmation and receipt. |
| Transactions (/transactions) | Payment history, statuses and identifiers. |

Build the UI against mock JSON fixtures first. Use a VITE_USE_MOCKS flag to switch between mock data and the real API. Poll the goal status endpoint while the graph is running; render trace events as they arrive.

# 12. Repository Structure

agentos/├── backend/│   ├── app/│   │   ├── main.py│   │   ├── config.py│   │   ├── db.py│   │   ├── models.py│   │   ├── schemas.py│   │   ├── llm.py│   │   ├── orchestration/│   │   │   ├── graph.py│   │   │   ├── state.py│   │   │   ├── router.py│   │   │   └── tools.py│   │   ├── agents/│   │   │   ├── goal_agent.py│   │   │   ├── discovery_agent.py│   │   │   ├── provider_agent.py│   │   │   ├── negotiation_agent.py│   │   │   └── planning_agent.py│   │   ├── payguard/│   │   │   ├── risk.py│   │   │   ├── policy.py│   │   │   └── engine.py│   │   ├── payments/│   │   │   ├── paypal.py│   │   │   └── service.py│   │   └── routers/│   │       ├── goals.py│   │       ├── plans.py│   │       ├── payments.py│   │       └── providers.py│   ├── seed.py│   ├── requirements.txt│   └── .env.example├── frontend/│   └── src/│       ├── api/│       ├── pages/│       ├── components/│       └── mocks/├── docs/├── docker-compose.yml└── README.md

# 13. Four-Day Implementation Plan

| Day | Work | Exit criterion |
|---|---|---|
| Day 1 – Foundation | Create repo; set up FastAPI, React and PostgreSQL; define Pydantic schemas and API contracts; seed demo providers; create PayPal Sandbox app; agree graph state and tool contracts. | POST /goals starts a run; UI can render mock data; Sandbox credentials tested. |
| Day 2 – Agents and orchestration | Implement Goal, Discovery, Provider, Negotiation and Planning nodes; build LangGraph state and conditional routing; record trace events; connect goal and offers screens. | A seeded goal creates a purchase plan; demonstrate at least one conditional retry. |
| Day 3 – PayGuard and payment | Implement AI risk analysis, deterministic policy engine, human approval checkpoint, PayPal create/capture and transaction persistence. | One complete Sandbox payment; BLOCKED and REVIEW flows work. |
| Day 4 – Tests and demo | Test policy failures, duplicate payment, LLM invalid output, retry limits and failure states; polish dashboard; record and rehearse demo. | Two repeatable end-to-end demo runs and a recorded successful Sandbox payment. |

# 14. Team Ownership (Four Members)

| Member | Ownership | Primary areas |
|---|---|---|
| A – Orchestration / AI | LangGraph graph, state, orchestrator, Goal Agent, LLM wrapper and trace. | orchestration/, goal_agent.py, llm.py |
| B – Discovery / Data | Provider catalogue, database models, discovery, provider offers and negotiation. | models.py, seed.py, discovery_agent.py, provider_agent.py, negotiation_agent.py |
| C – PayGuard / Payments | Risk analysis, deterministic policy, approval state and PayPal integration. | payguard/, payments/, plans and payment routers |
| D – Frontend | React routes, API client, mocks, timeline, offer views, PayGuard and receipt screens. | frontend/ |

# 15. Tests That Demonstrate the Claims

| Test | What it proves |
|---|---|
| Discovery retry when provider coverage is insufficient | Orchestrator reacts to intermediate results and selects a conditional action. |
| Maximum retry / iteration limit | The agentic loop is bounded and cannot run indefinitely. |
| Provider verification failure | Unverified providers cannot pass the mandatory policy. |
| Over-budget plan | Budget policy blocks the purchase. |
| Price below provider minimum | Negotiation and pricing constraints are enforced by code. |
| Plan total mismatch | Server-side amount integrity is enforced. |
| Duplicate payment request | Idempotency prevents duplicate live orders. |
| LLM invalid JSON or timeout | Schema validation and fallback behaviour work safely. |
| PayPal Sandbox create/capture | The payment integration works end to end. |
| Frontend sends altered amount/verdict | Backend ignores untrusted client payment values and re-checks the stored plan. |

# 16. Suggested Hackathon Demonstration

- Start with the corporate event request and show the structured goal.

- Show the orchestrator selecting Discovery and the agents executing.

- Trigger a demo case where too few verified providers are found; show the orchestrator requesting another discovery attempt.

- Show provider offers and a bounded negotiation result.

- Show the selected plan, total and remaining budget.

- Show PayGuard's risk flags and deterministic rule outcomes.

- Demonstrate a BLOCKED case using an unverified provider; show that payment is unavailable.

- Run the clean scenario, obtain explicit user approval and complete a PayPal Sandbox payment.

- Show the stored transaction receipt and execution trace.

# 17. Key Design Principles

- Agentic does not mean unrestricted: the orchestrator may choose only from validated, permitted tools and actions.

- Prices are computed by application code from provider pricing rules, not generated by an LLM.

- The plan optimiser selects combinations algorithmically; the LLM may explain the rationale but does not invent totals.

- PayGuard is independent of the orchestrator and has final policy veto authority.

- Human approval is mandatory before payment.

- The backend is the source of truth for amounts, plan state and payment status.

- Use integer minor units for money and idempotency for payment operations.

- Record agent actions, decisions, reasons, durations, retries and fallbacks in the execution trace.

- Clearly label seeded provider data and Sandbox payments as demonstrations.

# 18. Official Documentation and Setup Links

- LangGraph documentation: https://docs.langchain.com/oss/python/langgraph/overview

- FastAPI documentation: https://fastapi.tiangolo.com/

- OpenAI API documentation: https://platform.openai.com/docs/

- PostgreSQL documentation: https://www.postgresql.org/docs/

- React documentation: https://react.dev/

- Vite documentation: https://vite.dev/guide/

- Tailwind CSS documentation: https://tailwindcss.com/docs

- PayPal Developer portal: https://developer.paypal.com/

- Docker Compose documentation: https://docs.docker.com/compose/

- SQLAlchemy documentation: https://docs.sqlalchemy.org/

- Pydantic documentation: https://docs.pydantic.dev/

- pytest documentation: https://docs.pytest.org/

End of document

