from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass


@dataclass
class Ticket:
    id: str
    title: str
    body: str

    @staticmethod
    def from_github(repo: str, issue_number: int) -> "Ticket":
        """Fetch a ticket from GitHub via gh CLI.

        Requires authenticated gh CLI with access to the repository.
        """
        cmd = [
            "gh",
            "issue",
            "view",
            "-R",
            repo,
            str(issue_number),
            "--json",
            "number,title,body",
        ]
        out = subprocess.check_output(cmd, text=True)
        raw = json.loads(out)
        return Ticket(id=str(raw["number"]), title=raw["title"], body=raw.get("body", ""))


