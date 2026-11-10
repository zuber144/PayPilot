"""Unit tests for app/payments/paypal.py and app/payments/service.py."""

from __future__ import annotations

from typing import Any

import httpx
import pytest
from sqlalchemy.orm import Session

from app.config import settings
from app.enums import ErrorCode, PlanStatus, RuleOutcome, TxnStatus, Verdict
from app.errors import ApiError
from app.models import Goal, Plan, Transaction
from app.payments import paypal, service
from app.payments.paypal import PayPalError
from app.schemas import Flag, PayGuardResult, RuleResult


def _make_pg(
    verdict: Verdict = Verdict.APPROVED,
    flags: list[Flag] | None = None,
) -> PayGuardResult:
    return PayGuardResult(
        verdict=verdict,
        risk_score=0.1,
        ai_ok=True,
        flags=flags or [],
        rules=[RuleResult(id="BUDGET_CAP", result=RuleOutcome.PASS, detail="ok")],
    )


def _seed_goal_and_plan(
    db: Session,
    *,
    status: PlanStatus = PlanStatus.CHECKED,
    total_minor: int = 4_100_000,
    budget_minor: int = 5_000_000,
    currency: str = "INR",
    pg: PayGuardResult | None = None,
    acknowledged_flags: list[str] | None = None,
) -> tuple[Goal, Plan]:
    goal = Goal(
        raw_text="Corporate event catering for 100 people and photography in Bangalore",
        budget_minor=budget_minor,
        currency=currency,
        status="PLAN_READY",
        trace=[],
    )
    db.add(goal)
    db.flush()

    pg_res = pg or _make_pg()
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
                "currency": currency,
            },
            {
                "need_key": "photography",
                "provider_id": 4,
                "provider_name": "Studio X",
                "price_minor": 1_600_000,
                "timeline_days": 4,
                "verified": True,
                "currency": currency,
            },
        ],
        total_minor=total_minor,
        currency=currency,
        rationale="Best combination within budget",
        payguard_result=pg_res.model_dump(mode="json"),
        acknowledged_flags=acknowledged_flags or [],
        status=status.value,
    )
    db.add(plan)
    db.commit()
    db.refresh(goal)
    db.refresh(plan)
    return goal, plan


# --------------------------------------------------------------------------- paypal.py tests


def test_minor_to_str_and_str_to_minor() -> None:
    assert paypal.minor_to_str(4_100_000) == "41000.00"
    assert paypal.minor_to_str(0) == "0.00"
    assert paypal.minor_to_str(5) == "0.05"
    assert paypal.minor_to_str(123) == "1.23"

    with pytest.raises(ValueError):
        paypal.minor_to_str(-1)
    with pytest.raises(ValueError):
        paypal.minor_to_str(True)  # type: ignore[arg-type]

    assert paypal.str_to_minor("41000.00") == 4_100_000
    assert paypal.str_to_minor("41000") == 4_100_000
    assert paypal.str_to_minor("0.05") == 5
    assert paypal.str_to_minor("12.3") == 1230

    for bad in ("", "-10.00", "12.345", "abc", "12.ab"):
        with pytest.raises(PayPalError):
            paypal.str_to_minor(bad)


def test_paypal_mock_mode_deterministic() -> None:
    assert paypal.get_access_token() == "MOCK-ACCESS-TOKEN"
    order = paypal.create_order(
        amount_str="41000.00",
        currency="INR",
        return_url="http://localhost:5173/payments/return",
        cancel_url="http://localhost:5173/plans/1",
        request_id="plan-1",
    )
    assert order["id"] == "MOCK-plan-1"
    assert order["links"][0]["href"].endswith("/payments/return?token=MOCK-plan-1")

    cap = paypal.capture_order("MOCK-plan-1", request_id="cap-1")
    assert cap["status"] == "COMPLETED"
    unit_cap = cap["purchase_units"][0]["payments"]["captures"][0]
    assert unit_cap["id"] == "MOCK-CAP-MOCK-plan-1"
    assert unit_cap["amount"]["value"] == "41000.00"
    assert unit_cap["amount"]["currency_code"] == "INR"

    got = paypal.get_order("MOCK-plan-1")
    assert got["id"] == "MOCK-plan-1"
    assert got["status"] == "APPROVED"


