# Executive Worker MVP (vibe-coded v2)

This directory contains a minimal execution‑centric agent with immediate LLM integration (OpenAI).

## Structure

- `executive_worker/`
  - `agent.py` – main agent loop (plan via LLM → execute → validate → log)
  - `shell_runner.py` – arbitrary command execution
  - `git_ops.py` – git operations via shell
  - `codebase_utils.py` – search/index skeleton (Aider‑parity ready)
  - `edit_engine.py` – transactional multi‑file edits (skeleton)
  - `llm_client.py` – OpenAI client (uses `OPENAI_API_KEY`)
  - `models.py` – dataclasses for plan and run logging (Ticket vs Task separated)
  - `runs/` – per-run JSON logs for quick inspection
- `research/agentic-repos-borrowables.md` – reference notes
- `MVP_PRODUCT_SPEC.md` – spec driving this MVP
- `_archive/` – older versions retained for reference

## Quick start

1. Export your OpenAI API key:
   ```bash
   export OPENAI_API_KEY=sk-...
   ```
2. Run a quick planning+execution cycle from Python REPL:
   ```python
   from constitutional_agent_test.executive_worker.agent import ExecutiveWorker
   from constitutional_agent_test.executive_worker.models import Ticket

   agent = ExecutiveWorker(workspace_root="/workspaces/vox2")
   ticket = Ticket(ticket_id="ticket-local", title="Sanity check", description="Echo hello and git status")
   log = agent.execute_ticket(ticket)
   print(log.run_id)
   ```
3. Run logs will be written to `constitutional-agent-test/executive_worker/runs/`, and `task_tree.yaml` maintained at `constitutional-agent-test/`.

## Notes
- Git ops are executed via shell (no dedicated git client) per current preference.
- Codebase utilities are structured to enable future Aider‑like parity without large refactors.
- Edit engine is transactional and will rollback if a context match is not found.
