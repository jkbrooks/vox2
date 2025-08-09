from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import List


@dataclass
class RunSummary:
    task_id: str
    compiled: bool
    llm_plan_snippet: str
    file_name: str


def _collect_run_files(repo_root: Path) -> List[Path]:
    candidates: List[Path] = []
    # Primary mirror location
    primary = repo_root / "executive_worker" / "runs"
    if primary.exists():
        candidates.extend(sorted(primary.glob("run-*.json")))
    # Fallback original location
    fallback = repo_root / "executive_worker_runs"
    if fallback.exists():
        candidates.extend(sorted(fallback.glob("run-*.json")))
    # Deduplicate by name while preserving order
    seen = set()
    unique: List[Path] = []
    for p in candidates:
        if p.name in seen:
            continue
        seen.add(p.name)
        unique.append(p)
    return unique


def _read_summary(path: Path) -> RunSummary:
    data = json.loads(path.read_text(encoding="utf-8"))
    task_id = str(data.get("task_id", ""))
    compiled = bool((data.get("validation") or {}).get("compiled", False))
    llm_plan = str(data.get("llm_plan", ""))
    snippet = llm_plan[:100].replace("\n", " ")
    return RunSummary(task_id=task_id, compiled=compiled, llm_plan_snippet=snippet, file_name=path.name)


def regenerate_runs_index(repo_root: str) -> Path:
    root = Path(repo_root)
    runs_dir = root / "executive_worker" / "runs"
    runs_dir.mkdir(parents=True, exist_ok=True)

    rows: List[RunSummary] = []
    for run_file in _collect_run_files(root):
        try:
            rows.append(_read_summary(run_file))
        except Exception:
            continue

    lines: List[str] = []
    lines.append("| task_id | compiled | llm_plan (first 100 chars) | file |")
    lines.append("|---|---|---|---|")
    for r in rows:
        lines.append(f"| {r.task_id} | {str(r.compiled).lower()} | {r.llm_plan_snippet} | {r.file_name} |")

    index_path = runs_dir / "index.md"
    index_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return index_path


