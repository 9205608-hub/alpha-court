"""External anchor backends for the certified-run seal (prereg-gate.md §4.2–§4.3).

The anchor hardens a sealed chain head against full rewrite. It does not prove
declarations predate series (that is the content hash-chain) and is not
cryptographic non-repudiation (prereg-gate.md §6).

Verification keys on the recomputed chain head from the backend's own protected
state (``verify(chain_head)``) — never on a manifest-stored reference, which
lives inside the rewrite surface (rework-01 Finding A).
"""

from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Protocol, runtime_checkable


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@runtime_checkable
class AnchorBackend(Protocol):
    """Pluggable seal-time pin (prereg-gate.md §4.2; rework-01 query-by-head).

    ``ref_before_seal`` is non-None only when the backend can mint a reference
    *before* the seal line is written (FileAnchor). Git anchors after the fact
    and returns None from ``ref_before_seal``.

    ``verify(chain_head)`` answers "has this backend anchored THIS head?" from
    the backend's own state — not from a manifest ref.
    """

    def pin(self, chain_head: str) -> str:
        """Pin ``chain_head`` externally; return the anchor_ref for the manifest."""
        ...

    def verify(self, chain_head: str) -> bool:
        """Return True iff this backend has anchored ``chain_head``."""
        ...

    def ref_before_seal(self) -> str | None:
        """Reference usable inside the seal payload, or None if post-seal only."""
        ...


class NoopAnchor:
    """Test/dev anchor: pin returns ``\"noop\"``; verify always True."""

    def pin(self, chain_head: str) -> str:
        return "noop"

    def verify(self, chain_head: str) -> bool:
        return True

    def ref_before_seal(self) -> str | None:
        return None


class FileAnchor:
    """Append-only JSONL anchor file outside the ledger (prereg-gate.md §4.2).

    The anchor file is created at construction so the seal may reference an
    artifact that already exists (never reference an artifact that does not
    yet exist). ``verify`` reads this backend's own file, never a path from
    the manifest.
    """

    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        if not self._path.exists():
            self._path.touch()

    def pin(self, chain_head: str) -> str:
        record = {"chain_head": chain_head, "at": _utc_now_iso()}
        line = json.dumps(record, separators=(",", ":"), ensure_ascii=False)
        with self._path.open("a", encoding="utf-8") as f:
            f.write(line)
            f.write("\n")
        return str(self._path)

    def verify(self, chain_head: str) -> bool:
        if not self._path.is_file():
            return False
        try:
            text = self._path.read_text(encoding="utf-8")
        except OSError:
            return False
        for line in text.splitlines():
            if not line.strip():
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(rec, dict) and rec.get("chain_head") == chain_head:
                return True
        return False

    def ref_before_seal(self) -> str | None:
        return str(self._path)


class GitAnchor:
    """Git-commit anchor: one file ``anchors/<head>.txt`` per pin.

    Uses ``subprocess`` only when invoked — no import-time git dependency
    (prereg-gate.md §4.2). ``ref_before_seal`` is always None (pin after seal).
    ``verify`` queries by head (finds a commit containing ``anchors/<head>.txt``),
    not by a manifest-stored SHA.
    """

    def __init__(
        self,
        repo_dir: str | Path,
        *,
        committer_name: str | None = None,
        committer_email: str | None = None,
    ) -> None:
        self._repo = Path(repo_dir)
        self._committer_name = committer_name
        self._committer_email = committer_email

    def pin(self, chain_head: str) -> str:
        if not isinstance(chain_head, str) or not chain_head:
            raise ValueError("chain_head must be a non-empty str")
        anchors = self._repo / "anchors"
        anchors.mkdir(parents=True, exist_ok=True)
        rel = Path("anchors") / f"{chain_head}.txt"
        target = self._repo / rel
        target.write_text(f"{chain_head}\n", encoding="utf-8")
        self._git(["add", str(rel)])
        commit_args: list[str] = []
        # Only override identity when the caller passes it (tmp-repo tests).
        # Production default: use the repo's own git config (F-5).
        if self._committer_name is not None:
            commit_args.extend(["-c", f"user.name={self._committer_name}"])
        if self._committer_email is not None:
            commit_args.extend(["-c", f"user.email={self._committer_email}"])
        commit_args.extend(["commit", "-m", f"anchor {chain_head[:12]}"])
        self._git(commit_args)
        sha = self._git(["rev-parse", "HEAD"]).stdout.strip()
        return sha

    def verify(self, chain_head: str) -> bool:
        if not isinstance(chain_head, str) or not chain_head:
            return False
        rel = f"anchors/{chain_head}.txt"
        # Search history for a commit that introduced / contains this path.
        log = self._git(
            ["log", "--all", "--format=%H", "--", rel],
            check=False,
        )
        if log.returncode != 0 or not log.stdout.strip():
            return False
        # Check the most recent commit that touches the path.
        for sha in log.stdout.strip().splitlines():
            show = self._git(["show", f"{sha}:{rel}"], check=False)
            if show.returncode == 0 and show.stdout.strip() == chain_head:
                return True
        return False

    def ref_before_seal(self) -> str | None:
        return None

    def _git(
        self, args: list[str], *, check: bool = True
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["git", *args],
            cwd=self._repo,
            check=check,
            capture_output=True,
            text=True,
        )
