import subprocess
from pathlib import Path

from executive_worker.git_client import GitClient


def test_git_client_basic_flow(tmp_path):
    repo_root = Path(tmp_path)
    subprocess.run(["git", "init"], cwd=repo_root, check=True, stdout=subprocess.PIPE)
    # Configure identity locally so commit works in fresh temp repo
    subprocess.run(["git", "config", "user.email", "tester@example.com"], cwd=repo_root, check=True)
    subprocess.run(["git", "config", "user.name", "Tester"], cwd=repo_root, check=True)
    (repo_root / "README.md").write_text("hello", encoding="utf-8")

    client = GitClient(str(repo_root))
    client.add_all()
    commit = client.commit("chore: initial commit")
    assert commit.returncode == 0

    status = client.status_porcelain().strip()
    assert status == ""

