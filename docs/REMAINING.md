# Remaining Work

All backend exit criteria from the specification were achieved:
- `ruff check .` is clean (`All checks passed!`).
- `mypy app` is clean (`Success: no issues found in 33 source files`).
- `pytest -q` passes (`85 passed, 1 skipped` where the 1 skipped test is `@pytest.mark.live` awaiting live PayPal Sandbox credentials).
- `scripts/run_scenarios.py` passes all 4 scenarios (`4/4 scenarios passed`: `clean`, `retry`, `blocked`, `review`).
- The independent `reviewer` subagent reported **0 Critical, 0 High, 0 Medium** defects (and 3 minor Low observations).

## Items requiring live credentials (to run manually)
1. **Live PayPal Sandbox & OpenAI verification**:
   - Populate `OPENAI_API_KEY`, `PAYPAL_CLIENT_ID`, and `PAYPAL_CLIENT_SECRET` in `backend/.env` and set `LLM_MODE=live`, `PAYPAL_MODE=sandbox`.
   - Run `.venv\Scripts\python -m pytest -q -m live` (`backend/tests/test_e2e_sandbox.py`) to record a live Sandbox order creation + buyer approval/capture.
2. **Frontend (Person 2 scope)**:
   - Per the prompt ("Build ONLY the backend (section 3 of the work-division doc)"), `frontend/` was not built in this run.

