# Executive Worker MVP – Product Specification

This spec defines a minimal, testable, execution‑centric agent (“Executive Worker”) to operate on tickets. It prioritizes codebase understanding/navigation, reliable multi‑file edits, shell‑level execution, and strong git usage. It deliberately avoids PR flows, heavy observability, and outer-loop meta‑evolution.

References (context only):
- Open SWE (planning + execution agent, shell-based ops): https://github.com/langchain-ai/open-swe
- Claude Code (terminal/IDE agent, shell + edits): https://github.com/anthropics/claude-code
- ADAS (outer-loop meta-evolution): https://arxiv.org/abs/2408.08435
- AgentGen (curriculum/attribution ideas): https://arxiv.org/pdf/2408.00764

## 1) Scope and Goals
- Execute a single GitHub ticket end-to-end on Vox2 (dummy project benchmark).
- Use arbitrary shell commands to build/test/format/lint per repo needs (ShellRunner P0).
- Provide robust code navigation/search and a transactional edit engine (hunk diffs, multi-file apply).
- Maintain a simple, evolving task tree file and a per-run log file.
- Optionally set an Entity of Interest (EoI) per loop as an Attention Director (no gates).

Non-goals (MVP):
- PR/review workflows; parallelism/sandboxing; heavy observability/dashboards; per‑EoI documents; language adapters.

## 2) Core Artifacts
- task_tree.yaml (versioned in git)
  - Purpose: predictive, hierarchical plan + post‑hoc attribution of work to nodes.
  - The agent may add/edit nodes/dependencies/acceptance notes; not enforced during execution.
- run.json (one file per run)
  - Purpose: compact, structured trail for commands, commits, validation, and brief reflections.
- Git commits/diffs
  - Purpose: source of truth for code changes and evidence links in task_tree.yaml / run.json.

### 2.1 Minimal schemas (initial)
- task_tree.yaml (illustrative)
  ```yaml
  id: ticket-123
  title: "Short title from issue"
  nodes:
    - id: n-1
      title: "Adjust progression system API"
      deps: []
      status: partial | done | unchanged
      coverage_pct: 0..100
      acceptance: ["compiles", "tests pass", "update docs"]
      evidence:
        commits: ["<sha>"]
        files: ["server/world/.../file.rs"]
      notes: "Short line about what changed"
      children: []
  ```
- run.json (illustrative)
  ```json
  {
    "run_id": "r-2025-08-09-001",
    "task_id": "ticket-123",
    "start_ts": "2025-08-09T12:34:56Z",
    "end_ts": "2025-08-09T12:40:10Z",
    "eoi": { "label": "progression_system.rs", "path": "server/world/..." },
    "commands": [
      { "cmd": "cargo check", "exit_code": 0, "top_stderr": "", "duration_ms": 1234 }
    ],
    "commits": ["abc123"],
    "validation": { "compiled": true, "tests": { "passed": true, "summary": "3 passed" } },
    "affected_nodes": [
      {
        "id": "n-1",
        "status": "partial",
        "coverage_pct": 60,
        "evidence": { "commits": ["abc123"], "files": ["server/.../file.rs"] },
        "note": "updated API + tests"
      }
    ],
    "reflections": [ { "type": "decision", "message": "Polished component before system-level refactor" } ]
  }
  ```

## 3) System Prompt Inputs
- Ticket summary and body (task_id).
- Optional EoI (Attention Director): free-form handle (function/region/class/file/pattern/concern).
- ISO/IEEE 42010 vocabulary to bias context: stakeholders, viewpoints, concerns (lightweight text slots).
- Task tree snapshot (task_tree.yaml) for context only (not enforced).
- Repo constraints: write-scope allowlist, hop/time/diff-size budget hints.

## 4) Agent API (pseudo-code)
```python
class ExecutiveAgent:
    def __init__(self, workspace_root: str):
        self.workspace_root = workspace_root
        self.shell = ShellRunner(cwd=workspace_root)
        self.code = CodebaseUtilities(workspace_root)
        self.git = GitClient(workspace_root)

    def execute_ticket(self, ticket: Ticket) -> RunResult:
        # 1) create/refresh predictive task tree file
        self.task_tree = TaskTree.load_or_create(ticket)

        # 2) Initialize run log immediately for crash-safe incremental logging
        run_log = self.initialize_run_log(ticket)
        self.write_partial_run_log(run_log)  # Write initial state to disk

        ready = False
        while not ready:
            eoi = self.pick_eoi_optional(ticket, self.task_tree)
            run_log.eoi = eoi
            self.write_partial_run_log(run_log)  # Update with EOI selection
            
            prompt = self.generate_system_prompt(ticket, eoi, self.task_tree)

            plan = self.plan_current_cycle(prompt)        # may be ephemeral scratchpad
            run_log.plan_steps = len(plan)
            self.write_partial_run_log(run_log)  # Update with plan information
            
            result = self.execute_plan_with_tools(plan, run_log)   # search/edit/shell/git + incremental logging
            validation = self.validate_changes()          # build/tests
            run_log.validation = validation
            self.write_partial_run_log(run_log)  # Update with validation results

            self.update_task_tree(ticket, result, validation)
            commit_sha = self.commit_and_push(ticket)
            if commit_sha:
                run_log.commits.append(commit_sha)
                self.write_partial_run_log(run_log)  # Update with commit SHA

            ready = self.check_ready_to_submit(ticket, self.task_tree, validation)

        # Final completion status
        run_log.end_ts = datetime.utcnow().isoformat()
        run_log.status = "completed"
        self.write_partial_run_log(run_log)
        return run_log
```

