"""Drive the four demo scenarios through the HTTP API with LLM and PayPal mocked.

Usage (from backend/):  .venv\\Scripts\\python scripts\\run_scenarios.py
Exit code 0 only if all four scenarios pass.
"""

from __future__ import annotations

import os
import sys
import tempfile
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ["LLM_MODE"] = "mock"
os.environ["PAYPAL_MODE"] = "mock"

if sys.platform == "win32":
    import asyncio.proactor_events as _pe
    import asyncio.windows_events as _we
    import signal as _signal

    _signal.set_wakeup_fd = lambda fd, **kw: -1  # type: ignore[assignment]

    def _make_sp(self) -> None:  # type: ignore[no-untyped-def]
        self._ssock = None
        self._csock = type("_DummySock", (), {"fileno": lambda s: -1})()
        self._internal_fds += 1
        self._wake_ev = threading.Event()

    _pe.BaseProactorEventLoop._make_self_pipe = _make_sp  # type: ignore[attr-defined]
    _pe.BaseProactorEventLoop._close_self_pipe = (  # type: ignore[attr-defined]
        lambda self: setattr(self, "_internal_fds", self._internal_fds - 1)
    )
    _we.ProactorEventLoop._loop_self_reading = lambda self, f=None: None  # type: ignore[attr-defined]
    _pe.BaseProactorEventLoop._write_to_self = (  # type: ignore[attr-defined]
        lambda self: self._wake_ev.set() if hasattr(self, "_wake_ev") else None
    )
    _orig_poll = _we.IocpProactor._poll  # type: ignore[attr-defined]

    def _patched_poll(self, timeout=None):  # type: ignore[no-untyped-def]
        if self._loop is not None and hasattr(self._loop, "_wake_ev"):
            if timeout is None or timeout > 0:
                self._loop._wake_ev.wait(timeout)
            self._loop._wake_ev.clear()
            return _orig_poll(self, 0)
        return _orig_poll(self, timeout)

    _we.IocpProactor._poll = _patched_poll  # type: ignore[attr-defined]

from fastapi.testclient import TestClient  # noqa: E402

from app import db as db_module  # noqa: E402
from app.config import settings  # noqa: E402

settings.LLM_MODE = "mock"
settings.PAYPAL_MODE = "mock"
settings.PAYMENTS_ENABLED = True

API = "/api/v1"
EVENT_TEXT = "Birthday party supplies: 10 party hats and 50 balloons, needed within 5 days"
REVIEW_TEXT = "Office party: 20 party hats"
BUDGET = 2_000  # USD 20.00 in cents; catalog carts cost ~USD 3-7


class Fail(Exception):
    pass


def check(cond: bool, msg: str) -> None:
    if not cond:
        raise Fail(msg)


GOAL_POLL_SECONDS = 60.0


def start_goal(c: TestClient, text: str, budget: int, scenario: str) -> tuple[dict, dict | None]:
    r = c.post(f"{API}/goals", json={"raw_text": text, "budget_minor": budget, "currency": "USD", "scenario": scenario})
    check(r.status_code in (200, 201, 202), f"POST /goals -> {r.status_code} {r.text}")
    gid = r.json()["id"]
    # Over real HTTP the background workflow finishes after the response; poll (bounded).
    deadline = time.monotonic() + GOAL_POLL_SECONDS
    goal = c.get(f"{API}/goals/{gid}").json()
    while goal["status"] == "RUNNING" and time.monotonic() < deadline:
        time.sleep(0.25)
        goal = c.get(f"{API}/goals/{gid}").json()
    plan = c.get(f"{API}/plans/{goal['plan_id']}").json() if goal.get("plan_id") else None
    return goal, plan


def rule(plan: dict, rid: str) -> str:
    return next(r["result"] for r in plan["payguard"]["rules"] if r["id"] == rid)


def clean(c: TestClient) -> str:
    goal, plan = start_goal(c, EVENT_TEXT, BUDGET, "clean")
    check(goal["status"] == "PLAN_READY", f"goal status {goal['status']} q={goal.get('question')}")
    assert plan is not None
    check(plan["payguard"]["verdict"] == "APPROVED", f"verdict {plan['payguard']['verdict']}")
    check(plan["total_minor"] <= BUDGET, "over budget")
    names = sorted(i["provider_name"] for i in plan["items"])
    r = c.post(f"{API}/plans/{plan['id']}/approve", json={"acknowledged_flags": []})
    check(r.status_code == 200, f"approve {r.status_code} {r.text}")
    r = c.post(f"{API}/plans/{plan['id']}/pay", json={"amount_minor": 1})
    check(r.status_code == 200, f"pay {r.status_code} {r.text}")
    pay = r.json()
    check(bool(pay["approval_url"]), "no approval_url")
    r2 = c.post(f"{API}/plans/{plan['id']}/pay", json={})
    check(r2.status_code == 200 and r2.json()["paypal_order_id"] == pay["paypal_order_id"], "pay not idempotent")
    r = c.post(f"{API}/payments/capture", json={"paypal_order_id": pay["paypal_order_id"]})
    check(r.status_code == 200, f"capture {r.status_code} {r.text}")
    receipt = r.json()
    check(receipt["amount_minor"] == plan["total_minor"], "captured amount != plan total")
    check(receipt["status"] == "COMPLETED", f"txn status {receipt['status']}")
    final = c.get(f"{API}/plans/{plan['id']}").json()
    check(final["status"] == "PAID", f"plan status {final['status']}")
    txns = c.get(f"{API}/transactions").json()
    check(len(txns) == 1, f"expected 1 transaction, got {len(txns)}")
    return f"APPROVED and PAID, total {plan['total_minor']} cents, sellers {names}"


