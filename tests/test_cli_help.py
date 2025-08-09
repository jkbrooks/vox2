import os
import subprocess
from pathlib import Path


def test_cli_help_runs_successfully():
    repo_root = Path(__file__).resolve().parents[1]
    env = os.environ.copy()
    result = subprocess.run(
        ["python", "scripts/run_executive_worker.py", "--help"],
        cwd=str(repo_root),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert "Executive Worker MVP CLI" in result.stdout

