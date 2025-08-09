from __future__ import annotations

from typing import List

from .shell_runner import ShellRunner


class GitOps:
    def __init__(self, shell: ShellRunner) -> None:
        self.shell = shell

    def status(self) -> str:
        return self.shell.run("git status --porcelain").stdout

    def add_all(self) -> None:
        self.shell.run("git add -A")

    def commit(self, message: str) -> str:
        res = self.shell.run(f"git commit -m {self._q(message)}")
        return res.stdout + res.stderr

    def current_branch(self) -> str:
        return self.shell.run("git rev-parse --abbrev-ref HEAD").stdout.strip()

    def push(self, set_upstream: bool = False) -> str:
        if set_upstream:
            branch = self.current_branch()
            res = self.shell.run(f"git push -u origin {branch}")
        else:
            res = self.shell.run("git push")
        return res.stdout + res.stderr

    def _q(self, s: str) -> str:
        return '"' + s.replace('"', '\\"') + '"'
