# Agentic Repos: Borrowable Features (Core MVP Focus)

Scope: What we can borrow as reference implementations or quality bars for four MVP areas: (1) codebase understanding, (2) editing, (3) command execution/toolchain, (4) Git integration.

## Aider
- Codebase understanding: Builds a map of the codebase to work on larger projects effectively (quality bar: high). Reference: https://github.com/Aider-AI/aider
- Editing: Proven terminal workflow; multi-file edits; integrates linting/tests post-edit (quality bar: high). Borrow patterns for hunk/diff flow and commit messages.
- Command execution/toolchain: Runs linters/tests automatically; good ergonomics to copy.
- Git integration: Auto-commits with sensible messages; strong baseline to emulate.

## OpenHands
- Codebase understanding: Not a deep symbol index, but practical scanning and agent context assembly.
- Editing: Not focused on a transactional diff engine.
- Command execution/toolchain: Strong containerized ShellRunner and headless/CLI modes (quality bar: high). Reference: https://github.com/All-Hands-AI/OpenHands
- Git integration: Indirect, via commands within sandbox.

## dyad
- Codebase understanding: App-centric; no code symbol index.
- Editing: Product-UI oriented; not a transactional diff engine.
- Command execution/toolchain: N/A.
- Git integration: Native git with fallback to isomorphic-git; revert staging flow (borrowable). Reference path: `src/ipc/utils/git_utils.ts` (local clone).

## claude-flow
- Codebase understanding: Orchestration-centric; no dedicated symbol index.
- Editing: Provides backup/rollback manager rather than diff engine; borrowable for safety. Reference path: `src/migration/rollback-manager.ts` (local clone).
- Command execution/toolchain: Robust GitHub CLI safety wrapper (timeouts, retries, allowlist). Borrowable. Reference path: `src/utils/github-cli-safety-wrapper.js`.
- Git integration: Via safe `gh` wrapper; good production hardening baseline. Reference: https://github.com/ruvnet/claude-flow

## Claude Code (deobfuscation)
- Codebase understanding: Basic analyzer (files/lines/deps); regex content search. OK baseline.
- Editing: Simple line-diff and naive patch write; below our bar.
- Command execution/toolchain: Solid execution env with safety filters (borrowable).
- Git integration: Thin wrapper around `git` command. Reference: https://github.com/ghuntley/claude-code-source-code-deobfuscation/

## Cline
- Codebase understanding: Strong IDE context flow; not a symbol index.
- Editing: File edits with human-in-the-loop; checkpoint/restore pattern (borrowable quality bar for safety UX). Reference: https://github.com/cline/cline
- Command execution/toolchain: Command execution integrated in approval loop.
- Git integration: Checkpoints complement git; design pattern to emulate for rollbacks.

## Open SWE
- Codebase understanding: Planning-driven file targeting; good ideas for impacted-file selection.
- Editing: Edits orchestrated via planned steps; not a purpose-built diff engine.
- Command execution/toolchain: Executes repo-specific commands via tools; decent baseline.
- Git integration: Integrated into planned execution; reference implementation ideas. Reference: https://github.com/langchain-ai/open-swe

## LlamaCoder
- Codebase understanding: Artifact/demo focus; not applicable.
- Editing: Sandboxed preview UX; not our kernel.
- Command execution/toolchain: N/A.
- Git integration: N/A. Reference: https://github.com/nutlope/llamacoder

---

## What crosses our quality bar now (per MVP focus)
- Editing (transactional multi-file + diffs): Aider is the closest real reference; use as quality bar. Build our own hunk-based engine to match or exceed.
- Command execution/toolchain: OpenHands’ containerized ShellRunner is a strong baseline to emulate.
- Git integration: Aider auto-commit flow for ergonomics; dyad’s native/isomorphic-git combo and claude-flow’s safe `gh` wrapper + rollback manager for safety and resilience.
- Codebase understanding: Aider’s “code map” as a bar for practical large-repo performance; combine with our regex + workspace map + basic symbols.

## Concrete borrow list for MVP
- Diff/edit engine: Emulate Aider’s multi-file diff/commit ergonomics and messages; implement our own transactional hunk apply with rollback.
- ShellRunner: Emulate OpenHands (timeouts, buffers, background, env, container option). Add deny/allow list like claude-flow.
- Git: 
  - Auto-commit small steps (Aider-style),
  - Safe `gh` wrapper (claude-flow) for PR/comments when needed,
  - Native git with `isomorphic-git` fallback (dyad),
  - Backup/rollback snapshots (claude-flow/Cline pattern).
- Codebase understanding:
  - Regex search + workspace map + basic symbol detection (our spec),
  - Borrow indexing heuristics from Aider as a quality target.

## Links
- Aider: https://github.com/Aider-AI/aider
- OpenHands: https://github.com/All-Hands-AI/OpenHands
- dyad: https://github.com/dyad-sh/dyad
- claude-flow: https://github.com/ruvnet/claude-flow
- Claude Code (deobf): https://github.com/ghuntley/claude-code-source-code-deobfuscation/
- Cline: https://github.com/cline/cline
- Open SWE: https://github.com/langchain-ai/open-swe
- LlamaCoder: https://github.com/nutlope/llamacoder


