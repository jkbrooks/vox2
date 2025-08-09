import os
import pytest

from executive_worker.llm_client import OpenAIChatLLM
from executive_worker.ticket import Ticket


def test_openai_client_raises_without_api_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    client = OpenAIChatLLM()
    with pytest.raises(ValueError):
        client.generate_plan(ticket=Ticket(id="1", title="X", body="Y"))

