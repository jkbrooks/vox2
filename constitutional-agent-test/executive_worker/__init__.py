"""Executive Worker MVP package.

This package contains a minimal, execution‑centric agent implementation
with:
- ShellRunner for arbitrary commands
- Codebase utilities (search/index skeleton)
- Edit engine (transactional apply skeleton)
- Git ops via shell
- LLM client (OpenAI) for immediate planning integration
"""

__all__ = [
    "agent",
    "shell_runner",
    "codebase_utils",
    "edit_engine",
    "git_ops",
    "llm_client",
    "models",
]
