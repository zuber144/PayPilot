# PayPal AgentOS + PayGuard AI — Backend API Cheat Sheet

Base URL: `http://localhost:8000/api/v1`  
Interactive OpenAPI docs: `http://localhost:8000/docs`

All monetary values (`budget_minor`, `price_minor`, `total_minor`, `amount_minor`) are **integer minor units** (e.g., paise for `INR`: `₹50,000.00` = `5000000`).

---

## 1. Error Envelope (All Non-2xx Responses)

Every non-2xx response returns:

```json
{
  "error": {
    "code": "PLAN_NOT_APPROVED",
    "message": "Plan is BLOCKED and cannot be approved or paid."
  }
}
```

| Error Code | HTTP Status | When Returned |
|---|---|---|
| `VALIDATION_ERROR` | `422` | Invalid request body or missing required `REVIEW` flag acknowledgements |
| `NOT_FOUND` | `404` | Goal, plan, transaction, or route does not exist |
| `PLAN_NOT_APPROVED` | `409` | Plan is `BLOCKED`, not yet `USER_APPROVED`, or failed server-side PayGuard re-check |
| `DUPLICATE_PAYMENT` | `409` | Plan is already `PAID` |
| `CONFLICT` | `409` | Re-running PayGuard on a `PAYING` or `PAID` plan |
| `PAYPAL_ERROR` | `502` | PayPal API error or captured amount/currency mismatch |
| `PAYMENTS_DISABLED` | `503` | Global kill switch (`PAYMENTS_ENABLED=false`) is active |
| `INTERNAL_ERROR` | `500` | Unhandled server error |

---

## 2. Shared Enums

| Enum | Values |
|---|---|
| `goal.status` | `RUNNING`, `NEEDS_INPUT`, `PLAN_READY`, `FAILED` |
| `plan.status` | `DRAFT`, `CHECKED`, `USER_APPROVED`, `PAYING`, `PAID`, `FAILED` |
| `payguard.verdict` | `APPROVED`, `REVIEW`, `BLOCKED` |
| `rule.result` | `PASS`, `REVIEW`, `BLOCK` |
| `offer.status` | `OPEN`, `COUNTERED`, `ACCEPTED`, `REJECTED`, `SELECTED` |
| `trace.status` | `OK`, `RETRY`, `FALLBACK`, `ERROR` |
| `trace.node` | `orchestrator`, `goal`, `discovery`, `provider`, `negotiation`, `planning`, `payguard` |
| `transaction.status` | `CREATED`, `APPROVED`, `COMPLETED`, `FAILED` |
| `scenario` | `clean`, `retry`, `blocked`, `review` |

---

## 3. Endpoints (10 Routes)

### 3.1 `POST /api/v1/goals`
Create a purchasing goal and start the LangGraph workflow in the background.

**Request Body:**
```json
{
  "raw_text": "Corporate event in Bangalore: catering for 100 people and a photographer, event in 10 days",
  "budget_minor": 5000000,
  "currency": "INR",
  "scenario": "clean"
}
```

**Response (`202 Accepted`):**
```json
{
  "id": 1,
  "status": "RUNNING"
}
```

---

### 3.2 `GET /api/v1/goals/{id}`
Poll goal status, parsed requirements, live execution trace, and generated `plan_id`.

**Response (`200 OK`):**
```json
{
  "id": 1,
  "status": "PLAN_READY",
  "raw_text": "Corporate event in Bangalore: catering for 100 people and a photographer, event in 10 days",
  "budget_minor": 5000000,
  "currency": "INR",
  "scenario": "clean",
  "parsed": {
    "needs": [
      { "key": "catering", "category": "catering", "quantity": 100, "must_haves": [] },
      { "key": "photography", "category": "photography", "quantity": 1, "must_haves": [] }
    ],
    "deadline_days": 10,
    "currency": "INR"
  },
  "question": null,
  "trace": [
    {
      "seq": 1,
      "ts": "2026-11-10T12:00:00Z",
      "node": "goal",
      "action": "parse_goal",
      "status": "OK",
      "summary": "Parsed 2 need(s): catering, photography",
      "reason": "Parsed 2 need(s)",
      "duration_ms": 2,
      "data": { "needs": ["catering", "photography"], "deadline_days": 10, "currency": "INR" }
    }
  ],
  "plan_id": 1,
  "created_at": "2026-11-10T12:00:00Z"
}
```

---

### 3.3 `GET /api/v1/goals/{id}/offers`
Retrieve provider offers grouped by need, including every negotiation round (`round: 0` = opening offer, `1..3` = negotiation rounds).

**Response (`200 OK`):**
```json
{
  "goal_id": 1,
  "groups": [
    {
      "need_key": "catering",
      "offers": [
        {
          "provider_id": 1,
          "provider_name": "ABC Catering",
          "verified": true,
          "rating": 4.6,
          "timeline_days": 7,
          "opening_price_minor": 2800000,
          "final_price_minor": 2496666,
          "status": "SELECTED",
          "rounds": [
            { "round": 0, "price_minor": 2800000, "counter_minor": null, "status": "OPEN", "scope": "..." },
            { "round": 1, "price_minor": 2695000, "counter_minor": 2520000, "status": "COUNTERED", "scope": "..." },
            { "round": 2, "price_minor": 2593938, "counter_minor": 2425500, "status": "COUNTERED", "scope": "..." },
            { "round": 3, "price_minor": 2496666, "counter_minor": 2334544, "status": "SELECTED", "scope": "..." }
          ]
        }
      ]
    }
  ]
}
```

---

### 3.4 `GET /api/v1/plans/{id}`
Retrieve the selected purchase plan, line items, rationale, and latest PayGuard result (all 10 rules).

