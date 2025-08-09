from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional


def _run(cmd: List[str], cwd: Optional[str] = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        cmd, cwd=cwd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )


@dataclass
class GitCommandResult:
    returncode: int
    stdout: str
    stderr: str


class GitClient:
    """Minimal Git client for MVP.

    Provides a small set of operations and returns structured results.
    """

    def __init__(self, repo_root: str):
        self.repo_root = str(Path(repo_root).resolve())

    def _git(self, *args: str) -> GitCommandResult:
        completed = _run(["git", *args], cwd=self.repo_root)
        return GitCommandResult(completed.returncode, completed.stdout, completed.stderr)

    def current_branch(self) -> Optional[str]:
        result = self._git("rev-parse", "--abbrev-ref", "HEAD")
        return result.stdout.strip() if result.returncode == 0 else None

    def status_porcelain(self) -> str:
        return self._git("status", "--porcelain").stdout

    def add_all(self) -> GitCommandResult:
        return self._git("add", "-A")

    def commit(self, message: str) -> GitCommandResult:
        return self._git("commit", "-m", message)

    def push_current_branch(self) -> GitCommandResult:
        branch = self.current_branch()
        if not branch:
            return GitCommandResult(1, "", "Failed to discover current branch")
        return self._git("push", "-u", "origin", branch)

    def create_or_checkout_branch(self, branch_name: str) -> GitCommandResult:
        checkout = self._git("checkout", branch_name)
        if checkout.returncode == 0:
            return checkout
        return self._git("checkout", "-b", branch_name)


