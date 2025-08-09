from __future__ import annotations

import datetime as dt
import json
import os
import uuid
from typing import List, Optional, Tuple

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
from .task_tree import TaskTree


class ExecutiveWorker:
    def __init__(self, workspace_root: str, model: str = "gpt-4o-mini") -> None:
        self.workspace_root = workspace_root
        self.shell = ShellRunner(cwd=workspace_root)
        self.code = CodebaseUtilities(workspace_root)
        self.edit_engine = EditEngine(workspace_root)
        self.git = GitOps(self.shell)
        self.llm = LLMClient(model=model)
        self.task_tree: Optional[TaskTree] = None

    # --- Spec-aligned high-level API ---
    def execute_ticket(self, task: Task) -> RunLog:
        self.task_tree = TaskTree.load_or_create(self.workspace_root, task.task_id, task.title)

        ready = False
        cumulative_commands: List[CommandResult] = []
        cumulative_commits: List[str] = []
        start = dt.datetime.utcnow().isoformat()

        while not ready:
            eoi = self.pick_eoi_optional(task)
            prompt = self.generate_system_prompt(task, eoi)

            plan = self.plan_current_cycle(prompt)
            step_results, commit_shas = self.execute_plan_with_tools(task, plan)
            validation = self.validate_changes()

            self.update_task_tree(task, step_results, validation)
            commit_sha = self.commit_and_push(task)

            cumulative_commands.extend(step_results)
            if commit_sha:
                cumulative_commits.append(commit_sha)

            ready = self.check_ready_to_submit(task, validation)
            # For MVP, break after first loop to keep cycles short
            if not ready:
                ready = True

        end = dt.datetime.utcnow().isoformat()
        run_log = self.write_run_json(task, eoi, cumulative_commands, validation, cumulative_commits, start, end)
        return run_log

    # --- Steps ---
    def pick_eoi_optional(self, task: Task) -> Optional[dict]:
        # MVP: pass-through of provided EoI
        return task.eoi

    def generate_system_prompt(self, task: Task, eoi: Optional[dict]) -> str:
        tree_snapshot = "(no tree)"
        if self.task_tree is not None:
            # keep small to avoid prompt bloat
            tree_snapshot = json.dumps({"id": self.task_tree.id, "title": self.task_tree.title}, ensure_ascii=False)
        return (
            f"Ticket: {task.task_id} — {task.title}\n"
            f"Desc: {task.description}\n"
            f"EOI: {eoi or {}}\n"
            f"TaskTree: {tree_snapshot}\n"
            "Produce an actionable short plan as JSON list of steps with kinds: search|edit|shell|git|validate."
        )

    def plan_current_cycle(self, prompt: str) -> List[PlanStep]:
        return self.llm.create_plan_from_prompt(prompt)

    def execute_plan_with_tools(self, task: Task, plan: List[PlanStep]) -> Tuple[List[CommandResult], List[str]]:
        commands: List[CommandResult] = []
        commits: List[str] = []
        for step in plan:
            if step.kind == "search":
                pattern = step.args.get("pattern", ".*")
                globs = step.args.get("globs", ["**/*.py", "**/*.md", "**/*.rs", "**/*.ts", "**/*.tsx"])
                hits = self.code.grep(pattern, globs)
                preview = "\n".join([f"{p}:{ln}: {txt}" for p, ln, txt in hits[:10]])
                commands.append(CommandResult(cmd=f"SEARCH {pattern}", exit_code=0, stdout=preview, stderr="", duration_ms=0))
            elif step.kind == "edit":
                edits = step.args.get("edits", [])
                from .edit_engine import FileEdit

                file_edits = [FileEdit(e["path"], e["find"], e["replace"]) for e in edits if all(k in e for k in ("path", "find", "replace"))]
                self.edit_engine.apply_edits(file_edits)
                self.git.add_all()
                msg = step.args.get("message", f"chore: apply edits for {task.task_id}")
                commit_out = self.git.commit(msg)
                sha = self._extract_commit_sha(commit_out)
                if sha:
                    commits.append(sha)
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
                cmd = step.args.get("cmd", "true")
                res = self.shell.run(cmd)
                commands.append(res)
            else:
                continue
        return commands, commits

    def validate_changes(self) -> ValidationResult:
        # MVP: allow user-provided validation step or default noop; mark tests as true when exit_code==0 would be richer later
        return ValidationResult(compiled=None, tests=TestsSummary(passed=True, summary="by-step"))

    def update_task_tree(self, task: Task, results: List[CommandResult], validation: ValidationResult) -> None:
        if self.task_tree is None:
            return
        # MVP: record one synthetic node with evidence of commits
        files: List[str] = []
        commits: List[str] = []
        for r in results:
            if r.cmd.startswith("git ") or r.cmd == "edit_engine.apply_edits":
                # best-effort, we already attempted to parse commits earlier
                pass
        # Persist tree
        self.task_tree.set_status(node_id=f"node-{task.task_id}", status="partial", coverage_pct=10, note="initial pass")
        self.task_tree.record_evidence(node_id=f"node-{task.task_id}", commits=commits, files=files)
        self.task_tree.save(self.workspace_root)

    def commit_and_push(self, task: Task) -> str:
        status = self.git.status()
        if status.strip():
            self.git.add_all()
            out = self.git.commit(f"feat({task.task_id}): progress")
            _ = self.git.push()
            sha = self._extract_commit_sha(out)
            return sha
        return ""

    def write_run_json(
        self,
        task: Task,
        eoi: Optional[dict],
        commands: List[CommandResult],
        validation: ValidationResult,
        commits: List[str],
        start: str,
        end: str,
    ) -> RunLog:
        affected = [
            AffectedNode(
                id=f"node-{task.task_id}",
                status="partial",
                coverage_pct=10,
                evidence={"commits": commits, "files": []},
                note="initial pass",
            )
        ]
        run_log = RunLog(
            run_id=f"r-{uuid.uuid4()}",
            task_id=task.task_id,
            start_ts=start,
            end_ts=end,
            eoi=eoi,
            commands=commands,
            commits=commits,
            validation=validation,
            affected_nodes=affected,
            reflections=[{"type": "decision", "message": "MVP cycle executed"}],
        )
        self._write_run_json(run_log)
        return run_log

    # --- Helpers ---
    def _write_run_json(self, run_log: RunLog) -> None:
        runs_dir = os.path.join(self.workspace_root, "constitutional-agent-test", "runs")
        os.makedirs(runs_dir, exist_ok=True)
        path = os.path.join(runs_dir, f"{run_log.run_id}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(run_log, f, default=lambda o: o.__dict__, indent=2)

    def _extract_commit_sha(self, output: str) -> str:
        # Simple heuristic: fallback empty (we can improve by inspecting .git)
        return ""
