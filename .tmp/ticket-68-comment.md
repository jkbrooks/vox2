Decision: Claude Code deobfuscation review — not aiming for parity.

What we like
- Clean subsystem boundaries and bootstrap flow (config, terminal, auth, AI, codebase, fileOps, execution, commands, telemetry).
- Strong execution environment: timeouts, maxBuffer, background processes, deny/allow lists.
- Practical file ops safety: path normalization and file-size caps.
- Simple analyzer and search CLI for quick wins.

What we don't like / gaps vs our needs
- No autonomous plan → execute → validate loop (CLI-first, not agent-first).
- Editing model is minimal (no hunk-based multi-file diffs, transactional apply, or AST-aware edits).
- Git integration is thin (generic shell wrapper, no orchestration).
- Search/index lacks symbol/semantic navigation and dependency walking.

What we may borrow later (not focus now)
- Execution safety patterns and API surface.
- Module boundaries/initialization structure.
- Basic analyzer/search approach, extended with our index + symbols.

Near-term focus
- Build MVP kernel: hunk-based edit engine with transactional multi-file apply + rollback; regex + workspace map + basic symbols; strong git client; Rust-first commands.

References
- Repo: [ghuntley/claude-code-source-code-deobfuscation](https://github.com/ghuntley/claude-code-source-code-deobfuscation/)
- Blog: [Tradecraft post](https://ghuntley.com/tradecraft/?utm_source=chatgpt.com)
