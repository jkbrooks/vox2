from __future__ import annotations

import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional


@dataclass
class SearchHit:
    file_path: str
    line_number: int
    line: str
    context_before: List[str]
    context_after: List[str]


class CodebaseUtilities:
    """Lightweight codebase utilities: search and basic indexing.

    - Prefers ripgrep (rg) if available for speed and .gitignore awareness
    - Falls back to a simple Python regex walk
    """

    def __init__(self, workspace_root: str):
        self.workspace_root = str(Path(workspace_root).resolve())

    def _rg_available(self) -> bool:
        return shutil.which("rg") is not None

    def search(
        self,
        pattern: str,
        *,
        path_glob: Optional[str] = None,
        file_type: Optional[str] = None,
        before: int = 2,
        after: int = 2,
        max_results: int = 200,
        case_insensitive: bool = True,
    ) -> List[SearchHit]:
        if self._rg_available():
            return self._search_with_rg(
                pattern,
                path_glob=path_glob,
                file_type=file_type,
                before=before,
                after=after,
                max_results=max_results,
                case_insensitive=case_insensitive,
            )
        return self._search_with_python(
            pattern,
            path_glob=path_glob,
            before=before,
            after=after,
            max_results=max_results,
            case_insensitive=case_insensitive,
        )

    def _search_with_rg(
        self,
        pattern: str,
        *,
        path_glob: Optional[str],
        file_type: Optional[str],
        before: int,
        after: int,
        max_results: int,
        case_insensitive: bool,
    ) -> List[SearchHit]:
        cmd: List[str] = [
            "rg",
            "--line-number",
            f"-C{max(before, after)}",
            "--no-heading",
            "--color",
            "never",
        ]
        if case_insensitive:
            cmd.append("-i")
        if file_type:
            cmd += ["--type", file_type]
        if path_glob:
            cmd += ["--glob", path_glob]
        cmd += [pattern, self.workspace_root]

        try:
            out = subprocess.check_output(cmd, text=True, stderr=subprocess.DEVNULL)
        except subprocess.CalledProcessError:
            return []

        hits: List[SearchHit] = []
        for line in out.splitlines():
            if ":" not in line:
                continue
            path_part, rest = line.split(":", 1)
            if ":" not in rest:
                continue
            line_no_str, content = rest.split(":", 1)
            if not line_no_str.isdigit():
                continue
            hits.append(
                SearchHit(
                    file_path=path_part,
                    line_number=int(line_no_str),
                    line=content,
                    context_before=[],
                    context_after=[],
                )
            )
            if len(hits) >= max_results:
                break
        return hits

    def _iter_files(self, path_glob: Optional[str]) -> Iterable[Path]:
        root = Path(self.workspace_root)
        if not path_glob:
            yield from (p for p in root.rglob("*") if p.is_file())
            return
        yield from (p for p in root.rglob("*") if p.is_file() and p.match(path_glob))

    def _search_with_python(
        self,
        pattern: str,
        *,
        path_glob: Optional[str],
        before: int,
        after: int,
        max_results: int,
        case_insensitive: bool,
    ) -> List[SearchHit]:
        flags = re.IGNORECASE if case_insensitive else 0
        regex = re.compile(pattern, flags)
        hits: List[SearchHit] = []
        for file_path in self._iter_files(path_glob):
            try:
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    lines = f.readlines()
            except Exception:
                continue
            for idx, line in enumerate(lines, start=1):
                if regex.search(line):
                    start = max(0, idx - 1 - before)
                    end = min(len(lines), idx - 1 + 1 + after)
                    hits.append(
                        SearchHit(
                            file_path=str(file_path),
                            line_number=idx,
                            line=line.rstrip("\n"),
                            context_before=[l.rstrip("\n") for l in lines[start : idx - 1]],
                            context_after=[l.rstrip("\n") for l in lines[idx:end]],
                        )
                    )
                    if len(hits) >= max_results:
                        return hits
        return hits


