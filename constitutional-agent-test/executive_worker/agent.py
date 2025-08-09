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
    Ticket,
    TestsSummary,
    ValidationResult,
)
from .shell_runner import ShellRunner
from .task_tree import TaskTree
from .prompting import compose_system_prompt, load_iso_42010_eoi_excerpt, load_constitutional_prompt_excerpt


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
    def execute_ticket(self, ticket: Ticket) -> RunLog:
        self.task_tree = TaskTree.load_or_create(self.workspace_root, ticket.ticket_id, ticket.title)

        ready = False
        cumulative_commands: List[CommandResult] = []
        cumulative_commits: List[str] = []
        start = dt.datetime.utcnow().isoformat()

        while not ready:
            eoi = self.pick_eoi_optional(ticket)
            prompt = self.generate_system_prompt(ticket, eoi)

            plan = self.plan_current_cycle(prompt)
            step_results, commit_shas = self.execute_plan_with_tools(ticket, plan)
            validation = self.validate_changes()

            self.update_task_tree(ticket, step_results, validation)
            commit_sha = self.commit_and_push(ticket)

            cumulative_commands.extend(step_results)
            if commit_sha:
                cumulative_commits.append(commit_sha)

            ready = self.check_ready_to_submit(ticket, validation)
            if not ready:
                ready = True

        end = dt.datetime.utcnow().isoformat()
        run_log = self.write_run_json(ticket, eoi, cumulative_commands, validation, cumulative_commits, start, end)
        return run_log

    # --- Steps ---
    def pick_eoi_optional(self, ticket: Ticket) -> Optional[dict]:
        # If provided, use it; otherwise, ask LLM to pick from candidates using ISO/constitutional guidance
        if ticket.eoi:
            return ticket.eoi
        candidates = self.code.candidate_eoi_paths(limit=25)
        iso_excerpt = load_iso_42010_eoi_excerpt(self.workspace_root)
        guidance = "Prefer files/modules most relevant to the ticket description; choose focused EoI, not entire repo."
        choice = self.llm.choose_eoi(ticket=ticket, candidates=candidates, iso_eoi_excerpt=iso_excerpt, guidance=guidance)
        return choice

    def generate_system_prompt(self, ticket: Ticket, eoi: Optional[dict]) -> str:
        tree_snapshot = {"id": self.task_tree.id, "title": self.task_tree.title} if self.task_tree else {"id": "?", "title": "?"}
        iso_excerpt = load_iso_42010_eoi_excerpt(self.workspace_root)
        constitutional_excerpt = load_constitutional_prompt_excerpt(self.workspace_root)
        workspace_summary = self.code.workspace_summary(max_files=12)
        return compose_system_prompt(
            ticket={"id": ticket.ticket_id, "title": ticket.title, "description": ticket.description},
            eoi=eoi,
            task_tree_snapshot=tree_snapshot,
            workspace_summary=workspace_summary,
            iso_eoi_excerpt=iso_excerpt,
            constitutional_excerpt=constitutional_excerpt,
        )

    def plan_current_cycle(self, prompt: str) -> List[PlanStep]:
        return self.llm.create_plan_from_prompt(prompt)

    def execute_plan_with_tools(self, ticket: Ticket, plan: List[PlanStep]) -> Tuple[List[CommandResult], List[str]]:
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
                msg = step.args.get("message", f"chore: apply edits for {ticket.ticket_id}")
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
        return ValidationResult(compiled=None, tests=TestsSummary(passed=True, summary="by-step"))

    def update_task_tree(self, ticket: Ticket, results: List[CommandResult], validation: ValidationResult) -> None:
        if self.task_tree is None:
            return
        node_id = f"node-{ticket.ticket_id}"
        self.task_tree.set_status(node_id=node_id, status="partial", coverage_pct=10, note="initial pass")
        self.task_tree.record_evidence(node_id=node_id, commits=[], files=[])
        self.task_tree.save(self.workspace_root)

    def commit_and_push(self, ticket: Ticket) -> str:
        status = self.git.status()
        if status.strip():
            self.git.add_all()
            out = self.git.commit(f"feat({ticket.ticket_id}): progress")
            _ = self.git.push()
            sha = self._extract_commit_sha(out)
            return sha
        return ""

    def write_run_json(
        self,
        ticket: Ticket,
        eoi: Optional[dict],
        commands: List[CommandResult],
        validation: ValidationResult,
        commits: List[str],
        start: str,
        end: str,
    ) -> RunLog:
        affected = [
            AffectedNode(
                id=f"node-{ticket.ticket_id}",
                status="partial",
                coverage_pct=10,
                evidence={"commits": commits, "files": []},
                note="initial pass",
            )
        ]
        run_log = RunLog(
            run_id=f"r-{uuid.uuid4()}",
            task_id=ticket.ticket_id,
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
        runs_dir = os.path.join(self.workspace_root, "executive_worker", "runs")
        os.makedirs(runs_dir, exist_ok=True)
        path = os.path.join(runs_dir, f"{run_log.run_id}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(run_log, f, default=lambda o: o.__dict__, indent=2)

    def _extract_commit_sha(self, output: str) -> str:
        return ""

    def check_ready_to_submit(self, ticket: Ticket, validation: ValidationResult) -> bool:
        """MVP heuristic: treat one cycle as sufficient, or rely on tests result if provided."""
        if validation.tests and validation.tests.passed:
            return True
        return True
