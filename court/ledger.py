"""Append-only trial ledger: hypothesis / trial / evaluation / verdict event log.

Implements court-kernel-spec.md §5.7 and trial-ledger.md §5–7. Pure bookkeeping —
no statistics, no imports from other court modules.

v0.2 evidence layer (prereg-gate.md §3–§5): optional source_ref, evaluation
attestation checks, content hash-chain, court-opaque declaration/seal events.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import struct
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

# ---------------------------------------------------------------------------
# Record types (court-kernel-spec.md §5.7; trial-ledger.md §5)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SeConvention:
    """Standard-error convention declared at trial registration.

    trial-ledger.md §5.2; ruling E2: newey_west requires explicit lags.
    """

    kind: str  # "iid" | "newey_west"
    lags: int | None = None  # required iff kind == "newey_west"


@dataclass(frozen=True)
class Window:
    """Declared evaluation window; opaque labels (trial-ledger.md §5.2 / §9)."""

    start: str
    end: str


@dataclass(frozen=True)
class DeclaredProtocol:
    """Protocol locked before evaluation (trial-ledger.md §5.2; ruling B10)."""

    metric: str  # "returns" | "ic"
    window: Window
    periods_per_year: float
    direction: str = "two-sided"  # "two-sided" | "greater" | "less"
    se: SeConvention = SeConvention(kind="iid")


@dataclass(frozen=True)
class Series:
    """Performance series stored by value (trial-ledger.md §5.2)."""

    index: tuple[str, ...]
    values: tuple[float, ...]


@dataclass(frozen=True)
class HypothesisRecord:
    """Economic claim declaration (trial-ledger.md §5.1)."""

    hypothesis_id: str
    statement: str
    created_at: str  # ISO-8601 UTC


@dataclass(frozen=True)
class TrialRecord:
    """Assembled from registration + at most one evaluation (trial-ledger.md §5.2)."""

    trial_id: str
    hypothesis_id: str
    spec: dict
    params: dict
    registered_at: str
    declared: DeclaredProtocol
    source_ref: str | None = None
    series: Series | None = None
    evaluated_at: str | None = None
    attestation: dict | None = None


@dataclass(frozen=True)
class VerdictRecord:
    """One statistic applied to one scope (trial-ledger.md §5.3)."""

    verdict_id: str
    statistic: str
    scope: tuple[str, ...]
    params: dict
    computed: dict
    decisions: dict[str, str]
    judged_at: str
    engine_version: str | None = None
    # role: "discriminating" | "informational" | None (legacy pre-v0.2).
    # Derived at judgment time; see selection-verdict-isomorphism.md Q3 / D16.
    role: str | None = None


@dataclass(frozen=True)
class DeclarationRecord:
    """Court-opaque declaration event (prereg-gate.md §3; payload uninterpreted)."""

    declaration_id: str
    payload: dict
    created_at: str


@dataclass(frozen=True)
class SealRecord:
    """Court-opaque seal event; must be the final event (prereg-gate.md §4.2 / §5)."""

    seal_id: str
    payload: dict
    created_at: str


class LedgerCorruptionError(RuntimeError):
    """Replay-time corruption of the JSONL event log (ruling B8; §3.5)."""


# Genesis prev_hash for a chained ledger (prereg-gate.md §4.1).
_GENESIS_HASH = "0" * 64
_HASH_EXCLUDE = frozenset({"at", "prev_hash", "event_hash"})
_WINDOW_KEYS = frozenset({"start", "end"})


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------

_VALID_METRICS = frozenset({"returns", "ic"})
_VALID_DIRECTIONS = frozenset({"two-sided", "greater", "less"})
_VALID_SE_KINDS = frozenset({"iid", "newey_west"})
_VALID_DECISIONS = frozenset({"pass", "reject"})


def _utc_now_iso() -> str:
    """ISO-8601 UTC with explicit offset (ruling B6)."""
    return datetime.now(timezone.utc).isoformat()


def _require_json_serializable(obj: Any, name: str) -> None:
    """Fail-closed JSON boundary (ruling B9): json.dumps(..., allow_nan=False)."""
    try:
        json.dumps(obj, allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} is not JSON-serializable: {exc}") from exc


def _pretransform_for_hash(obj: Any) -> Any:
    """Recursively replace floats with little-endian IEEE-754 hex (prereg-gate §4.1).

    bool is not float; ints stay ints. NaN/Inf must already be impossible.
    Dict keys must be str: non-str keys would sort differently at write vs
    after json.loads (int keys → str keys), causing a false-positive chain
    break. Fail closed with ValueError — never coerce.
    """
    if isinstance(obj, float):
        return struct.pack("<d", obj).hex()
    if isinstance(obj, dict):
        out: dict[str, Any] = {}
        for k, v in obj.items():
            if not isinstance(k, str):
                raise ValueError(
                    f"dict keys on the hash path must be str, got "
                    f"{type(k).__name__} key {k!r}"
                )
            out[k] = _pretransform_for_hash(v)
        return out
    if isinstance(obj, list):
        return [_pretransform_for_hash(v) for v in obj]
    if isinstance(obj, tuple):
        return [_pretransform_for_hash(v) for v in obj]
    return obj


def canonical_json(obj: Any) -> str:
    """Canonical JSON for the hash path only (storage lines stay insertion-order)."""
    return json.dumps(
        _pretransform_for_hash(obj),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def content_hash(event: Mapping[str, Any]) -> str:
    """SHA-256 hex of canonical_json(event minus at/prev_hash/event_hash)."""
    content = {k: v for k, v in event.items() if k not in _HASH_EXCLUDE}
    return hashlib.sha256(canonical_json(content).encode("utf-8")).hexdigest()


def link_event_hash(prev_hash: str, content_hash_hex: str) -> str:
    """event_hash = sha256( (prev_hash + content_hash).encode('ascii') )."""
    return hashlib.sha256((prev_hash + content_hash_hex).encode("ascii")).hexdigest()


def _validate_attestation(
    attestation: dict,
    declared: DeclaredProtocol,
    series: Series,
) -> None:
    """Fail-closed attestation-vs-declared checks (prereg-gate Q4 / ticket §2)."""
    _require_json_serializable(attestation, "attestation")
    if "metric" not in attestation:
        raise ValueError("attestation missing required key 'metric'")
    if "window" not in attestation:
        raise ValueError("attestation missing required key 'window'")
    if attestation["metric"] != declared.metric:
        raise ValueError(
            f"attestation metric {attestation['metric']!r} != declared.metric "
            f"{declared.metric!r}"
        )
    window = attestation["window"]
    if not isinstance(window, Mapping):
        raise ValueError("attestation window must be a mapping")
    if set(window.keys()) != _WINDOW_KEYS:
        raise ValueError(
            "attestation window must contain exactly keys {'start', 'end'}, "
            f"got {sorted(window.keys())}"
        )
    if window["start"] != declared.window.start or window["end"] != declared.window.end:
        raise ValueError(
            f"attestation window {dict(window)!r} != declared.window "
            f"({declared.window.start!r}, {declared.window.end!r})"
        )
    if "n_evaluation_dates" in attestation:
        n = attestation["n_evaluation_dates"]
        if isinstance(n, bool) or not isinstance(n, int):
            raise ValueError(
                f"attestation n_evaluation_dates must be a non-bool int, got {n!r}"
            )
        if n != len(series.values):
            raise ValueError(
                f"attestation n_evaluation_dates {n} != len(series.values) "
                f"{len(series.values)}"
            )


def _validate_declared(declared: DeclaredProtocol) -> None:
    """Malformed declared protocol guards (§5.7 fail-closed table / register)."""
    if declared.metric not in _VALID_METRICS:
        raise ValueError(
            f"declared.metric must be one of {sorted(_VALID_METRICS)}, "
            f"got {declared.metric!r}"
        )
    if declared.direction not in _VALID_DIRECTIONS:
        raise ValueError(
            f"declared.direction must be one of {sorted(_VALID_DIRECTIONS)}, "
            f"got {declared.direction!r}"
        )
    if declared.periods_per_year <= 0:
        raise ValueError(
            f"declared.periods_per_year must be > 0, got {declared.periods_per_year!r}"
        )
    se = declared.se
    if se.kind not in _VALID_SE_KINDS:
        raise ValueError(
            f"declared.se.kind must be one of {sorted(_VALID_SE_KINDS)}, got {se.kind!r}"
        )
    if se.kind == "iid" and se.lags is not None:
        raise ValueError("declared.se.lags must be None when se.kind is 'iid'")
    if se.kind == "newey_west":
        if se.lags is None:
            raise ValueError("declared.se.lags is required when se.kind is 'newey_west'")
        if not isinstance(se.lags, int) or isinstance(se.lags, bool) or se.lags < 0:
            raise ValueError(
                f"declared.se.lags must be an int >= 0 when se.kind is 'newey_west', "
                f"got {se.lags!r}"
            )


def _validate_series(series: Series) -> None:
    """Series guards for record() (§5.7; rulings B2, B5)."""
    if len(series.index) != len(series.values):
        raise ValueError(
            f"series index/values length mismatch: "
            f"{len(series.index)} != {len(series.values)}"
        )
    if len(series.index) == 0:
        raise ValueError("series must be non-empty")
    if len(set(series.index)) != len(series.index):
        raise ValueError("series index labels must be unique within the series")
    for i, v in enumerate(series.values):
        if not isinstance(v, (int, float)) or isinstance(v, bool) or not math.isfinite(v):
            raise ValueError(f"series values must be finite floats; bad value at {i}: {v!r}")


def _declared_to_dict(declared: DeclaredProtocol) -> dict[str, Any]:
    return {
        "metric": declared.metric,
        "window": {"start": declared.window.start, "end": declared.window.end},
        "periods_per_year": declared.periods_per_year,
        "direction": declared.direction,
        "se": {"kind": declared.se.kind, "lags": declared.se.lags},
    }


def _declared_from_dict(d: dict[str, Any]) -> DeclaredProtocol:
    se_raw = d["se"]
    return DeclaredProtocol(
        metric=d["metric"],
        window=Window(start=d["window"]["start"], end=d["window"]["end"]),
        periods_per_year=float(d["periods_per_year"]),
        direction=d.get("direction", "two-sided"),
        se=SeConvention(kind=se_raw["kind"], lags=se_raw.get("lags")),
    )


def _series_to_dict(series: Series) -> dict[str, Any]:
    return {"index": list(series.index), "values": list(series.values)}


def _series_from_dict(d: dict[str, Any]) -> Series:
    return Series(
        index=tuple(str(x) for x in d["index"]),
        values=tuple(float(x) for x in d["values"]),
    )


def _format_id(prefix: str, n: int) -> str:
    """Zero-padded sequential ids (ruling B3): h-/t-/v-/d-/s-000001."""
    return f"{prefix}-{n:06d}"


# ---------------------------------------------------------------------------
# Ledger
# ---------------------------------------------------------------------------


class Ledger:
    """Append-only JSONL trial ledger (trial-ledger.md §6–7; spec §5.7).

    Three layers: this class is pure bookkeeping and understands no statistics.
    Homogeneous per file: either fully chained (hash fields on every event) or
    fully legacy (no hash fields); mixed files raise LedgerCorruptionError.
    """

    def __init__(self, path: Path) -> None:
        self._path = path
        self._hypotheses: dict[str, HypothesisRecord] = {}
        self._trials: dict[str, TrialRecord] = {}
        self._trial_order: list[str] = []
        self._verdicts: list[VerdictRecord] = []
        self._judged_trials: set[str] = set()
        self._declarations: list[DeclarationRecord] = []
        self._seal: SealRecord | None = None
        self._next_h = 1
        self._next_t = 1
        self._next_v = 1
        self._next_d = 1
        self._next_s = 1
        # New/empty files are chained (prereg-gate / ticket §4).
        self._chained: bool = True
        self._chain_head: str | None = _GENESIS_HASH
        self._mode_determined: bool = False

    # -- construction / replay -------------------------------------------------

    @classmethod
    def open(cls, path: str | Path) -> Ledger:
        """Create the file if absent; otherwise replay and index it.

        Torn final line: truncate + fsync, then proceed (ruling B8).
        Mid-file unparseable line or invariant violation → LedgerCorruptionError.
        Legacy/chained mode is decided after torn-final truncation from the first
        intact event (empty after truncation → chained).
        """
        path = Path(path)
        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.touch()
            # fsync the parent so the new directory entry is durable — content
            # fsyncs alone do not cover create (§7.1 durability; v0.2-12 D).
            dir_fd = os.open(path.parent, os.O_RDONLY)
            try:
                os.fsync(dir_fd)
            finally:
                os.close(dir_fd)
            return cls(path)

        raw = path.read_bytes()
        if raw == b"":
            return cls(path)

        ledger = cls(path)
        # Reconstruct line spans from raw BYTES for accurate truncate (ruling
        # B8): offsets feed f.truncate(nbytes), so they must be byte offsets —
        # character-counted spans undercount any non-ASCII content, and a torn
        # tail cutting a multi-byte sequence in half must not crash decoding.
        # If raw ends with \n, the final split segment is empty and is not a line.
        parts = raw.split(b"\n")
        content_parts = parts if not raw.endswith(b"\n") else parts[:-1]

        line_spans: list[tuple[int, int, bytes]] = []
        pos = 0
        for part in content_parts:
            start = pos
            end = pos + len(part)
            line_spans.append((start, end, part))
            pos = end + 1  # account for the separating newline

        for i, (start, _end, chunk) in enumerate(line_spans):
            is_last = i == len(line_spans) - 1
            if chunk == b"":
                if is_last:
                    ledger._truncate_to(start)
                    break
                raise LedgerCorruptionError(
                    f"unparseable empty line at mid-file offset {start}"
                )
            try:
                text = chunk.decode("utf-8")
            except UnicodeDecodeError as exc:
                if is_last:
                    # Torn trailing line (mid-sequence cut): truncate (B8).
                    ledger._truncate_to(start)
                    break
                raise LedgerCorruptionError(
                    f"undecodable mid-file line at offset {start}: {exc}"
                ) from exc
            try:
                event = json.loads(text)
            except json.JSONDecodeError as exc:
                if is_last:
                    # Torn trailing line: truncate from file (ruling B8).
                    ledger._truncate_to(start)
                    break
                raise LedgerCorruptionError(
                    f"unparseable mid-file line at offset {start}: {exc}"
                ) from exc
            if not isinstance(event, dict) or "type" not in event or "at" not in event:
                if is_last:
                    ledger._truncate_to(start)
                    break
                raise LedgerCorruptionError(f"invalid event envelope at offset {start}")
            try:
                ledger._replay_one(event)
            except LedgerCorruptionError:
                raise
            except Exception as exc:
                # Invariant violations during replay are corruption.
                raise LedgerCorruptionError(
                    f"replay invariant violation at offset {start}: {exc}"
                ) from exc

        # Empty after truncation (or no intact events) remains chained.
        if not ledger._mode_determined:
            ledger._chained = True
            ledger._chain_head = _GENESIS_HASH

        return ledger

    def _truncate_to(self, nbytes: int) -> None:
        """Truncate the ledger file to nbytes and fsync (ruling B8)."""
        with self._path.open("r+b") as f:
            f.truncate(nbytes)
            f.flush()
            os.fsync(f.fileno())

    def _replay_one(self, event: dict[str, Any]) -> None:
        """Replay one intact event: mode, chain verify, seal-final, apply."""
        has_hash = "event_hash" in event
        if not self._mode_determined:
            self._mode_determined = True
            self._chained = has_hash
            if self._chained:
                self._chain_head = _GENESIS_HASH
            else:
                self._chain_head = None
        elif self._chained != has_hash:
            raise LedgerCorruptionError(
                "mixed chained/legacy events in ledger file (homogeneous per file)"
            )

        if self._chained:
            if "prev_hash" not in event or "event_hash" not in event:
                raise LedgerCorruptionError(
                    "chained event missing prev_hash or event_hash"
                )
            expected_prev = self._chain_head
            assert expected_prev is not None
            if event["prev_hash"] != expected_prev:
                raise LedgerCorruptionError(
                    f"prev_hash mismatch: stored {event['prev_hash']!r} != "
                    f"expected {expected_prev!r}"
                )
            ch = content_hash(event)
            eh = link_event_hash(expected_prev, ch)
            if event["event_hash"] != eh:
                raise LedgerCorruptionError(
                    f"event_hash mismatch for type={event.get('type')!r}: "
                    f"stored {event['event_hash']!r} != recomputed {eh!r}"
                )
            self._chain_head = eh

        if self._seal is not None:
            raise LedgerCorruptionError(
                "event after seal (seal must be the final event)"
            )

        self._apply_event(event, corrupt_on_error=True)

    def _apply_event(self, event: dict[str, Any], *, corrupt_on_error: bool) -> None:
        """Apply one event to the in-memory index (replay or post-append)."""
        etype = event["type"]
        at = event["at"]

        def _err(msg: str) -> None:
            if corrupt_on_error:
                raise LedgerCorruptionError(msg)
            raise ValueError(msg)

        if etype == "hypothesis":
            hid = event["hypothesis_id"]
            if hid in self._hypotheses:
                _err(f"duplicate hypothesis_id {hid!r}")
            rec = HypothesisRecord(
                hypothesis_id=hid,
                statement=event["statement"],
                created_at=at,
            )
            self._hypotheses[hid] = rec
            self._bump_counter_from_id(hid, "h")
        elif etype == "trial":
            tid = event["trial_id"]
            hid = event["hypothesis_id"]
            if tid in self._trials:
                _err(f"duplicate trial_id {tid!r}")
            if hid not in self._hypotheses:
                _err(f"trial references unknown hypothesis_id {hid!r}")
            declared = _declared_from_dict(event["declared"])
            try:
                _validate_declared(declared)
            except ValueError as exc:
                # Same validator as the write path (v0.2-12 slice B symmetry).
                _err(f"trial {tid!r} declared protocol invalid: {exc}")
            rec = TrialRecord(
                trial_id=tid,
                hypothesis_id=hid,
                spec=event["spec"],
                params=event["params"],
                registered_at=at,
                declared=declared,
                source_ref=event.get("source_ref"),
            )
            self._trials[tid] = rec
            self._trial_order.append(tid)
            self._bump_counter_from_id(tid, "t")
        elif etype == "evaluation":
            tid = event["trial_id"]
            if tid not in self._trials:
                _err(f"evaluation references unknown trial_id {tid!r}")
            existing = self._trials[tid]
            if existing.series is not None:
                _err(f"duplicate evaluation for trial_id {tid!r}")
            series = _series_from_dict(event["series"])
            try:
                # Same validator as record() (RP-1 finding 0 on v0.2-12).
                _validate_series(series)
            except ValueError as exc:
                _err(f"evaluation for trial {tid!r} series invalid: {exc}")
            attestation = event.get("attestation")
            if attestation is not None:
                try:
                    if not isinstance(attestation, dict):
                        raise ValueError("attestation must be a dict")
                    _validate_attestation(attestation, existing.declared, series)
                except ValueError as exc:
                    if corrupt_on_error:
                        raise LedgerCorruptionError(
                            f"attestation invariant violation on replay: {exc}"
                        ) from exc
                    raise
            self._trials[tid] = replace(
                existing,
                series=series,
                evaluated_at=at,
                attestation=attestation,
            )
        elif etype == "verdict":
            vid = event["verdict_id"]
            scope = tuple(event["scope"])
            decisions = dict(event["decisions"])
            role = event.get("role")
            # Write-path emptiness guards mirrored (RP-1 finding 1 on v0.2-12).
            if not event["statistic"]:
                _err(f"verdict {vid!r} statistic must be a non-empty string")
            if not scope:
                _err(f"verdict {vid!r} scope must be non-empty")
            for tid in scope:
                if tid not in self._trials:
                    _err(f"verdict scope references unknown trial_id {tid!r}")
            # Write-path checks mirrored on replay (v0.2-12 slice B symmetry).
            for tid, decision in decisions.items():
                if tid not in self._trials:
                    _err(f"verdict decisions reference unknown trial_id {tid!r}")
                if decision not in _VALID_DECISIONS:
                    _err(
                        f"verdict {vid!r} decision for {tid!r} must be 'pass' "
                        f"or 'reject', got {decision!r}"
                    )
            outside = sorted(set(decisions) - set(scope))
            if outside:
                _err(
                    f"verdict {vid!r} decisions reference trials outside its "
                    f"scope: {outside}"
                )
            if role is not None and role not in ("discriminating", "informational"):
                _err(
                    f"verdict {vid!r} role must be None, 'discriminating', or "
                    f"'informational', got {role!r}"
                )
            rec = VerdictRecord(
                verdict_id=vid,
                statistic=event["statistic"],
                scope=scope,
                params=event["params"],
                computed=event["computed"],
                decisions=decisions,
                judged_at=at,
                engine_version=event.get("engine_version"),
                role=role,
            )
            self._verdicts.append(rec)
            self._judged_trials.update(decisions.keys())
            self._bump_counter_from_id(vid, "v")
        elif etype == "declaration":
            did = event["declaration_id"]
            payload = event["payload"]
            if not isinstance(payload, dict):
                _err("declaration payload must be a dict")
            rec_d = DeclarationRecord(
                declaration_id=did,
                payload=payload,
                created_at=at,
            )
            self._declarations.append(rec_d)
            self._bump_counter_from_id(did, "d")
        elif etype == "seal":
            if self._seal is not None:
                _err("second seal event")
            sid = event["seal_id"]
            payload = event["payload"]
            if not isinstance(payload, dict):
                _err("seal payload must be a dict")
            self._seal = SealRecord(
                seal_id=sid,
                payload=payload,
                created_at=at,
            )
            self._bump_counter_from_id(sid, "s")
        else:
            _err(f"unknown event type {etype!r}")

    def _bump_counter_from_id(self, id_: str, prefix: str) -> None:
        """Advance sequential id counters past any id seen during replay."""
        # format: p-000001
        try:
            n = int(id_.split("-", 1)[1])
        except (IndexError, ValueError):
            return
        if prefix == "h":
            self._next_h = max(self._next_h, n + 1)
        elif prefix == "t":
            self._next_t = max(self._next_t, n + 1)
        elif prefix == "v":
            self._next_v = max(self._next_v, n + 1)
        elif prefix == "d":
            self._next_d = max(self._next_d, n + 1)
        elif prefix == "s":
            self._next_s = max(self._next_s, n + 1)

    # -- durable append --------------------------------------------------------

    def _require_not_sealed(self) -> None:
        if self._seal is not None:
            raise ValueError("ledger is sealed; no further mutations allowed")

    def _append_event(self, event: dict[str, Any]) -> None:
        """Hash (if chained) then json.dumps + newline + flush + fsync (B4/B9).

        Storage-line serialization is frozen (insertion order, default ensure_ascii,
        allow_nan=False). Hash fields are appended last before the write.
        chain_head advances only after the durable write returns.
        """
        new_head: str | None = None
        if self._chained:
            prev = self._chain_head
            assert prev is not None
            ch = content_hash(event)
            eh = link_event_hash(prev, ch)
            # Append last in insertion order (ticket §3).
            event["prev_hash"] = prev
            event["event_hash"] = eh
            new_head = eh
        line = json.dumps(event, allow_nan=False, separators=(",", ":"))
        with self._path.open("a", encoding="utf-8") as f:
            f.write(line)
            f.write("\n")
            f.flush()
            os.fsync(f.fileno())
        if new_head is not None:
            self._chain_head = new_head

    # -- write side ------------------------------------------------------------

    def register_hypothesis(self, statement: str) -> str:
        """Declare an economic claim (trial-ledger.md §7.1)."""
        self._require_not_sealed()
        hid = _format_id("h", self._next_h)
        self._next_h += 1
        at = _utc_now_iso()
        event = {
            "type": "hypothesis",
            "at": at,
            "hypothesis_id": hid,
            "statement": statement,
        }
        self._append_event(event)
        self._apply_event(event, corrupt_on_error=False)
        return hid

    def register(
        self,
        hypothesis_id: str,
        spec: dict,
        params: dict,
        declared: DeclaredProtocol,
        source_ref: str | None = None,
    ) -> str:
        """Register one trial; stamps registered_at (trial-ledger.md §7.1)."""
        self._require_not_sealed()
        if hypothesis_id not in self._hypotheses:
            raise ValueError(f"unknown hypothesis_id {hypothesis_id!r}")
        if source_ref is not None and not isinstance(source_ref, str):
            raise ValueError(
                f"source_ref must be str or None, got {type(source_ref).__name__}"
            )
        _validate_declared(declared)
        _require_json_serializable(spec, "spec")
        _require_json_serializable(params, "params")

        tid = _format_id("t", self._next_t)
        self._next_t += 1
        at = _utc_now_iso()
        event = {
            "type": "trial",
            "at": at,
            "trial_id": tid,
            "hypothesis_id": hypothesis_id,
            "spec": spec,
            "params": params,
            "declared": _declared_to_dict(declared),
            "source_ref": source_ref,
        }
        # Ensure full event is serializable before write.
        _require_json_serializable(event, "trial event")
        self._append_event(event)
        self._apply_event(event, corrupt_on_error=False)
        return tid

    def record(
        self,
        trial_id: str,
        series: Series,
        attestation: dict | None = None,
    ) -> None:
        """Attach the performance series; stamps evaluated_at (§7.1)."""
        self._require_not_sealed()
        if trial_id not in self._trials:
            raise ValueError(f"unknown trial_id {trial_id!r}")
        if self._trials[trial_id].series is not None:
            raise ValueError(f"trial {trial_id!r} is already evaluated")
        _validate_series(series)
        if attestation is not None:
            if not isinstance(attestation, dict):
                raise ValueError("attestation must be a dict")
            _validate_attestation(attestation, self._trials[trial_id].declared, series)

        at = _utc_now_iso()
        event: dict[str, Any] = {
            "type": "evaluation",
            "at": at,
            "trial_id": trial_id,
            "series": _series_to_dict(series),
        }
        if attestation is not None:
            event["attestation"] = attestation
        _require_json_serializable(event, "evaluation event")
        self._append_event(event)
        self._apply_event(event, corrupt_on_error=False)

    def append_verdict(
        self,
        statistic: str,
        scope: Sequence[str],
        params: dict,
        computed: dict,
        decisions: dict[str, str],
        engine_version: str | None = None,
        role: str | None = None,
    ) -> str:
        """Write-side entry for the judge layer (trial-ledger.md §7.1)."""
        self._require_not_sealed()
        if not statistic:
            raise ValueError("statistic must be a non-empty string")
        if not scope:
            raise ValueError("scope must be non-empty")
        if role is not None and role not in ("discriminating", "informational"):
            raise ValueError(
                f"role must be None, 'discriminating', or 'informational', "
                f"got {role!r}"
            )
        scope_list = list(scope)
        for tid in scope_list:
            if tid not in self._trials:
                raise ValueError(f"unknown trial_id in scope: {tid!r}")
        scope_set = set(scope_list)
        for tid, decision in decisions.items():
            if tid not in self._trials:
                raise ValueError(f"unknown trial_id in decisions: {tid!r}")
            if tid not in scope_set:
                raise ValueError(
                    f"decision trial {tid!r} is not in the verdict scope "
                    f"(decisions must be a subset of scope)"
                )
            if decision not in _VALID_DECISIONS:
                raise ValueError(
                    f"decision for {tid!r} must be 'pass' or 'reject', got {decision!r}"
                )
        _require_json_serializable(params, "params")
        _require_json_serializable(computed, "computed")

        vid = _format_id("v", self._next_v)
        self._next_v += 1
        at = _utc_now_iso()
        event = {
            "type": "verdict",
            "at": at,
            "verdict_id": vid,
            "statistic": statistic,
            "scope": scope_list,
            "params": params,
            "computed": computed,
            "decisions": dict(decisions),
            "engine_version": engine_version,
        }
        if role is not None:
            event["role"] = role
        _require_json_serializable(event, "verdict event")
        self._append_event(event)
        self._apply_event(event, corrupt_on_error=False)
        return vid

    def append_declaration(self, payload: dict) -> str:
        """Append a court-opaque declaration event (prereg-gate.md §3)."""
        self._require_not_sealed()
        if not isinstance(payload, dict):
            raise ValueError("declaration payload must be a dict")
        _require_json_serializable(payload, "declaration payload")
        did = _format_id("d", self._next_d)
        self._next_d += 1
        at = _utc_now_iso()
        event = {
            "type": "declaration",
            "at": at,
            "declaration_id": did,
            "payload": payload,
        }
        _require_json_serializable(event, "declaration event")
        self._append_event(event)
        self._apply_event(event, corrupt_on_error=False)
        return did

    def append_seal(self, payload: dict) -> str:
        """Append the seal event (at most one; final event — prereg-gate.md §5)."""
        self._require_not_sealed()
        if not isinstance(payload, dict):
            raise ValueError("seal payload must be a dict")
        _require_json_serializable(payload, "seal payload")
        sid = _format_id("s", self._next_s)
        self._next_s += 1
        at = _utc_now_iso()
        event = {
            "type": "seal",
            "at": at,
            "seal_id": sid,
            "payload": payload,
        }
        _require_json_serializable(event, "seal event")
        self._append_event(event)
        self._apply_event(event, corrupt_on_error=False)
        return sid

    # -- read side -------------------------------------------------------------

    @property
    def chain_head(self) -> str | None:
        """Last event_hash, genesis for empty chained, None for legacy."""
        return self._chain_head

    def declarations(self) -> list[DeclarationRecord]:
        """List declaration records in append order."""
        return list(self._declarations)

    def seal(self) -> SealRecord | None:
        """Return the seal record if present."""
        return self._seal

    def trials(self, scope: Sequence[str] | None = None) -> list[TrialRecord]:
        """List trial records; scope defaults to the whole ledger (§7.2)."""
        if scope is None:
            return [self._trials[tid] for tid in self._trial_order]
        out: list[TrialRecord] = []
        for tid in scope:
            if tid not in self._trials:
                raise ValueError(f"unknown trial_id in scope: {tid!r}")
            out.append(self._trials[tid])
        return out

    def series(self, trial_id: str) -> Series:
        """Return the stored performance series for an evaluated trial (§7.2)."""
        if trial_id not in self._trials:
            raise ValueError(f"unknown trial_id {trial_id!r}")
        rec = self._trials[trial_id]
        if rec.series is None:
            raise ValueError(f"trial {trial_id!r} is not yet evaluated")
        return rec.series

    def matrix(
        self, trial_ids: Sequence[str]
    ) -> tuple[tuple[str, ...], np.ndarray]:
        """Synchronous T×N performance matrix; fail-closed alignment (§7.2).

        Never outer-join, resample, or reorder indices. Columns follow trial_ids order.
        """
        if not trial_ids:
            raise ValueError("trial_ids must be non-empty")
        series_list: list[Series] = []
        for tid in trial_ids:
            if tid not in self._trials:
                raise ValueError(f"unknown trial_id {tid!r}")
            rec = self._trials[tid]
            if rec.series is None:
                raise ValueError(f"trial {tid!r} is not yet evaluated")
            series_list.append(rec.series)

        ref_index = series_list[0].index
        for i, s in enumerate(series_list[1:], start=1):
            if s.index != ref_index:
                raise ValueError(
                    f"series index for trial_ids[{i}]={trial_ids[i]!r} is not "
                    f"label-for-label identical to the first trial "
                    f"(trial_ids[0]={trial_ids[0]!r}); never outer-join/resample/reorder"
                )

        t = len(ref_index)
        n = len(series_list)
        mat = np.empty((t, n), dtype=np.float64)
        for j, s in enumerate(series_list):
            mat[:, j] = s.values
        return ref_index, mat

    def verdicts(self, trial_id: str | None = None) -> list[VerdictRecord]:
        """List verdicts; optional filter to those whose scope contains trial_id.

        ``decisions ⊆ scope`` is an enforced invariant (write and replay both
        validate it), so filtering on scope alone is complete.
        """
        if trial_id is None:
            return list(self._verdicts)
        if trial_id not in self._trials:
            raise ValueError(f"unknown trial_id {trial_id!r}")
        return [v for v in self._verdicts if trial_id in v.scope]

    def status(self, trial_id: str) -> str:
        """Derived status: registered → evaluated → judged (trial-ledger.md §5.2)."""
        if trial_id not in self._trials:
            raise ValueError(f"unknown trial_id {trial_id!r}")
        if trial_id in self._judged_trials:
            return "judged"
        if self._trials[trial_id].series is not None:
            return "evaluated"
        return "registered"
