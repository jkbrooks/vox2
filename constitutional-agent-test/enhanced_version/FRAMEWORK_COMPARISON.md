# Agent Framework Comparison: Open SWE vs Claude Code vs Our Kernel

This document compares core capabilities of two reference implementations and our current minimal kernel, with a focus on the smallest viable feature set needed to replicate a Cursor-like, human-in-the-loop development experience.

References:
- Open SWE (LangGraph-based) — [github.com/langchain-ai/open-swe](https://github.com/langchain-ai/open-swe)
- Claude Code (terminal/IDE agent) — [github.com/anthropics/claude-code](https://github.com/anthropics/claude-code)

## 1) High-level positioning

- Open SWE:
  - Cloud-hosted, asynchronous coding agent built on LangGraph.
  - Distinct planning step with user approval; parallel task execution; end-to-end task mgmt (issues and PRs).
  - Can be run via UI and via GitHub issue labels (e.g., `open-swe`, `open-swe-auto`).
  - Source: [Open SWE](https://github.com/langchain-ai/open-swe)

- Claude Code:
  - Agentic coding tool living in terminal/IDE; understands codebase, executes routine tasks, handles git workflows via natural language.
  - Emphasizes local developer loop (edits, explains, runs commands, manages branches/PRs) with light setup.
  - Source: [Claude Code](https://github.com/anthropics/claude-code)

- Our kernel (current state):
  - Minimal tool layer focused on Rust project: FileTools, CommandTools (cargo), CodebaseTools, simple planning/implementation/testing/review loop, optional LLM.
  - Constitutional features (EoI navigation, reflections), but limited persistence, limited git/GitHub integration, and minimal editor/diff ergonomics.

## 2) Functional capabilities (by category)

### A. Planning and human-in-the-loop
- Open SWE:
  - Dedicated planning step; user can accept/edit/reject plan before execution; plans can be triggered from UI or by GitHub label.
  - Parallel execution of tasks in sandboxed environments; end-to-end task lifecycle (issue → PR).
- Claude Code:
  - Interactive terminal/IDE loop; accepts natural language commands; supports iterative refinement; can manage git workflows.
- Our kernel:
  - Simple planning phase; no explicit plan-approval checkpoint; no UI/IDE integration; single-task, single-threaded loop.

Key gap for our kernel: explicit plan object with approval/edit hooks; resumable runs; conversational checkpoints.

### B. Codebase understanding & navigation
- Open SWE:
  - LangGraph-based orchestration; repository-level reasoning; multi-file edits; context routing across steps.
- Claude Code:
  - Strong local codebase understanding with commands to search, modify, and explain; supports multi-file workflows.
- Our kernel:
  - Basic file listing and substring search; relevance search is keyword-based; no structured semantic search or code map; limited multi-file coordination.

Key gap for our kernel: robust code search (regex and semantic), workspace map/index, cross-file dependency awareness, and edit orchestration.

### C. Editing model (diffs, patches, AST)
- Open SWE:
  - Multi-file edits, PR creation; typically works via planned steps that apply changes and validate.
- Claude Code:
  - Comfortable issuing diffs/edits; manages staged changes, commits, and branch flows.
- Our kernel:
  - Read/overwrite whole files; single-string replacement; no patch/diff abstraction; no AST-safe edits.

Key gap for our kernel: patch/diff abstraction (line-hunks), file create/move/delete, AST-assisted edits for common languages, and conflict-safe apply.

### D. Command execution & toolchain
- Open SWE:
  - Executes commands/tests in sandbox; can run validations and formatting before PRs.
- Claude Code:
  - Runs commands/tests locally; integrates with git flows; supports iterative run-fix cycles.
- Our kernel:
  - Runs `cargo check/test/build`; generic `run_command`; no language-agnostic adapters, no test discovery/unified reporting, limited timeouts/retries.

Key gap for our kernel: language-agnostic adapters (JS/TS, Python, Rust), test discovery/report unification, retry/backoff policies, and lint/format hooks.

### E. Git & GitHub integration (issues/PRs/boards)
- Open SWE:
  - Creates GitHub issues and PRs automatically; can close issues upon completion.
- Claude Code:
  - Manages git branches/commits/PRs; designed to integrate with GitHub repo flows.
- Our kernel:
  - Has helper shell scripts for Projects v2, but no embedded git client, no commit/branch orchestration API, no PR creation, no review loops.

Key gap for our kernel: built-in git operations (status, branch, commit, rebase), PR creation/update/comments, and minimal Projects v2 affordances.

### F. Execution model (parallelism, sandboxing, resumability)
- Open SWE:
  - Parallel tasks; cloud sandbox per task; resilient execution; resumable state.
- Claude Code:
  - Single-user interactive loop; resilient to local environment; quick iteration.
- Our kernel:
  - Single task, single process; no resumability snapshot; no sandbox/container orchestration.

Key gap for our kernel: run state persistence (checkpointing), resumable workflows, optional containerized runs for isolation.

### G. Observability, cost, and safety
- Open SWE:
  - End-to-end task management visibility; UI provides plan/status; PRs as artifacts.
- Claude Code:
  - Terminal/IDE transcripts; integrates with git history; explicit commands and diffs.
- Our kernel:
  - Reflection log and stdout capture; no structured run logs/metrics; no cost tracking; limited safety rails.

Key gap for our kernel: structured run logs, per-run IDs, token/cost budgets, guardrails (write-scopes, file allowlists), and dry-run support.

## 3) Minimum viable kernel to replicate Cursor-like experience

Goal: Enable multi-hour/day iterative development with human steering, on our terms, before considering deeper framework adoption.

Proposed minimal capability checklist:

1) Planning & checkpoints
   - Plan object with steps, rationale, and acceptance gates (approve/edit/reject).
   - Resumable runs with persisted state (run ID, mode, EoI, step index, artifacts).

2) Code search & index
   - Regex and subtree search; basic semantic/code-symbol search (pluggable backends).
   - Workspace index (files, modules, tests, ownership hints) with quick filters.

3) Editing ergonomics
   - Patch/diff API (hunk-based), file create/move/delete, multi-file apply, preview/dry-run.
   - Optional AST-assisted edits for Rust, Python, and JS/TS (incremental).

4) Commands & validations
   - Language adapters: Rust (cargo), Python (pytest/ruff/black), JS/TS (pnpm/yarn, vitest/jest, eslint/prettier).
   - Unified test runner interface with parsed results and short summaries.

