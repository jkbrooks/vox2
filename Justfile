build: cargo check

test: pytest -q

agent-run issue=<num>: ./scripts/agent_run.sh --issue <num>

runs-index: python scripts/generate_index.py