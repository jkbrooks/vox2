#!/usr/bin/env bash
set -euo pipefail

echo "--- [DEBUG] Running post-create.sh ---"
echo "[DEBUG] Timestamp: $(date)"
echo "[DEBUG] User: $(whoami)"

echo "[DEBUG] Checking for GitHub CLI (gh)..."
if ! command -v gh &> /dev/null; then
    echo "❌ [DEBUG] ERROR: 'gh' command not found. Aborting."
    exit 1
fi
echo "✅ [DEBUG] 'gh' command is available in PATH."

echo "[DEBUG] Checking for GH_PAT secret..."
if [[ -n "${GH_PAT:-}" ]]; then
  echo "✅ [DEBUG] GH_PAT secret is present."
  echo "🔑 [DEBUG] Proceeding with custom PAT authentication..."

  echo "[DEBUG] Unsetting default GITHUB_TOKEN to avoid conflicts..."
  unset GITHUB_TOKEN

  echo "[DEBUG] Attempting 'gh auth login' with the provided token..."
  echo "$GH_PAT" | gh auth login --hostname github.com --with-token
  echo "✅ [DEBUG] 'gh auth login' completed."

  echo "[DEBUG] Running 'gh auth setup-git' to configure git..."
  gh auth setup-git
  echo "✅ [DEBUG] 'gh auth setup-git' completed."

  echo "[DEBUG] Verifying final auth status with 'gh auth status':"
  gh auth status
  
  echo "🎉 [DEBUG] Script finished. Custom PAT should now be active."
else
  echo "⚠️ [DEBUG] GH_PAT secret not found or is empty."
  echo "[DEBUG] Please double-check that a secret named GH_PAT is configured for this repository in Codespaces settings."
  echo "[DEBUG] Default Codespaces token will be used."
fi

echo "--- [DEBUG] post-create.sh finished ---"
