#!/usr/bin/env bash
set -euo pipefail

ISSUE=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --issue)
      ISSUE="$2"; shift 2;;
    *) echo "Unknown arg: $1"; exit 2;;
  esac
done

if [[ -z "${ISSUE}" ]]; then
  echo "Usage: $0 --issue <num>" >&2
  exit 2
fi

export EXEC_SKIP_DOCS_BUILD=1

python scripts/run_executive_worker.py run \
  --repo jkbrooks/vox2 \
  --issue "${ISSUE}" \
  --use-llm \
  --workspace-root "$(pwd)"

echo "Regenerating runs index..."
python - <<'PY'
from executive_worker.runs_indexer import regenerate_runs_index
import os
path = regenerate_runs_index(os.getcwd())
print(f"Index written to {path}")
PY


