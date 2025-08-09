from __future__ import annotations

import os
from typing import List, Optional, Dict

from .models import PlanStep, Ticket

try:
    from openai import OpenAI  # type: ignore
except Exception:  # pragma: no cover
    OpenAI = None  # type: ignore


SYSTEM_PROMPT = (
    "You are the Executive Worker planner. Given a ticket, produce a small plan "
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

    def create_plan(self, ticket: Ticket) -> List[PlanStep]:
        prompt = (
            f"Ticket ID: {ticket.ticket_id}\nTitle: {ticket.title}\nDescription: {ticket.description}\n"
            f"EOI: {ticket.eoi or {}}\n"
            "Return JSON list of steps as [{\"description\":str, \"kind\":str, \"args\":{}}]."
        )
        return self._chat_json_list(SYSTEM_PROMPT, prompt)

    def create_plan_from_prompt(self, prompt: str) -> List[PlanStep]:
        return self._chat_json_list(SYSTEM_PROMPT, prompt)

    def choose_eoi(self, *, ticket: Ticket, candidates: List[str], iso_eoi_excerpt: str, guidance: str) -> Optional[Dict[str, str]]:
        """Ask the LLM to select the best EoI from candidate paths, optionally returning None.
        Returns {label, path} or None.
        """
        if not candidates:
            return ticket.eoi  # fallback
        cand_text = "\n".join(f"- {c}" for c in candidates[:25])
        user_prompt = (
            "You will choose an Entity of Interest (EoI) to focus planning.\n"
            f"Ticket: {ticket.ticket_id} — {ticket.title}\nDesc: {ticket.description}\n\n"
            "Candidates (file/class/module paths):\n" + cand_text + "\n\n"
            "ISO/IEEE 42010 EoI context:\n" + (iso_eoi_excerpt or "(none)") + "\n\n"
            "Guidance:\n" + guidance + "\n\n"
            "Return JSON: {label: str, path: str} or null if none is appropriate."
        )
        resp = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "Decide on an effective EoI for focused coding work."},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.1,
        )
        content = resp.choices[0].message.content or "null"
        import json

        try:
            obj = json.loads(content)
            if obj is None:
                return None
            if isinstance(obj, dict) and "path" in obj and "label" in obj:
                return {"label": str(obj["label"]), "path": str(obj["path"])}
        except Exception:
            pass
        return ticket.eoi
