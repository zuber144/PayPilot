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


14. **Postgres verification without Docker (finish pass)** — Docker is not installed on the dev laptop. Step 2 was verified against PostgreSQL 16.14
portable binaries (EDB zip, extracted to `.pg/`, gitignored) on port 5432 with the same
agentos/agentos/agentos credentials as docker-compose.yml. docker-compose.yml is unchanged
and remains the recommended path. `scripts/run_scenarios.py --base-url URL` now drives a
running uvicorn over real HTTP (polls RUNNING goals, bounded at 60 s) in addition to the
default in-process mode.
15. **LLM provider: Anthropic Claude Haiku 5.5 (finish pass)** — at the user's request `app/llm.py` gained an
`LLM_PROVIDER` switch (default `anthropic`, model `claude-haiku-5-5`, effort `low`) using structured outputs
constrained to each task's Pydantic schema; the OpenAI path and every deterministic fallback are unchanged.
The key is read from `ANTHROPIC_API_KEY` (shell env or `.env`), never logged. Startup logs the active provider.
Live tests are now opt-in (`addopts = -m 'not live'`) so plain `pytest` never spends money.
16. **PayPal Sandbox currency and live capture (finish pass)** — Sandbox `create_order` in INR returned
`422 CURRENCY_NOT_SUPPORTED`, and India sandbox accounts could not pay. The demo is USD-only, using US business and
personal Sandbox accounts. Live end-to-end run (Postgres, Claude Haiku 5.5, PAYPAL_MODE=sandbox): clean goal ->
APPROVED -> /approve -> /pay -> buyer approved in browser -> /payments/capture. Order `9PG11902P8810833V`,
**capture ID `4H067940UN781852J`**, USD 46,000.00, COMPLETED; plan PAID; repeat capture idempotent.
17. **Mandatory first negotiation round (finish pass)** — the live Claude router skipped negotiation on the clean
goal and planned at list price (4,600,000). Fixed in code, not the prompt: `router.allowed_actions()` returns only
`[negotiate]` when offers exist and no round has run (`MAX_NEGOTIATION_ROUNDS=0` still yields `[plan]`). The LLM
chooses freely between negotiate and plan only after round 1. Live clean now 4,425,700 vs 4,600,000 list
(ABC 2,695,000, Studio X 1,730,700); mock unchanged at 4,096,666. Regression tests in `tests/test_orchestration.py`.
18. **Pivot: service procurement -> e-commerce product comparison (lead decision, 2026-11-11)** — agents 2-4 now
search, extract and compare store listings (Amazon/Flipkart) instead of negotiating with seeded vendors. Graph,
router, PayGuard, payments and the API routes are unchanged in shape.
   - **Listings reuse the `providers` table.** One row per store listing: new columns `listing_key` (unique;
     catalog key or URL), `store`, `product_title`, `url`, `pack_size`, `shipping_minor`, `review_count`,
     `original_currency`/`original_price_minor`/`original_shipping_minor`, `source` (`catalog`|`live`).
     `base_price_minor = min_price_minor` = one pack in USD cents, `concession_rate = 0`, `turnaround_days` =
     delivery days. `name` = "Seller (Store)" and is no longer unique. Existing databases must be recreated
     (delete `agentos.db` / drop the Postgres schema); `create_all` does not add columns.
   - **Search (`app/search/`).** `SEARCH_MODE=mock` (default, offline) reads the seeded catalog
     (`app/search/catalog.py`). `SEARCH_MODE=live` scrapes allowlisted store search pages (lead chose direct
     scraping over a search API). The fetcher is HTTPS-only, re-checks `SEARCH_ALLOWED_HOSTS` on every redirect
     hop (max `SEARCH_MAX_REDIRECTS`), caps the body at `SEARCH_MAX_BYTES`, times out after
     `SEARCH_TIMEOUT_SECONDS` and sends a generic User-Agent. Any store/need failure falls back to the catalog
     and the discovery node writes a `web_search` FALLBACK trace event. The search runs once per goal;
     discovery retries only re-filter. Known risk: Amazon/Flipkart pages are often JS-rendered or bot-walled
     and scraping may conflict with their terms of service, so expect live mode to fall back regularly.
   - **Prices are parsed in code, never by the LLM** (JSON-LD `offers.price`, Amazon `a-price-whole`, rupee
     regex), using Decimal -> integer paise. The LLM writes only the listing summary and the cart rationale.
     Scraped titles are truncated and labelled untrusted in the risk prompt.
   - **Currency: INR display, USD charge.** Goals, plans, budgets and PayPal stay USD
     (`SUPPORTED_CURRENCIES=["USD"]`). Every pack price and shipping fee is converted once, at ingest, with
     integer ceil division at the fixed `INR_PAISE_PER_USD=8400` (never undercharges; no live FX call). Line
     total = packs x pack cents + shipping cents, so TOTAL_INTEGRITY holds. INR line totals
     (`original_price_minor`) are display-only.
   - **Quantity.** packs = ceil(quantity / pack_size), where pack_size is parsed from the title ("Pack of 10",
     "50 pcs") and defaults to 1. A null quantity means one pack.
   - **Seller verification is derived:** store in `VERIFIED_STORES` AND rating >= `VERIFIED_MIN_RATING` (4.0)
     AND reviews >= `VERIFIED_MIN_REVIEWS` (50). The orchestrator never relaxes it.
   - **Negotiation node = price comparison.** `MAX_NEGOTIATION_ROUNDS=1`. The pass re-derives line totals from
     the listing (prices never change), marks offers ACCEPTED and tags BEST_PRICE / FASTEST_DELIVERY /
     TOP_RATED per item. The mandatory-first-round rule (#17) still applies. `COUNTER_RATIO` was removed.
   - **PRICE_FLOOR** keeps its RuleId but now checks listing price integrity: each line must equal
     packs x stored pack price + stored shipping, with packs >= 1. RuleId order and the 10-rule contract are
     unchanged. No DELIVERY_DEADLINE rule was added; `deadline_days` is parsed but not yet enforced.
   - **SINGLE_VENDOR_SHARE** still groups by listing (seller). A single-item cart is therefore REVIEW, which is
     the review scenario.
   - **Scenarios** (budget USD 20.00 = 2,000 cents): clean "10 party hats and 50 balloons" -> PartyZone
     (Flipkart) 346 + Balloon Bazaar (Amazon) 237 = 583 cents, APPROVED + PAID. retry -> strict min_rating 4.5
     leaves 0 verified hats, so retry 1 relaxes rating. blocked -> cheapest Meesho sellers are unverified,
     VERIFIED_PROVIDER BLOCK. review -> "20 party hats" goes to a single seller, SINGLE_VENDOR_SHARE REVIEW.
   - **Price drift (live mode):** listing rows are shared and keyed by URL, so a later goal re-scraping the same
     URL updates its price. `/pay` re-runs PayGuard from the DB, so an earlier plan whose line no longer matches
     the listing is BLOCKED by PRICE_FLOOR at payment time. It is never charged at a stale price.
   - **Section-15 test mapping:** `test_negotiation.py` "price never goes below min_price" became "compared price
     always equals the listing, and PRICE_FLOOR blocks a line below the listing". The orchestration regression
     test was renamed `test_router_llm_preferring_plan_still_runs_comparison_round`. All other section-15 files
     are unchanged in purpose. New: `tests/test_search.py` (FX, parsers, fetch allowlist and limits, fallback).
   - **Live-mode finding (2026-11-11):** a live goal for "10 party hats and 50 balloons" found 20 listings but
     0 verified hat listings. Amazon hat listings were below 4.0 stars or 50 reviews, and Flipkart search cards
     show no ratings, so its listings parse as 0 stars. The goal ended at NEEDS_INPUT after 2 retries, because
     verification is never relaxed. Possible follow-up: one bounded product-page JSON-LD fetch per Flipkart
     listing to get its rating.
