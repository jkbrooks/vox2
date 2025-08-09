from __future__ import annotations

import os
from typing import List

from .models import PlanStep, Task

try:
    from openai import OpenAI  # type: ignore
except Exception:  # pragma: no cover
    OpenAI = None  # type: ignore


SYSTEM_PROMPT = (
    "You are the Executive Worker planner. Given a task, produce a small plan "
    "with steps of kinds: search | edit | shell | git | validate. Keep it short and executable."
)


class LLMClient:
    def __init__(self, model: str = "gpt-4o-mini") -> None:
        api_key = os.getenv("OPENAI_API_KEY", "")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY not set in environment")
        if OpenAI is None:
            raise RuntimeError("openai package not available. Install openai>=1.0.0")
        self.client = OpenAI(api_key=api_key)
        self.model = model

    def _chat_json_list(self, system_prompt: str, user_prompt: str) -> List[PlanStep]:
        resp = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.2,
        )
        content = resp.choices[0].message.content or "[]"
        import json

        try:
            raw = json.loads(content)
        except Exception:
            raw = []
        steps: List[PlanStep] = []
        for item in raw:
            if not isinstance(item, dict):
                continue
            steps.append(
                PlanStep(
                    description=str(item.get("description", "")),
                    kind=str(item.get("kind", "shell")),
                    args=item.get("args", {}) or {},
                )
            )
        return steps

    def create_plan(self, task: Task) -> List[PlanStep]:
        prompt = (
            f"Task ID: {task.task_id}\nTitle: {task.title}\nDescription: {task.description}\n"
            f"EOI: {task.eoi or {}}\n"
            "Return JSON list of steps as [{\"description\":str, \"kind\":str, \"args\":{}}]."
        )
        return self._chat_json_list(SYSTEM_PROMPT, prompt)

    def create_plan_from_prompt(self, prompt: str) -> List[PlanStep]:
        return self._chat_json_list(SYSTEM_PROMPT, prompt)
