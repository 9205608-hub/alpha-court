"""Bridge-level assertions for scripts/dispatch.sh worker seams.

Anti-recurrence for CR-16: neither cursor-agent nor dsh headless has a
--json-schema flag, so for those seams the receipt schema must ride the
prompt. When that channel disappears, the worker cannot know the receipt
contract and every dispatch dies at validation (exit 3) AFTER a full worker
run — the expensive failure mode this file exists to keep dead.

These tests assert the INVARIANT ("the schema-less seams reach the schema
channel"), not the implementation site: the channel is now a shared
`receipt_prompt_suffix()` helper rather than text inlined in each seam, and a
test that pinned the old site would have blocked that refactor while adding no
safety.

Second anti-recurrence (2026-08-15, first ds dispatch): with the schema in the
prompt, a worker will happily template its receipt off the schema TEXT and
carry `$schema` / `title` into the instance, which the strict validator
rejects. The fix is a prompt rule, not a looser validator and not an extractor
that strips keys — the receipt is the worker's factual self-report and the
commander must never rewrite it. So the rule text is pinned here.
"""

from __future__ import annotations

from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
_DISPATCH = (_REPO / "scripts" / "dispatch.sh").read_text(encoding="utf-8")

# Seams whose CLI has no --json-schema flag: the schema MUST ride the prompt.
_SCHEMALESS_SEAMS = ("worker_invoke_cursor()", "worker_invoke_ds()")


def _seam_body(marker: str) -> str:
    assert marker in _DISPATCH, f"{marker} seam missing from dispatch.sh"
    return _DISPATCH.split(marker, 1)[1].split("\n}\n", 1)[0]


def test_receipt_prompt_suffix_carries_schema():
    body = _seam_body("receipt_prompt_suffix()")
    assert "RECEIPT SCHEMA" in body
    assert '$(cat "$SCHEMA")' in body


def test_schemaless_seams_reach_the_schema_channel():
    for marker in _SCHEMALESS_SEAMS:
        body = _seam_body(marker)
        assert "receipt_prompt_suffix" in body or (
            "RECEIPT SCHEMA" in body and '$(cat "$SCHEMA")' in body
        ), f"{marker} does not carry the receipt schema into the prompt"


def test_receipt_rules_forbid_copying_schema_metadata():
    body = _seam_body("receipt_prompt_suffix()")
    assert "INSTANCE of the schema" in body
    assert "schema" in body and "metadata" in body


def test_grok_invoke_carries_receipt_schema_flag():
    body = _seam_body("worker_invoke_grok()")
    assert "--json-schema" in body


def test_ds_seam_pins_the_dsh_version():
    """dsh is a 0.1.x developer preview; `@latest` would swap the worker under
    us between dispatches, which breaks run-to-run comparability."""
    assert "DSH_PKG" in _DISPATCH
    assert "@deepseek-ai/dsh@" in _DISPATCH
    assert "@deepseek-ai/dsh@latest" not in _DISPATCH


def test_ds_seam_rejects_knobs_it_cannot_honour():
    """dsh headless takes only the task text. Silently dropping -n/-t/-e would
    weaken the worker contract invisibly, so they must fail loudly."""
    # Slice to the worker-kind case arm's terminator, NOT the first "  *)":
    # the ds arm contains a nested `case "$DS_MODEL"` with its own default arm.
    ds_guard = _DISPATCH.split("  ds)", 1)[1].split('  *) echo "unknown worker kind', 1)[0]
    for flag in ("-n", "-t", "-e"):
        assert flag in ds_guard, f"ds guard does not reject {flag}"
    assert "DEEPSEEK_API_KEY" in ds_guard
