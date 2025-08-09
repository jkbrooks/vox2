from __future__ import annotations

import os
from executive_worker.prompting import (
    load_iso_42010_eoi_excerpt,
    load_constitutional_prompt_excerpt,
    compose_system_prompt,
)


def test_prompt_excerpts_and_compose(tmp_path):
    root = tmp_path
    # Seed minimal files that functions look for
    (root / "scrap").mkdir(parents=True, exist_ok=True)
    (root / "scrap" / "ISO-IEEE-42010-Architecture-Description.md").write_text("## 3 Terms and definitions\n**3.12 entity of interest**\nEoI subject...", encoding="utf-8")
    (root / "constitutional-agent-test" / "_archive" / "prompts").mkdir(parents=True, exist_ok=True)
    (root / "constitutional-agent-test" / "_archive" / "prompts" / "constitutional_system_prompt.md").write_text(
        "## Your Identity and Context\n...\n### Fundamental Concepts\n...\n", encoding="utf-8"
    )

    iso = load_iso_42010_eoi_excerpt(str(root))
    const = load_constitutional_prompt_excerpt(str(root))
    assert "entity of interest" in iso.lower()
    assert "identity and context" in const.lower()

    sys = compose_system_prompt(
        ticket={"id": "t1", "title": "x", "description": "y"},
        eoi=None,
        task_tree_snapshot={"id": "t1", "title": "x"},
        workspace_summary="dirs: []",
        iso_eoi_excerpt=iso,
        constitutional_excerpt=const,
    )
    assert "[TICKET]" in sys and "[ISO_42010_EOI_EXCERPT]" in sys
