# PayPilot AgentOS API Cheat Sheet

Base URL: `http://localhost:8000/api/v1`

## Endpoints Summary

| Method | Endpoint | Description | Request Body | Response |
|--------|----------|-------------|--------------|----------|
| `POST` | `/goals` | Initialize procurement agent pipeline | `CreateGoalRequest` | `Goal` |
| `GET` | `/goals/{id}` | Get goal status & progressive trace | None | `Goal` |
| `GET` | `/goals/{id}/offers` | Get negotiation offers across rounds | None | `Offer[]` |
| `GET` | `/plans/{id}` | Get plan details & PayGuard audit | None | `Plan` |
| `POST` | `/plans/{id}/payguard` | Run or re-evaluate PayGuard AI | None | `PayGuardResult` |
| `POST` | `/plans/{id}/approve` | Human-in-the-loop signoff | `ApproveRequest` | `Plan` |
| `POST` | `/plans/{id}/pay` | Create PayPal Sandbox Order | None | `PayResponse` |
| `POST` | `/payments/capture` | Capture authorized PayPal payment | `CaptureRequest` | `CaptureResponse` |
| `GET` | `/payments/transactions`| List immutable ledger transactions | None | `Transaction[]` |
| `GET` | `/providers` | List marketplace providers | None | `Provider[]` |

---

## Example Payloads

### Create Goal
```json
POST /api/v1/goals
{
  "raw_text": "Build a responsive website and write SEO copy",
  "budget_minor": 500000,
  "currency": "USD",
  "user_id": 1
}
```

### Approve Plan
```json
POST /api/v1/plans/1/approve
{
  "acknowledged_flags": ["VENDOR_CONCENTRATION"]
}
```

### Capture Payment
```json
POST /api/v1/payments/capture
{
  "token": "PP-ORDER-ID-OR-TOKEN",
  "plan_id": 1
}
```
