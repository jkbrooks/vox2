from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Iterable, List, Tuple


class CodebaseUtilities:
    def __init__(self, root: str) -> None:
        self.root = root

    def glob_files(self, patterns: List[str]) -> List[str]:
        results: List[str] = []
        for pat in patterns:
            results.extend([str(p) for p in Path(self.root).rglob(pat)])
        return results

    def grep(self, pattern: str, file_globs: List[str]) -> List[Tuple[str, int, str]]:
        compiled = re.compile(pattern)
        hits: List[Tuple[str, int, str]] = []
        for path in self.glob_files(file_globs):
            try:
                with open(path, "r", encoding="utf-8", errors="ignore") as f:
                    for i, line in enumerate(f, start=1):
                        if compiled.search(line):
                            hits.append((os.path.relpath(path, self.root), i, line.rstrip("\n")))
            except Exception:
                continue
        return hits

    def workspace_summary(self, max_files: int = 10) -> str:
        """Return a brief summary: notable directories and a sample of key files."""
        roots = [
            "constitutional-agent-test",
            "src",
            "server",
            "client",
            "apps",
            "packages",
        ]
        existing = [r for r in roots if os.path.isdir(os.path.join(self.root, r))]
        sample_files: List[str] = []
        for g in ["**/*.py", "**/*.md", "**/*.ts", "**/*.rs"]:
            for p in Path(self.root).rglob(g):
                rel = os.path.relpath(str(p), self.root)
                if len(sample_files) < max_files:
                    sample_files.append(rel)
                else:
                    break
            if len(sample_files) >= max_files:
                break
        return (
            f"dirs: {existing}\n"
            f"sample_files: {sample_files[:max_files]}"
        )

    def candidate_eoi_paths(self, limit: int = 20) -> List[str]:
        """Best-effort list of interesting file paths/classes as EoI candidates.
        For now: top-level README/specs/entrypoints and Python modules under constitutional-agent-test.
        """
        candidates: List[str] = []
        globs = [
            "README.md",
            "MVP_PRODUCT_SPEC.md",
            "constitutional-agent-test/**/*.md",
            "constitutional-agent-test/executive_worker/**/*.py",
        ]
        seen = set()
        for g in globs:
            for p in Path(self.root).rglob(g):
                rel = os.path.relpath(str(p), self.root)
                if rel not in seen:
                    candidates.append(rel)
                    seen.add(rel)
                if len(candidates) >= limit:
                    return candidates
        return candidates

    # Placeholders for future Aider-parity components:
    # - workspace index (language map, symbol table, imports)
    # - impacted-file selection via dependency walk
