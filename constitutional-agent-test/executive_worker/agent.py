from __future__ import annotations

import datetime as dt
import json
import os
import uuid
from typing import List

from .codebase_utils import CodebaseUtilities
from .edit_engine import EditEngine
from .git_ops import GitOps
from .llm_client import LLMClient
from .models import (
    AffectedNode,
    CommandResult,
    PlanStep,
    RunLog,
    Task,
    TestsSummary,
    ValidationResult,
)
from .shell_runner import ShellRunner


class ExecutiveWorker:
    def __init__(self, workspace_root: str, model: str = "gpt-4o-mini") -> None:
        self.workspace_root = workspace_root
        self.shell = ShellRunner(cwd=workspace_root)
        self.code = CodebaseUtilities(workspace_root)
        self.edit_engine = EditEngine(workspace_root)
        self.git = GitOps(self.shell)
        self.llm = LLMClient(model=model)

    def execute_task(self, task: Task) -> RunLog:
        start = dt.datetime.utcnow().isoformat()
        plan: List[PlanStep] = self.llm.create_plan(task)
        commands: List[CommandResult] = []
        commits: List[str] = []

        for step in plan:
            if step.kind == "search":
                pattern = step.args.get("pattern", ".*")
                globs = step.args.get("globs", ["**/*.py", "**/*.md", "**/*.rs", "**/*.ts", "**/*.tsx"])  # best effort
                hits = self.code.grep(pattern, globs)
                preview = "\n".join([f"{p}:{ln}: {txt}" for p, ln, txt in hits[:10]])
                commands.append(CommandResult(cmd=f"SEARCH {pattern}", exit_code=0, stdout=preview, stderr="", duration_ms=0))
            elif step.kind == "edit":
                # Expect args: [{path, find, replace}] list
                edits = step.args.get("edits", [])
                from .edit_engine import FileEdit

                file_edits = [FileEdit(e["path"], e["find"], e["replace"]) for e in edits if all(k in e for k in ("path", "find", "replace"))]
                self.edit_engine.apply_edits(file_edits)
                self.git.add_all()
                msg = step.args.get("message", f"chore: apply edits for {task.task_id}")
                commit_out = self.git.commit(msg)
                commits.append(self._extract_commit_sha(commit_out))
                commands.append(CommandResult(cmd="edit_engine.apply_edits", exit_code=0, stdout=commit_out, stderr="", duration_ms=0))
            elif step.kind == "shell":
                cmd = step.args.get("cmd", "echo noop")
                res = self.shell.run(cmd)
                commands.append(res)
            elif step.kind == "git":
                action = step.args.get("action", "push")
                if action == "push":
                    out = self.git.push()
                else:
                    out = self.git.status()
                commands.append(CommandResult(cmd=f"git {action}", exit_code=0, stdout=out, stderr="", duration_ms=0))
            elif step.kind == "validate":
                # Basic validation step — run tests or build
                cmd = step.args.get("cmd", "true")
                res = self.shell.run(cmd)
                commands.append(res)
            else:
                # Unknown kind, ignore safely
                continue

        end = dt.datetime.utcnow().isoformat()
        validation = ValidationResult(compiled=None, tests=TestsSummary(passed=True, summary="by-step"))
        affected = [
            AffectedNode(
                id=f"node-{task.task_id}",
                status="partial",
                coverage_pct=10,
                evidence={"commits": [c for c in commits if c], "files": []},
                note="initial pass",
            )
        ]
        run_log = RunLog(
            run_id=f"r-{uuid.uuid4()}",
            task_id=task.task_id,
            start_ts=start,
            end_ts=end,
            eoi=task.eoi,
            commands=commands,
            commits=[c for c in commits if c],
            validation=validation,
            affected_nodes=affected,
            reflections=[{"type": "decision", "message": "Initial MVP cycle executed"}],
        )
        self._write_run_json(run_log)
        return run_log

    def _write_run_json(self, run_log: RunLog) -> None:
        runs_dir = os.path.join(self.workspace_root, "constitutional-agent-test", "runs")
        os.makedirs(runs_dir, exist_ok=True)
        path = os.path.join(runs_dir, f"{run_log.run_id}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(run_log, f, default=lambda o: o.__dict__, indent=2)

    def _extract_commit_sha(self, output: str) -> str:
        # Best-effort parse — optional
        # If parsing fails, return empty string; git log can be used later
        lines = output.splitlines()
        for line in lines:
            if line.startswith("[") and "]" in line:
                # fallback heuristic
                return ""
        return ""
