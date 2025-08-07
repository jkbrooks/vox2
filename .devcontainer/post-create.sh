#!/usr/bin/env bash
set -euo pipefail

# This script is executed by Codespaces after the container is created.
# It uses a personal access token (PAT) stored as a Codespaces secret
# to grant the environment access to other private repositories.

# GH_PAT should be set as a Codespaces secret for this repository.
if [[ -n "${GH_PAT:-}" ]]; then
  echo "🔑 Configuring GitHub authentication with custom PAT..."

  # The default GITHUB_TOKEN provided by Codespaces is scoped only to the
  # current repository. To use our own PAT with wider permissions, we must
  # first unset this environment variable before logging in.
  ORIGINAL_GITHUB_TOKEN="${GITHUB_TOKEN-}"
  unset GITHUB_TOKEN

  # Log in to the GitHub CLI non-interactively using the PAT.
  echo "$GH_PAT" | gh auth login --hostname github.com --with-token

  # Configure git to use the same token for all git operations.
  gh auth setup-git

  # Restore the GITHUB_TOKEN variable with our PAT for other tools that may need it.
  export GITHUB_TOKEN="$GH_PAT"

  echo "✅ GitHub CLI & git are now authenticated using the custom PAT."
  echo "You can now access other private repositories that the token is scoped for."
else
  echo "⚠️ GH_PAT secret not found."
  echo "Please create a secret in this repository's Codespaces settings to enable automatic authentication."
fi

