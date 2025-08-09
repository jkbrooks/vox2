from __future__ import annotations

import os
from dataclasses import dataclass
from typing import List


@dataclass
class FileEdit:
    path: str
    original_substring: str
    replacement: str


class EditEngine:
    def __init__(self, root: str) -> None:
        self.root = root

    def apply_edits(self, edits: List[FileEdit]) -> None:
        backups: List[tuple[str, str]] = []
        try:
            for e in edits:
                target = os.path.join(self.root, e.path)
                with open(target, "r", encoding="utf-8") as f:
                    content = f.read()
                if e.original_substring not in content:
                    raise RuntimeError(f"Context not found in {e.path}")
                new_content = content.replace(e.original_substring, e.replacement, 1)
                backups.append((target, content))
                with open(target, "w", encoding="utf-8") as f:
                    f.write(new_content)
        except Exception:
            # rollback
            for path, old in backups[::-1]:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(old)
            raise
