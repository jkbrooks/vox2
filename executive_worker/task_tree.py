from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import List

import yaml


@dataclass
class TaskNode:
    id: str
    title: str
    deps: List[str] = field(default_factory=list)
    status: str = "unchanged"  # unchanged | partial | done
    coverage_pct: int = 0
    acceptance: List[str] = field(default_factory=lambda: ["compiles", "tests pass"])
    evidence_commits: List[str] = field(default_factory=list)
    evidence_files: List[str] = field(default_factory=list)
    note: str = ""
    children: List["TaskNode"] = field(default_factory=list)


@dataclass
class TaskTree:
    id: str
    title: str
    nodes: List[TaskNode] = field(default_factory=list)

    @staticmethod
    def file_path(repo_root: str) -> Path:
        return Path(repo_root) / "task_tree.yaml"

    @classmethod
    def load_or_create(cls, repo_root: str, task_id: str, title: str) -> "TaskTree":
        path = cls.file_path(repo_root)
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                raw = yaml.safe_load(f) or {}
            nodes: List[TaskNode] = []
            for n in raw.get("nodes", []) or []:
                nodes.append(
                    TaskNode(
                        id=str(n.get("id")),
                        title=str(n.get("title", "")),
                        deps=list(n.get("deps", []) or []),
                        status=str(n.get("status", "unchanged")),
                        coverage_pct=int(n.get("coverage_pct", 0)),
                        acceptance=list(n.get("acceptance", []) or []),
                        evidence_commits=list((n.get("evidence", {}) or {}).get("commits", []) or []),
                        evidence_files=list((n.get("evidence", {}) or {}).get("files", []) or []),
                        note=str(n.get("notes", "")),
                        children=[
                            TaskNode(
                                id=str(c.get("id")),
                                title=str(c.get("title", "")),
                            )
                            for c in (n.get("children", []) or [])
                        ],
                    )
                )
            return cls(id=str(raw.get("id", task_id)), title=str(raw.get("title", title)), nodes=nodes)

        tree = cls(id=task_id, title=title, nodes=[])
        tree.save(repo_root)
        return tree

    def save(self, repo_root: str) -> None:
        out = {
            "id": self.id,
            "title": self.title,
            "nodes": [
                {
                    "id": n.id,
                    "title": n.title,
                    "deps": n.deps,
                    "status": n.status,
                    "coverage_pct": n.coverage_pct,
                    "acceptance": n.acceptance,
                    "evidence": {
                        "commits": n.evidence_commits,
                        "files": n.evidence_files,
                    },
                    "notes": n.note,
                    "children": [asdict(c) for c in n.children],
                }
                for n in self.nodes
            ],
        }
        with open(self.file_path(repo_root), "w", encoding="utf-8") as f:
            yaml.safe_dump(out, f, sort_keys=False)

    def add_or_update_node(self, node: TaskNode) -> None:
        for i, existing in enumerate(self.nodes):
            if existing.id == node.id:
                self.nodes[i] = node
                return
        self.nodes.append(node)

    @staticmethod
    def write_run_json(repo_root: str, payload: dict) -> Path:
        runs_dir = Path(repo_root) / "executive_worker_runs"
        runs_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")
        path = runs_dir / f"run-{ts}.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
        return path


