# Decisions log

Autonomous backend build. Each decision is final unless a test or reviewer defect forces a change.

1. **No pandoc available** — converted the .docx specs to markdown with a small Python script (`docs/*.md`).
2. **Addendum out of scope** — `PayPal_AgentOS_PayGuard_Addendum_Additions.docx` (ML models, injection classifier, AUTHORIZE flow, etc.) was not part of the brief. Only the kill switch (`PAYMENTS_ENABLED`) was adopted because it is cheap.
3. **Default DB is SQLite** (`sqlite:///./agentos.db`) so everything runs offline with no Docker. PostgreSQL via `docker-compose.yml` is supported by setting `DATABASE_URL`; JSON columns use JSONB on Postgres.
4. **Mock modes are defaults**: `LLM_MODE=mock`, `PAYPAL_MODE=mock`. The LLM mock is deterministic (keyword goal parsing, router picks the default action, risk 0.1).
5. **Contract extensions** beyond the spec's table columns: `goals.scenario`, `goals.question`, `offers.counter_minor`, `plans.acknowledged_flags`, `providers.currency`, `transactions.request_id`, `transactions.approval_url`. Needed for the scenario hint, NEEDS_INPUT question, negotiation-round display, approval acks and idempotency.
6. **AI failure cap** — when the risk call fails, both AI_RISK_HIGH and AI_RISK_MEDIUM return REVIEW ("AI risk check unavailable"), so the verdict can never be APPROVED and the user must acknowledge.
7. **Flags requiring acknowledgement** = every rule whose result is REVIEW (flag id = rule id). AI informational flags (`AI:<id>`) never need acknowledgement.
8. **Blocked scenario** — discovery normally drops unverified providers. The `blocked` scenario hint sets `include_unverified=True` (a deliberately misconfigured discovery) so PayGuard's independent VERIFIED_PROVIDER rule is demonstrated catching it. Budget INR 36,000 makes the cheapest combination use an unverified provider.
9. **Review scenario** — goal asks only for catering, so a single vendor holds 100% of the total and SINGLE_VENDOR_SHARE returns REVIEW.
10. **Retry scenario** — strict filters min_rating 4.5 / max_turnaround 5; retry 1 drops min_rating, retry 2 drops max_turnaround. Verification never relaxed.
11. **NEEDS_INPUT answering** — the 10-route contract has no "answer" route, so the user submits a new goal. Not implemented beyond storing the question.
12. **Error status codes** — PLAN_NOT_APPROVED/DUPLICATE_PAYMENT/CONFLICT 409, VALIDATION_ERROR 422, NOT_FOUND 404, PAYPAL_ERROR 502, PAYMENTS_DISABLED 503.
13. **Orchestrator in Antigravity** — the brief assumed Claude Code subagents (`.claude/agents/`). This run uses Antigravity subagents with the same roles (builders, tester, reviewer). They all run on the selected model, so per-role model choice and `/cost` budget checks don't apply here; the time and iteration limits are enforced instead.
