from __future__ import annotations

import os
import sys
from uuid import uuid4
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    sqlite_path = Path(__file__).resolve().parents[1] / "tests" / f"test_metrics_{uuid4().hex}.db"
    os.environ["DATABASE_URL"] = f"sqlite:///{sqlite_path.as_posix()}"
    os.environ["DATABASE_CONNECT_RETRIES"] = "1"
    os.environ["DATABASE_CONNECT_RETRY_SECONDS"] = "0"
    os.environ["FIXED_TODAY"] = "2026-04-27"

    from app.core.config import get_settings

    get_settings.cache_clear()

    from app.main import app

    with TestClient(app) as test_client:
        yield test_client
