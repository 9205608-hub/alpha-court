"""Verify a sealed certified ledger (prereg-gate.md §4.1 / §5 / §9).

Verification is **replay + recompute only** — no adapter re-run, no
cross-machine head reproduction. Raises ``CertificationError`` naming the
FIRST violated invariant (ordered below).

Invariant order (ticket v0.2-07 + rework-01):
1. raw completeness + replay-on-COPY (final byte is ``\\n``; every line full
   chain envelope; Ledger.open on a copy succeeds and matches recomputed head)
2. chained (legacy → \"uncertified: no chain\")
3. seal exists and is the FINAL raw line
4. raw event order: run_config #1; policy before first verdict; every
   evaluation precedes the seal
5. seal policy payload == on-chain policy declaration by raw dict equality;
   **exactly one** aggregation_policy declaration (rework-01 FIX 3)
6. seal chain_head == recomputed head before seal; manifest matches final
7. seal scope == derived evaluated set; verdict_ids == ALL verdict events
7.5 exactly one judgment event; its verdict_ids == all chain verdicts == seal's;
    multiset of battery statistics == multiset of verdict statistics (rework-02)
8. every evaluation carries attestation; run_config-overlapping keys match
9. when backend supplied: ``backend.verify(final_head)`` must be True
   (query-by-recomputed-head; never gated on manifest — rework-01 Finding A)
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import tempfile
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from court.ledger import Ledger, content_hash, link_event_hash
from harness.aggregation_policy import AggregationPolicy
from harness.anchor import AnchorBackend, FileAnchor, GitAnchor
from harness.run import CertificationError as CertificationError  # re-export

_GENESIS = "0" * 64
_ENVELOPE_KEYS = frozenset({"type", "at", "prev_hash", "event_hash"})
_RUN_CONFIG_KIND = "run_config"
_POLICY_KIND = "aggregation_policy"
_JUDGMENT_KIND = "judgment"


@dataclass(frozen=True)
class VerificationReport:
    """Outcome of a successful ``verify`` (prereg-gate.md §9).

    ``anchor_ref`` is advisory (from the manifest when present). Non-str
    values are reported faithfully rather than silently coerced to None
    (rework-01 F-6).

    ``anchor_status`` is ``\"verified\"`` when a backend was supplied and
    attested the recomputed head, or ``\"reported\"`` when no backend was
    supplied (rework-02 FIX 3).
    """

    chain_head: str
    seal_event_hash: str
    n_trials: int
    n_verdicts: int
    policy_id: str
    anchor_ref: Any
    anchor_status: str = "reported"


def _fail(msg: str) -> None:
    raise CertificationError(msg)


def _read_raw_lines(path: Path) -> list[str]:
    """Read raw file bytes and apply crisp completeness rule (invariant 1).

    The file's final byte must be the ``\\n`` terminating the seal line.
    Every line must parse as a JSON dict carrying the full chain envelope.
    Trailing blank lines, envelope-less final JSON, or a missing final
    newline all fail — ``Ledger.open`` would silently truncate several of
    these.
    """
    raw = path.read_bytes()
    if not raw:
        _fail("invariant 1: empty ledger file (incomplete / uncertified)")
    if raw[-1:] != b"\n":
        _fail(
            "invariant 1: file final byte is not newline terminating the last "
            "line (missing final newline / incomplete)"
        )
    text = raw.decode("utf-8")
    # splitlines(keepends=False) drops the trailing empty segment after final \n
    lines = text.split("\n")
    if lines and lines[-1] == "":
        lines = lines[:-1]
    if not lines:
        _fail("invariant 1: no events in ledger file")
    # Reject internal blank lines (would be mid-file empty → open truncates last)
    for i, line in enumerate(lines):
        if line == "":
            _fail(f"invariant 1: blank line at raw index {i} (incomplete envelope)")
        try:
            event = json.loads(line)
        except json.JSONDecodeError as exc:
            _fail(f"invariant 1: line {i} is not JSON: {exc}")
        if not isinstance(event, dict):
            _fail(f"invariant 1: line {i} is not a JSON dict")
        missing = _ENVELOPE_KEYS - set(event.keys())
        if missing:
            _fail(
                f"invariant 1: line {i} missing chain envelope keys "
                f"{sorted(missing)} (type/at/prev_hash/event_hash required)"
            )
    return lines


def _parse_events(lines: list[str]) -> list[dict[str, Any]]:
    return [json.loads(line) for line in lines]


def _recompute_chain_head(events: list[dict[str, Any]]) -> str:
    head = _GENESIS
    for event in events:
        if event.get("prev_hash") != head:
            _fail(
                f"chain prev_hash mismatch at type={event.get('type')!r}: "
                f"stored {event.get('prev_hash')!r} != expected {head!r}"
            )
        ch = content_hash(event)
        eh = link_event_hash(head, ch)
        if event.get("event_hash") != eh:
            _fail(
                f"event_hash mismatch at type={event.get('type')!r}: "
                f"stored {event.get('event_hash')!r} != recomputed {eh!r}"
            )
        head = eh
    return head


def _replay_on_copy(path: Path, expected_head: str) -> tuple[int, int]:
    """Invariant 1 (F-2): replay on a COPY — never mutate the source."""
    with tempfile.TemporaryDirectory(prefix="ac-verify-") as tmp:
        copy_path = Path(tmp) / path.name
        shutil.copy2(path, copy_path)
        try:
            ledger = Ledger.open(copy_path)
        except Exception as exc:
            _fail(f"invariant 1: ledger replay failed on copy: {exc}")
        if ledger.chain_head is None:
            _fail("invariant 1: replay produced unchained ledger")
        if ledger.chain_head != expected_head:
            _fail(
                f"invariant 1: replay chain_head {ledger.chain_head!r} != "
                f"recomputed {expected_head!r}"
            )
        return len(ledger.trials()), len(ledger.verdicts())


def _check_raw_order(events: list[dict[str, Any]]) -> None:
    """Invariant 4 — walk raw JSONL lines (read surfaces hide interleaving)."""
    if not events:
        _fail("invariant 4: no events")
    first = events[0]
    if first.get("type") != "declaration":
        _fail(
            "invariant 4: event #1 must be the run_config declaration, "
            f"got type={first.get('type')!r}"
        )
    payload0 = first.get("payload")
    if not isinstance(payload0, dict) or payload0.get("kind") != _RUN_CONFIG_KIND:
        _fail("invariant 4: event #1 must be run_config declaration (kind=run_config)")

    first_verdict_idx: int | None = None
    policy_idx: int | None = None
    for i, ev in enumerate(events):
        et = ev.get("type")
        if et == "verdict" and first_verdict_idx is None:
            first_verdict_idx = i
        if et == "declaration":
            pl = ev.get("payload")
            if isinstance(pl, dict) and pl.get("kind") == _POLICY_KIND:
                if policy_idx is None:
                    policy_idx = i

    if policy_idx is None:
        _fail("invariant 4: no aggregation policy declaration on chain")
    if first_verdict_idx is not None and policy_idx >= first_verdict_idx:
        _fail(
            "invariant 4: policy declaration must precede the first verdict "
            f"(policy at raw index {policy_idx}, first verdict at {first_verdict_idx})"
        )
    # every evaluation precedes the seal — seal is final (inv 3)
    seen_seal = False
    for i, ev in enumerate(events):
        if ev.get("type") == "seal":
            seen_seal = True
        elif seen_seal and ev.get("type") == "evaluation":
            _fail(
                f"invariant 4: evaluation at raw index {i} follows a seal"
            )

    # rework-02 FIX 2: judgment (success-only) must sit after every verdict.
    verdict_indices = [i for i, ev in enumerate(events) if ev.get("type") == "verdict"]
    judgment_indices = [
        i
        for i, ev in enumerate(events)
        if ev.get("type") == "declaration"
        and isinstance(ev.get("payload"), dict)
        and ev["payload"].get("kind") == _JUDGMENT_KIND
    ]
    if judgment_indices and verdict_indices:
        j_idx = judgment_indices[0]
        last_verdict_idx = max(verdict_indices)
        if j_idx <= last_verdict_idx:
            _fail(
                "invariant 4: judgment event must come after every verdict "
                f"(judgment at raw index {j_idx}, last verdict at {last_verdict_idx})"
            )


def _run_config_from_events(events: list[dict[str, Any]]) -> dict:
    for ev in events:
        if ev.get("type") != "declaration":
            continue
        pl = ev.get("payload")
        if isinstance(pl, dict) and pl.get("kind") == _RUN_CONFIG_KIND:
            cfg = pl.get("config")
            if not isinstance(cfg, dict):
                _fail("run_config declaration config is not a dict")
            return cfg
    _fail("missing run_config declaration")
    raise AssertionError("unreachable")  # pragma: no cover


def _policy_declarations(
    events: list[dict[str, Any]],
) -> list[tuple[str, dict]]:
    """All aggregation_policy declarations (declaration_id, payload)."""
    found: list[tuple[str, dict]] = []
    for ev in events:
        if ev.get("type") != "declaration":
            continue
        pl = ev.get("payload")
        if isinstance(pl, dict) and pl.get("kind") == _POLICY_KIND:
            did = ev.get("declaration_id")
            if not isinstance(did, str):
                _fail("policy declaration missing declaration_id")
            found.append((did, pl))
    return found


def _judgment_payloads(events: list[dict[str, Any]]) -> list[dict]:
    out: list[dict] = []
    for ev in events:
        if ev.get("type") != "declaration":
            continue
        pl = ev.get("payload")
        if isinstance(pl, dict) and pl.get("kind") == _JUDGMENT_KIND:
            out.append(pl)
    return out


def _derived_scope_from_events(events: list[dict[str, Any]]) -> list[str]:
    """Registration-order trials that have an evaluation event."""
    order: list[str] = []
    evaluated: set[str] = set()
    for ev in events:
        if ev.get("type") == "trial":
            tid = ev["trial_id"]
            order.append(tid)
        elif ev.get("type") == "evaluation":
            evaluated.add(ev["trial_id"])
    return [tid for tid in order if tid in evaluated]


def verify(
    path: str | Path,
    anchor: AnchorBackend | None = None,
) -> VerificationReport:
    """Verify a sealed certified ledger; raise on the first violated invariant."""
    path = Path(path)
    if not path.is_file():
        _fail(f"ledger path does not exist or is not a file: {path}")

    # --- invariant 1: raw completeness ---------------------------------------
    lines = _read_raw_lines(path)
    events = _parse_events(lines)

    # --- invariant 2: chained ------------------------------------------------
    for i, ev in enumerate(events):
        ph = ev.get("prev_hash")
        eh = ev.get("event_hash")
        if not isinstance(ph, str) or not ph:
            _fail("uncertified: no chain (legacy or missing prev_hash)")
        if not isinstance(eh, str) or not eh:
            _fail("uncertified: no chain (legacy or missing event_hash)")
        if len(eh) != 64:
            _fail("uncertified: no chain (malformed event_hash)")
        if len(ph) != 64:
            _fail("uncertified: no chain (malformed prev_hash)")

    # Recompute full chain (also catches mid-file content tamper)
    final_head = _recompute_chain_head(events)

    # invariant 1 continued: replay-on-COPY (ticket lists under inv 1; F-2)
    n_trials, n_verdicts = _replay_on_copy(path, final_head)

    # --- invariant 3: seal exists and is FINAL raw line ----------------------
    seal_indices = [i for i, ev in enumerate(events) if ev.get("type") == "seal"]
    if not seal_indices:
        _fail("no seal: ledger is unsealed / uncertified")
    if seal_indices[-1] != len(events) - 1:
        _fail("invariant 3: seal must be the final raw line")
    if len(seal_indices) != 1:
        _fail("invariant 3: more than one seal event on chain")
    seal_event = events[-1]
    seal_payload = seal_event.get("payload")
    if not isinstance(seal_payload, dict):
        _fail("invariant 3: seal payload must be a dict")

    # --- invariant 4: raw event order ----------------------------------------
    _check_raw_order(events)

    # --- invariant 5: exactly one policy + seal policy raw equality ----------
    policy_decls = _policy_declarations(events)
    if len(policy_decls) == 0:
        _fail("invariant 5: no aggregation_policy declaration on chain")
    if len(policy_decls) != 1:
        _fail(
            f"invariant 5: exactly one aggregation_policy declaration required, "
            f"found {len(policy_decls)}"
        )
    policy_did, on_chain_policy = policy_decls[0]
    seal_policy = seal_payload.get("policy")
    if seal_policy != on_chain_policy:
        _fail(
            "invariant 5: seal policy payload does not equal on-chain policy "
            "declaration payload (raw dict equality; smuggled keys must fail)"
        )
    if seal_payload.get("policy_declaration_id") != policy_did:
        _fail(
            "invariant 5: seal policy_declaration_id does not match on-chain "
            f"declaration id {policy_did!r}"
        )

    # --- invariant 6: seal chain_head + optional manifest --------------------
    events_before_seal = events[:-1]
    head_before = (
        _recompute_chain_head(events_before_seal) if events_before_seal else _GENESIS
    )
    if seal_payload.get("chain_head") != head_before:
        _fail(
            "invariant 6: seal chain_head does not equal recomputed head over "
            f"events before seal (seal={seal_payload.get('chain_head')!r}, "
            f"recomputed={head_before!r})"
        )
    seal_event_hash = seal_event["event_hash"]
    if seal_event_hash != final_head:
        _fail(
            "invariant 6: seal event_hash is not the final chain head "
            f"({seal_event_hash!r} != {final_head!r})"
        )

    # Advisory only — never trusted for the anchor decision (Finding A).
    manifest_anchor_ref: Any = None
    manifest_path = path.parent / "run_manifest.json"
    if manifest_path.is_file():
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            _fail(f"invariant 6: run_manifest.json is not valid JSON: {exc}")
        if not isinstance(manifest, dict):
            _fail("invariant 6: run_manifest.json must be a JSON object")
        if manifest.get("chain_head") != final_head:
            _fail(
                "invariant 6: manifest chain_head mismatch "
                f"(manifest={manifest.get('chain_head')!r}, final={final_head!r})"
            )
        if manifest.get("seal_event_hash") != seal_event_hash:
            _fail(
                "invariant 6: manifest seal_event_hash mismatch "
                f"(manifest={manifest.get('seal_event_hash')!r}, "
                f"seal={seal_event_hash!r})"
            )
        # F-6: report faithfully; do not silently coerce non-str to None.
        if "anchor_ref" in manifest:
            manifest_anchor_ref = manifest.get("anchor_ref")

    # --- invariant 7: scope + all verdict ids --------------------------------
    derived_scope = _derived_scope_from_events(events)
    seal_scope = seal_payload.get("scope")
    if seal_scope != derived_scope:
        _fail(
            "invariant 7: seal scope does not equal derived registered-and-"
            f"evaluated set (seal={seal_scope!r}, derived={derived_scope!r})"
        )
    all_verdict_ids = [
        ev["verdict_id"] for ev in events if ev.get("type") == "verdict"
    ]
    seal_vids = seal_payload.get("verdict_ids")
    if seal_vids != all_verdict_ids:
        _fail(
            "invariant 7: seal verdict_ids must equal ALL verdict events on the "
            f"chain (wild/smuggled verdict) seal={seal_vids!r} "
            f"chain={all_verdict_ids!r}"
        )

    # --- invariant 7.5: covering judgment event (rework-01 F-1) --------------
    jpayloads = _judgment_payloads(events)
    if len(jpayloads) == 0:
        _fail(
            "invariant 7.5: no judgment event on sealed ledger "
            "(verdicts without a covering judgment)"
        )
    if len(jpayloads) != 1:
        _fail(
            f"invariant 7.5: exactly one judgment event required, "
            f"found {len(jpayloads)}"
        )
    j_vids = jpayloads[0].get("verdict_ids")
    if j_vids != all_verdict_ids:
        _fail(
            "invariant 7.5: judgment verdict_ids must equal ALL verdict events "
            f"(judgment={j_vids!r}, chain={all_verdict_ids!r})"
        )
    if j_vids != seal_vids:
        _fail(
            "invariant 7.5: judgment verdict_ids must equal seal verdict_ids "
            f"(judgment={j_vids!r}, seal={seal_vids!r})"
        )
    # rework-02 FIX 1: battery statistics multiset == verdict statistics multiset
    battery = jpayloads[0].get("battery")
    if not isinstance(battery, list):
        _fail("invariant 7.5: judgment battery must be a list")
    battery_stats: list[str] = []
    for i, app in enumerate(battery):
        if not isinstance(app, dict) or "statistic" not in app:
            _fail(
                f"invariant 7.5: judgment battery[{i}] must be a dict with "
                "'statistic'"
            )
        battery_stats.append(app["statistic"])
    verdict_stats = [
        ev["statistic"] for ev in events if ev.get("type") == "verdict"
    ]
    if Counter(battery_stats) != Counter(verdict_stats):
        _fail(
            "invariant 7.5: judgment battery does not match verdict statistics "
            f"(battery={sorted(battery_stats)!r}, "
            f"verdicts={sorted(verdict_stats)!r})"
        )

    # --- invariant 8: evaluation attestations vs run_config ------------------
    run_config = _run_config_from_events(events)
    for i, ev in enumerate(events):
        if ev.get("type") != "evaluation":
            continue
        att = ev.get("attestation")
        if not isinstance(att, dict):
            _fail(
                f"invariant 8: evaluation at raw index {i} missing attestation dict"
            )
        for key in att:
            if key not in run_config:
                continue
            if att[key] != run_config[key]:
                _fail(
                    f"invariant 8: evaluation attestation key {key!r} conflicts "
                    f"with run_config (attestation={att[key]!r}, "
                    f"run_config={run_config[key]!r})"
                )

    # --- invariant 9: optional anchor (query-by-recomputed-head) -------------
    # Never gate on the manifest's anchor_ref (Finding A / rework-01 FIX 2).
    anchor_status = "reported"
    if anchor is not None:
        try:
            ok = anchor.verify(final_head)
        except Exception as exc:
            _fail(
                "anchor supplied but does not attest the recomputed head "
                f"(backend error: {exc})"
            )
        if not ok:
            _fail(
                "anchor supplied but does not attest the recomputed head "
                f"(head={final_head!r})"
            )
        anchor_status = "verified"

    # policy_id for the report
    try:
        policy_obj = AggregationPolicy.from_payload(on_chain_policy)
        policy_id = policy_obj.policy_id
    except ValueError as exc:
        _fail(f"on-chain policy payload is not a valid AggregationPolicy: {exc}")
        raise AssertionError("unreachable") from exc  # pragma: no cover

    return VerificationReport(
        chain_head=final_head,
        seal_event_hash=seal_event_hash,
        n_trials=n_trials,
        n_verdicts=n_verdicts,
        policy_id=policy_id,
        anchor_ref=manifest_anchor_ref,
        anchor_status=anchor_status,
    )


def _parse_anchor_arg(spec: str | None) -> AnchorBackend | None:
    """Parse ``--anchor file:<path>|git:<repo>|none`` (rework-02 FIX 3)."""
    if spec is None or spec == "none":
        return None
    if ":" not in spec:
        raise ValueError(
            f"invalid --anchor {spec!r}; expected file:<path>, git:<repo>, or none"
        )
    kind, _, rest = spec.partition(":")
    if kind == "file":
        if not rest:
            raise ValueError("--anchor file: requires a path")
        return FileAnchor(rest)
    if kind == "git":
        if not rest:
            raise ValueError("--anchor git: requires a repo_dir")
        return GitAnchor(rest)
    if kind == "none":
        return None
    raise ValueError(
        f"unknown --anchor kind {kind!r}; expected file, git, or none"
    )


def main(argv: list[str] | None = None) -> int:
    """CLI: ``python -m harness.verify <ledger.jsonl> [--anchor ...]``."""
    parser = argparse.ArgumentParser(
        prog="python -m harness.verify",
        description="Verify a sealed certified ledger (prereg-gate / ticket 07).",
    )
    parser.add_argument("ledger", help="path to the sealed ledger JSONL")
    parser.add_argument(
        "--anchor",
        default=None,
        metavar="SPEC",
        help="optional backend: file:<path>, git:<repo_dir>, or none (default)",
    )
    ns = parser.parse_args(list(sys.argv[1:] if argv is None else argv))
    try:
        backend = _parse_anchor_arg(ns.anchor)
    except (ValueError, OSError) as exc:
        # OSError: FileAnchor/GitAnchor construction touches the filesystem;
        # a malformed path (e.g. file:/dev/null/foo) must exit 1 cleanly, not
        # escape as a traceback (v0.2-12 F).
        print(str(exc), file=sys.stderr)
        return 1
    try:
        report = verify(ns.ledger, anchor=backend)
    except CertificationError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(
        json.dumps(
            {
                "chain_head": report.chain_head,
                "seal_event_hash": report.seal_event_hash,
                "n_trials": report.n_trials,
                "n_verdicts": report.n_verdicts,
                "policy_id": report.policy_id,
                "anchor_ref": report.anchor_ref,
                "anchor_status": report.anchor_status,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
