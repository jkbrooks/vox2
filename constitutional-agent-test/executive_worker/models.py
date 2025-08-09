from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any


@dataclass
class PlanStep:
    description: str
    kind: str  # search | edit | shell | git | validate
    args: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Task:
    task_id: str
    title: str
    description: str
    eoi: Optional[Dict[str, str]] = None  # {label, path}


@dataclass
class CommandResult:
    cmd: str
    exit_code: int
    stdout: str
    stderr: str
    duration_ms: int


@dataclass
class TestsSummary:
    passed: bool
    summary: str


@dataclass
class ValidationResult:
    compiled: Optional[bool] = None
    tests: Optional[TestsSummary] = None


@dataclass
class AffectedNode:
    id: str
    status: str  # partial | done | unchanged
    coverage_pct: int
    evidence: Dict[str, List[str]]  # {commits:[], files:[]}
    note: str


@dataclass
class RunLog:
    run_id: str
    task_id: str
    start_ts: str
    end_ts: str
    eoi: Optional[Dict[str, str]]
    commands: List[CommandResult]
    commits: List[str]
    validation: ValidationResult
    affected_nodes: List[AffectedNode]
    reflections: List[Dict[str, str]]
