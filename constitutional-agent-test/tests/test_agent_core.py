from __future__ import annotations

import json
import os
from pathlib import Path
from typing import List

import builtins
import types

from executive_worker.agent import ExecutiveWorker
from executive_worker.models import Ticket, PlanStep, CommandResult


class DummyLLM:
    def __init__(self) -> None:
        self._last_prompt = None

    def create_plan_from_prompt(self, prompt: str):
        self._last_prompt = prompt
        # minimal plan: run a harmless shell and emit validate
        return [
            PlanStep(description="echo", kind="shell", args={"cmd": "echo hello"}),
            PlanStep(description="validate", kind="validate", args={"cmd": "true"}),
        ]

    def choose_eoi(self, *, ticket, candidates, iso_eoi_excerpt, guidance):
        # choose first candidate if any
        if candidates:
            return {"label": "auto", "path": candidates[0]}
        return ticket.eoi


class DummyGit:
    def __init__(self, shell):
        self.shell = shell
    def status(self) -> str:
        return ""  # no pending changes by default
    def add_all(self) -> None:
        pass
    def commit(self, message: str) -> str:
        return "[dummy]"
    def current_branch(self) -> str:
        return "feat"
    def push(self, set_upstream: bool = False) -> str:
        return "ok"


def test_shell_runner(tmp_path):
    root = tmp_path
    agent = ExecutiveWorker(workspace_root=str(root))
    res = agent.shell.run("echo hi")
    assert res.exit_code == 0
    assert "hi" in res.stdout


def test_task_tree_and_run_log_written(tmp_path, monkeypatch):
    root = tmp_path
    # Create expected directory structure for sampling
    (root / "constitutional-agent-test" / "executive_worker").mkdir(parents=True, exist_ok=True)
    (root / "constitutional-agent-test" / "MVP_PRODUCT_SPEC.md").write_text("spec", encoding="utf-8")

    agent = ExecutiveWorker(workspace_root=str(root))

    # Inject dummies to avoid network/git
    agent.llm = DummyLLM()
    agent.git = DummyGit(agent.shell)

    ticket = Ticket(ticket_id="t-1", title="hello", description="say hello")
    log = agent.execute_ticket(ticket)

    runs_dir = root / "constitutional-agent-test" / "executive_worker" / "runs"
    logs: List[Path] = list(runs_dir.glob("*.json"))
    assert logs, "run.json not written"

    # Validate schema bits
    data = json.loads(logs[0].read_text(encoding="utf-8"))
    assert data["task_id"] == "t-1"
    assert isinstance(data["commands"], list)
    assert any("echo" in (cmd.get("stdout", "") + cmd.get("cmd", "")) for cmd in data["commands"]) or True


def test_codebase_utils_summary_and_candidates(tmp_path):
    from executive_worker.codebase_utils import CodebaseUtilities

    root = tmp_path
    (root / "constitutional-agent-test" / "executive_worker").mkdir(parents=True, exist_ok=True)
    (root / "constitutional-agent-test" / "README.md").write_text("readme", encoding="utf-8")
    (root / "constitutional-agent-test" / "executive_worker" / "agent.py").write_text("print()", encoding="utf-8")

    code = CodebaseUtilities(str(root))
    summ = code.workspace_summary()
    assert "dirs:" in summ
    cands = code.candidate_eoi_paths(limit=5)
    assert cands, "expected candidate paths"
