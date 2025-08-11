from __future__ import annotations

import os
import shlex
import subprocess
import time
from typing import Dict, Optional

from .models import CommandResult


class ShellRunner:
    def __init__(self, cwd: str) -> None:
        self.cwd = cwd

    def run(self, cmd: str, env: Optional[Dict[str, str]] = None, timeout: Optional[int] = None) -> CommandResult:
        start = time.time()
        merged_env = os.environ.copy()
        if env:
            merged_env.update(env)
        try:
            # Handle compound shell commands with && or ||
            if any(op in cmd for op in ['&&', '||', ';', '|']):
                # Use shell=True for compound commands
                proc = subprocess.run(
                    cmd,
                    cwd=self.cwd,
                    env=merged_env,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    timeout=timeout,
                    text=True,
                    shell=True,
                )
            else:
                # Use shell=False for simple commands
                proc = subprocess.run(
                    cmd if isinstance(cmd, list) else shlex.split(cmd),
                    cwd=self.cwd,
                    env=merged_env,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    timeout=timeout,
                    text=True,
                )
            end = time.time()
            return CommandResult(
                cmd=cmd,
                exit_code=proc.returncode,
                stdout=proc.stdout,
                stderr=proc.stderr,
                duration_ms=int((end - start) * 1000),
            )
        except subprocess.TimeoutExpired as ex:
            end = time.time()
            return CommandResult(
                cmd=cmd,
                exit_code=-1,
                stdout=ex.stdout or "",
                stderr=(ex.stderr or "") + "\nTIMEOUT",
                duration_ms=int((end - start) * 1000),
            )
