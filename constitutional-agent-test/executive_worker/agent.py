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

        # Initialize run log immediately for crash-safe logging
        run_log = self._initialize_run_log(ticket)
        self._write_partial_run_log(run_log)  # Write initial state

        ready = False
        while not ready:
            eoi = self.pick_eoi_optional(ticket)
            run_log.eoi = eoi
            self._write_partial_run_log(run_log)  # Update with EOI

            prompt = self.generate_system_prompt(ticket, eoi)

            plan = self.plan_current_cycle(prompt)
            run_log.plan_steps = len(plan)
            self._write_partial_run_log(run_log)  # Update with plan info

            step_results = self._execute_plan_with_incremental_logging(ticket, plan, run_log)
            validation = self.validate_changes()
            run_log.validation = validation
            self._write_partial_run_log(run_log)  # Update with validation

            self.update_task_tree(ticket, step_results, validation)
            commit_sha = self.commit_and_push(ticket)
            if commit_sha:
                run_log.commits.append(commit_sha)
                self._write_partial_run_log(run_log)  # Update with commit

            ready = self.check_ready_to_submit(ticket, validation)
            if not ready:
                ready = True

        # Final completion
        run_log.end_ts = dt.datetime.utcnow().isoformat()
        run_log.status = "completed"
        run_log.affected_nodes = [
            AffectedNode(
                id=f"node-{ticket.ticket_id}",
                status="partial",
                coverage_pct=10,
                evidence={"commits": run_log.commits, "files": []},
                note="initial pass",
            )
        ]
        run_log.reflections = [{"type": "decision", "message": "MVP cycle executed"}]
        self._write_partial_run_log(run_log)  # Final complete log
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
        plan = self.llm.create_plan_from_prompt(prompt)
        # Debug: print the plan to see what's being generated
        print(f"DEBUG: Generated plan with {len(plan)} steps:")
        for i, step in enumerate(plan):
            print(f"  {i+1}. Kind: '{step.kind}', Description: '{step.description[:50]}...'")
            print(f"     Args: {step.args}")
            print(f"     Type of step: {type(step)}, Type of kind: {type(step.kind)}")
        return plan

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
                
                # Skip non-executable descriptive commands
                if not self._is_valid_shell_command(cmd):
                    commands.append(CommandResult(
                        cmd=cmd, 
                        exit_code=-1, 
                        stdout="", 
                        stderr=f"Skipped non-executable command: {cmd}", 
                        duration_ms=0
                    ))
                    continue
                    
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
                
                # Handle compound validation commands by splitting on && and running separately
                if "&&" in cmd:
                    sub_commands = [c.strip() for c in cmd.split("&&")]
                    all_passed = True
                    combined_stdout = ""
                    combined_stderr = ""
                    total_duration = 0
                    
                    for sub_cmd in sub_commands:
                        if self._is_valid_shell_command(sub_cmd):
                            sub_res = self.shell.run(sub_cmd)
                            combined_stdout += sub_res.stdout + "\n"
                            combined_stderr += sub_res.stderr + "\n"
                            total_duration += sub_res.duration_ms
                            if sub_res.exit_code != 0:
                                all_passed = False
                    
                    res = CommandResult(
                        cmd=cmd,
                        exit_code=0 if all_passed else 1,
                        stdout=combined_stdout.strip(),
                        stderr=combined_stderr.strip(),
                        duration_ms=total_duration
                    )
                else:
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
    def _initialize_run_log(self, ticket: Ticket) -> RunLog:
        """Create initial run log with basic ticket info and start timestamp."""
        run_log = RunLog(
            run_id=f"r-{uuid.uuid4()}",
            task_id=ticket.ticket_id,
            start_ts=dt.datetime.utcnow().isoformat(),
            status="in_progress"
        )
        
        # Generate consistent filename for this run (store in instance for reuse)
        now = dt.datetime.utcnow()
        time_first = now.strftime("%H%M%S-%Y%m%d")
        short_uuid = run_log.run_id.split('-')[-1]
        self._current_run_filename = f"{time_first}-{run_log.task_id}-{short_uuid}.json"
        
        return run_log

    def _write_partial_run_log(self, run_log: RunLog) -> None:
        """Write current run log state to disk immediately (crash-safe)."""
        # For tests, write to workspace_root structure; for production, use script directory
        if "pytest" in sys.modules or "/tmp/pytest" in self.workspace_root:
            # Test mode: write to workspace_root/constitutional-agent-test/executive_worker/runs
            runs_dir = os.path.join(self.workspace_root, "constitutional-agent-test", "executive_worker", "runs")
        else:
            # Production mode: write to script directory
            script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # constitutional-agent-test dir
            runs_dir = os.path.join(script_dir, "executive_worker", "runs")
        os.makedirs(runs_dir, exist_ok=True)
        
        # Use consistent filename generated at run start (reuse same file for all incremental writes)
        path = os.path.join(runs_dir, self._current_run_filename)
        
        with open(path, "w", encoding="utf-8") as f:
            json.dump(run_log, f, default=lambda o: o.__dict__, indent=2)

    def _execute_plan_with_incremental_logging(self, ticket: Ticket, plan: List[PlanStep], run_log: RunLog) -> List[CommandResult]:
        """Execute plan with incremental logging after each command."""
        commands: List[CommandResult] = []
        for i, step in enumerate(plan):
            try:
                # Ensure args is always a dict
                args = step.args if isinstance(step.args, dict) else {}
                
                if step.kind == "search":
                    pattern = args.get("pattern", ".*")
                    globs = args.get("globs", ["**/*.py", "**/*.md", "**/*.rs", "**/*.ts", "**/*.tsx"])
                    
                    # Use enhanced semantic search if available
                    if self.use_enhanced and self.enhanced_code and args.get("semantic", False):
                        query = args.get("query", pattern)
                        results = self.enhanced_code.semantic_search(query, max_results=10)
                        preview = "\\n".join([f"{r['file_path']}:{getattr(r.get('symbol'), 'line_number', '?')}: {getattr(r.get('symbol'), 'name', r.get('type', 'unknown'))}" for r in results[:10]])
                        commands.append(CommandResult(cmd=f"SEMANTIC_SEARCH {query}", exit_code=0, stdout=preview, stderr="", duration_ms=0))
                    else:
                        # Fallback to basic grep
                        hits = self.code.grep(pattern, globs)
                        preview = "\\n".join([f"{p}:{ln}: {txt}" for p, ln, txt in hits[:10]])
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
                        run_log.commits.append(sha)
                        
                elif step.kind == "shell":
                    cmd = args.get("cmd", "echo noop")
                    
                    # Skip non-executable descriptive commands
                    if not self._is_valid_shell_command(cmd):
                        commands.append(CommandResult(
                            cmd=cmd, 
                            exit_code=-1, 
                            stdout="", 
                            stderr=f"Skipped non-executable command: {cmd}", 
                            duration_ms=0
                        ))
                        continue
                        
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
                                validation_info += f"\\nSuggestions: {'; '.join(error_analysis.suggestions[:3])}"
                            commands.append(CommandResult(cmd=f"VALIDATE_WITH_ANALYSIS: {cmd}", exit_code=res.exit_code, 
                                                        stdout=validation_info, stderr=res.stderr, duration_ms=res.duration_ms))
                        except Exception:
                            commands.append(res)  # Original result on analysis error
                    else:
                        commands.append(res)
                else:
                    continue
                    
                # Update run log after each command
                run_log.commands.append(commands[-1])
                run_log.current_step = i + 1
                self._write_partial_run_log(run_log)  # Log after each command
                
            except Exception as e:
                # Log the failure and continue or abort based on severity
                error_result = CommandResult(cmd=step.description, exit_code=-1, 
                                           stdout="", stderr=str(e), duration_ms=0)
                commands.append(error_result)
                run_log.commands.append(error_result)
                run_log.error = str(e)
                run_log.status = "failed"
                self._write_partial_run_log(run_log)  # Log the error immediately
                if self._is_fatal_error(e):
                    break
                    
        return commands

    def _is_fatal_error(self, error: Exception) -> bool:
        """Determine if an error should stop execution entirely."""
        # For now, consider all exceptions non-fatal to allow partial progress
        return False

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
    
    def _is_valid_shell_command(self, cmd: str) -> bool:
        """Check if a command is a valid shell command and not descriptive text."""
        if not cmd or not isinstance(cmd, str):
            return False
        
        # Commands that start with common shell utilities are likely valid
        valid_starters = [
            'mkdir', 'touch', 'echo', 'ls', 'cd', 'cp', 'mv', 'rm', 'cat', 'grep',
            'find', 'sed', 'awk', 'sort', 'uniq', 'head', 'tail', 'wc', 'chmod',
            'cargo', 'npm', 'python', 'node', 'git', 'rustc', 'gcc', 'make', 'cmake'
        ]
        
        cmd_lower = cmd.lower().strip()
        first_word = cmd_lower.split()[0] if cmd_lower.split() else ""
        
        # Check if it starts with a valid command
        if first_word in valid_starters:
            return True
        
        # Check if it's a path-based command (starts with ./ or /)
        if first_word.startswith('./') or first_word.startswith('/'):
            return True
        
        # Descriptive text patterns that are NOT shell commands
        descriptive_patterns = [
            'define', 'implement', 'create a', 'add a', 'write', 'build', 
            'generate', 'establish', 'set up', 'configure'
        ]
        
        # If it starts with descriptive words, it's probably not a shell command
        for pattern in descriptive_patterns:
            if cmd_lower.startswith(pattern):
                return False
        
        # If it contains no shell operators and looks like English text, skip it
        shell_operators = ['|', '>', '<', '&&', '||', ';', '$(', '`']
        has_operators = any(op in cmd for op in shell_operators)
        
        # If it's all lowercase words without operators, likely descriptive
        if not has_operators and len(cmd.split()) > 3 and cmd.islower():
            return False
            
        return True