def retry(c: TestClient) -> str:
    goal, plan = start_goal(c, EVENT_TEXT, BUDGET, "retry")
    retries = [e for e in goal["trace"] if e["status"] == "RETRY"]
    check(bool(retries), "no RETRY trace event")
    check(goal["status"] == "PLAN_READY", f"goal status {goal['status']}")
    offers = c.get(f"{API}/goals/{goal['id']}/offers").json()
    names = {o["provider_name"] for g in offers["groups"] for o in g["offers"]}
    check("PartyZone Official (Flipkart)" in names, f"relaxed-filter listing not offered: {names}")
    return f"{len(retries)} RETRY event(s): {retries[0]['reason']}"


def blocked(c: TestClient) -> str:
    goal, plan = start_goal(c, EVENT_TEXT, BUDGET, "blocked")
    check(plan is not None, f"no plan, goal status {goal['status']}")
    assert plan is not None
    check(plan["payguard"]["verdict"] == "BLOCKED", f"verdict {plan['payguard']['verdict']}")
    check(rule(plan, "VERIFIED_PROVIDER") == "BLOCK", "VERIFIED_PROVIDER not BLOCK")
    r = c.post(f"{API}/plans/{plan['id']}/approve", json={"acknowledged_flags": ["VERIFIED_PROVIDER"]})
    check(
        r.status_code >= 400 and r.json()["error"]["code"] == "PLAN_NOT_APPROVED",
        f"approve {r.status_code} {r.text}",
    )
    r = c.post(f"{API}/plans/{plan['id']}/pay", json={"verdict": "APPROVED"})
    check(r.status_code >= 400 and r.json()["error"]["code"] == "PLAN_NOT_APPROVED", f"pay {r.status_code} {r.text}")
    return "BLOCKED by VERIFIED_PROVIDER; /approve and /pay rejected"


def review(c: TestClient) -> str:
    goal, plan = start_goal(c, REVIEW_TEXT, BUDGET, "review")
    check(plan is not None, f"no plan, goal status {goal['status']}")
    assert plan is not None
    check(plan["payguard"]["verdict"] == "REVIEW", f"verdict {plan['payguard']['verdict']}")
    check(rule(plan, "SINGLE_VENDOR_SHARE") == "REVIEW", "SINGLE_VENDOR_SHARE not REVIEW")
    r = c.post(f"{API}/plans/{plan['id']}/pay", json={})
    check(r.status_code >= 400, "pay allowed before approval")
    r = c.post(f"{API}/plans/{plan['id']}/approve", json={"acknowledged_flags": []})
    check(r.status_code == 422 and r.json()["error"]["code"] == "VALIDATION_ERROR", f"unacked approve {r.status_code}")
    needed = [f["id"] for f in plan["payguard"]["flags"] if f["requires_ack"]]
    r = c.post(f"{API}/plans/{plan['id']}/approve", json={"acknowledged_flags": needed})
    check(r.status_code == 200 and r.json()["status"] == "USER_APPROVED", f"acked approve {r.status_code} {r.text}")
    r = c.post(f"{API}/plans/{plan['id']}/pay", json={})
    check(r.status_code == 200, f"pay after ack {r.status_code} {r.text}")
    return f"REVIEW; approval needed acks {needed}; pay allowed after ack"


SCENARIOS = [("clean", clean), ("retry", retry), ("blocked", blocked), ("review", review)]


def main_live(base_url: str) -> list[tuple[str, bool, str]]:
    import httpx

    results: list[tuple[str, bool, str]] = []
    with httpx.Client(base_url=base_url, timeout=30.0) as c:
        providers = c.get(f"{API}/providers")
        check(providers.status_code == 200, f"server not ready at {base_url}: {providers.status_code}")
        check(len(providers.json()) >= 6, "database not seeded (expected >= 6 providers)")
        for name, fn in SCENARIOS:
            try:
                results.append((name, True, fn(c)))  # type: ignore[arg-type]
            except Exception as e:  # noqa: BLE001
                results.append((name, False, f"{type(e).__name__}: {e}"))
    return results


def main() -> int:
    if "--base-url" in sys.argv:
        results = main_live(sys.argv[sys.argv.index("--base-url") + 1])
    else:
        results = main_inprocess()
    for name, ok, msg in results:
        print(f"[{'PASS' if ok else 'FAIL'}] {name}: {msg}")
    passed = sum(ok for _, ok, _ in results)
    print(f"{passed}/{len(results)} scenarios passed")
    return 0 if passed == len(results) else 1


def main_inprocess() -> list[tuple[str, bool, str]]:
    from app.main import create_app
    from seed import seed

    results: list[tuple[str, bool, str]] = []
    for name, fn in SCENARIOS:
        with tempfile.TemporaryDirectory() as tmp:
            eng = db_module.init_engine(f"sqlite:///{Path(tmp) / 's.db'}")
            with db_module.SessionLocal() as s:
                seed(s)
            try:
                with TestClient(create_app(init_db=False)) as c:
                    results.append((name, True, fn(c)))
            except Exception as e:  # noqa: BLE001
                results.append((name, False, f"{type(e).__name__}: {e}"))
            finally:
                eng.dispose()
    return results


if __name__ == "__main__":
    raise SystemExit(main())

