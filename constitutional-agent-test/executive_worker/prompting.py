from __future__ import annotations

import os
from typing import Optional, Dict


# Paths are resolved relative to the workspace root passed in
# ISO doc typically lives one directory up at repo root under scrap/
ISO_REL_PATHS = [
    os.path.join("..", "scrap", "ISO-IEEE-42010-Architecture-Description.md"),
    os.path.join("scrap", "ISO-IEEE-42010-Architecture-Description.md"),
]
CONSTITUTIONAL_PROMPT_REL_PATHS = [
    os.path.join("_archive", "prompts", "constitutional_system_prompt.md"),
    os.path.join("constitutional-agent-test", "_archive", "prompts", "constitutional_system_prompt.md"),
]


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
    text = ""
    for rel in ISO_REL_PATHS:
        path = os.path.join(workspace_root, rel)
        text = _read_text(path, max_chars=100_000)
        if text:
            break
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
    text = ""
    for rel in CONSTITUTIONAL_PROMPT_REL_PATHS:
        path = os.path.join(workspace_root, rel)
        text = _read_text(path, max_chars=20_000)
        if text:
            break
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
    deep_plan: Optional[Dict[str, str]] = None,
) -> str:
    """Compose a richer system prompt including ISO/IEEE 42010 context and prior guidance.

    ticket: {id, title, description}
    eoi: optional {label, path}
    task_tree_snapshot: {id, title}
    workspace_summary: short stats and notable hints
    """
    parts: list[str] = []
    parts.append("You are the Executive Worker planner with enhanced codebase understanding capabilities.")
    parts.append("Follow ISO/IEC/IEEE 42010 notions for EoI and viewpoints when focusing attention.")
    parts.append("Parse ticket requirements carefully and create concrete, actionable steps.")
    parts.append("You have access to semantic search, AST-aware editing, and intelligent error recovery.")
    parts.append("Use these enhanced capabilities to create more precise and effective plans.")

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

    if deep_plan:
        parts.append("\n[DEEP_PLANNING_CONTEXT]")
        parts.append(f"Requirements: {deep_plan.get('requirements', [])}")
        parts.append(f"Success Criteria: {deep_plan.get('success_criteria', [])}")
        parts.append(f"Identified Risks: {deep_plan.get('risks', [])}")
        parts.append(f"Strategy: {deep_plan.get('strategy', '')}")
        parts.append(f"Complexity: {deep_plan.get('estimated_complexity', 'unknown')}")

    parts.append(
        "\n[INSTRUCTIONS]\n"
        "IMPORTANT: Create COMPREHENSIVE plans that implement complete features in a single cycle.\n"
        "Modern LLMs can handle substantial multi-file changes - aim for 10-20+ steps per cycle.\n\n"
        "1) If CURRENT_EOI is empty or suboptimal, select a better EOI (entity of interest) for this cycle.\n"
        "2) Analyze the ticket description for ALL requirements - don't just do one small piece.\n"
        "3) Create a SUBSTANTIAL plan that implements a complete logical feature or major component.\n"
        "4) Produce a concrete, executable plan as a JSON list of steps: [{\"description\":str, \"kind\":str, \"args\":dict}]\n"
        "5) Available step kinds:\n"
        "   - search: {\"pattern\": str, \"globs\": [str], \"semantic\": bool, \"query\": str} - search for files/content\n"
        "     * Use semantic=true with query for meaning-based search (\"authentication logic\", \"error handling\")\n"
        "     * Use semantic=false with pattern for regex-based search\n"
        "   - edit: {\"edits\": [{\"path\": str, \"find\": str, \"replace\": str}], \"message\": str, \"edit_type\": str} - edit files\n"
        "     * edit_type options: \"basic\" (default), \"ast\" (syntax-aware), \"rename\" (symbol renaming), \"refactor\"\n"
        "     * For rename: include \"old_name\": str, \"new_name\": str, \"scope\": \"global|local\"\n"
        "     * MAKE SUBSTANTIAL EDITS - add complete functions, structs, modules, not just 1-2 lines\n"
        "   - shell: {\"cmd\": str} - run shell commands (mkdir, touch, etc.) with auto-recovery on errors\n"
        "   - git: {\"action\": \"status|push\"} - git operations\n"
        "   - validate: {\"cmd\": str} - validation commands with intelligent error analysis\n"
        "6) For file creation: use shell commands (mkdir -p, touch) followed by edit steps to add COMPLETE content.\n"
        "7) Be specific about file paths and implement COMPLETE functionality, not placeholders.\n"
        "8) Leverage semantic search for understanding codebase structure and dependencies.\n"
        "9) Use AST-aware editing for precise code transformations when modifying existing code.\n"
        "10) AVOID tiny incremental changes - implement complete features with proper error handling.\n"
        "11) Return valid JSON array only, no explanation text."
    )

    return "\n".join(parts)
