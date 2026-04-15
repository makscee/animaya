#!/usr/bin/env bash
set -euo pipefail

# git-versioning install (Phase 4, GITV-01)
# Locked assumption A2: git repo root is ~/hub/ (knowledge/ is a subdir).
GIT_REPO_ROOT="${HOME}/hub"
mkdir -p "${GIT_REPO_ROOT}/knowledge"

if [ ! -d "${GIT_REPO_ROOT}/.git" ]; then
  echo "[git-versioning] initializing git repo at ${GIT_REPO_ROOT}"
  git -C "${GIT_REPO_ROOT}" init -q
  git -C "${GIT_REPO_ROOT}" config user.name "Animaya Bot"
  git -C "${GIT_REPO_ROOT}" config user.email "bot@animaya.local"
  # Initial empty commit so HEAD exists and subsequent diffs work
  git -C "${GIT_REPO_ROOT}" commit --allow-empty -q -m "animaya: git-versioning installed"
else
  echo "[git-versioning] existing git repo found at ${GIT_REPO_ROOT}; preserving it"
  # Ensure committer identity is set locally even on existing repos
  if ! git -C "${GIT_REPO_ROOT}" config user.name >/dev/null 2>&1; then
    git -C "${GIT_REPO_ROOT}" config user.name "Animaya Bot"
    git -C "${GIT_REPO_ROOT}" config user.email "bot@animaya.local"
  fi
fi

echo "[git-versioning] install complete"
