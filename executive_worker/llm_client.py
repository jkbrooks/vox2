from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional

from .ticket import Ticket


class LLMInterface:
    """Abstract interface for an LLM client."""

    def generate_plan(self, *, ticket: Ticket, repo_context: Optional[str] = None) -> str:  # pragma: no cover - interface only
        raise NotImplementedError


@dataclass
class OpenAIChatLLM(LLMInterface):
    """Minimal OpenAI chat-based LLM client.

    Usage requires OPENAI_API_KEY to be present in the environment unless an explicit
    api_key is provided to the constructor.
    """

    model: str = "gpt-4o-mini"
    temperature: float = 0.2
    max_tokens: int = 700
    api_key: Optional[str] = None

    def _resolve_api_key(self) -> str:
        key = self.api_key or os.environ.get("OPENAI_API_KEY")
        if not key:
            raise ValueError(
                "OPENAI_API_KEY is not set; provide api_key to OpenAIChatLLM or set the env var"
            )
        return key

    def generate_plan(self, *, ticket: Ticket, repo_context: Optional[str] = None) -> str:
        # Lazy import so that tests can run without the SDK installed if unused
        try:
            from openai import OpenAI  # type: ignore
        except Exception as exc:  # pragma: no cover - import error branch is environment-dependent
            raise RuntimeError(
                "The 'openai' package is required. Add it to requirements and install."
            ) from exc

        client = OpenAI(api_key=self._resolve_api_key())

        system_prompt = (
            "You are an Executive Worker coding agent."
            " Generate a concise plan (steps) to address the provided ticket in this repository."
            " Keep steps small and executable. Do not write code, only the plan."
        )

        user_prompt = f"""
Ticket: #{ticket.id} - {ticket.title}

Summary:
{ticket.body[:2000]}

Repo Context (optional, may be empty):
{(repo_context or '')[:2000]}

Deliver: 5-10 concise steps with rationale when useful.
"""

        response = client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=self.temperature,
            max_tokens=self.max_tokens,
        )
        content = response.choices[0].message.content or ""
        return content.strip()


