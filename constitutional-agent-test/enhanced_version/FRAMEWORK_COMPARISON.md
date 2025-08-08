# Agent Framework Comparison: Open SWE vs Claude Code vs Our Kernel

This document compares core capabilities of two reference implementations and our current minimal kernel, with a focus on the smallest viable feature set needed to replicate a Cursor-like, human-in-the-loop development experience.

References:
- Open SWE (LangGraph-based) — [github.com/langchain-ai/open-swe](https://github.com/langchain-ai/open-swe)
- Claude Code (terminal/IDE agent) — [github.com/anthropics/claude-code](https://github.com/anthropics/claude-code)

## 1) Scope for MVP (autonomous loop, small features)

- Agent runs primarily unattended in short runs that validate task-tree navigation and directional correctness.
- Human-in-the-loop UX and PR flows can come later.
- Focus now: codebase understanding/navigation, edit ergonomics, Rust-first commands, strong git, frequent pushes.

## 2) Functional capabilities (by category)

### A. Planning (lightweight)
- Small plan with steps and rationale is sufficient for MVP.
- Optional: persist run state (ID/current step) later if needed; no UI/approval gates required now.

### B. Codebase understanding & navigation (expand)
- What others provide
  - Open SWE: Repository-scale reasoning, multi-file change planning, step-wise context routing across planning/execution; strong file targeting via planners. [link](https://github.com/langchain-ai/open-swe)
  - Claude Code: Local repo awareness; fast search/explain/edit loops; multi-file edits driven by natural language; good heuristics for where to change. [link](https://github.com/anthropics/claude-code)
- What we need for MVP parity-feel
  - Regex and structural search: file-glob filters, regex, multi-file hits with surrounding context.
  - Semantic/code-symbol search (pluggable): function/class symbol lookup; simple embedding-based nearest neighbors for code blocks/comments (opt-in backend).
  - Workspace map/index (definition): an in-memory index capturing
    - Files → language/type; modules/packages; tests mapping
    - Symbols table (defs/refs where feasible), import graph per language
    - Ownership hints (dirs → subsystems), common entry points (main, bin, tests)
  - Cross-file dependency awareness: follow imports/uses to pull adjacent files into context automatically.
  - Edit orchestration:
    - For each proposed change: identify impacted files via search + dependency walk
    - Order edits deterministically (interfaces before impls/tests)
    - Generate a single consolidated diff across files, preview/dry-run, then apply.
  - Rust-first practicality:
    - Parse Cargo.toml to understand crates/bins/tests
    - Map src/lib.rs, src/main.rs, and module trees; associate tests in tests/ and mod tests.

Result: users can speak at a higher abstraction ("update progression system API and corresponding tests"), and the agent locates, edits, and validates across relevant files reliably.

### C. Editing model (expand)
- Needed capabilities
  - Patch/diff abstraction: hunk-based edits with context lines; multi-file batch apply; preview/dry-run.
  - File ops: create/move/delete; header/boilerplate insertion; license headers.
  - Conflict-safe apply: rebase-aware 3-way merging when upstream changes occur; fallback to minimal-context retries.
  - AST-assisted edits (language-specific):
    - Rust focus for MVP: leverage rust-analyzer or tree-sitter for safe inserts/renames; run rustfmt post-edit.
    - Surface planned edits as semantic ops when possible (rename symbol, add function, modify signature) then render to text.
  - Multi-file coordination: transactional apply (all-or-nothing), with rollback via git if validation fails.

Contrast to current kernel: today we overwrite whole files or do single replacement. We need an edit engine with hunks and Rust-centric AST helpers to feel “Claude/Open SWE-like.”

### D. Command execution & toolchain (Rust-first, extensible)
- MVP approach
  - Language adapter interface: build(), test(), fmt(), optional lint(), with stdout/stderr parsing to short summaries.
  - Implement Rust adapter now: cargo check/test/build, rustfmt; basic error pattern extraction.
  - Defer sandboxing; rely on Codespaces environment; rely on git to revert bad changes.
  - Design for easy addition of Python adapter next (pytest/ruff/black), then JS/TS.

### E. Git integration (strong VCS; minimal GitHub)
- Requirements
  - Frequent, small commits with clear messages; branch hygiene (feature branches per task tree leaf).
  - Ops: status/diff, add/restore, commit, stash, rebase, reset, tag snapshots.
  - Push often to remote; GitHub integration limited to push for now (no PR orchestration needed).
  - Provide quick rollback to last green commit.

### F. Execution model (deprioritized)
- Parallelism, sandboxing, and resumability are out-of-scope for MVP. Optional snapshotting via git tags or lightweight run state can be added later if needed.

### G. Observability and safety (later)
- Nice-to-have after first successful run: per-run logs (ID, steps, commands, diffs), write-scope allowlist, and dry-run support.

## 3) Minimum viable kernel for autonomous MVP

Goal: Enable multi-hour/day iterative development autonomously on small features before deeper framework adoption.

Proposed minimal capability checklist:

1) Planning (light)
   - Small plan object with steps and rationale; optional persisted run ID/state later.

2) Code search & index (critical)
   - Regex/substring search with file globs and context; semantic/symbol search (pluggable).
   - Workspace index: files→modules/tests, symbol table, import graph, ownership hints.

3) Editing ergonomics (critical)
   - Patch/diff hunk API, multi-file transactional apply, preview/dry-run, rollback via git.
   - AST-assisted edits (Rust first: rust-analyzer/tree-sitter; rustfmt after edits).

4) Commands & validations (Rust-first)
   - Rust adapter now (cargo check/test/build, rustfmt); design interface for Python/JS next.
   - Parse outputs to short, actionable summaries.

5) Git workflow (strong)
   - Git ops: status/diff/add/restore/commit/stash/rebase/reset; frequent pushes.
   - No PR flows required for MVP.

6) Human controls
   - Not required for MVP beyond basic safety prompts if desired.

7) Observability & safety
   - Optional initial run; add structured logs/guards after first end-to-end success.

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
1. Implement code search/index (regex + workspace map + basic symbols); wire into planning.
2. Introduce patch/diff engine (preview/dry-run), multi-file transactional apply, rollback via git.
3. Add Rust adapter (cargo check/test/build, rustfmt); short error summaries.
4. Implement strong git operations and frequent push.

Phase B (Navigation & context)
5. Enhance semantic/symbol search; improve dependency walking and impacted-file selection.
6. Tiered ISO/IEEE loader + viewpoint triggers; integrate with plan/context assembly.

Phase C (Observability & safety)
7. Per-run logs/metrics, write-scope allowlist, minimal retry/backoff.

These steps keep the kernel minimal and composable, while closing the critical gaps observed in
Open SWE ([link](https://github.com/langchain-ai/open-swe)) and Claude Code ([link](https://github.com/anthropics/claude-code)).

## 6) Decision posture

- Build the minimal kernel first, measured against one real feature change end-to-end.
- If gaps remain large after Phase B, reevaluate adopting or interoperating with
  Open SWE or Claude Code as execution backends while preserving our constitutional layer.


