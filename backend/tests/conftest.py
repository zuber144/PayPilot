"""Shared fixtures (owned by the lead).

Every test gets a fresh SQLite file DB, mock LLM, mock PayPal and seeded providers.
"""

import os

os.environ.setdefault("LLM_MODE", "mock")
os.environ.setdefault("PAYPAL_MODE", "mock")

from collections.abc import Iterator  # noqa: E402

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from app import db as db_module  # noqa: E402
from app.config import settings  # noqa: E402


@pytest.fixture(autouse=True)
def _offline_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "LLM_MODE", "mock")
    monkeypatch.setattr(settings, "PAYPAL_MODE", "mock")
    monkeypatch.setattr(settings, "PAYMENTS_ENABLED", True)


@pytest.fixture()
def engine(tmp_path):  # type: ignore[no-untyped-def]
    eng = db_module.init_engine(f"sqlite:///{tmp_path / 'test.db'}")
    from seed import seed

    with db_module.SessionLocal() as s:
        seed(s)
    yield eng
    eng.dispose()


@pytest.fixture()
def db(engine) -> Iterator[Session]:  # type: ignore[no-untyped-def]
    with db_module.SessionLocal() as s:
        yield s


@pytest.fixture()
def client(engine) -> Iterator[TestClient]:  # type: ignore[no-untyped-def]
    from app.main import create_app

    with TestClient(create_app(init_db=False)) as c:
        yield c
