from __future__ import annotations

import os
from dataclasses import dataclass
import shutil
from pathlib import Path
from typing import Optional

from .git_client import GitClient
from .shell_runner import ShellRunner
from .task_tree import TaskNode, TaskTree
from .ticket import Ticket
from .llm_client import LLMInterface
from .runs_indexer import regenerate_runs_index


@dataclass
class RunResult:
    run_json_path: str
    commit_sha: Optional[str]


class ExecutiveAgent:
    """Minimal execution-centric agent.

    For MVP, this agent does not call an LLM. It exercises the control flow,
    runs validation commands, and writes the artifacts defined by the spec.
    """

    def __init__(self, workspace_root: str, llm: Optional[LLMInterface] = None):
        self.workspace_root = str(Path(workspace_root).resolve())
        self.shell = ShellRunner(cwd=self.workspace_root)
        self.git = GitClient(self.workspace_root)
        self.llm = llm

    def execute_ticket(self, ticket: Ticket, eoi: Optional[str] = None) -> RunResult:
        tree = TaskTree.load_or_create(self.workspace_root, f"ticket-{ticket.id}", ticket.title)

        # Optional: generate a small plan using LLM (no code execution yet)
        llm_plan: Optional[str] = None
        if self.llm is not None:
            try:
                llm_plan = self.llm.generate_plan(ticket=ticket, repo_context=None)
            except Exception as exc:
                llm_plan = f"[LLM plan generation failed: {exc}]"

        commands = []
        cargo_toml = Path(self.workspace_root) / "Cargo.toml"
        if cargo_toml.exists():
            result = self.shell.run("cargo check")
            commands.append(result)
        docs_pkg = Path(self.workspace_root) / "docs" / "package.json"
        if docs_pkg.exists() and os.environ.get("EXEC_SKIP_DOCS_BUILD") != "1":
            use_pnpm = os.system("command -v pnpm >/dev/null 2>&1") == 0
            install_cmd = (
                "pnpm install --ignore-scripts --frozen-lockfile=false"
                if use_pnpm
                else "npm ci --ignore-scripts || npm install"
            )
            build_cmd = "pnpm -C docs build" if use_pnpm else "(cd docs && npm run build)"
            commands.append(self.shell.run(install_cmd))
            commands.append(self.shell.run(build_cmd))

        node = TaskNode(
            id="n-validate",
            title="Project compiles",
            deps=[],
            status="done" if all(c.success for c in commands) else "partial",
            coverage_pct=100 if all(c.success for c in commands) else 50,
            acceptance=["compiles", "docs build"],
            note=(
                "Build checks passed" if all(c.success for c in commands) else "One or more checks failed"
            ),
        )
        tree.add_or_update_node(node)
        tree.save(self.workspace_root)

        self.git.add_all()
        commit = self.git.commit(f"chore(ticket-{ticket.id}): update task_tree with validation results")
        commit_sha: Optional[str] = None
        if commit.returncode == 0:
            head = self.git._git("rev-parse", "HEAD")
            if head.returncode == 0:
                commit_sha = head.stdout.strip()

        payload = {
            "task_id": f"ticket-{ticket.id}",
            "title": ticket.title,
            "eoi": eoi,
            "llm_plan": llm_plan,
            "commands": [
                {
                    "cmd": c.command,
                    "cwd": c.cwd,
                    "exit_code": c.exit_code,
                    "duration_ms": c.duration_ms,
                    "top_stderr": c.stderr.splitlines()[:5],
                }
                for c in commands
            ],
            "commit": commit_sha,
            "validation": {
                "compiled": all(c.success for c in commands) if commands else True,
            },
        }
        run_path = TaskTree.write_run_json(self.workspace_root, payload)

        # Also copy the run artifact to a user-friendly location for quick access
        try:
            friendly_dir = Path(self.workspace_root) / "executive_worker" / "runs"
            friendly_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(run_path, friendly_dir / run_path.name)
            # Regenerate the runs index (best-effort)
            regenerate_runs_index(self.workspace_root)
        except Exception:
            # Non-fatal: best-effort convenience copy and index update
            pass

        return RunResult(run_json_path=str(run_path), commit_sha=commit_sha)