def test_paypal_sandbox_token_cache_and_headers(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "PAYPAL_MODE", "sandbox")
    monkeypatch.setattr(settings, "PAYPAL_CLIENT_ID", "cid")
    monkeypatch.setattr(settings, "PAYPAL_CLIENT_SECRET", "csec")
    paypal.clear_token_cache()

    calls: list[tuple[str, str, dict[str, Any]]] = []

    class DummyResponse:
        def __init__(self, status_code: int, payload: dict[str, Any]) -> None:
            self.status_code = status_code
            self._payload = payload
            self.text = str(payload)

        def json(self) -> dict[str, Any]:
            return self._payload

    class DummyClient:
        def __init__(self, **kwargs: Any) -> None:
            self.timeout = kwargs.get("timeout")

        def __enter__(self) -> DummyClient:
            return self

        def __exit__(self, *args: Any) -> None:
            pass

        def post(self, url: str, **kwargs: Any) -> DummyResponse:
            headers = kwargs.get("headers") or {}
            calls.append(("POST", url, headers))
            if url.endswith("/v1/oauth2/token"):
                return DummyResponse(200, {"access_token": "LIVE-TOK-1", "expires_in": 3600})
            if url.endswith("/v2/checkout/orders"):
                return DummyResponse(
                    201,
                    {
                        "id": "ORDER-123",
                        "status": "CREATED",
                        "links": [{"rel": "approve", "href": "https://sandbox.paypal.com/approve?token=ORDER-123"}],
                    },
                )
            if url.endswith("/capture"):
                return DummyResponse(
                    201,
                    {
                        "id": "ORDER-123",
                        "status": "COMPLETED",
                        "purchase_units": [
                            {
                                "payments": {
                                    "captures": [
                                        {
                                            "id": "CAP-123",
                                            "status": "COMPLETED",
                                            "amount": {"currency_code": "INR", "value": "41000.00"},
                                        }
                                    ]
                                }
                            }
                        ],
                    },
                )
            return DummyResponse(404, {})

        def get(self, url: str, **kwargs: Any) -> DummyResponse:
            headers = kwargs.get("headers") or {}
            calls.append(("GET", url, headers))
            return DummyResponse(200, {"id": "ORDER-123", "status": "APPROVED"})

    monkeypatch.setattr(httpx, "Client", DummyClient)

    t1 = paypal.get_access_token()
    t2 = paypal.get_access_token()
    assert t1 == "LIVE-TOK-1"
    assert t2 == "LIVE-TOK-1"
    assert len([c for c in calls if c[1].endswith("/token")]) == 1

    created = paypal.create_order("41000.00", "INR", "http://ret", "http://can", "req-99")
    assert created["id"] == "ORDER-123"
    create_headers = [c[2] for c in calls if c[1].endswith("/v2/checkout/orders")][0]
    assert create_headers["PayPal-Request-Id"] == "req-99"

    captured = paypal.capture_order("ORDER-123", "cap-req-99")
    assert captured["status"] == "COMPLETED"
    cap_headers = [c[2] for c in calls if c[1].endswith("/capture")][0]
    assert cap_headers["PayPal-Request-Id"] == "cap-req-99"

    fetched = paypal.get_order("ORDER-123")
    assert fetched["status"] == "APPROVED"
    paypal.clear_token_cache()


# --------------------------------------------------------------------------- service.py tests


