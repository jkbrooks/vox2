from __future__ import annotations

from pathlib import Path

import click

from .agent import ExecutiveAgent
from .ticket import Ticket
from .llm_client import OpenAIChatLLM


@click.group()
def cli() -> None:
    """Executive Worker MVP CLI."""


@cli.command("run")
@click.option("--workspace-root", default=str(Path.cwd()), help="Workspace root path")
@click.option("--repo", required=True, help="GitHub repo (e.g., jkbrooks/personal_project_management)")
@click.option("--issue", type=int, required=True, help="GitHub issue number")
@click.option("--eoi", default=None, help="Optional Entity of Interest label")
@click.option("--use-llm/--no-llm", default=False, help="Enable LLM planning and execution")
@click.option("--model", default="gpt-4o-mini", help="OpenAI model (if --use-llm)")
@click.option("--temperature", default=0.2, type=float, help="OpenAI temperature (if --use-llm)")
@click.option("--max-tokens", default=700, type=int, help="OpenAI max tokens (if --use-llm)")
def run_cmd(
    workspace_root: str,
    repo: str,
    issue: int,
    eoi: str | None,
    use_llm: bool,
    model: str,
    temperature: float,
    max_tokens: int,
) -> None:
    """Execute a single ticket end-to-end per MVP flow."""
    ticket = Ticket.from_github(repo, issue)
    llm = OpenAIChatLLM(model=model, temperature=temperature, max_tokens=max_tokens) if use_llm else None
    agent = ExecutiveAgent(workspace_root, llm=llm)
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


