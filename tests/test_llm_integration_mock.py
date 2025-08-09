from executive_worker.agent import ExecutiveAgent
from executive_worker.ticket import Ticket


class FakeLLM:
    def generate_plan(self, *, ticket, repo_context=None):
        return f"Plan for {ticket.id}: Step 1, Step 2"


def test_agent_includes_llm_plan_in_run_json(tmp_path):
    agent = ExecutiveAgent(str(tmp_path), llm=FakeLLM())
    ticket = Ticket(id="42", title="Test", body="Do something")
    result = agent.execute_ticket(ticket)
    content = (tmp_path / "executive_worker_runs").glob("run-*.json")
    paths = list(content)
    assert paths, "run json should be written"
    data = paths[0].read_text(encoding="utf-8")
    assert "Plan for 42" in data

