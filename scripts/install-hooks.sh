#!/usr/bin/env bash
# install-hooks.sh — enable the tracked git hooks in .githooks/ via core.hooksPath.
#
# Idempotent. Sets core.hooksPath to the TRACKED .githooks dir (version-controlled, one command
# to enable) and ensures the exec bit — git SILENTLY ignores a non-executable hook, so a missing
# +x is a fail-open we close here. Run once per clone/machine; core.hooksPath lives in the shared
# .git/config, so it applies across linked worktrees of this repo.
#
# HONEST NOTE: this makes the gates auto-fire; it does not make them unbypassable. --no-verify,
# core.hooksPath overrides, and non-commit paths still bypass — that is a documented ceiling; real
# enforcement is server-side CI (DESIGNED).
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
HOOKS_DIR="$ROOT/.githooks"

if [ ! -d "$HOOKS_DIR" ]; then
  echo "install-hooks: $HOOKS_DIR missing — is this the alpha-court repo?" >&2
  exit 1
fi

chmod +x "$HOOKS_DIR"/pre-commit "$HOOKS_DIR"/pre-merge-commit "$HOOKS_DIR"/run-gates.sh

current="$(git config --local --get core.hooksPath || true)"
if [ "$current" = ".githooks" ]; then
  echo "install-hooks: already installed (core.hooksPath=.githooks)"
else
  if [ -n "$current" ] && [ "$current" != ".githooks" ]; then
    echo "install-hooks: WARNING — core.hooksPath was '$current'; overwriting with .githooks" >&2
  fi
  git config --local core.hooksPath .githooks
  echo "install-hooks: set core.hooksPath=.githooks"
fi

# verify the exec bit actually took (an editor/umask could still leave it off)
for h in pre-commit pre-merge-commit; do
  if [ ! -x "$HOOKS_DIR/$h" ]; then
    echo "install-hooks: FAILED to make $h executable (git would silently ignore it)" >&2
    exit 1
  fi
done
echo "install-hooks: gates armed on pre-commit + pre-merge-commit (bypassable by --no-verify — see run-gates.sh)"
