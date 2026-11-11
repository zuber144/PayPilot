# CLAUDE.md — Backend rules for PayPal AgentOS + PayGuard AI

Spec: `docs/PayPal_AgentOS_PayGuard_AI_Updated_Architecture.md` and
`docs/AgentOS_PayGuard_Two_Person_Work_Division.md` (section 3 = backend). Decisions: `docs/DECISIONS.md`.
The addendum doc is **out of scope** for this build.
**Domain pivot (DECISIONS.md #18):** the app now compares e-commerce store listings (Amazon/Flipkart) instead of
negotiating with service vendors. "Provider" in code = one store listing; the "negotiation" node = price comparison.

## Frozen contract (do not edit without the lead)
`backend/app/enums.py`, `schemas.py`, `models.py`, `config.py`, `db.py`, `errors.py`.
If you need a contract change, report it to the lead instead of editing.

## Hard rules
1. Money = integer minor units everywhere. Never floats for money. Conversion to a decimal
   string happens only in `payments/paypal.py` (`minor_to_str(4100000) == "41000.00"`).
2. `/pay` reads the amount from the stored plan (`plans.total_minor`), never from the request.
3. The LLM never sets prices, totals, verdicts, approvals or orchestration outside the allowed list.
   Code computes all numbers. The LLM writes text and picks from code-computed allowed actions only.
4. PayGuard deterministic rules override the AI layer. If the AI call fails: `ai_ok=False`, verdict capped at REVIEW
   (AI_RISK_HIGH and AI_RISK_MEDIUM both return REVIEW with detail "AI risk check unavailable").
5. Discovery retries relax only preference filters (`Filters`). Verification is never relaxed by the orchestrator.
6. All loops are bounded by `config.py` limits (MAX_DISCOVERY_RETRIES, MAX_NEGOTIATION_ROUNDS,
   MAX_PLAN_REVISIONS, MAX_GRAPH_STEPS, MAX_PLAN_COMBINATIONS).
7. Everything runs offline: `LLM_MODE=mock`, `PAYPAL_MODE=mock`, `SEARCH_MODE=mock` are defaults. Live tests use `@pytest.mark.live`
   and are skipped without keys.
8. No secrets in git. Never log API keys.
9. Every non-2xx response uses `{"error": {"code", "message"}}` (raise `app.errors.ApiError`).
10. Every agent action and every fallback writes a trace event (`TraceEvent`); fallbacks use status FALLBACK.

## File ownership (Phase 1)
| Builder | Owns |
|---|---|
| A | `app/llm.py`, `app/llm_mock.py`, `app/orchestration/*` (state.py, graph.py, router.py, tools.py) |
| B | `app/agents/*`, `app/search/*`, `backend/seed.py` |
| C | `app/payguard/*` (policy.py, risk.py, engine.py) |
| D | `app/payments/*`, `app/routers/*`, `app/main.py` |
| Tester | `backend/tests/*` (except `conftest.py`, owned by the lead) |
| Lead | contract files, `CLAUDE.md`, `docs/*`, `scripts/*`, `conftest.py` |

## Module interfaces (everyone codes against these)

### `app/llm.py` (A)
```python
class LLMFailure(Exception): ...
def call_json(system: str, user: str, schema_model: type[T], *, task: str) -> T
```
- `task` ∈ {"goal_parse","route","offer_text","negotiation_text","plan_rationale","risk"}.
- Mock mode (`settings.LLM_MODE=="mock"` or no key): delegates to `app.llm_mock.respond(task, system, user) -> dict`
  then validates with `schema_model`. Deterministic.
- Live mode (`LLM_PROVIDER`): `anthropic` (default; `ANTHROPIC_MODEL=claude-haiku-5-5`, structured outputs
  constrained to `schema_model` via `anthropic.transform_schema`, no temperature, refusal/max_tokens -> error) or
  `openai` (JSON mode). Timeout `LLM_TIMEOUT_SECONDS`, SDK retries off, `LLM_RETRIES` retry on invalid
  JSON/validation error, then raise `LLMFailure`. Timeouts/API errors also raise `LLMFailure`.
  Live smoke test: `pytest -m live tests/test_llm_live.py` (live tests are opt-in; default pytest runs offline).
- The raw transport is a module-level function `_raw_completion(system, user, task) -> str` so tests can monkeypatch it
  (to return invalid JSON or raise TimeoutError) — when monkeypatched, it is used in both modes. Concretely:
  `call_json` always calls `_raw_completion`; in mock mode `_raw_completion` returns `json.dumps(llm_mock.respond(...))`.
- `llm_mock.respond` user prompts: callers put a JSON object in `user` (e.g. `{"raw_text":..., "currency":...}`)
  so the mock can parse it. Goal mock: keyword parse (cater/food -> catering with quantity from "for N people";
  photo -> photography). Route mock: returns the first allowed action listed in the user JSON `allowed`.
  Risk mock: risk_score 0.1, no flags. Text tasks: short templated strings.

### `app/agents/*` (B) — pure functions, no DB writes, no trace writes (graph does those)
```python
# goal_agent.py
def run(raw_text: str, currency: str) -> GoalAgentResult
#   GoalAgentResult(parsed: ParsedGoal | None, question: str | None, fallback: bool, reason: str)
#   needs empty / LLMFailure -> parsed=None, question set. Never proceed with empty needs.
# discovery_agent.py
def initial_filters(scenario: str | None) -> Filters          # "retry" -> min_rating 4.5, max_turnaround 5
def relax_filters(filters: Filters, attempt: int) -> tuple[Filters, list[str]]  # attempt 1 drops min_rating, 2 drops max_turnaround
def run(providers: list[ProviderOut], needs: list[Need], filters: Filters, *, include_unverified: bool = False)
    -> tuple[dict[str, list[ProviderOut]], CoverageReport]
#   Ranked by rating desc, then price asc. Unverified dropped unless include_unverified (blocked-scenario demo only).
#   Coverage counts only VERIFIED candidates.
# provider_agent.py  (Product Extractor)
def run(need: Need, providers: list[ProviderOut]) -> tuple[list[OfferDraft], bool]   # (round-0 offers, fallback_used)
#   packs = ceil(quantity / pack_size) (None -> 1); price_minor = packs * base_price_minor + shipping_minor.
#   LLM writes the listing summary only; on LLMFailure use template text.
# negotiation_agent.py  (Price Comparison; node name kept)
def run_round(offers, providers, round_no, *, allow_revision=False) -> list[OfferDraft]
#   Re-derives each line total from the listing (prices never change), status ACCEPTED,
#   tags BEST_PRICE / FASTEST_DELIVERY / TOP_RATED per need. Bounded by MAX_NEGOTIATION_ROUNDS (=1).
# planning_agent.py
def run(final_offers: list[OfferDraft], needs: list[Need], providers: dict[int, ProviderOut],
        budget_minor: int, currency: str) -> tuple[PlanDraft | None, bool]   # (plan, rationale_fallback_used)
#   itertools.product one offer per need (cap MAX_PLAN_COMBINATIONS), drop total > budget,
#   sort (total asc, avg rating desc, max turnaround asc). LLM writes rationale only; template on failure.
```

### `app/search/*` (B) — listings; prices parsed in code, never by the LLM
```python
# normalize.py: RawListing, to_usd_minor (INR paise -> USD cents, integer ceil at INR_PAISE_PER_USD),
#   pack_size_from_title, is_verified (VERIFIED_STORES + VERIFIED_MIN_RATING + VERIFIED_MIN_REVIEWS), to_provider_fields
# catalog.py: CATALOG (offline listings, tuned for the 4 scenarios)
# parsers.py: pure parsers (JSON-LD, Amazon search, Flipkart search); return [] on unreadable markup
# live.py: fetch() (HTTPS + SEARCH_ALLOWED_HOSTS on every redirect, size/time caps), search_store() -> SearchError
# service.py: find_listings(db, needs) -> SearchOutcome  # mock: catalog rows; live: scrape+upsert, catalog fallback
```

### `app/payguard/*` (C)
```python
# policy.py — pure
def evaluate(plan: PlanDraft, goal_budget_minor: int, goal_currency: str,
             providers: dict[int, ProviderOut], other_plan_statuses: list[str]) -> list[RuleResult]
#   the 8 deterministic rules (all except AI_RISK_*), in RuleId order
# risk.py
def assess(plan: PlanDraft, goal_text: str, budget_minor: int) -> tuple[float | None, list[Flag], bool]  # (score, flags, ai_ok)
# engine.py
def combine(policy_results, risk_score, ai_flags, ai_ok) -> PayGuardResult   # pure; 10 rules in RuleId order
def run_payguard(plan, goal_budget_minor, goal_currency, goal_text, providers, other_plan_statuses) -> PayGuardResult
def run_for_plan(db: Session, plan_id: int) -> PayGuardResult   # loads from DB; does NOT commit
```
Flags: every rule with result REVIEW (or BLOCK) becomes `Flag(id=rule.id, source="POLICY" or "AI", requires_ack=(result==REVIEW))`.
AI informational flags: `Flag(id="AI:<id>", source="AI", requires_ack=False)`.

### `app/orchestration/*` (A)
```python
def run_workflow(goal_id: int) -> None   # graph.py; opens its own SessionLocal; never raises (marks goal FAILED + ERROR trace)
```
Persists: goal.parsed, goal.status, goal.question, trace (commit after each node so polling sees it live),
offer rows (one per round), plan row (status CHECKED, payguard_result), offer status SELECTED for chosen offers.
Discovery calls `search.service.find_listings` once per goal and writes a `web_search` trace event
(FALLBACK when the catalog was used in live mode). Scenario "blocked" => discovery `include_unverified=True`.
Scenario "retry" => strict initial filters. PRICE_FLOOR = listing price integrity (line == packs x price + shipping).
Router: once offers exist, at least one negotiation round is mandatory. With `retries["negotiation"] == 0`,
`allowed_actions()` returns only `[negotiate]`; the LLM may choose `plan` only after a round has run (enforced in code).

### `app/payments/*` + routers (D)
- `paypal.py`: `minor_to_str`, `get_access_token()` (cached), `create_order(amount_str, currency, return_url, cancel_url, request_id) -> dict`,
  `capture_order(order_id, request_id) -> dict`, `get_order(order_id) -> dict`. Mock mode returns deterministic fake orders
  (`id="MOCK-<request_id>"`, approval link `{FRONTEND_URL}/payments/return?token=<id>`), status COMPLETED on capture.
  Raise `PayPalError` on failures.
- `service.py`: `approve(db, plan_id, acknowledged)`, `pay(db, plan_id)`, `capture(db, order_id)`, `reconcile(db, plan_id)`.
- Plan status flow: DRAFT -> CHECKED -> USER_APPROVED -> PAYING -> PAID (or FAILED).
- `main.py`: `create_app(init_db: bool = True) -> FastAPI` (init_db=True calls `db.init_engine()` and `seed()` on startup);
  module-level `app = create_app()` for uvicorn. All routes under `/api/v1`. Handlers for ApiError,
  RequestValidationError (-> VALIDATION_ERROR 422), HTTPException (404 -> NOT_FOUND) and Exception (-> INTERNAL_ERROR 500),
  all producing the envelope. CORS for FRONTEND_URL. POST /goals uses FastAPI BackgroundTasks to call `run_workflow(goal_id)`.

### `backend/seed.py` (B)
`def seed(db: Session) -> None` — idempotent (upsert by `listing_key` / user email), commits. `if __name__ == "__main__":`
calls `init_engine()` then `seed()`. Loads `app/search/catalog.py` (INR listings converted to USD cents; PayPal Sandbox
rejects INR). Clean scenario (budget 2,000 cents): 10 hats + 50 balloons -> 346 + 237 = 583 cents.

## Commands (run from `backend/`)
```
.venv\Scripts\python -m ruff check .
.venv\Scripts\python -m mypy app
.venv\Scripts\python -m pytest -q
.venv\Scripts\python scripts\run_scenarios.py
```

## Definition of done
ruff clean, mypy clean, pytest green, all 4 scenarios pass via HTTP (clean = APPROVED + PAID in mock mode,
retry shows a RETRY trace event, blocked rejects /pay, review requires acknowledged flags), reviewer reports
zero Critical/High, the 10 section-15 tests exist (Sandbox one is `@pytest.mark.live`).
