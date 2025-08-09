from __future__ import annotations

import os
import subprocess
import time
from dataclasses import dataclass
from typing import Dict, Optional


@dataclass
class ShellResult:
    success: bool
    exit_code: int
    stdout: str
    stderr: str
    duration_ms: int
    command: str
    cwd: str


class ShellRunner:
    """Execute shell commands with controlled environment and capture outputs.

    The runner is intentionally simple for MVP: executes a command string using
    the system shell, honors a working directory, and returns a structured
    result with timing.
    """

    def __init__(self, cwd: Optional[str] = None):
        self.default_cwd = cwd or os.getcwd()

    def run(
        self,
        command: str,
        *,
        cwd: Optional[str] = None,
        env_overrides: Optional[Dict[str, str]] = None,
        timeout: Optional[int] = None,
    ) -> ShellResult:
        start_time = time.time()
        effective_cwd = cwd or self.default_cwd
        env = os.environ.copy()
        if env_overrides:
            env.update(env_overrides)

        completed = subprocess.run(
            command,
            cwd=effective_cwd,
            env=env,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
            text=True,
        )

        duration_ms = int((time.time() - start_time) * 1000)
        return ShellResult(
            success=completed.returncode == 0,
            exit_code=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
            duration_ms=duration_ms,
            command=command,
            cwd=effective_cwd,
        )


