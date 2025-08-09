"""Executive Worker MVP package.

Provides a minimal execution-centric agent capable of:
- Navigating a codebase
- Making multi-file edits
- Running shell build/test commands
- Committing changes with Git

This package is intentionally small and focused per the MVP spec.
"""

from .shell_runner import ShellRunner
from .codebase_utils import CodebaseUtilities
from .git_client import GitClient
from .task_tree import TaskTree
from .ticket import Ticket
from .agent import ExecutiveAgent
from .llm_client import LLMInterface, OpenAIChatLLM

__all__ = [
    "ShellRunner",
    "CodebaseUtilities",
    "GitClient",
    "TaskTree",
    "Ticket",
    "ExecutiveAgent",
    "LLMInterface",
    "OpenAIChatLLM",
]

__version__ = "0.1.0"