def test_approve_validation_and_idempotency(db: Session) -> None:
    # 1. BLOCKED plan rejected
    _, blocked_plan = _seed_goal_and_plan(db, pg=_make_pg(Verdict.BLOCKED))
    with pytest.raises(ApiError) as exc_info:
        service.approve(db, blocked_plan.id, [])
    assert exc_info.value.code == ErrorCode.PLAN_NOT_APPROVED

    # 2. REVIEW plan missing required flag acknowledgement -> VALIDATION_ERROR listing flag
    review_flag = Flag(
        id="SINGLE_VENDOR_SHARE",
        source="POLICY",
        message="Single vendor > 70%",
        requires_ack=True,
    )
    info_flag = Flag(
        id="AI:note",
        source="AI",
        message="Informational note",
        requires_ack=False,
    )
    _, review_plan = _seed_goal_and_plan(
        db,
        pg=_make_pg(Verdict.REVIEW, [review_flag, info_flag]),
    )
    with pytest.raises(ApiError) as exc_info:
        service.approve(db, review_plan.id, [])
    assert exc_info.value.code == ErrorCode.VALIDATION_ERROR
    assert "SINGLE_VENDOR_SHARE" in exc_info.value.message

    # 3. Acknowledge required flag -> USER_APPROVED
    out1 = service.approve(db, review_plan.id, ["SINGLE_VENDOR_SHARE"])
    assert out1.status == PlanStatus.USER_APPROVED
    assert out1.acknowledged_flags == ["SINGLE_VENDOR_SHARE"]
    assert out1.approved_at is not None

    # 4. Idempotent re-approve when already USER_APPROVED
    out2 = service.approve(db, review_plan.id, ["SINGLE_VENDOR_SHARE"])
    assert out2.status == PlanStatus.USER_APPROVED


