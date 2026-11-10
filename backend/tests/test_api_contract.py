"""Tests for the frozen API contract: OpenAPI route table and standard error envelopes."""

import re

from fastapi.testclient import TestClient

from app.enums import ErrorCode


def test_all_10_routes_exist_in_openapi(client: TestClient) -> None:
    """Verify all 10 contract endpoints exist in app.openapi()."""
    schema = client.app.openapi()  # type: ignore[union-attr, attr-defined]
    paths: dict[str, dict] = schema.get("paths", {})

    expected = [
        ("post", r"^/api/v1/goals$"),
        ("get", r"^/api/v1/goals/\{[^/]+\}$"),
        ("get", r"^/api/v1/goals/\{[^/]+\}/offers$"),
        ("get", r"^/api/v1/plans/\{[^/]+\}$"),
        ("post", r"^/api/v1/plans/\{[^/]+\}/payguard$"),
        ("post", r"^/api/v1/plans/\{[^/]+\}/approve$"),
        ("post", r"^/api/v1/plans/\{[^/]+\}/pay$"),
        ("post", r"^/api/v1/payments/capture$"),
        ("get", r"^/api/v1/transactions$"),
        ("get", r"^/api/v1/providers$"),
    ]

    for method, pattern in expected:
        matched = any(
            re.match(pattern, path) and method in methods
            for path, methods in paths.items()
        )
        assert matched, f"Missing route {method.upper()} matching {pattern} in {list(paths.keys())}"


def test_error_envelope_on_404_422_409(client: TestClient) -> None:
    """Verify non-2xx responses use {"error": {"code": ..., "message": ...}} for 404, 422, and 409."""
    # 404 NOT_FOUND
    r404 = client.get("/api/v1/goals/999999")
    assert r404.status_code == 404
    body404 = r404.json()
    assert "error" in body404
    assert body404["error"]["code"] == ErrorCode.NOT_FOUND
    assert isinstance(body404["error"]["message"], str)

    # 422 VALIDATION_ERROR (request validation failure: budget_minor <= 0)
    r422 = client.post(
        "/api/v1/goals",
        json={"raw_text": "short", "budget_minor": -10, "currency": "USD"},
    )
    assert r422.status_code == 422
    body422 = r422.json()
    assert "error" in body422
    assert body422["error"]["code"] == ErrorCode.VALIDATION_ERROR
    assert isinstance(body422["error"]["message"], str)

    # 409 PLAN_NOT_APPROVED (paying a CHECKED plan before approval)
    create_r = client.post(
        "/api/v1/goals",
        json={
            "raw_text": "Corporate event in Bangalore: catering for 100 people and a photographer",
            "budget_minor": 5_000_000,
            "currency": "USD",
            "scenario": "clean",
        },
    )
    goal = client.get(f"/api/v1/goals/{create_r.json()['id']}").json()
    r409 = client.post(f"/api/v1/plans/{goal['plan_id']}/pay", json={})
    assert r409.status_code == 409
    body409 = r409.json()
    assert "error" in body409
    assert body409["error"]["code"] == ErrorCode.PLAN_NOT_APPROVED
    assert isinstance(body409["error"]["message"], str)
