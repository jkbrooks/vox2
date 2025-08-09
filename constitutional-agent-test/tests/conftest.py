import os
import pytest


@pytest.fixture(autouse=True)
def _ensure_openai_key(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", os.getenv("OPENAI_API_KEY", "test-key"))
    yield