def test_pay_lifecycle_and_idempotency(db: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    _, plan = _seed_goal_and_plan(db, status=PlanStatus.USER_APPROVED)
    monkeypatch.setattr(service, "_run_for_plan", lambda _db, _pid: _make_pg(Verdict.APPROVED))

    res1 = service.pay(db, plan.id)
    assert res1.plan_id == plan.id
    assert res1.paypal_order_id == f"MOCK-plan-{plan.id}"
    assert res1.status == PlanStatus.PAYING
    assert res1.reused is False

    # Calling pay again while PAYING returns existing transaction with reused=True
    res2 = service.pay(db, plan.id)
    assert res2.paypal_order_id == res1.paypal_order_id
    assert res2.reused is True


def test_pay_kill_switch_and_guards(db: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    _, plan = _seed_goal_and_plan(db, status=PlanStatus.CHECKED)

    # Requires USER_APPROVED
    with pytest.raises(ApiError) as exc_info:
        service.pay(db, plan.id)
    assert exc_info.value.code == ErrorCode.PLAN_NOT_APPROVED

    # Kill switch
    monkeypatch.setattr(settings, "PAYMENTS_ENABLED", False)
    with pytest.raises(ApiError) as exc_info:
        service.pay(db, plan.id)
    assert exc_info.value.code == ErrorCode.PAYMENTS_DISABLED
    monkeypatch.setattr(settings, "PAYMENTS_ENABLED", True)

    # Re-run PayGuard returns BLOCKED -> reverts plan to CHECKED and raises PLAN_NOT_APPROVED
    plan.status = PlanStatus.USER_APPROVED.value
    db.commit()
    monkeypatch.setattr(service, "_run_for_plan", lambda _db, _pid: _make_pg(Verdict.BLOCKED))
    with pytest.raises(ApiError) as exc_info:
        service.pay(db, plan.id)
    assert exc_info.value.code == ErrorCode.PLAN_NOT_APPROVED
    db.refresh(plan)
    assert plan.status == PlanStatus.CHECKED.value


def test_capture_and_amount_verification(db: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    _, plan = _seed_goal_and_plan(db, status=PlanStatus.USER_APPROVED, total_minor=4_100_000)
    monkeypatch.setattr(service, "_run_for_plan", lambda _db, _pid: _make_pg(Verdict.APPROVED))
    pay_res = service.pay(db, plan.id)

    # Capture succeeds
    txn_out = service.capture(db, pay_res.paypal_order_id)
    assert txn_out.status == TxnStatus.COMPLETED
    assert txn_out.amount_minor == 4_100_000
    assert txn_out.capture_id == f"MOCK-CAP-{pay_res.paypal_order_id}"
    db.refresh(plan)
    assert plan.status == PlanStatus.PAID.value

    # Second capture is idempotent (no second PayPal call)
    def _boom(*_a: Any, **_k: Any) -> dict[str, Any]:
        raise AssertionError("capture_order should not be called again")

    monkeypatch.setattr(paypal, "capture_order", _boom)
    txn_out2 = service.capture(db, pay_res.paypal_order_id)
    assert txn_out2.id == txn_out.id
    assert txn_out2.status == TxnStatus.COMPLETED

    # Paid plan rejects another /pay with DUPLICATE_PAYMENT
    with pytest.raises(ApiError) as exc_info:
        service.pay(db, plan.id)
    assert exc_info.value.code == ErrorCode.DUPLICATE_PAYMENT


def test_capture_amount_mismatch_fails_plan(db: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    _, plan = _seed_goal_and_plan(db, status=PlanStatus.USER_APPROVED, total_minor=4_100_000)
    monkeypatch.setattr(service, "_run_for_plan", lambda _db, _pid: _make_pg(Verdict.APPROVED))
    pay_res = service.pay(db, plan.id)

    monkeypatch.setattr(
        paypal,
        "capture_order",
        lambda oid, request_id=None: {
            "id": oid,
            "status": "COMPLETED",
            "purchase_units": [
                {
                    "payments": {
                        "captures": [
                            {
                                "id": "BAD-CAP",
                                "status": "COMPLETED",
                                "amount": {"currency_code": "INR", "value": "99999.00"},
                            }
                        ]
                    }
                }
            ],
        },
    )

    with pytest.raises(ApiError) as exc_info:
        service.capture(db, pay_res.paypal_order_id)
    assert exc_info.value.code == ErrorCode.PAYPAL_ERROR
    db.refresh(plan)
    assert plan.status == PlanStatus.FAILED.value


def test_reconcile_approved_and_completed(db: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    _, plan = _seed_goal_and_plan(db, status=PlanStatus.USER_APPROVED, total_minor=4_100_000)
    monkeypatch.setattr(service, "_run_for_plan", lambda _db, _pid: _make_pg(Verdict.APPROVED))
    service.pay(db, plan.id)

    # In mock mode get_order returns APPROVED -> reconcile triggers capture -> COMPLETED
    rec = service.reconcile(db, plan.id)
    assert rec is not None
    assert rec.status == TxnStatus.COMPLETED
    db.refresh(plan)
    assert plan.status == PlanStatus.PAID.value

    # Also test reconcile when get_order returns COMPLETED directly
    _, plan2 = _seed_goal_and_plan(db, status=PlanStatus.PAYING, total_minor=2_500_000)
    txn2 = Transaction(
        plan_id=plan2.id,
        paypal_order_id="ORD-DIRECT-COMP",
        request_id=f"plan-{plan2.id}",
        approval_url="http://ret",
        amount_minor=2_500_000,
        currency="INR",
        status=TxnStatus.CREATED.value,
    )
    db.add(txn2)
    db.commit()

    monkeypatch.setattr(
        paypal,
        "get_order",
        lambda oid: {
            "id": oid,
            "status": "COMPLETED",
            "purchase_units": [
                {
                    "payments": {
                        "captures": [
                            {
                                "id": "CAP-DIRECT",
                                "status": "COMPLETED",
                                "amount": {"currency_code": "INR", "value": "25000.00"},
                            }
                        ]
                    }
                }
            ],
        },
    )
    rec2 = service.reconcile(db, plan2.id)
    assert rec2 is not None
    assert rec2.status == TxnStatus.COMPLETED
    assert rec2.capture_id == "CAP-DIRECT"
    db.refresh(plan2)
    assert plan2.status == PlanStatus.PAID.value
