#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from executive_worker.agent import ExecutiveWorker
from executive_worker.models import Ticket


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workspace-root", default=os.path.dirname(os.getcwd()))
    ap.add_argument("--id", required=True)
    ap.add_argument("--title", required=True)
    ap.add_argument("--description", required=True)
    ap.add_argument("--model", default="gpt-4o-mini")
    ap.add_argument("--use-enhanced", action="store_true", help="Use enhanced codebase utilities")
    args = ap.parse_args()

    agent = ExecutiveWorker(workspace_root=args.workspace_root, model=args.model, use_enhanced=args.use_enhanced)
    ticket = Ticket(ticket_id=args.id, title=args.title, description=args.description)
    run_log = agent.execute_ticket(ticket)
    print(json.dumps(run_log.__dict__, default=lambda o: o.__dict__, indent=2))


if __name__ == "__main__":
    main()
