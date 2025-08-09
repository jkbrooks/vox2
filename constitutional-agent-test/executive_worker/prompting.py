from __future__ import annotations

import os
from typing import Optional, Dict


ISO_PATH = os.path.join("scrap", "ISO-IEEE-42010-Architecture-Description.md")
CONSTITUTIONAL_PROMPT_PATH = os.path.join(
    "constitutional-agent-test", "_archive", "prompts", "constitutional_system_prompt.md"
)


def _read_text(path: str, max_chars: Optional[int] = None) -> str:
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            text = f.read()
            if max_chars is not None and len(text) > max_chars:
                return text[:max_chars]
            return text
    except Exception:
        return ""


def load_iso_42010_eoi_excerpt(workspace_root: str) -> str:
    """Extract the EoI definition section from the ISO/IEEE 42010 doc if available.

    We search for the "3.12 entity of interest" heading and return a short excerpt
    to prime the LLM on the formal definition, avoiding huge prompts.
    """
    path = os.path.join(workspace_root, ISO_PATH)
    text = _read_text(path, max_chars=100_000)
    if not text:
        return ""
    lower = text.lower()
    start = lower.find("3.12 entity of interest")
    if start == -1:
        start = lower.find("**3.12 entity of interest**")
    if start == -1:
        return ""
    # Grab until the next numbered definition or next heading markers
    end_markers = ["\n**3.13 ", "\n3.13 ", "\n##", "\n###"]
    end = len(text)
    for m in end_markers:
        idx = text.find(m, start + 1)
        if idx != -1:
            end = min(end, idx)
    excerpt = text[start:end].strip()
    # Trim to a reasonable length
    if len(excerpt) > 1200:
        excerpt = excerpt[:1200] + "\n..."
    return excerpt


def load_constitutional_prompt_excerpt(workspace_root: str) -> str:
    """Load curated excerpt from the prior constitutional prompt for expectations/context."""
    path = os.path.join(workspace_root, CONSTITUTIONAL_PROMPT_PATH)
    text = _read_text(path, max_chars=20_000)
    if not text:
        return ""
    # Keep a compact subset: identity/context headers, EoI section, stakeholder+concern, viewpoints.
    keep_sections = [
        "## Your Identity and Context",
        "### Fundamental Concepts",
        "### Stakeholder Framework",
        "### Viewpoint and View System",
        "## Task Tree Awareness",
        "## Mode Switching Triggers",
    ]
    lines = text.splitlines()
    selected: list[str] = []
    include = False
    current_header = None
    for line in lines:
        if line.startswith("#"):
            current_header = line.strip()
            include = any(h in current_header for h in keep_sections)
        if include:
            selected.append(line)
    excerpt = "\n".join(selected)
    if len(excerpt) > 2000:
        excerpt = excerpt[:2000] + "\n..."
    return excerpt


def compose_system_prompt(
    *,
    ticket: Dict[str, str],
    eoi: Optional[Dict[str, str]],
    task_tree_snapshot: Dict[str, str],
    workspace_summary: str,
    iso_eoi_excerpt: str,
    constitutional_excerpt: str,
) -> str:
    """Compose a richer system prompt including ISO/IEEE 42010 context and prior guidance.

    ticket: {id, title, description}
    eoi: optional {label, path}
    task_tree_snapshot: {id, title}
    workspace_summary: short stats and notable hints
    """
    parts: list[str] = []
    parts.append("You are the Executive Worker planner.")
    parts.append("Follow ISO/IEC/IEEE 42010 notions for EoI and viewpoints when focusing attention.")

    parts.append("\n[TICKET]")
    parts.append(f"id: {ticket.get('id')}\ntitle: {ticket.get('title')}\ndescription: {ticket.get('description')}")

    parts.append("\n[CURRENT_EOI]")
    parts.append(str(eoi or {}))

    parts.append("\n[TASK_TREE]")
    parts.append(str(task_tree_snapshot))

    parts.append("\n[WORKSPACE_SUMMARY]")
    parts.append(workspace_summary)

    if iso_eoi_excerpt:
        parts.append("\n[ISO_42010_EOI_EXCERPT]")
        parts.append(iso_eoi_excerpt)

    if constitutional_excerpt:
        parts.append("\n[CONSTITUTIONAL_PROMPT_EXCERPT]")
        parts.append(constitutional_excerpt)

    parts.append(
        "\n[INSTRUCTIONS]\n"
        "1) If CURRENT_EOI is empty or suboptimal, select a better EOI (entity of interest) for this cycle.\n"
        "2) Produce a short, executable plan as a JSON list of steps: [{description, kind, args}] with kinds in {search, edit, shell, git, validate}.\n"
        "3) Keep the plan compact and grounded in files and commands relevant to the chosen EOI."
    )

    return "\n".join(parts)