5) Git/GitHub workflow (thin layer)
   - Git operations: status/branch/commit/stash/rebase; patch staging.
   - PR lifecycle: create/update description, link to issue, request review.
   - Optional: Projects v2 status update helper.

6) Human-in-the-loop controls
   - Checkpoints for plan, risky edits, large diffs; quick accept/decline or inline nudge.
   - Run transcript and change summary outputs suitable for posting to issues/PRs.

7) Observability & safety
   - Per-run log with steps, commands, outputs (truncated), diffs, metrics (tokens/time).
   - Write-scope guard (allowed paths), env-sanitization, dry-run mode.

8) Constitutional features (our differentiator)
   - EoI navigation hooks influence plan and context selection.
   - Tiered ISO/IEEE context loading (Base/Reflection/Deep Dive) triggered by mode/viewpoint.

## 4) Where our kernel stands today

Strengths:
- Simple, readable tool layer; quick to extend.
- LLM integration defaulting to cost-efficient models.
- Constitutional scaffolding (EoI, reflections) already present.

Primary gaps vs Open SWE / Claude Code:
- No plan approval loop; minimal persistence/resume.
- Limited search/index; no semantic or symbol-level navigation.
- No patch/diff model; no AST edits; limited multi-file coordination.
- Limited git/PR integration; helper scripts exist but not integrated as first-class APIs.
- Single-task execution; no sandboxing; no robust retry/backoff.
- Sparse observability; no token/cost budgets or guardrails.

## 5) Focused next steps (incremental roadmap)

Phase A (Minimum viable loop)
1. Add plan object + approval checkpoint; persist run state (JSON per run ID).
2. Introduce patch/diff API (apply/preview), multi-file support, and dry-run.
3. Add language adapters (Rust, Python, JS/TS) with unified test runner output.
4. Implement basic git ops and PR creation (commit/branch/PR describe and link).

Phase B (Navigation & context)
5. Lightweight workspace index + regex/symbol search; surface top-K relevant files.
6. Tiered ISO/IEEE loader + viewpoint triggers; wire to plan/context assembly.

Phase C (Observability & safety)
7. Per-run logs/metrics (tokens/time/steps), redaction, write-scope allowlist.
8. Simple retry/backoff, error classification, and checkpoint recovery.

These steps keep the kernel minimal and composable, while closing the critical gaps observed in
Open SWE ([link](https://github.com/langchain-ai/open-swe)) and Claude Code ([link](https://github.com/anthropics/claude-code)).

## 6) Decision posture

- Build the minimal kernel first, measured against one real feature change end-to-end.
- If gaps remain large after Phase B, reevaluate adopting or interoperating with
  Open SWE or Claude Code as execution backends while preserving our constitutional layer.