**Response (`200 OK`):**
```json
{
  "id": 1,
  "goal_id": 1,
  "status": "CHECKED",
  "currency": "INR",
  "total_minor": 4096666,
  "budget_minor": 5000000,
  "rationale": "Selected the lowest-total combination of verified providers within budget...",
  "items": [
    {
      "need_key": "catering",
      "provider_id": 1,
      "provider_name": "ABC Catering",
      "price_minor": 2496666,
      "timeline_days": 7,
      "verified": true,
      "currency": "INR"
    },
    {
      "need_key": "photography",
      "provider_id": 4,
      "provider_name": "Studio X",
      "price_minor": 1600000,
      "timeline_days": 4,
      "verified": true,
      "currency": "INR"
    }
  ],
  "payguard": {
    "verdict": "APPROVED",
    "risk_score": 0.1,
    "ai_ok": true,
    "flags": [],
    "rules": [
      { "id": "BUDGET_CAP", "result": "PASS", "detail": "..." },
      { "id": "TXN_LIMIT", "result": "PASS", "detail": "..." },
      { "id": "VERIFIED_PROVIDER", "result": "PASS", "detail": "..." },
      { "id": "CURRENCY_MATCH", "result": "PASS", "detail": "..." },
      { "id": "NO_DUPLICATE", "result": "PASS", "detail": "..." },
      { "id": "PRICE_FLOOR", "result": "PASS", "detail": "..." },
      { "id": "TOTAL_INTEGRITY", "result": "PASS", "detail": "..." },
      { "id": "AI_RISK_HIGH", "result": "PASS", "detail": "..." },
      { "id": "AI_RISK_MEDIUM", "result": "PASS", "detail": "..." },
      { "id": "SINGLE_VENDOR_SHARE", "result": "PASS", "detail": "..." }
    ],
    "checked_at": "2026-11-10T12:00:01Z"
  },
  "acknowledged_flags": [],
  "approved_at": null
}
```

---

### 3.5 `POST /api/v1/plans/{id}/payguard`
Re-run PayGuard on the stored plan and return the updated `PayGuardResult`.

---

### 3.6 `POST /api/v1/plans/{id}/approve`
Record explicit human authorization. For `REVIEW` plans, every flag with `requires_ack: true` must be listed in `acknowledged_flags`. Rejected with `409 PLAN_NOT_APPROVED` if verdict is `BLOCKED`.

**Request Body:**
```json
{
  "acknowledged_flags": ["SINGLE_VENDOR_SHARE"]
}
```

---

### 3.7 `POST /api/v1/plans/{id}/pay`
Re-checks PayGuard server-side, reads `total_minor` strictly from the stored plan (ignores any client-supplied amount/verdict), and creates or reuses a PayPal order (`PayPal-Request-Id: plan-{id}`).

**Request Body:** `{}`

**Response (`200 OK`):**
```json
{
  "plan_id": 1,
  "paypal_order_id": "MOCK-plan-1",
  "approval_url": "http://localhost:5173/payments/return?token=MOCK-plan-1",
  "status": "PAYING",
  "reused": false
}
```

---

### 3.8 `POST /api/v1/payments/capture`
Capture an approved PayPal order after buyer return. Idempotent: calling again on a captured order returns the stored receipt without a second capture call.

**Request Body:**
```json
{
  "paypal_order_id": "MOCK-plan-1"
}
```

**Response (`200 OK`):**
```json
{
  "id": 1,
  "plan_id": 1,
  "goal_id": 1,
  "goal_summary": "Corporate event in Bangalore: catering for 100 people and a photographer, event ",
  "paypal_order_id": "MOCK-plan-1",
  "capture_id": "MOCK-CAP-MOCK-plan-1",
  "amount_minor": 4096666,
  "currency": "INR",
  "status": "COMPLETED",
  "created_at": "2026-11-10T12:00:02Z"
}
```

---

### 3.9 `GET /api/v1/transactions`
List all transactions, newest first (`list[TransactionOut]`).

---

### 3.10 `GET /api/v1/providers`
List all seeded providers (`list[ProviderOut]`, each flagged with `"demo": true`).

---

## 4. Triggering the Four Demo Scenarios

Pass `"scenario"` in `POST /api/v1/goals`:

| Scenario | Payload | Expected Outcome |
|---|---|---|
| **1. Clean** | `scenario: "clean"`, `budget_minor: 5000000`, catering + photography | Verified providers (`ABC Catering` + `Studio X`), total `4,096,666` paise, verdict `APPROVED`, `/approve` -> `/pay` -> `/payments/capture` -> `PAID` |
| **2. Retry** | `scenario: "retry"`, `budget_minor: 5000000`, catering + photography | Discovery starts with strict filters (`min_rating=4.5`, `max_turnaround_days=5`), finds only 1 verified photographer (`Studio X`), orchestrator emits `RETRY` trace events relaxing preference filters (never verification), `LensCraft` appears, plan succeeds |
| **3. Blocked** | `scenario: "blocked"`, `budget_minor: 3600000`, catering + photography | Discovery includes unverified providers so cheapest combo (`QuickBites Co` + `PixelNest`) fits budget; PayGuard's `VERIFIED_PROVIDER` rule returns `BLOCK`, verdict `BLOCKED`, `/approve` and `/pay` rejected with `409 PLAN_NOT_APPROVED` |
| **4. Review** | `scenario: "review"`, `budget_minor: 5000000`, raw_text `"Catering for 100 people for our office event"` | Single vendor holds 100% (> 70%) of total; `SINGLE_VENDOR_SHARE` returns `REVIEW`, `/approve` with `[]` rejected (`422 VALIDATION_ERROR`), `/approve` with `["SINGLE_VENDOR_SHARE"]` succeeds |
