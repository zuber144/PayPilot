# PayPilot AgentOS + PayGuard AI Architecture

## 1. System Overview

PayPilot AgentOS is an autonomous procurement engine that pairs a multi-step agent pipeline with a deterministic safety and compliance layer (**PayGuard AI**) and **PayPal Orders API v2** settlement.

```mermaid
flowchart TD
    User([Procurement Officer]) -->|Goal & Budget| Frontend[React + Vite + Tailwind UI]
    Frontend -->|POST /api/v1/goals| API[FastAPI Monolith]
    
    subgraph AgentPipeline["5-Step Deterministic Agent Pipeline"]
        S1[1. Goal Analyzer] --> S2[2. Discovery Agent]
        S2 --> S3[3. Provider Agents]
        S3 --> S4[4. Negotiation Agent]
        S4 --> S5[5. Plan Generator]
    end
    
    API --> AgentPipeline
    AgentPipeline -->|Generated Plan| PayGuard[PayGuard AI Engine]
    
    subgraph PayGuardEngine["Dual-Layer PayGuard AI"]
        R1[Deterministic Rules Engine\n10 Strict Checks]
        R2[ML Risk Classifier\n0.0 - 1.0 Float Score]
        R1 --> VerdictCombiner{Verdict Combiner}
        R2 --> VerdictCombiner
    end
    
    PayGuard --> PayGuardEngine
    VerdictCombiner -->|APPROVED / REVIEW / BLOCKED| PlanVerdict[Plan Status]
    
    subgraph PaymentSettlement["PayPal Sandbox Settlement"]
        UserReview([Human Sign-off]) -->|Approve & Pay| PP_Create[PayPal Orders v2 Create]
        PP_Create -->|Approve URL| PP_Sandbox[PayPal Sandbox Auth]
        PP_Sandbox -->|Return Token| PP_Capture[PayPal Orders v2 Capture]
        PP_Capture -->|Captured Ledger| DB[(PostgreSQL Ledger)]
    end
    
    PlanVerdict --> PaymentSettlement
```

## 2. Core Modules

### 2.1 Fixed 5-Step Pipeline
The agent pipeline runs as a controlled state machine:
1. **Goal Analyzer**: Extracts needs, budget caps, deadline, and ISO-4217 currency.
2. **Discovery Agent**: Queries verified and candidate providers matching needed capabilities.
3. **Provider Agents**: Simulates provider pricing strategies and concessions.
4. **Negotiation Agent**: Executes iterative discount rounds within provider concession limits.
5. **Plan Generator**: Synthesizes the optimal cost-quality provider bundle into an executable plan.

### 2.2 PayGuard AI Decision Engine
A dual-layer verification gate evaluated before any money moves:
- **Deterministic Rules**:
  - `BUDGET_CAP`: Plan total &le; Goal budget
  - `TXN_LIMIT`: Plan total &le; Max transaction limit ($10,000 / ₹1,000,000)
  - `VERIFIED_PROVIDER`: All providers must be verified (KYC/KYB)
  - `CURRENCY_MATCH`: Standard ISO-4217 currency validation
  - `NO_DUPLICATE`: Idempotency safeguard preventing double billing
  - `PRICE_FLOOR`: No line item below provider minimum cost floor
  - `TOTAL_INTEGRITY`: Strict sum check over line items
  - `GOAL_ALIGNMENT`: Deliverables strictly match declared needs
  - `ML_RISK`: Machine learning risk score (< 0.40 = PASS, 0.40 - 0.70 = REVIEW, > 0.70 = BLOCK)
  - `SINGLE_VENDOR_SHARE`: Flags vendor concentration (> 70% = REVIEW)

### 2.3 PayPal Orders v2 Sandbox Integration
- Server-to-server OAuth token generation with in-memory caching
- Orders API v2 order creation with `CAPTURE` intent
- Return handler with mount-once capture idempotency
- Ledger recording of PayPal Order ID, Capture ID, amount in minor units, and timestamp.
