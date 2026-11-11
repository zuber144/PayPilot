"""Shared fixtures (owned by the lead).

Every test gets a fresh SQLite file DB, mock LLM, mock PayPal and seeded providers.
"""

import os
import sys
import threading

os.environ.setdefault("LLM_MODE", "mock")
os.environ.setdefault("PAYPAL_MODE", "mock")

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

