"""Tests for commander-side receipt extract + validate (scripts/dispatch_receipt.py).

Drives the CLI as a subprocess against tmp fixtures. Does not call grok or
dispatch.sh end-to-end.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "dispatch_receipt.py"
SCHEMA = REPO_ROOT / "scripts" / "receipt.schema.json"
REAL_ENVELOPE = (
    REPO_ROOT
    / ".scratch"
    / "dispatch"
    / "v0.2-09-aggregation-policy"
    / "raw-20260713-160854.json"
)


def _valid_receipt(**overrides: object) -> dict:
    base: dict = {
        "ticket_id": "v0.2-test",
        "status": "done",
        "summary": "test summary",
        "branch": "dispatch/test",
        "commit": "abc123",
        "worktree_path": "/tmp/wt",
        "files_changed": [
            {
                "path": "scripts/dispatch.sh",
                "action": "modified",
                "purpose": "two-seam refactor",
            }
        ],
        "self_test": [{"cmd": "true", "exit_code": 0}],
        "deviations": [],
        "open_questions": [],
    }
    base.update(overrides)
    return base


def _run(
    raw_path: Path, receipt_out: Path, schema: Path = SCHEMA
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), str(raw_path), str(schema), str(receipt_out)],
        check=False,
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
    )


def test_valid_real_envelope_exits_zero_writes_receipt(tmp_path: Path) -> None:
    """Committed real envelope → exit 0, receipt written, summary printed."""
    assert REAL_ENVELOPE.is_file(), f"fixture missing: {REAL_ENVELOPE}"
    out = tmp_path / "receipt.json"
    result = _run(REAL_ENVELOPE, out)
    assert result.returncode == 0, result.stderr
    assert out.is_file()
    receipt = json.loads(out.read_text(encoding="utf-8"))
    assert receipt["status"] in ("done", "partial", "blocked", "failed")
    assert "ticket_id" in receipt
    assert "[dispatch] status:" in result.stdout
    assert "[dispatch] branch:" in result.stdout
    assert "[dispatch] commit:" in result.stdout
    assert "[dispatch] worktree:" in result.stdout
    # session line is printed by dispatch.sh, not the extractor
    assert "[dispatch] session:" not in result.stdout


def test_text_concat_decode_fallback_exits_zero(tmp_path: Path) -> None:
    """structuredOutput absent; valid receipt only in text concat-decode → 0."""
    receipt = _valid_receipt()
    # Mimic grok text field: concatenated JSON objects; last dict wins.
    text = json.dumps({"turn": 1, "msg": "progress"}) + json.dumps(receipt)
    envelope = {"text": text, "sessionId": "sess-fallback"}
    raw = tmp_path / "raw.json"
    raw.write_text(json.dumps(envelope), encoding="utf-8")
    out = tmp_path / "receipt.json"
    result = _run(raw, out)
    assert result.returncode == 0, result.stderr
    written = json.loads(out.read_text(encoding="utf-8"))
    assert written["ticket_id"] == "v0.2-test"
    assert written["status"] == "done"


def test_no_receipt_anywhere_exits_4(tmp_path: Path) -> None:
    envelope = {"text": "no json here", "sessionId": "x"}
    raw = tmp_path / "raw.json"
    raw.write_text(json.dumps(envelope), encoding="utf-8")
    out = tmp_path / "receipt.json"
    result = _run(raw, out)
    assert result.returncode == 4
    assert "no structured receipt found" in result.stderr
    assert str(raw) in result.stderr
    assert not out.exists()


def test_missing_required_key_exits_3(tmp_path: Path) -> None:
    receipt = _valid_receipt()
    del receipt["summary"]
    raw = tmp_path / "raw.json"
    raw.write_text(json.dumps({"structuredOutput": receipt}), encoding="utf-8")
    out = tmp_path / "receipt.json"
    result = _run(raw, out)
    assert result.returncode == 3
    assert "receipt invalid" in result.stderr
    assert "summary" in result.stderr
    assert not out.exists()


def test_status_not_in_enum_exits_3(tmp_path: Path) -> None:
    receipt = _valid_receipt(status="finished")
    raw = tmp_path / "raw.json"
    raw.write_text(json.dumps({"structuredOutput": receipt}), encoding="utf-8")
    out = tmp_path / "receipt.json"
    result = _run(raw, out)
    assert result.returncode == 3
    assert "receipt invalid" in result.stderr
    assert "finished" in result.stderr
    assert "status" in result.stderr


def test_self_test_item_missing_exit_code_exits_3(tmp_path: Path) -> None:
    receipt = _valid_receipt(self_test=[{"cmd": "true"}])
    raw = tmp_path / "raw.json"
    raw.write_text(json.dumps({"structuredOutput": receipt}), encoding="utf-8")
    out = tmp_path / "receipt.json"
    result = _run(raw, out)
    assert result.returncode == 3
    assert "receipt invalid" in result.stderr
    assert "exit_code" in result.stderr


def test_files_changed_bad_action_enum_exits_3(tmp_path: Path) -> None:
    receipt = _valid_receipt(
        files_changed=[
            {"path": "a.py", "action": "rewritten", "purpose": "nope"}
        ]
    )
    raw = tmp_path / "raw.json"
    raw.write_text(json.dumps({"structuredOutput": receipt}), encoding="utf-8")
    out = tmp_path / "receipt.json"
    result = _run(raw, out)
    assert result.returncode == 3
    assert "receipt invalid" in result.stderr
    assert "rewritten" in result.stderr or "action" in result.stderr


def test_unexpected_top_level_key_exits_3(tmp_path: Path) -> None:
    receipt = _valid_receipt(extra_field="nope")
    raw = tmp_path / "raw.json"
    raw.write_text(json.dumps({"structuredOutput": receipt}), encoding="utf-8")
    out = tmp_path / "receipt.json"
    result = _run(raw, out)
    assert result.returncode == 3
    assert "receipt invalid" in result.stderr
    assert "extra_field" in result.stderr


def test_exit_code_string_not_int_exits_3(tmp_path: Path) -> None:
    receipt = _valid_receipt(self_test=[{"cmd": "true", "exit_code": "0"}])
    raw = tmp_path / "raw.json"
    raw.write_text(json.dumps({"structuredOutput": receipt}), encoding="utf-8")
    out = tmp_path / "receipt.json"
    result = _run(raw, out)
    assert result.returncode == 3
    assert "receipt invalid" in result.stderr
    assert "exit_code" in result.stderr


def test_valid_with_notes_for_referee_exits_zero(tmp_path: Path) -> None:
    receipt = _valid_receipt(notes_for_referee="look at the seam first")
    raw = tmp_path / "raw.json"
    raw.write_text(json.dumps({"structuredOutput": receipt}), encoding="utf-8")
    out = tmp_path / "receipt.json"
    result = _run(raw, out)
    assert result.returncode == 0, result.stderr
    written = json.loads(out.read_text(encoding="utf-8"))
    assert written["notes_for_referee"] == "look at the seam first"


def test_deviations_item_not_string_exits_3(tmp_path: Path) -> None:
    receipt = _valid_receipt(deviations=[{"not": "a string"}])
    raw = tmp_path / "raw.json"
    raw.write_text(json.dumps({"structuredOutput": receipt}), encoding="utf-8")
    out = tmp_path / "receipt.json"
    result = _run(raw, out)
    assert result.returncode == 3
    assert "receipt invalid" in result.stderr
