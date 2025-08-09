from __future__ import annotations

from pathlib import Path

import click

from .agent import ExecutiveAgent
from .ticket import Ticket


@click.group()
def cli() -> None:
    """Executive Worker MVP CLI."""


@cli.command("run")
@click.option("--workspace-root", default=str(Path.cwd()), help="Workspace root path")
@click.option("--repo", required=True, help="GitHub repo (e.g., jkbrooks/personal_project_management)")
@click.option("--issue", type=int, required=True, help="GitHub issue number")
@click.option("--eoi", default=None, help="Optional Entity of Interest label")
def run_cmd(workspace_root: str, repo: str, issue: int, eoi: str | None) -> None:
    """Execute a single ticket end-to-end per MVP flow."""
    ticket = Ticket.from_github(repo, issue)
    agent = ExecutiveAgent(workspace_root)
    result = agent.execute_ticket(ticket, eoi=eoi)
    click.echo(f"Run complete. Artifacts: {result.run_json_path}")


def main() -> int:
    try:
        cli(standalone_mode=False)
    except click.ClickException as e:
        e.show()
        return 2
    except SystemExit as e:
        return int(e.code)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


