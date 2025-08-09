from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

try:
    import yaml  # type: ignore
except Exception:  # pragma: no cover
    yaml = None  # type: ignore


@dataclass
class TaskTreeNode:
    id: str
    title: str
    deps: List[str] = field(default_factory=list)
    status: str = "partial"  # partial | done | unchanged
    coverage_pct: int = 0
    acceptance: List[str] = field(default_factory=lambda: ["compiles", "tests pass"])
    evidence: Dict[str, List[str]] = field(default_factory=lambda: {"commits": [], "files": []})
    notes: str = ""
    children: List["TaskTreeNode"] = field(default_factory=list)


@dataclass
class TaskTree:
    id: str
    title: str
    nodes: List[TaskTreeNode] = field(default_factory=list)

    @staticmethod
    def path_for(workspace_root: str) -> str:
        return os.path.join(workspace_root, "constitutional-agent-test", "task_tree.yaml")

    @classmethod
    def load_or_create(cls, workspace_root: str, task_id: str, title: str) -> "TaskTree":
        path = cls.path_for(workspace_root)
        if os.path.exists(path) and yaml is not None:
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f) or {}
                nodes = []
                for nd in data.get("nodes", []) or []:
                    nodes.append(
                        TaskTreeNode(
                            id=str(nd.get("id", "")),
                            title=str(nd.get("title", "")),
                            deps=list(nd.get("deps", []) or []),
                            status=str(nd.get("status", "partial")),
                            coverage_pct=int(nd.get("coverage_pct", 0)),
                            acceptance=list(nd.get("acceptance", []) or []),
                            evidence={
                                "commits": list((nd.get("evidence", {}) or {}).get("commits", []) or []),
                                "files": list((nd.get("evidence", {}) or {}).get("files", []) or []),
                            },
                            notes=str(nd.get("notes", "")),
                            children=[],
                        )
                    )
                return cls(id=str(data.get("id", task_id)), title=str(data.get("title", title)), nodes=nodes)
            except Exception:
                pass
        tree = cls(id=task_id, title=title, nodes=[])
        tree.save(workspace_root)
        return tree

    def to_dict(self) -> Dict[str, Any]:
        def node_to_dict(n: TaskTreeNode) -> Dict[str, Any]:
            return {
                "id": n.id,
                "title": n.title,
                "deps": n.deps,
                "status": n.status,
                "coverage_pct": n.coverage_pct,
                "acceptance": n.acceptance,
                "evidence": n.evidence,
                "notes": n.notes,
                "children": [node_to_dict(c) for c in n.children],
            }

        return {"id": self.id, "title": self.title, "nodes": [node_to_dict(n) for n in self.nodes]}

    def save(self, workspace_root: str) -> None:
        path = self.path_for(workspace_root)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        data = self.to_dict()
        text: Optional[str] = None
        if yaml is not None:
            try:
                text = yaml.safe_dump(data, sort_keys=False)
            except Exception:
                text = None
        if text is None:
            # very simple YAML writer for our limited schema
            lines: List[str] = []
            lines.append(f"id: {data['id']}")
            lines.append(f"title: \"{data['title']}\"")
            lines.append("nodes:")
            for n in data["nodes"]:
                lines.append(f"- id: {n['id']}")
                lines.append(f"  title: \"{n['title']}\"")
                lines.append("  deps: [" + ", ".join(n.get("deps", [])) + "]")
                lines.append(f"  status: {n.get('status', 'partial')}")
                lines.append(f"  coverage_pct: {int(n.get('coverage_pct', 0))}")
                lines.append("  acceptance: [" + ", ".join([f'\"{a}\"' for a in (n.get("acceptance", []) or [])]) + "]")
                evidence = n.get("evidence", {}) or {}
                lines.append("  evidence:")
                lines.append("    commits: [" + ", ".join([f'\"{c}\"' for c in (evidence.get("commits", []) or [])]) + "]")
                lines.append("    files: [" + ", ".join([f'\"{f}\"' for f in (evidence.get("files", []) or [])]) + "]")
                lines.append(f"  notes: \"{n.get('notes', '')}\"")
                lines.append("  children: []")
            text = "\n".join(lines)
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)

    def _get_or_create_node(self, node_id: str, title: str) -> TaskTreeNode:
        for n in self.nodes:
            if n.id == node_id:
                return n
        n = TaskTreeNode(id=node_id, title=title)
        self.nodes.append(n)
        return n

    def record_evidence(self, node_id: str, commits: List[str], files: List[str]) -> None:
        node = self._get_or_create_node(node_id, title=node_id)
        node.evidence.setdefault("commits", []).extend([c for c in commits if c])
        node.evidence.setdefault("files", []).extend([p for p in files if p])

    def set_status(self, node_id: str, status: str, coverage_pct: int, note: str = "") -> None:
        node = self._get_or_create_node(node_id, title=node_id)
        node.status = status
        node.coverage_pct = coverage_pct
        node.notes = note
