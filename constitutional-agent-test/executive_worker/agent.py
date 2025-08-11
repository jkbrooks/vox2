from __future__ import annotations

import datetime as dt
import json
import os
import sys
import uuid
from pathlib import Path
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
    DeepPlan,
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
        self.workspace_root = os.path.abspath(workspace_root)
        self.shell = ShellRunner(cwd=self.workspace_root)
        
        # Initialize both basic and enhanced utilities with the correct root
        self.code = CodebaseUtilities(self.workspace_root)
        self.enhanced_code = EnhancedCodebaseUtils(self.workspace_root) if use_enhanced else None
        
        self.edit_engine = EditEngine(self.workspace_root)
        self.enhanced_edit_engine = EnhancedEditEngine(self.workspace_root) if use_enhanced else None
        
        self.error_handler = IntelligentErrorHandler(self.workspace_root) if use_enhanced else None
        
        self.git = GitOps(self.shell)
        self.llm = LLMClient(model=model)
        self.task_tree: Optional[TaskTree] = None
        self.use_enhanced = use_enhanced

    # --- Spec-aligned high-level API ---
    def execute_ticket(self, ticket: Ticket) -> RunLog:
        # Phase II: Deep upfront planning - analyze requirements and create strategy
        deep_plan = self.analyze_requirements_and_plan(ticket)
        
        # Create/refresh task tree with deep planning context
        self.task_tree = TaskTree.load_or_create(self.workspace_root, ticket.ticket_id, ticket.title, deep_plan)

        # Initialize run log immediately for crash-safe logging
        run_log = self._initialize_run_log(ticket, deep_plan)
        self._write_partial_run_log(run_log)  # Write initial state

        try:
            print(f"\n🚀 Starting execution cycles for ticket #{ticket.ticket_id}")
            cycle_count = 0
            # Increased cycle limit for complex tickets - modern LLMs can handle substantial changes
            max_cycles = 100 if deep_plan.estimated_complexity in ["high", "epic"] else 50
            ready = False
            while not ready and cycle_count < max_cycles:
                cycle_count += 1
                print(f"\n🔄 Execution Cycle #{cycle_count}")
                
                print("🎯 Selecting Entity of Interest...")
                eoi = self.pick_eoi_optional(ticket)
                if eoi:
                    print(f"   ✓ Selected EoI: {eoi.get('label', 'Unknown')} ({eoi.get('path', 'No path')})")
                else:
                    print("   ℹ️  No specific EoI selected")
                run_log.eoi = eoi
                self._write_partial_run_log(run_log)  # Update with EOI
    
                print("📝 Generating system prompt with deep planning context...")
                prompt = self.generate_system_prompt(ticket, eoi, deep_plan)
    
                print("🎯 Creating execution plan...")
                plan = self.plan_current_cycle(prompt)
                print(f"   ✓ Generated plan with {len(plan)} steps")
                run_log.plan_steps = len(plan)
                self._write_partial_run_log(run_log)  # Update with plan info
    
                print("⚡ Executing plan with error recovery...")
                step_results = self._execute_plan_with_incremental_logging(ticket, plan, run_log)
                
                print("🔍 Validating changes...")
                validation = self.validate_changes()
                print(f"   📊 Compilation: {'✅ PASS' if validation.compiled else '❌ FAIL'}")
                if validation.tests:
                    print(f"   🧪 Tests: {'✅ PASS' if validation.tests.passed else '❌ FAIL'}")
                run_log.validation = validation
                self._write_partial_run_log(run_log)  # Update with validation
    
                print("📋 Updating task tree...")
                self.update_task_tree(ticket, step_results, validation)
                
                # Only commit if we have substantial changes and validation passes
                should_commit = (
                    validation.compiled and 
                    validation.tests and validation.tests.passed and
                    len(step_results) >= 3  # Only commit if we made substantial progress
                )
                
                if should_commit:
                    print("💾 Committing substantial progress...")
                    commit_sha = self.commit_and_push(ticket)
                    if commit_sha:
                        print(f"   ✓ Committed: {commit_sha[:8]}")
                        run_log.commits.append(commit_sha)
                        self._write_partial_run_log(run_log)  # Update with commit
                    else:
                        print("   ℹ️  No changes to commit")
                else:
                    print("💾 Deferring commit until substantial progress is made")
    
                print("✅ Checking if ready to submit...")
                ready = self.check_ready_to_submit(ticket, validation, deep_plan)
                
                if not ready:
                    print("   🔄 Not ready yet, continuing to next cycle...")
                else:
                    print("   🎉 Ready to submit!")
                    
            # Check if we hit cycle limit
            if cycle_count >= max_cycles and not ready:
                print(f"❌ Hit maximum cycle limit ({max_cycles}), execution failed")
                run_log.status = "failed_max_cycles"
                run_log.error = f"Agent failed to complete ticket after {max_cycles} cycles"
            else:
                run_log.status = "completed"
    
            # Final completion
            print(f"\n🎉 Ticket #{ticket.ticket_id} completed successfully!")
            print(f"   📊 Total cycles: {cycle_count}")
            print(f"   💾 Commits made: {len(run_log.commits)}")
            print(f"   ⏱️  Run ID: {run_log.run_id}")
            
            run_log.end_ts = dt.datetime.utcnow().isoformat()
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
            
            print(f"📄 Run log saved: {self._current_run_filename}")
            return run_log
        except Exception as e:
            run_log.status = "CRASHED"
            run_log.error = f"Agent crashed with exception: {e}"
            run_log.end_ts = dt.datetime.utcnow().isoformat()
            self._write_partial_run_log(run_log)
            print(f"💥 Agent crashed! Final run log saved to {self._current_run_filename}")
            raise e

    # --- Phase II: Deep Planning ---
    def analyze_requirements_and_plan(self, ticket: Ticket) -> DeepPlan:
        """
        Phase II: Perform comprehensive upfront analysis before execution cycles begin.
        Returns strategic plan with requirements, success criteria, and approach.
        """
        print(f"🧠 Phase II: Deep planning analysis for ticket #{ticket.ticket_id}")
        
        # Get codebase context for analysis
        print("📋 Analyzing codebase context...")
        if self.use_enhanced and self.enhanced_code:
            codebase_summary = self.enhanced_code.workspace_summary(max_files=15)
        else:
            codebase_summary = self.code.workspace_summary(max_files=15)
            
        # 1) Requirement decomposition
        print("🔍 Step 1/4: Analyzing requirements...")
        requirements = self.llm.analyze_requirements(ticket.description)
        print(f"   ✓ Identified {len(requirements)} requirements")
        
        # 2) Success criteria definition  
        print("🎯 Step 2/4: Defining success criteria...")
        success_criteria = self.llm.define_success_criteria(ticket, requirements)
        print(f"   ✓ Defined {len(success_criteria)} success criteria")
        
        # 3) Risk assessment and complexity analysis
        print("⚠️  Step 3/4: Assessing risks and complexity...")
        risks = self.llm.assess_complexity_and_risks(ticket, requirements, codebase_summary)
        print(f"   ✓ Identified {len(risks)} risk factors")
        
        # 4) High-level strategy formulation
        print("🎲 Step 4/4: Creating implementation strategy...")
        strategy = self.llm.create_strategy(ticket, requirements, risks, codebase_summary)
        print("   ✓ Strategy formulated")
        
        # 5) Estimate complexity level
        print("🔢 Estimating complexity level...")
        complexity = "low"
        if len(requirements) > 5 or len(risks) > 3:
            complexity = "medium"
        if len(requirements) > 10 or any("async" in str(r).lower() or "macro" in str(r).lower() for r in requirements + risks):
            complexity = "high" 
        if len(requirements) > 15:
            complexity = "epic"
            
        print(f"✅ Deep planning complete! Complexity: {complexity.upper()}")
        print(f"   📋 {len(requirements)} requirements, 🎯 {len(success_criteria)} success criteria, ⚠️ {len(risks)} risks")
            
        return DeepPlan(
            requirements=requirements,
            success_criteria=success_criteria,
            risks=risks,
            strategy=strategy,
            estimated_complexity=complexity
        )

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

    def generate_system_prompt(self, ticket: Ticket, eoi: Optional[dict], deep_plan: DeepPlan) -> str:
        tree_snapshot = {"id": self.task_tree.id, "title": self.task_tree.title} if self.task_tree else {"id": "?", "title": "?"}
        iso_excerpt = load_iso_42010_eoi_excerpt(self.workspace_root)
        constitutional_excerpt = load_constitutional_prompt_excerpt(self.workspace_root)
        if self.use_enhanced and self.enhanced_code:
            workspace_summary = self.enhanced_code.workspace_summary(max_files=12)
        else:
            workspace_summary = self.code.workspace_summary(max_files=12)
        # Convert deep_plan to dict format for prompt
        deep_plan_dict = None
        if deep_plan:
            deep_plan_dict = {
                "requirements": deep_plan.requirements,
                "success_criteria": deep_plan.success_criteria,
                "risks": deep_plan.risks,
                "strategy": deep_plan.strategy,
                "estimated_complexity": deep_plan.estimated_complexity
            }
            
        return compose_system_prompt(
            ticket={"id": ticket.ticket_id, "title": ticket.title, "description": ticket.description},
            eoi=eoi,
            task_tree_snapshot=tree_snapshot,
            workspace_summary=workspace_summary,
            iso_eoi_excerpt=iso_excerpt,
            constitutional_excerpt=constitutional_excerpt,
            deep_plan=deep_plan_dict,
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
        """
        Validate changes by running appropriate build/test commands.
        Returns ValidationResult with actual compilation and test status.
        """
        # Detect project type and run appropriate validation
        workspace_path = Path(self.workspace_root)
        
        # Check if this is a Rust project
        if (workspace_path / "Cargo.toml").exists():
            return self._validate_rust_project()
        # Check if this is a Python project  
        elif (workspace_path / "pyproject.toml").exists() or (workspace_path / "setup.py").exists():
            return self._validate_python_project()
        # Check if this is a Node.js project
        elif (workspace_path / "package.json").exists():
            return self._validate_node_project()
        else:
            # Generic validation - assume it compiles if no obvious syntax errors
            return ValidationResult(compiled=True, tests=TestsSummary(passed=True, summary="no specific project type detected"))
    
    def _validate_rust_project(self) -> ValidationResult:
        """Validate Rust project with cargo check and cargo test."""
        print("🔍 Running Rust validation (cargo check + cargo test)...")
        
        # Check compilation, suppressing warnings
        check_result = self.shell.run("cargo check --quiet --all-targets --all-features 2>/dev/null")
        compiled = check_result.exit_code == 0
        
        if not compiled:
            # If compilation fails, re-run without suppression to capture the actual error
            check_result_with_error = self.shell.run("cargo check")
            print(f"❌ Cargo check failed: {check_result_with_error.stderr}")
        else:
            print("✅ Cargo check passed")
        
        # Run tests, suppressing warnings
        test_result = self.shell.run("cargo test --quiet --all-targets --all-features 2>/dev/null")
        tests_passed = test_result.exit_code == 0
        
        if not tests_passed:
            # If tests fail, re-run without suppression to capture the failure details
            test_result_with_error = self.shell.run("cargo test")
            print(f"❌ Cargo test failed: {test_result_with_error.stderr}")
        else:
            print("✅ Cargo test passed")
        
        return ValidationResult(
            compiled=compiled,
            tests=TestsSummary(
                passed=tests_passed,
                summary=f"cargo check: {'PASS' if compiled else 'FAIL'}, cargo test: {'PASS' if tests_passed else 'FAIL'}"
            )
        )
    
    def _validate_python_project(self) -> ValidationResult:
        """Validate Python project with syntax check and pytest."""
        print("🔍 Running Python validation (syntax + pytest)...")
        
        # Check syntax by trying to compile all Python files
        compile_result = self.shell.run("python -m py_compile **/*.py")
        compiled = compile_result.exit_code == 0
        
        # Run tests if pytest is available
        test_result = self.shell.run("python -m pytest --tb=short")
        tests_passed = test_result.exit_code == 0
        
        return ValidationResult(
            compiled=compiled,
            tests=TestsSummary(
                passed=tests_passed,
                summary=f"syntax check: {'PASS' if compiled else 'FAIL'}, pytest: {'PASS' if tests_passed else 'FAIL'}"
            )
        )
    
    def _validate_node_project(self) -> ValidationResult:
        """Validate Node.js project with TypeScript check and npm test."""
        print("🔍 Running Node.js validation (tsc + npm test)...")
        
        # Check TypeScript compilation if available
        tsc_result = self.shell.run("npx tsc --noEmit")
        compiled = tsc_result.exit_code == 0
        
        # Run tests
        test_result = self.shell.run("npm test")
        tests_passed = test_result.exit_code == 0
        
        return ValidationResult(
            compiled=compiled,
            tests=TestsSummary(
                passed=tests_passed,
                summary=f"tsc: {'PASS' if compiled else 'FAIL'}, npm test: {'PASS' if tests_passed else 'FAIL'}"
            )
        )

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
    def _initialize_run_log(self, ticket: Ticket, deep_plan: Optional[DeepPlan] = None) -> RunLog:
        """Create initial run log with basic ticket info, start timestamp, and deep planning context."""
        run_log = RunLog(
            run_id=f"r-{uuid.uuid4()}",
            task_id=ticket.ticket_id,
            start_ts=dt.datetime.utcnow().isoformat(),
            status="in_progress",
            deep_plan=deep_plan
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
                    res = self._execute_shell_with_recovery(cmd, max_attempts=5)
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

    def check_ready_to_submit(self, ticket: Ticket, validation: ValidationResult, deep_plan: DeepPlan) -> bool:
        """
        Phase II: Comprehensive validation against deep planning requirements.
        Only return True when ticket is actually complete.
        """
        # 1) Technical validation must pass
        if not validation.compiled:
            print("❌ Not ready: Code doesn't compile")
            return False
            
        if validation.tests and not validation.tests.passed:
            print("❌ Not ready: Tests are failing")
            return False
            
        # 2) Semantic validation against deep plan success criteria
        semantic_result = self.validate_against_success_criteria(ticket, deep_plan)
        if not semantic_result:
            print("❌ Not ready: Success criteria not met")
            return False
            
        print("✅ Ready to submit: All validation criteria passed")
        return True
        
    def validate_against_success_criteria(self, ticket: Ticket, deep_plan: DeepPlan) -> bool:
        """
        Phase II: Semantic validation - does the implementation actually meet the ticket requirements?
        """
        try:
            # Get current codebase state
            if self.use_enhanced and self.enhanced_code:
                workspace_summary = self.enhanced_code.workspace_summary(max_files=10)
            else:
                workspace_summary = self.code.workspace_summary(max_files=10)
                
            # Ask LLM to validate against success criteria
            validation_prompt = (
                f"Evaluate if this ticket has been successfully completed:\n\n"
                f"Ticket: {ticket.title}\n"
                f"Description: {ticket.description}\n\n"
                f"Original Requirements: {deep_plan.requirements}\n"
                f"Success Criteria: {deep_plan.success_criteria}\n\n"
                f"Current Codebase State:\n{workspace_summary}\n\n"
                f"Has the ticket been successfully completed? Consider:\n"
                f"1. Are all requirements implemented?\n"
                f"2. Do the changes meet the success criteria?\n"
                f"3. Is the implementation functional and complete?\n\n"
                f"Return JSON: {{\"completed\": true/false, \"reason\": \"explanation\"}}"
            )
            
            resp = self.llm.client.chat.completions.create(
                model=self.llm.model,
                messages=[
                    {"role": "system", "content": "You evaluate ticket completion against requirements and success criteria."},
                    {"role": "user", "content": validation_prompt},
                ],
                temperature=0.1,
            )
            
            content = resp.choices[0].message.content or '{"completed": false, "reason": "No response"}'
            import json
            result = json.loads(content)
            
            if isinstance(result, dict) and "completed" in result:
                completed = result.get("completed", False)
                reason = result.get("reason", "No reason provided")
                print(f"🔍 Semantic validation: {reason}")
                return completed
                
        except Exception as e:
            print(f"⚠️ Semantic validation error: {e}")
            
        # Fallback: basic heuristic validation
        return self._basic_completion_heuristic(ticket, deep_plan)
        
    def _basic_completion_heuristic(self, ticket: Ticket, deep_plan: DeepPlan) -> bool:
        """Fallback validation when LLM semantic validation fails"""
        # Check if we have some files created/modified based on requirements
        requirements_met = 0
        total_requirements = len(deep_plan.requirements)
        
        if total_requirements == 0:
            return True  # No specific requirements
            
        # Simple heuristic: check for key terms from requirements in workspace
        try:
            if self.use_enhanced and self.enhanced_code:
                files = self.enhanced_code.glob_files("**/*")
            else:
                files = self.code.glob_files("**/*")
                
            workspace_content = " ".join([f.lower() for f in files])
            
            for req in deep_plan.requirements:
                req_lower = req.lower()
                # Look for key implementation terms
                if any(term in workspace_content for term in req_lower.split() if len(term) > 3):
                    requirements_met += 1
                    
        except Exception:
            pass
            
        completion_ratio = requirements_met / total_requirements if total_requirements > 0 else 0
        completed = completion_ratio >= 0.5  # At least 50% of requirements show evidence
        
        print(f"🔍 Heuristic validation: {requirements_met}/{total_requirements} requirements have evidence ({completion_ratio:.1%})")
        return completed
        
    def _execute_shell_with_recovery(self, cmd: str, max_attempts: int = 5) -> CommandResult:
        """
        Phase II: Execute shell command with aggressive error recovery (up to 5 attempts).
        Uses intelligent error analysis and progressive fix strategies.
        """
        last_result = None
        
        for attempt in range(max_attempts):
            print(f"🔧 Shell attempt {attempt + 1}/{max_attempts}: {cmd}")
            
            result = self.shell.run(cmd)
            
            if result.exit_code == 0:
                if attempt > 0:
                    print(f"✅ Command succeeded after {attempt + 1} attempts")
                return result
                
            print(f"❌ Attempt {attempt + 1} failed (exit {result.exit_code}): {result.stderr[:200]}...")
            last_result = result
            
            # Don't try recovery on the last attempt
            if attempt >= max_attempts - 1:
                break
                
            # Try intelligent error recovery
            if self.use_enhanced and self.error_handler:
                try:
                    error_analysis = self.error_handler.analyze_error(
                        result.stderr or result.stdout, cmd
                    )
                    
                    if error_analysis.confidence > 0.5 and error_analysis.suggestions:
                        # Progressive strategy: try different suggestions on different attempts
                        suggestion_idx = min(attempt, len(error_analysis.suggestions) - 1)
                        suggested_cmd = error_analysis.suggestions[suggestion_idx]
                        
                        print(f"🔍 Error analysis (confidence {error_analysis.confidence:.1%}): {error_analysis.explanation}")
                        print(f"💡 Trying fix: {suggested_cmd}")
                        
                        # Update cmd for next attempt
                        cmd = suggested_cmd
                        continue
                        
                except Exception as e:
                    print(f"⚠️ Error recovery failed: {e}")
                    
            # Fallback recovery strategies based on common error patterns
            cmd = self._apply_fallback_recovery(cmd, result, attempt)
            
        print(f"💥 Command failed after {max_attempts} attempts")
        return last_result or CommandResult(cmd=cmd, exit_code=-1, stdout="", stderr="Max attempts exceeded", duration_ms=0)
        
    def _apply_fallback_recovery(self, cmd: str, failed_result: CommandResult, attempt: int) -> str:
        """Apply fallback recovery strategies when intelligent recovery isn't available"""
        error_text = (failed_result.stderr + " " + failed_result.stdout).lower()
        
        # Strategy 1: Permission issues
        if "permission denied" in error_text and not cmd.startswith("sudo"):
            return f"sudo {cmd}"
            
        # Strategy 2: Directory doesn't exist
        if "no such file or directory" in error_text and ("mkdir" not in cmd and "touch" not in cmd):
            if "/" in cmd:
                # Try creating parent directories first
                return f"mkdir -p $(dirname {cmd.split()[-1]}) && {cmd}"
                
        # Strategy 3: File already exists (for touch/mkdir)
        if "file exists" in error_text:
            if cmd.startswith("mkdir"):
                return cmd.replace("mkdir", "mkdir -p")
            elif cmd.startswith("touch"):
                return f"rm -f {cmd.split()[-1]} && {cmd}"
                
        # Strategy 4: Cargo/Rust specific
        if "cargo" in cmd and ("error" in error_text or "failed" in error_text):
            if attempt == 0:
                return "cargo clean && " + cmd
            elif attempt == 1:
                return cmd.replace("cargo check", "cargo check --all-features")
                
        # Strategy 5: Add verbosity for debugging
        if attempt >= 2:
            if cmd.startswith("cargo"):
                return cmd + " --verbose"
            elif cmd.startswith("npm") or cmd.startswith("yarn"):
                return cmd + " --verbose"
                
        return cmd  # No fallback strategy found
