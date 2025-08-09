from __future__ import annotations

import datetime as dt
import json
import os
import sys
import uuid
from typing import List, Optional, Tuple

from .codebase_utils import CodebaseUtilities
from .enhanced_codebase_utils import EnhancedCodebaseUtils
from .edit_engine import EditEngine
from .enhanced_edit_engine import EnhancedEditEngine
from .error_recovery import IntelligentErrorHandler
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
    def __init__(self, workspace_root: str, model: str = "gpt-4o-mini", use_enhanced: bool = True) -> None:
        self.workspace_root = workspace_root
        self.shell = ShellRunner(cwd=workspace_root)
        
        # Initialize both basic and enhanced utilities
        self.code = CodebaseUtilities(workspace_root)
        self.enhanced_code = EnhancedCodebaseUtils(workspace_root) if use_enhanced else None
        
        self.edit_engine = EditEngine(workspace_root)
        self.enhanced_edit_engine = EnhancedEditEngine(workspace_root) if use_enhanced else None
        
        self.error_handler = IntelligentErrorHandler(workspace_root) if use_enhanced else None
        
        self.git = GitOps(self.shell)
        self.llm = LLMClient(model=model)
        self.task_tree: Optional[TaskTree] = None
        self.use_enhanced = use_enhanced

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
        if self.use_enhanced and self.enhanced_code:
            candidates = self.enhanced_code.candidate_eoi_paths(limit=25)
        else:
            candidates = self.code.candidate_eoi_paths(limit=25)
        iso_excerpt = load_iso_42010_eoi_excerpt(self.workspace_root)
        guidance = "Prefer files/modules most relevant to the ticket description; choose focused EoI, not entire repo."
        choice = self.llm.choose_eoi(ticket=ticket, candidates=candidates, iso_eoi_excerpt=iso_excerpt, guidance=guidance)
        return choice

    def generate_system_prompt(self, ticket: Ticket, eoi: Optional[dict]) -> str:
        tree_snapshot = {"id": self.task_tree.id, "title": self.task_tree.title} if self.task_tree else {"id": "?", "title": "?"}
        iso_excerpt = load_iso_42010_eoi_excerpt(self.workspace_root)
        constitutional_excerpt = load_constitutional_prompt_excerpt(self.workspace_root)
        if self.use_enhanced and self.enhanced_code:
            workspace_summary = self.enhanced_code.workspace_summary(max_files=12)
        else:
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
            # Ensure args is always a dict
            args = step.args if isinstance(step.args, dict) else {}
            
            if step.kind == "search":
                pattern = args.get("pattern", ".*")
                globs = args.get("globs", ["**/*.py", "**/*.md", "**/*.rs", "**/*.ts", "**/*.tsx"])
                
                # Use enhanced semantic search if available
                if self.use_enhanced and self.enhanced_code and args.get("semantic", False):
                    query = args.get("query", pattern)
                    results = self.enhanced_code.semantic_search(query, max_results=10)
                    preview = "\n".join([f"{r['file_path']}:{getattr(r.get('symbol'), 'line_number', '?')}: {getattr(r.get('symbol'), 'name', r.get('type', 'unknown'))}" for r in results[:10]])
                    commands.append(CommandResult(cmd=f"SEMANTIC_SEARCH {query}", exit_code=0, stdout=preview, stderr="", duration_ms=0))
                else:
                    # Fallback to basic grep
                    hits = self.code.grep(pattern, globs)
                    preview = "\n".join([f"{p}:{ln}: {txt}" for p, ln, txt in hits[:10]])
                    commands.append(CommandResult(cmd=f"SEARCH {pattern}", exit_code=0, stdout=preview, stderr="", duration_ms=0))
            elif step.kind == "edit":
                edits = args.get("edits", [])
                from .edit_engine import FileEdit

                file_edits = []
                
                # Handle the expected format: list of edits with path/find/replace
                for e in edits:
                    if all(k in e for k in ("path", "find", "replace")):
                        file_edits.append(FileEdit(e["path"], e["find"], e["replace"]))
                
                # Handle LLM's actual format: single file with path/content
                if not file_edits and "path" in args and "content" in args:
                    # Create new file or append content
                    path = args["path"]
                    content = args["content"]
                    file_edits = [FileEdit(path, "", content)]  # Empty find means append/create
                
                # Use enhanced edit engine for AST-aware operations if available
                edit_type = args.get("edit_type", "basic")
                if self.use_enhanced and self.enhanced_edit_engine and edit_type in ["ast", "rename", "refactor"]:
                    try:
                        if edit_type == "rename" and "old_name" in args and "new_name" in args:
                            # Symbol renaming across codebase
                            affected_files = self.enhanced_edit_engine.rename_symbol(
                                args["old_name"], args["new_name"], args.get("scope", "global")
                            )
                            commands.append(CommandResult(cmd=f"RENAME_SYMBOL {args['old_name']} -> {args['new_name']}", 
                                                        exit_code=0, stdout=f"Renamed in {len(affected_files)} files", stderr="", duration_ms=0))
                        else:
                            # Enhanced AST-aware editing
                            self.enhanced_edit_engine.apply_edits(file_edits)
                            commands.append(CommandResult(cmd="enhanced_edit_engine.apply_edits", exit_code=0, stdout="AST-aware edits applied", stderr="", duration_ms=0))
                    except Exception as e:
                        # Fallback to basic editing on error
                        self.edit_engine.apply_edits(file_edits)
                        commands.append(CommandResult(cmd="edit_engine.apply_edits (fallback)", exit_code=0, stdout=f"Fallback edit: {str(e)}", stderr="", duration_ms=0))
                else:
                    # Basic editing
                    self.edit_engine.apply_edits(file_edits)
                    commands.append(CommandResult(cmd="edit_engine.apply_edits", exit_code=0, stdout="Basic edits applied", stderr="", duration_ms=0))
                
                self.git.add_all()
                msg = args.get("message", f"chore: apply edits for {ticket.ticket_id}")
                commit_out = self.git.commit(msg)
                sha = self._extract_commit_sha(commit_out)
                if sha:
                    commits.append(sha)
            elif step.kind == "shell":
                cmd = args.get("cmd", "echo noop")
                res = self.shell.run(cmd)
                
                # Use intelligent error recovery if command failed and enhanced mode is enabled
                if res.exit_code != 0 and self.use_enhanced and self.error_handler:
                    try:
                        error_analysis = self.error_handler.analyze_error(res.stderr or res.stdout, cmd)
                        if error_analysis.confidence > 0.7 and error_analysis.suggestions:
                            # Try the first high-confidence suggestion
                            suggested_cmd = error_analysis.suggestions[0]
                            recovery_res = self.shell.run(suggested_cmd)
                            if recovery_res.exit_code == 0:
                                commands.append(CommandResult(cmd=f"RECOVERED: {suggested_cmd}", exit_code=0, 
                                                            stdout=f"Auto-recovered from error: {recovery_res.stdout}", stderr="", duration_ms=recovery_res.duration_ms))
                            else:
                                commands.append(res)  # Original failed command
                        else:
                            commands.append(res)  # Original failed command
                    except Exception:
                        commands.append(res)  # Original failed command on recovery error
                else:
                    commands.append(res)
            elif step.kind == "git":
                action = args.get("action", "push")
                if action == "push":
                    out = self.git.push()
                else:
                    out = self.git.status()
                commands.append(CommandResult(cmd=f"git {action}", exit_code=0, stdout=out, stderr="", duration_ms=0))
            elif step.kind == "validate":
                cmd = args.get("cmd", "true")
                res = self.shell.run(cmd)
                
                # Enhanced validation with error analysis
                if res.exit_code != 0 and self.use_enhanced and self.error_handler:
                    try:
                        error_analysis = self.error_handler.analyze_error(res.stderr or res.stdout, cmd)
                        validation_info = f"Validation failed. Error type: {error_analysis.error_type}, Confidence: {error_analysis.confidence:.2f}"
                        if error_analysis.suggestions:
                            validation_info += f"\nSuggestions: {'; '.join(error_analysis.suggestions[:3])}"
                        commands.append(CommandResult(cmd=f"VALIDATE_WITH_ANALYSIS: {cmd}", exit_code=res.exit_code, 
                                                    stdout=validation_info, stderr=res.stderr, duration_ms=res.duration_ms))
                    except Exception:
                        commands.append(res)  # Original result on analysis error
                else:
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
        # For tests, write to workspace_root structure; for production, use script directory
        if "pytest" in sys.modules or "/tmp/pytest" in self.workspace_root:
            # Test mode: write to workspace_root/constitutional-agent-test/executive_worker/runs
            runs_dir = os.path.join(self.workspace_root, "constitutional-agent-test", "executive_worker", "runs")
        else:
            # Production mode: write to script directory
            script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # constitutional-agent-test dir
            runs_dir = os.path.join(script_dir, "executive_worker", "runs")
        os.makedirs(runs_dir, exist_ok=True)
        
        # Create time-first filename for easy identification in short file viewers
        # Format: HHMMSS-YYYYMMDD-{task_id}-{short_uuid}.json
        now = dt.datetime.utcnow()
        time_first = now.strftime("%H%M%S-%Y%m%d")
        short_uuid = run_log.run_id.split('-')[-1]  # Last part of UUID for uniqueness
        filename = f"{time_first}-{run_log.task_id}-{short_uuid}.json"
        path = os.path.join(runs_dir, filename)
        
        with open(path, "w", encoding="utf-8") as f:
            json.dump(run_log, f, default=lambda o: o.__dict__, indent=2)

    def _extract_commit_sha(self, output: str) -> str:
        return ""

    def check_ready_to_submit(self, ticket: Ticket, validation: ValidationResult) -> bool:
        """MVP heuristic: treat one cycle as sufficient, or rely on tests result if provided."""
        if validation.tests and validation.tests.passed:
            return True
        return True
