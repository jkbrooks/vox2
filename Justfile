set shell := ["bash", "-c"]

# Build the Rust workspace
build:
    source "$HOME/.cargo/env" 2>/dev/null || true
    cargo check

# Run Python tests quietly
test:
    pytest -q

# Run the Executive Worker agent with LLM planning on a GitHub issue
# Usage: just agent-run issue=7
agent-run issue="":
    if [ -z "{{issue}}" ]; then echo "Usage: just agent-run issue=<num>"; exit 2; fi
    ./scripts/agent_run.sh --issue {{issue}}

# Rebuild the runs index from all run artifacts
runs-index:
    python - <<'PY'
from executive_worker.runs_indexer import regenerate_runs_index
import os
print(regenerate_runs_index(os.getcwd()))
PY


