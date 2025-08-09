Update on agentic repos evaluation:

- Renamed branch to `research/agentic-coding-repos-eval` and pushed.
- Reviewed these repos against our MVP focus (codebase understanding, editing, commands/toolchain, git):
  - Aider: strong multi-file edit ergonomics and auto-commit flow; use as editing/git quality bar. [Aider](https://github.com/Aider-AI/aider)
  - OpenHands: containerized ShellRunner and headless/CLI patterns; emulate for command execution. [OpenHands](https://github.com/All-Hands-AI/OpenHands)
  - dyad: native git + isomorphic-git fallback; useful revert staging. [dyad](https://github.com/dyad-sh/dyad)
  - claude-flow: safe GitHub CLI wrapper + backup/rollback manager; borrow for safety/rollback. [claude-flow](https://github.com/ruvnet/claude-flow)
  - Open SWE: planner-driven file targeting; ideas for impacted-file selection. [Open SWE](https://github.com/langchain-ai/open-swe)
  - Cline: checkpoint/restore UX pattern; good safety bar. [Cline](https://github.com/cline/cline)
  - LlamaCoder: artifact demo UX; not directly relevant to kernel. [LlamaCoder](https://github.com/nutlope/llamacoder)
- Created a concise borrowables doc capturing what crosses our bar and what to copy now:
  - `docs/research/agentic-repos-borrowables.md` (in vox2) — permalink to branch: https://github.com/jkbrooks/vox2/blob/research/agentic-coding-repos-eval/docs/research/agentic-repos-borrowables.md

Decision posture:
- Don’t chase parity with any single repo. Borrow best-in-class pieces and build our own kernel:
  - Editing: implement transactional hunk engine (Aider as the quality bar) with rollback.
  - Commands: adopt OpenHands-like ShellRunner ergonomics (timeouts, background, env/container), with deny/allow list.
  - Git: auto-commit small steps (Aider), native+isomorphic-git fallback (dyad), safe gh wrapper + backups (claude-flow/Cline).
  - Understanding: regex + workspace map + basic symbols now; aim toward Aider-like “code map” performance.

Branch: `research/agentic-coding-repos-eval`.
