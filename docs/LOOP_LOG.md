# Loop log

Start: 2026-11-10T13:54:40+05:30 — hard stop 16:54:40 (+3h), max 6 iterations.

| Iter | Time | Tests pass/fail | Defects fixed / remaining | Notes |
|---|---|---|---|---|
| 0 | 13:58 | – | – | Phase 0 contract written |
| 1 | 17:39 | 85 pass / 0 fail (1 skipped live) | 7 test alignment fixes / 0 Critical, 0 High, 0 Medium, 3 Low remaining | All 4 scenarios pass; ruff + mypy clean; reviewer audit clean |

| F1 | 2026-11-10 18:16 | 85 pass / 0 fail (1 skipped live) | 0 fixes needed | Fresh venv (Py 3.11.9): ruff + mypy clean; versions pinned in backend/requirements.lock |
| F2 | 2026-11-10 18:43 | 4/4 scenarios over HTTP | 0 fixes needed | uvicorn + PostgreSQL 16.14 from empty DB, seeded; LLM+PayPal mocked; added run_scenarios.py --base-url mode |
| F3 | 2026-11-10 18:53 | 85 offline pass; 7/7 live LLM pass | 0 fixes needed | Anthropic claude-haiku-5-5 wired via LLM_PROVIDER; 4/4 HTTP scenarios on Postgres with live LLM (one transient APIConnectionError run fell back safely, re-run clean) |
| F4 | 2026-11-10 19:21 | live Sandbox pytest 1/1; live capture COMPLETED | INR->USD switch | INR rejected by Sandbox; USD order 9PG11902P8810833V captured, capture ID 4H067940UN781852J (USD 46,000.00), plan PAID |
