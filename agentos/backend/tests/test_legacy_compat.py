"""Legacy (agentos/backend) API compatibility: additive aliases and derived fields only.

The canonical contract is unchanged; these tests pin the extra shapes the original
agentos/frontend was written against (DECISIONS.md #19).
"""

from fastapi.testclient import TestClient

API = "/api/v1"
GOAL = {
    "raw_text": "Birthday party supplies: 10 party hats and 50 balloons",
    "budget_minor": 2_000,
    "currency": "USD",
    "user_id": 1,
}


def _plan(client: TestClient) -> tuple[dict, dict]:
    r = client.post(f"{API}/goals", json=GOAL)
    assert r.status_code == 202
    goal = client.get(f"{API}/goals/{r.json()['id']}").json()
    assert goal["status"] == "PLAN_READY"
    return goal, client.get(f"{API}/plans/{goal['plan_id']}").json()


def test_goal_accepts_user_id_and_trace_has_legacy_fields(client: TestClient) -> None:
    goal, _ = _plan(client)
    assert goal["user_id"] == 1
    ev = goal["trace"][0]
    assert ev["step"] == f"{ev['node']}:{ev['action']}"
    assert ev["used_fallback"] is (ev["status"] == "FALLBACK")


def test_unknown_user_id_is_ignored(client: TestClient) -> None:
    r = client.post(f"{API}/goals", json={**GOAL, "user_id": 999_999})
    assert r.status_code == 202
    assert client.get(f"{API}/goals/{r.json()['id']}").json()["user_id"] is None


def test_flat_offers_match_grouped_offers(client: TestClient) -> None:
    goal, _ = _plan(client)
    flat = client.get(f"{API}/goals/{goal['id']}/offers/flat").json()
    grouped = client.get(f"{API}/goals/{goal['id']}/offers").json()
    n_rounds = sum(len(o["rounds"]) for g in grouped["groups"] for o in g["offers"])
    assert len(flat) == n_rounds == 8  # 4 listings x (round 0 + comparison round 1)
    assert {"id", "goal_id", "provider_id", "need_key", "round", "price_minor", "scope",
            "timeline_days", "status"} <= set(flat[0])
    assert sum(1 for o in flat if o["status"] == "SELECTED") == 2
    assert client.get(f"{API}/goals/999999/offers/flat").status_code == 404


def test_plan_has_legacy_payguard_result_and_item_fields(client: TestClient) -> None:
    _, plan = _plan(client)
    legacy = plan["payguard_result"]
    assert legacy["verdict"] == plan["payguard"]["verdict"] == "APPROVED"
    assert [r["rule"] for r in legacy["rules"]] == [r["id"] for r in plan["payguard"]["rules"]]
    assert all(r["passed"] for r in legacy["rules"])
    sev = {r["rule"]: r["severity"] for r in legacy["rules"]}
    assert sev["BUDGET_CAP"] == "BLOCK" and sev["SINGLE_VENDOR_SHARE"] == "REVIEW"
    assert legacy["risk_score"] == round(plan["payguard"]["risk_score"] * 100)
    assert legacy["summary"].startswith("APPROVED")
    for item in plan["items"]:
        assert item["offer_id"] is not None
        assert item["scope"]


def test_legacy_blocked_view_marks_failed_rule(client: TestClient) -> None:
    r = client.post(f"{API}/goals", json={**GOAL, "scenario": "blocked"})
    goal = client.get(f"{API}/goals/{r.json()['id']}").json()
    legacy = client.get(f"{API}/plans/{goal['plan_id']}").json()["payguard_result"]
    assert legacy["verdict"] == "BLOCKED"
    vp = next(x for x in legacy["rules"] if x["rule"] == "VERIFIED_PROVIDER")
    assert vp["passed"] is False and vp["severity"] == "BLOCK"


def test_pay_returns_transaction_id_and_legacy_capture_body(client: TestClient) -> None:
    _, plan = _plan(client)
    assert client.post(f"{API}/plans/{plan['id']}/approve", json={"acknowledged_flags": []}).status_code == 200
    pay = client.post(f"{API}/plans/{plan['id']}/pay", json={}).json()
    assert isinstance(pay["transaction_id"], int)

    wrong = client.post(f"{API}/payments/capture", json={"token": pay["paypal_order_id"], "plan_id": plan["id"] + 1})
    assert wrong.status_code == 409
    assert wrong.json()["error"]["code"] == "CONFLICT"

    r = client.post(f"{API}/payments/capture", json={"token": pay["paypal_order_id"], "plan_id": plan["id"]})
    assert r.status_code == 200
    body = r.json()
    assert body["transaction_id"] == body["id"] == pay["transaction_id"]
    assert body["status"] == "COMPLETED" and body["amount_minor"] == plan["total_minor"]


def test_capture_requires_an_order_id(client: TestClient) -> None:
    r = client.post(f"{API}/payments/capture", json={"plan_id": 1})
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "VALIDATION_ERROR"
    r = client.post(f"{API}/payments/capture", json={"paypal_order_id": "A", "token": "B"})
    assert r.status_code == 422


def test_payments_transactions_alias(client: TestClient) -> None:
    assert client.get(f"{API}/payments/transactions").json() == client.get(f"{API}/transactions").json()
