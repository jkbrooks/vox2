from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any


@dataclass
class PlanStep:
    description: str
    kind: str  # search | edit | shell | git | validate
    args: Dict[str, Any] = field(default_factory=dict)


@dataclass
class FileEdit:
    """Represents a file edit operation."""
    path: str
    original_substring: str
    replacement: str


# Ticket: external unit of work (e.g., GitHub issue/PR or local ticket)
@dataclass
class Ticket:
    ticket_id: str
    title: str
    description: str
    eoi: Optional[Dict[str, str]] = None  # optional attention director {label, path}


# Task: internal task-tree node concept (distinct from Ticket)
@dataclass
class Task:
    node_id: str
    title: str
    notes: str = ""


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
    task_id: str  # kept as 'task_id' in schema to match spec; value is the ticket_id
    start_ts: str
    end_ts: str
    eoi: Optional[Dict[str, str]]
    commands: List[CommandResult]
    commits: List[str]
    validation: ValidationResult
    affected_nodes: List[AffectedNode]
    reflections: List[Dict[str, str]]