### 4.1 Incremental Run Logging Methods

```python
def initialize_run_log(self, ticket: Ticket) -> RunLog:
    """Create initial run log with basic ticket info and start timestamp."""
    return RunLog(
        run_id=f"r-{uuid.uuid4()}",
        task_id=ticket.ticket_id,
        start_ts=datetime.utcnow().isoformat(),
        status="in_progress",
        commands=[],
        commits=[],
        plan_steps=0,
        current_step=0
    )

def write_partial_run_log(self, run_log: RunLog) -> None:
    """Write current run log state to disk immediately (crash-safe)."""
    # Write to runs/{HHMMSS-YYYYMMDD-task_id-uuid}.json
    # Overwrites previous version with current state

def execute_plan_with_tools(self, plan: List[PlanStep], run_log: RunLog) -> List[CommandResult]:
    """Execute plan with incremental logging after each command."""
    results = []
    for i, step in enumerate(plan):
        try:
            result = self.execute_single_step(step)
            results.append(result)
            run_log.commands.append(result)
            run_log.current_step = i + 1
            self.write_partial_run_log(run_log)  # Log after each command
        except Exception as e:
            # Log the failure and determine if execution should continue
            error_result = CommandResult(cmd=step.description, exit_code=-1, 
                                       stdout="", stderr=str(e), duration_ms=0)
            results.append(error_result)
            run_log.commands.append(error_result)
            run_log.error = str(e)
            run_log.status = "failed"
            self.write_partial_run_log(run_log)  # Log the error immediately
            if self.is_fatal_error(e):
                break
    return results
```

Notes:
- plan, execute, validate can be combined in one LLM prompt if desired; MVP supports either pattern.
- A cycle ends when the agent decides it's done for now; nodes need not be 100% complete.
- **Incremental logging ensures run analysis is possible even when agent crashes mid-execution.**

## 5) Functions / Tools

### 5.1 Codebase understanding & navigation (critical)
- Search: file-globs + regex with context lines; file type filters.
- Index: files → language/type; modules/packages; map tests; basic symbol table; per-language import graph (best-effort).
- Relevance selection for edits: combine search hits + dependency walk to surface impacted files.

### 5.2 File editing (Edit Engine)
- Hunk-based multi‑file diffs with preview/dry‑run; transactional apply (all‑or‑nothing).
- File ops: create/move/delete; header/boilerplate insertion.
- Conflict‑safe apply: detect upstream changes; attempt minimal-context retries; fallback guidance if needed.

### 5.3 ShellRunner (P0)
- Arbitrary command execution with:
  - Inputs: cmd (str), cwd, env overrides, timeout.
  - Output: { success, exit_code, stdout, stderr, duration_ms }.
- Nice‑to‑have later: streaming logs, allow/deny list, redaction.

### 5.4 Git and GitHub
- Strong local git: status/diff/add/restore/commit/rebase/reset; frequent small commits; tag snapshots if needed.
- Push to origin; GitHub PR/review flows are out of scope for MVP.

### 5.5 Task tree management
- load_or_create(ticket) → task_tree.yaml stub with root id/title.
- Update after each loop: for affected nodes set status/coverage/evidence/notes; allow adding nodes/deps/acceptance.
- The tree is guidance + attribution only; not enforced during execution.

### 5.6 Reload system prompt (dynamic inputs)
- Compose prompt from ticket, optional EoI, light ISO/IEEE slots (stakeholders/viewpoints/concerns), task_tree snapshot, and constraints.
- Keep it compact; no heavy constitutional content in MVP.

## 6) Execution Flow Details
1) create_task_tree(ticket)
2) while not ready_to_submit:
   - pick or change EoI (optional; can be None)
   - generate system prompt (EoI + stakeholders/viewpoints/concerns + tree snapshot)
   - create plan for current cycle (or fold into next step)
   - execute plan with tools (search→edit→shell→git)
   - validate changes (build/tests)
   - update task_tree.yaml (status/coverage/evidence/notes; edits allowed)
   - commit changes and push

## 7) Guardrails (not blocking MVP; keep minimal)
- Write-scope allowlist.
- Hop/time/diff-size budget guidance.
- Quick rollback to last green commit.

## 8) Testing & Acceptance
- Benchmark on Vox2 against the prior Cursor run (same features/files outcome).
- Acceptance:
  - Agent performs at least one multi‑file change that compiles.
  - Produces task_tree.yaml and run.json with coherent attribution and trails.
  - Commits/pushes small, incremental changes.

## 9) Telemetry & Logging (initial)
- Single run.json per cycle.
- No dashboards; rely on git + minimal JSON.

## 10) Extensibility (post‑MVP)
- Optional plan store (read_plan/update_plan tools) for resumability across sessions.
- Language‑specific parsers (cargo/pytest) if generic output parsing proves insufficient.
- PR orchestration; outer‑loop ADAS/AgentGen pipelines; n8n/LangGraph wrappers for durable execution.

## 11) Open Questions
- Exact task_tree.yaml keys and maturity levels (keep light now; evolve empirically).
- How much ISO/IEEE vocabulary meaningfully improves outcomes per EoI—tune after first runs.
- Commit policy defaults (per file vs per logical step) – likely per logical step.
