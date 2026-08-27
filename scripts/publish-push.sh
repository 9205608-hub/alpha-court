#!/usr/bin/env bash
# Receipt-verified push of an audited export tree to the public snapshot repo.
#
# Flow (TOCTOU-bound): export -> audit (writes receipt) -> verify receipt -> git init
# -> commit with fixed identity -> push. The audit refuses trees containing .git, so
# the receipt is taken before init; the tree hash ignores .git afterwards.
#
# usage: scripts/publish-push.sh <export-tree> <remote-url>
set -euo pipefail

EXPORT_TREE=${1:?usage: publish-push.sh <export-tree> <remote-url>}
REMOTE=${2:?usage: publish-push.sh <export-tree> <remote-url>}
RULES=${PUBLISH_RULES:-docs/private/publish-rules.txt}
RECEIPT="${EXPORT_TREE%/}-audit-receipt.json"

if [ -d "$EXPORT_TREE/.git" ]; then
  echo "publish-push: $EXPORT_TREE already has .git — re-export first (audit needs a raw tree)" >&2
  exit 2
fi

python -m harness.publish_audit --tree "$EXPORT_TREE" --rules "$RULES" --receipt "$RECEIPT"

python - "$EXPORT_TREE" "$RECEIPT" <<'PY'
import sys

from harness.publish_audit import verify_receipt

if not verify_receipt(sys.argv[1], sys.argv[2]):
    print("publish-push: receipt mismatch — tree changed after audit (TOCTOU); aborting",
          file=sys.stderr)
    sys.exit(1)
PY

cd "$EXPORT_TREE"
git init -q -b main
git config user.name "Spencer"
git config user.email "[REDACTED-EMAIL]"
git add -A
git commit -q -m "snapshot: $(date +%Y-%m-%d)"
git remote add public "$REMOTE"
git push --force public main
echo "publish-push: snapshot pushed to $REMOTE"
