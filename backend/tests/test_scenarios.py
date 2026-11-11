"""End-to-end HTTP tests for the four demo scenarios (clean, retry, blocked, review)."""

from fastapi.testclient import TestClient

from app.enums import ErrorCode, GoalStatus, PlanStatus, RuleId, RuleOutcome, TraceStatus, TxnStatus, Verdict

SHOPPING_TEXT = "Birthday party supplies: 10 party hats and 50 balloons, needed within 5 days"
BUDGET = 2_000  # USD 20.00 in cents


def test_scenario_clean_e2e(client: TestClient) -> None:
    """Scenario 1 (clean): PLAN_READY, verdict APPROVED, approve -> pay -> capture -> PAID & COMPLETED."""
    r = client.post(
        "/api/v1/goals",
        json={
            "raw_text": SHOPPING_TEXT,
            "budget_minor": BUDGET,
            "currency": "USD",
            "scenario": "clean",
        },
    )
    assert r.status_code in (200, 201, 202)
    goal_id = r.json()["id"]

    goal = client.get(f"/api/v1/goals/{goal_id}").json()
    assert goal["status"] == GoalStatus.PLAN_READY
    assert goal["plan_id"] is not None
    plan_id = goal["plan_id"]

    plan = client.get(f"/api/v1/plans/{plan_id}").json()
    assert plan["status"] == PlanStatus.CHECKED
    assert plan["payguard"]["verdict"] == Verdict.APPROVED
    assert plan["total_minor"] <= BUDGET
    # Clean cart: cheapest verified listing per item, shipping included (catalog: 346 + 237 cents)
    assert plan["total_minor"] == 583
    assert sorted(i["provider_name"] for i in plan["items"]) == [
        "Balloon Bazaar (Amazon)",
        "PartyZone Official (Flipkart)",
    ]
    for item in plan["items"]:
        assert item["price_minor"] == item["packs"] * item["pack_price_minor"] + item["shipping_minor"]

    app_r = client.post(f"/api/v1/plans/{plan_id}/approve", json={"acknowledged_flags": []})
    assert app_r.status_code == 200
    assert app_r.json()["status"] == PlanStatus.USER_APPROVED

    pay_r = client.post(f"/api/v1/plans/{plan_id}/pay", json={})
    assert pay_r.status_code == 200
    pay_data = pay_r.json()
    assert pay_data["status"] == PlanStatus.PAYING
    assert pay_data["paypal_order_id"]

    cap_r = client.post("/api/v1/payments/capture", json={"paypal_order_id": pay_data["paypal_order_id"]})
    assert cap_r.status_code == 200
    txn = cap_r.json()
    assert txn["status"] == TxnStatus.COMPLETED
    assert txn["amount_minor"] == plan["total_minor"]

    final_plan = client.get(f"/api/v1/plans/{plan_id}").json()
    assert final_plan["status"] == PlanStatus.PAID


def test_scenario_retry_e2e(client: TestClient) -> None:
    """Scenario 2 (retry): trace has RETRY event, plan produced, and the party-hat listing that the
    strict min_rating filter excluded (PartyZone, rating 4.2) appears after relaxation."""
    r = client.post(
        "/api/v1/goals",
        json={
            "raw_text": SHOPPING_TEXT,
            "budget_minor": BUDGET,
            "currency": "USD",
            "scenario": "retry",
        },
    )
    assert r.status_code in (200, 201, 202)
    goal_id = r.json()["id"]

    goal = client.get(f"/api/v1/goals/{goal_id}").json()
    assert goal["status"] == GoalStatus.PLAN_READY
    assert goal["plan_id"] is not None
    assert any(ev["status"] == TraceStatus.RETRY for ev in goal["trace"])

    offers_out = client.get(f"/api/v1/goals/{goal_id}/offers").json()
    hat_groups = [g for g in offers_out["groups"] if g["need_key"] == "party_hats"]
    assert len(hat_groups) == 1
    provider_names = {o["provider_name"] for o in hat_groups[0]["offers"]}
    assert "PartyZone Official (Flipkart)" in provider_names


def test_scenario_blocked_e2e(client: TestClient) -> None:
    """Scenario 3 (blocked): verdict BLOCKED, VERIFIED_PROVIDER BLOCK,
    /approve and /pay rejected with PLAN_NOT_APPROVED.
    """
    r = client.post(
        "/api/v1/goals",
        json={
            "raw_text": SHOPPING_TEXT,
            "budget_minor": BUDGET,
            "currency": "USD",
            "scenario": "blocked",
        },
    )
    assert r.status_code in (200, 201, 202)
    goal_id = r.json()["id"]

    goal = client.get(f"/api/v1/goals/{goal_id}").json()
    assert goal["status"] == GoalStatus.PLAN_READY
    plan_id = goal["plan_id"]
    assert plan_id is not None

    plan = client.get(f"/api/v1/plans/{plan_id}").json()
    assert plan["payguard"]["verdict"] == Verdict.BLOCKED
    rules_by_id = {rule["id"]: rule["result"] for rule in plan["payguard"]["rules"]}
    assert rules_by_id[RuleId.VERIFIED_PROVIDER] == RuleOutcome.BLOCK

    app_r = client.post(f"/api/v1/plans/{plan_id}/approve", json={"acknowledged_flags": []})
    assert app_r.status_code == 409
    assert app_r.json()["error"]["code"] == ErrorCode.PLAN_NOT_APPROVED

    pay_r = client.post(f"/api/v1/plans/{plan_id}/pay", json={})
    assert pay_r.status_code == 409
    assert pay_r.json()["error"]["code"] == ErrorCode.PLAN_NOT_APPROVED


def test_scenario_review_e2e(client: TestClient) -> None:
    """Scenario 4 (review): verdict REVIEW, SINGLE_VENDOR_SHARE REVIEW,
    approve without acks -> 422, with acks -> USER_APPROVED.
    """
    r = client.post(
        "/api/v1/goals",
        json={
            "raw_text": "Office party: 20 party hats",
            "budget_minor": BUDGET,
            "currency": "USD",
            "scenario": "review",
        },
    )
    assert r.status_code in (200, 201, 202)
    goal_id = r.json()["id"]

    goal = client.get(f"/api/v1/goals/{goal_id}").json()
    assert goal["status"] == GoalStatus.PLAN_READY
    plan_id = goal["plan_id"]
    assert plan_id is not None

    plan = client.get(f"/api/v1/plans/{plan_id}").json()
    assert plan["payguard"]["verdict"] == Verdict.REVIEW
    rules_by_id = {rule["id"]: rule["result"] for rule in plan["payguard"]["rules"]}
    assert rules_by_id[RuleId.SINGLE_VENDOR_SHARE] == RuleOutcome.REVIEW

    bad_app = client.post(f"/api/v1/plans/{plan_id}/approve", json={"acknowledged_flags": []})
    assert bad_app.status_code == 422
    assert bad_app.json()["error"]["code"] == ErrorCode.VALIDATION_ERROR

    good_app = client.post(
        f"/api/v1/plans/{plan_id}/approve",
        json={"acknowledged_flags": ["SINGLE_VENDOR_SHARE"]},
    )
    assert good_app.status_code == 200
    assert good_app.json()["status"] == PlanStatus.USER_APPROVED
