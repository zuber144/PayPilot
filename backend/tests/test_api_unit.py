"""Unit tests for all 10 routes under /api/v1 and error envelope handlers in app/main.py."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app import db as db_module
from app.enums import OfferStatus, PlanStatus, RuleOutcome, Verdict
from app.main import create_app
from app.models import Goal, Offer, Plan, Provider
from app.payments import service as payment_service
from app.routers import goals as goals_router
from app.schemas import Flag, PayGuardResult, RuleResult

API = "/api/v1"


@pytest.fixture()
def api_db(tmp_path):  # type: ignore[no-untyped-def]
    eng = db_module.init_engine(f"sqlite:///{tmp_path / 'api_unit.db'}")
    with db_module.SessionLocal() as s:
        p1 = Provider(
            name="ABC Catering",
            category="catering",
            base_price_minor=2_800_000,
            min_price_minor=2_400_000,
            concession_rate=0.0375,
            rating=4.6,
            turnaround_days=7,
            verified=True,
            currency="INR",
            persona="Reliable caterer",
        )
        p2 = Provider(
            name="Studio X",
            category="photography",
            base_price_minor=1_800_000,
            min_price_minor=1_500_000,
            concession_rate=0.0385,
            rating=4.7,
            turnaround_days=4,
            verified=True,
            currency="INR",
            persona="Event photographer",
        )
        s.add_all([p1, p2])
        s.commit()
    yield eng
    eng.dispose()


@pytest.fixture()
def api_session(api_db) -> Session:  # type: ignore[no-untyped-def, misc]
    with db_module.SessionLocal() as s:
        yield s


@pytest.fixture()
def api_client(api_db) -> TestClient:  # type: ignore[no-untyped-def, misc]
    with TestClient(create_app(init_db=False)) as c:
        yield c


def _sample_pg(verdict: Verdict = Verdict.APPROVED, flags: list[Flag] | None = None) -> PayGuardResult:
    return PayGuardResult(
        verdict=verdict,
        risk_score=0.12,
        ai_ok=True,
        flags=flags or [],
        rules=[RuleResult(id="BUDGET_CAP", result=RuleOutcome.PASS, detail="Within budget")],
    )


def test_goals_create_get_and_offers(
    api_client: TestClient,
    api_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    started_goals: list[int] = []
    monkeypatch.setattr(goals_router, "_start_workflow", lambda gid: started_goals.append(gid))

    # 1. POST /goals
    r = api_client.post(
        f"{API}/goals",
        json={
            "raw_text": "Need catering for 100 people and photography",
            "budget_minor": 5_000_000,
            "currency": "INR",
            "scenario": "clean",
        },
    )
    assert r.status_code in (201, 202)
    created = r.json()
    gid = created["id"]
    assert created["status"] == "RUNNING"
    assert started_goals == [gid]

    # Add offer rounds and a plan for this goal
    api_session.add_all(
        [
            Offer(
                goal_id=gid,
                provider_id=1,
                need_key="catering",
                round=0,
                price_minor=2_800_000,
                counter_minor=None,
                scope="Buffet for 100",
                timeline_days=7,
                status=OfferStatus.OPEN.value,
            ),
            Offer(
                goal_id=gid,
                provider_id=1,
                need_key="catering",
                round=1,
                price_minor=2_520_000,
                counter_minor=2_520_000,
                scope="Buffet for 100",
                timeline_days=7,
                status=OfferStatus.SELECTED.value,
            ),
        ]
    )
    plan = Plan(
        goal_id=gid,
        items=[
            {
                "need_key": "catering",
                "provider_id": 1,
                "provider_name": "ABC Catering",
                "price_minor": 2_520_000,
                "timeline_days": 7,
                "verified": True,
                "currency": "INR",
            }
        ],
        total_minor=2_520_000,
        currency="INR",
        rationale="Good fit",
        payguard_result=_sample_pg().model_dump(mode="json"),
        status=PlanStatus.CHECKED.value,
    )
    api_session.add(plan)
    api_session.commit()

    # 2. GET /goals/{id} includes latest plan_id
    r_goal = api_client.get(f"{API}/goals/{gid}")
    assert r_goal.status_code == 200
    g_data = r_goal.json()
    assert g_data["id"] == gid
    assert g_data["plan_id"] == plan.id

    # 3. GET /goals/{id}/offers
    r_offers = api_client.get(f"{API}/goals/{gid}/offers")
    assert r_offers.status_code == 200
    o_data = r_offers.json()
    assert o_data["goal_id"] == gid
    assert len(o_data["groups"]) == 1
    grp = o_data["groups"][0]
    assert grp["need_key"] == "catering"
    po = grp["offers"][0]
    assert po["provider_name"] == "ABC Catering"
    assert po["opening_price_minor"] == 2_800_000
    assert po["final_price_minor"] == 2_520_000
    assert po["status"] == "SELECTED"
    assert len(po["rounds"]) == 2


def test_plans_payguard_approve_pay_capture_transactions_and_providers(
    api_client: TestClient,
    api_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    goal = Goal(
        raw_text="A" * 100,  # > 80 chars to test goal_summary truncation
        budget_minor=5_000_000,
        currency="INR",
        status="PLAN_READY",
        trace=[],
    )
    api_session.add(goal)
    api_session.flush()

    plan = Plan(
        goal_id=goal.id,
        items=[
            {
                "need_key": "catering",
                "provider_id": 1,
                "provider_name": "ABC Catering",
                "price_minor": 2_500_000,
                "timeline_days": 7,
                "verified": True,
                "currency": "INR",
            }
        ],
        total_minor=2_500_000,
        currency="INR",
        rationale="Solid",
        payguard_result=_sample_pg(Verdict.APPROVED).model_dump(mode="json"),
        status=PlanStatus.CHECKED.value,
    )
    api_session.add(plan)
    api_session.commit()

    # 4. GET /plans/{id}
    r_plan = api_client.get(f"{API}/plans/{plan.id}")
    assert r_plan.status_code == 200
    assert r_plan.json()["total_minor"] == 2_500_000

    # 5. POST /plans/{id}/approve
    r_app = api_client.post(f"{API}/plans/{plan.id}/approve", json={"acknowledged_flags": []})
    assert r_app.status_code == 200
    assert r_app.json()["status"] == "USER_APPROVED"

    # 6. POST /plans/{id}/payguard when USER_APPROVED and new verdict adds unacked REVIEW flag -> reverts to CHECKED
    rev_flag = Flag(id="SINGLE_VENDOR_SHARE", source="POLICY", message=">70%", requires_ack=True)
    monkeypatch.setattr(
        payment_service,
        "_run_for_plan",
        lambda _db, _pid: _sample_pg(Verdict.REVIEW, [rev_flag]),
    )
    r_pg = api_client.post(f"{API}/plans/{plan.id}/payguard")
    assert r_pg.status_code == 200
    assert r_pg.json()["verdict"] == "REVIEW"
    r_plan_after = api_client.get(f"{API}/plans/{plan.id}")
    assert r_plan_after.json()["status"] == "CHECKED"

    # Re-approve with required flag
    r_app2 = api_client.post(
        f"{API}/plans/{plan.id}/approve",
        json={"acknowledged_flags": ["SINGLE_VENDOR_SHARE"]},
    )
    assert r_app2.status_code == 200
    assert r_app2.json()["status"] == "USER_APPROVED"

    # 7. POST /plans/{id}/pay ignores untrusted body amount
    r_pay = api_client.post(f"{API}/plans/{plan.id}/pay", json={"amount_minor": 1, "verdict": "APPROVED"})
    assert r_pay.status_code == 200
    pay_data = r_pay.json()
    assert pay_data["status"] == "PAYING"
    assert pay_data["reused"] is False

    # Re-running payguard on a PAYING plan is rejected with CONFLICT (409)
    r_pg_conflict = api_client.post(f"{API}/plans/{plan.id}/payguard")
    assert r_pg_conflict.status_code == 409
    assert r_pg_conflict.json()["error"]["code"] == "CONFLICT"

    # 8. POST /payments/capture
    r_cap = api_client.post(
        f"{API}/payments/capture",
        json={"paypal_order_id": pay_data["paypal_order_id"]},
    )
    assert r_cap.status_code == 200
    cap_data = r_cap.json()
    assert cap_data["amount_minor"] == 2_500_000
    assert cap_data["status"] == "COMPLETED"
    assert cap_data["goal_id"] == goal.id
    assert cap_data["goal_summary"] == "A" * 80

    # 9. GET /transactions
    r_txns = api_client.get(f"{API}/transactions")
    assert r_txns.status_code == 200
    txns = r_txns.json()
    assert len(txns) == 1
    assert txns[0]["paypal_order_id"] == pay_data["paypal_order_id"]
    assert len(txns[0]["goal_summary"]) == 80

    # 10. GET /providers
    r_provs = api_client.get(f"{API}/providers")
    assert r_provs.status_code == 200
    provs = r_provs.json()
    assert len(provs) == 2
    assert all(p["demo"] is True for p in provs)


def test_error_envelope_handlers(api_client: TestClient) -> None:
    # 404 NOT_FOUND on missing resource
    r_404 = api_client.get(f"{API}/goals/99999")
    assert r_404.status_code == 404
    assert r_404.json()["error"]["code"] == "NOT_FOUND"

    # 404 NOT_FOUND on unknown route
    r_route_404 = api_client.get("/api/v1/does-not-exist")
    assert r_route_404.status_code == 404
    assert r_route_404.json()["error"]["code"] == "NOT_FOUND"

    # 422 VALIDATION_ERROR on invalid body
    r_422 = api_client.post(f"{API}/goals", json={"raw_text": "hi", "budget_minor": -5})
    assert r_422.status_code == 422
    assert r_422.json()["error"]["code"] == "VALIDATION_ERROR"
