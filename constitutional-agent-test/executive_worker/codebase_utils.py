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

    # Placeholders for future Aider-parity components:
    # - workspace index (language map, symbol table, imports)
    # - impacted-file selection via dependency walk
