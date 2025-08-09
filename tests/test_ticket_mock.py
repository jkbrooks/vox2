import json
from executive_worker.ticket import Ticket


def test_ticket_from_github_with_mock(monkeypatch):
    def fake_check_output(cmd, text=True):
        payload = {"number": 123, "title": "Fake Issue", "body": "Details"}
        return json.dumps(payload)

    monkeypatch.setattr("subprocess.check_output", fake_check_output)
    t = Ticket.from_github("owner/repo", 123)
    assert t.id == "123"
    assert t.title == "Fake Issue"
    assert t.body == "Details"

