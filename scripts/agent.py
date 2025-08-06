"""Minimal Constitutional Agent skeleton (Ticket #68)

This script will be used inside GitHub Codespaces to iterate over tasks and
manipulate the vox2 repository.  It currently provides only the core structure
outlined in the ticket and will be expanded incrementally.
"""

from __future__ import annotations

import json
import pathlib
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List

from rich.console import Console
from rich.table import Table

# Optional imports guarded for now (Claude / Anthropic not installed locally)
try:
    import anthropic  # type: ignore
except ImportError:  # pragma: no cover
    anthropic = None  # type: ignore

ROOT = pathlib.Path(__file__).resolve().parent.parent
CONTEXT_PATH = ROOT / "context.json"

console = Console()

# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class AgentContext:
    """Runtime context persisted to disk between cycles."""

    L1_agent: str = "Constitutional Task Agent v1"
    L2_coordination: str = "GitHub Project Board"
    L3_product: str = "vox2"
    L4_feature: str = "initial"
    L5_task: str = "bootstrap"
    task_tree: str = ""
    mode: str = "execution"  # or "constitutional"
    memory: List[str] = field(default_factory=list)

    @classmethod
    def load(cls) -> "AgentContext":
        if CONTEXT_PATH.exists():
            data = json.loads(CONTEXT_PATH.read_text())
            return cls(**data)
        return cls()

    def save(self) -> None:
        CONTEXT_PATH.write_text(json.dumps(self.__dict__, indent=2))


@dataclass
class ConstitutionalAgent:
    """Core agent loop following Ticket #68 minimal spec."""

    context: AgentContext

    def run_cycle(self) -> None:
        console.rule("[bold green]New Cycle")
        self.show_context()
        response = self.call_llm(self.build_prompt())
        self.parse_and_act(response)
        self.context.save()

    # ---------------------------- internals ---------------------------------

    def build_prompt(self) -> str:
        # TODO: Load constitutional system prompt template, inject context
        return "(Stub prompt with context placeholders)"

    def call_llm(self, prompt: str) -> str:
        if anthropic is None:
            console.print("[yellow]Anthropic SDK not installed. Returning stub response.")
            return "STUB_RESPONSE: no-api"
        client = anthropic.Anthropic()
        # NOTE: Anthropic's new SDK uses messages API; update when integrating
        message = client.messages.create(
            model="claude-3-sonnet-20240229",
            max_tokens=512,
            messages=[{"role": "user", "content": prompt}],
        )
        return message.content[0].text  # type: ignore

    def parse_and_act(self, llm_response: str) -> None:
        # TODO: Parse the response JSON/markdown and perform actions
        console.print("[blue]LLM Response:\n", llm_response)
        # Example: switch mode every cycle as placeholder
        self.context.mode = "constitutional" if self.context.mode == "execution" else "execution"

    # ---------------------------- utilities ----------------------------------

    def show_context(self) -> None:
        table = Table(title="Agent Context")
        for key, value in self.context.__dict__.items():
            table.add_row(key, str(value))
        console.print(table)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    context = AgentContext.load()
    agent = ConstitutionalAgent(context)

    cycles = 3  # For initial smoke-test; switch to while True for full loop
    for _ in range(cycles):
        agent.run_cycle()
        time.sleep(1)


if __name__ == "__main__":
    main()
