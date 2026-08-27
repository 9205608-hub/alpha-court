"""CertifiedRun — the pre-registration gate (prereg-gate.md §3–§6, §8–§9).

The harness owns the loop: the agent never passes a scope, cannot evaluate
outside the loop on the certified path, and seals once per multiplicity
family. Uncertified direct ``court`` use remains legitimate calculator use;
the missing or invalid seal is the detection (prereg-gate.md §2 Q1–Q2).

Honest boundaries (prereg-gate.md §6 — on the first screen):
1. **Pre-seal truncation window** — before the seal there is no external pin;
   deleting a trailing evaluation leaves a ledger byte-indistinguishable from
   an honest registered-but-unevaluated prefix (torn-write recovery legitimizes
   a missing tail). The seal-must-be-final rule closes this *after* sealing.
2. **Off-path pre-screening** — the seal certifies the family evaluated through
   *this* Run, not that nothing was tried on a direct adapter/court path.
3. **In-process forgery** — attestations are unsigned in-process dicts; a
   valid seal certifies protocol-consistency and order of recorded events, not
   that the sanctioned adapter produced them. No in-process nonces/HMACs.
4. **Sibling runs** — splitting one search across many certified runs is
   invisible to any single seal; RP-1 presentation rule, not mechanized here.

Failure semantics for ``judge``: if ``court.judge`` raises for any reason the
single ``judge`` slot is still consumed and the run can never be sealed —
mid-battery orphan verdicts leave no on-chain ``judgment`` declaration, so
``open()`` recovery also refuses seal (rework-01 F-1).
"""

from __future__ import annotations

import json
import platform
import re
from collections.abc import Sequence
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

import court
from court.judge import Application, Judgment
from court.judge import judge as court_judge
from court.ledger import DeclaredProtocol, Ledger, Series
from harness.aggregation_policy import (
    AggregationPolicy,
    declare_policy,
    read_declared_policy,
)
from harness.anchor import AnchorBackend
from harness.blades import (
    BLADE_REPORT_KIND,
    append_blade_roster,
    find_blade_calibration_record,
    find_blade_roster,
    roster_entry,
    validate_blade_report,
)

_HYPOTHESIS_ID_RE = re.compile(r"^h-\d{6}$")
_RUN_CONFIG_KIND = "run_config"
_JUDGMENT_KIND = "judgment"
_SEAL_KIND = "seal"


class CertificationError(Exception):
    """Fail-closed verification / certified-path conformance failure.

    Caller errors (bad arguments, wrong lifecycle) raise ``ValueError``.
    Protocol or chain verification failures raise ``CertificationError``
    (prereg-gate.md §5). Never repair, coerce, or silently drop.
    """


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _require_json_serializable_dict(obj: Any, name: str) -> dict:
    if not isinstance(obj, dict):
        raise ValueError(f"{name} must be a dict, got {type(obj).__name__}")
    if not obj:
        raise ValueError(f"{name} must be a non-empty dict")
    try:
        json.dumps(obj, allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be JSON-serializable: {exc}") from exc
    return obj


def _policy_payload_from_ledger(ledger: Ledger, declaration_id: str) -> dict:
    """Return the on-chain declaration payload dict (verbatim, not re-serialized).

    Object round-trips through ``AggregationPolicy.from_payload`` drop unknown
    keys (prereg-gate / 09 handoff ⚠-2); the seal must copy the raw payload.
    """
    for rec in ledger.declarations():
        if rec.declaration_id == declaration_id:
            return rec.payload
    raise CertificationError(
        f"policy declaration {declaration_id!r} not found on ledger"
    )


def _resolve_on_flag(spec: dict, blade_name: str) -> str:
    """Read ``on_flag`` for ``blade_name`` from the trial spec (default ``record``)."""
    try:
        on_flag = spec.get("blades", {}).get(blade_name, {}).get("on_flag", "record")
    except (AttributeError, TypeError) as exc:
        raise CertificationError(
            f"trial spec blades[{blade_name!r}] is not a dict of on_flag settings"
        ) from exc
    if on_flag not in ("record", "screen"):
        raise CertificationError(
            f"invalid on_flag {on_flag!r} for blade {blade_name!r}; "
            "expected 'record' or 'screen'"
        )
    return on_flag


def _spec_declares_screen(spec: Any) -> bool:
    """True when this trial spec sets ``on_flag: screen`` for any blade name."""
    if not isinstance(spec, dict):
        return False
    blades_cfg = spec.get("blades")
    if not isinstance(blades_cfg, dict):
        return False
    for cfg in blades_cfg.values():
        if isinstance(cfg, dict) and cfg.get("on_flag") == "screen":
            return True
    return False


def _attached_roster_entries(blades: Sequence) -> list[dict]:
    return [roster_entry(blade) for blade in blades]


def _normalize_blades(blades: Sequence | None) -> tuple[Any, ...] | None:
    """Validate and freeze the blade roster; empty sequence is no roster."""
    if blades is None:
        return None
    roster = tuple(blades)
    if not roster:
        return None
    names: list[str] = []
    for blade in roster:
        name = getattr(blade, "name", None)
        if not isinstance(name, str) or not name:
            raise CertificationError(
                f"blade protocol violation: {type(blade).__name__} "
                "must expose a non-empty-str .name"
            )
        run_fn = getattr(blade, "run", None)
        if not callable(run_fn):
            raise CertificationError(
                f"blade protocol violation: blade {name!r} must expose a callable .run"
            )
        names.append(name)
    dupes = sorted({n for n in names if names.count(n) > 1})
    if dupes:
        raise CertificationError(f"duplicate blade names refused: {dupes}")
    return roster


def _trial_has_blade_report(ledger: Ledger, trial_id: str) -> bool:
    for rec in ledger.declarations():
        payload = rec.payload
        if (
            isinstance(payload, dict)
            and payload.get("kind") == BLADE_REPORT_KIND
            and payload.get("trial_id") == trial_id
        ):
            return True
    return False


def _derived_scope(ledger: Ledger) -> list[str]:
    """Every trial with status evaluated or judged, in registration order.

    Registered-but-unevaluated trials keep file-drawer semantics — visible on
    the chain, not in N (prereg-gate.md §8).
    """
    return [
        t.trial_id
        for t in ledger.trials()
        if ledger.status(t.trial_id) in ("evaluated", "judged")
    ]


def _check_meta_conformance(meta: dict, run_config: dict) -> None:
    """Every key in meta that also exists in run_config must be raw-equal.

    Covers universe / versions / nested config (prereg-gate.md §3, audit D7).
    """
    if not isinstance(meta, dict):
        raise CertificationError(
            f"evaluator meta must be a dict, got {type(meta).__name__}"
        )
    for key in meta:
        if key not in run_config:
            continue
        if meta[key] != run_config[key]:
            raise CertificationError(
                f"attestation/run_config conformance failed for key {key!r}: "
                f"meta={meta[key]!r} != run_config={run_config[key]!r}"
            )


def _find_run_config(ledger: Ledger) -> dict:
    for rec in ledger.declarations():
        payload = rec.payload
        if isinstance(payload, dict) and payload.get("kind") == _RUN_CONFIG_KIND:
            cfg = payload.get("config")
            if not isinstance(cfg, dict) or not cfg:
                raise CertificationError("run_config declaration has empty/invalid config")
            return cfg
    raise CertificationError("missing run_config declaration on certified ledger")


def _find_judgment_payloads(ledger: Ledger) -> list[dict]:
    """All on-chain judgment declaration payloads (court-opaque)."""
    out: list[dict] = []
    for rec in ledger.declarations():
        payload = rec.payload
        if isinstance(payload, dict) and payload.get("kind") == _JUDGMENT_KIND:
            out.append(payload)
    return out


def _judgment_from_payload(payload: dict, ledger: Ledger) -> Judgment:
    """Rebuild Judgment from a judgment declaration payload + chain verdicts."""
    vids = payload.get("verdict_ids")
    if not isinstance(vids, list):
        raise CertificationError("judgment payload missing verdict_ids list")
    decisions: dict[str, dict[str, str]] = {}
    by_id = {v.verdict_id: v for v in ledger.verdicts()}
    for vid in vids:
        v = by_id.get(vid)
        if v is None:
            # A judgment declaration must reference verdicts on this chain; a
            # missing one is tampering/corruption, never skippable (v0.2-12 C).
            raise CertificationError(
                f"judgment payload references unknown verdict_id {vid!r}"
            )
        decisions[v.verdict_id] = dict(v.decisions)
    return Judgment(verdict_ids=tuple(str(x) for x in vids), decisions=decisions)


def _battery_from_config(config: Sequence[Application]) -> list[dict]:
    """Verbatim Application list for the judgment declaration."""
    battery: list[dict] = []
    for app in config:
        if not isinstance(app.params, dict):
            raise ValueError(
                f"Application.params must be a dict, got {type(app.params).__name__}"
            )
        battery.append({"statistic": app.statistic, "params": dict(app.params)})
    return battery


class CertifiedRun:
    """One multiplicity family: propose → evaluate → judge → seal.

    Construction writes the ``run_config`` declaration as the first chain event
    and the aggregation policy as the second (prereg-gate.md §3). The agent
    never passes a scope; ``judge`` derives it from the complete
    registered-and-evaluated set. A successful ``judge`` appends a court-opaque
    ``judgment`` declaration so mid-battery bricks cannot be revived via
    ``open()`` (rework-01 F-1).
    """

    def __init__(
        self,
        ledger: Ledger,
        evaluator: Any,
        run_config: dict,
        *,
        anchor: AnchorBackend | None = None,
        blades: Sequence | None = None,
        judge_consumed: bool = False,
        judgment: Judgment | None = None,
        scope: list[str] | None = None,
        incomplete_judgment: bool = False,
    ) -> None:
        self._ledger = ledger
        self._evaluator = evaluator
        self._run_config = run_config
        self._anchor = anchor
        self._blades: tuple[Any, ...] | None = _normalize_blades(blades)
        self._judge_consumed = judge_consumed
        self._judgment = judgment
        self._scope = list(scope) if scope is not None else None
        self._judge_failed = False
        # Verdicts on chain without a covering judgment declaration (brick/crash).
        self._incomplete_judgment = incomplete_judgment

    # -- construction ---------------------------------------------------------

    @classmethod
    def create(
        cls,
        path: str | Path,
        run_config: dict,
        policy: AggregationPolicy,
        evaluator: Any,
        anchor: AnchorBackend | None = None,
        *,
        blades: Sequence | None = None,
    ) -> CertifiedRun:
        """Open a FRESH ledger and lock run_config + aggregation policy.

        An existing non-empty file raises ``ValueError`` — a certified run
        never adopts a foreign ledger.
        """
        path = Path(path)
        run_config = _require_json_serializable_dict(run_config, "run_config")
        if not isinstance(policy, AggregationPolicy):
            raise ValueError(
                f"policy must be AggregationPolicy, got {type(policy).__name__}"
            )
        if path.exists() and path.stat().st_size > 0:
            raise ValueError(
                f"certified run refuses existing non-empty ledger file: {path}"
            )
        path.parent.mkdir(parents=True, exist_ok=True)
        ledger = Ledger.open(path)
        # First chain event: run_config (prereg-gate.md §3, audit D7).
        ledger.append_declaration({"kind": _RUN_CONFIG_KIND, "config": run_config})
        # Second: aggregation policy (ticket 09 / prereg-gate.md §7).
        declare_policy(ledger, policy)
        return cls(ledger, evaluator, run_config, anchor=anchor, blades=blades)

    @classmethod
    def open(
        cls,
        path: str | Path,
        evaluator: Any,
        anchor: AnchorBackend | None = None,
        *,
        blades: Sequence | None = None,
    ) -> CertifiedRun:
        """Re-attach to an existing UNSEALED certified ledger.

        Replay verifies the chain. Missing run_config/policy, already-sealed,
        or legacy/chainless files raise ``CertificationError``.

        Judged-state recovery (rework-01): only a covering ``judgment``
        declaration authorizes seal. Verdicts without a judgment event mean
        ``judge`` is spent and ``seal()`` raises
        ``CertificationError("judged run incomplete: ...")``.
        """
        path = Path(path)
        if not path.exists():
            raise CertificationError(f"certified ledger not found: {path}")
        try:
            ledger = Ledger.open(path)
        except Exception as exc:
            raise CertificationError(f"ledger replay failed: {exc}") from exc
        if ledger.chain_head is None:
            raise CertificationError("uncertified: no chain (legacy ledger)")
        if ledger.seal() is not None:
            raise CertificationError("ledger is already sealed; open refuses sealed runs")
        try:
            run_config = _find_run_config(ledger)
        except CertificationError:
            raise
        if read_declared_policy(ledger) is None:
            raise CertificationError("missing aggregation policy declaration")

        judge_consumed = False
        judgment: Judgment | None = None
        scope: list[str] | None = None
        incomplete_judgment = False

        jpayloads = _find_judgment_payloads(ledger)
        if len(jpayloads) > 1:
            raise CertificationError(
                f"corrupt certified ledger: {len(jpayloads)} judgment declarations"
            )
        if len(jpayloads) == 1:
            judge_consumed = True
            judgment = _judgment_from_payload(jpayloads[0], ledger)
            scope = _derived_scope(ledger)
        elif ledger.verdicts():
            # Brick or crash: verdicts without a covering judgment event.
            judge_consumed = True
            incomplete_judgment = True

        return cls(
            ledger,
            evaluator,
            run_config,
            anchor=anchor,
            blades=blades,
            judge_consumed=judge_consumed,
            judgment=judgment,
            scope=scope,
            incomplete_judgment=incomplete_judgment,
        )

    # -- accessors ------------------------------------------------------------

    @property
    def ledger(self) -> Ledger:
        return self._ledger

    @property
    def path(self) -> Path:
        return self._ledger._path  # noqa: SLF001 — intentional path surface

    # -- loop -----------------------------------------------------------------

    def propose(
        self,
        statement_or_hypothesis_id: str,
        spec: dict,
        params: dict,
        declared: DeclaredProtocol,
        source_ref: str | None = None,
    ) -> str:
        """Register a hypothesis (when given a statement) + trial.

        Discrimination rule: an argument matching ``^h-\\d{6}$`` is treated as
        an existing hypothesis id (unknown → court's ValueError); anything else
        is a new statement. Sealed ledgers surface court's seal raise.
        """
        if not isinstance(statement_or_hypothesis_id, str) or not statement_or_hypothesis_id:
            raise ValueError("statement_or_hypothesis_id must be a non-empty str")
        if _HYPOTHESIS_ID_RE.fullmatch(statement_or_hypothesis_id):
            hid = statement_or_hypothesis_id
        else:
            hid = self._ledger.register_hypothesis(statement_or_hypothesis_id)
        return self._ledger.register(
            hid, spec, params, declared, source_ref=source_ref
        )

    def evaluate(self, trial_id: str, scores: Any) -> None:
        """Evaluate via the injected evaluator; record with attestation.

        Conformance (fail-closed ``CertificationError``): every key of
        ``result.meta`` that also exists in ``run_config`` must be raw-equal
        (prereg-gate.md §3 / §5). Court re-checks metric/window/shape on record.

        When blades are attached, they run after the series is built and before
        ``ledger.record``. A flagged blade whose trial spec declares
        ``on_flag: screen`` skips the record — the trial stays ``registered``.
        """
        trials = self._ledger.trials([trial_id])
        trial = trials[0]
        if self._blades is None:
            pinned = find_blade_roster(self._ledger)
            if pinned is not None:
                raise CertificationError(
                    "ledger has a pinned blade roster; reopen with the equivalent blades"
                )
            if _spec_declares_screen(trial.spec):
                raise CertificationError(
                    "spec declares screening but no blades attached"
                )
        if (
            self._ledger.status(trial_id) == "registered"
            and _trial_has_blade_report(self._ledger, trial_id)
        ):
            raise CertificationError(
                f"trial {trial_id!r} was screened; re-evaluation refused"
            )
        declared = trial.declared
        result = self._evaluator.evaluate(scores, declared.metric)
        meta = result.meta
        if not isinstance(meta, dict):
            raise CertificationError(
                f"evaluator result.meta must be a dict, got {type(meta).__name__}"
            )
        _check_meta_conformance(meta, self._run_config)
        index = tuple(str(x) for x in result.index)
        values = tuple(float(x) for x in np.asarray(result.values).tolist())
        series = Series(index=index, values=values)
        if self._blades is not None:
            if not self._apply_blades(
                trial_id, trial.spec, trial.params, declared, series
            ):
                return
        self._ledger.record(trial_id, series, attestation=dict(meta))

    def _apply_blades(
        self,
        trial_id: str,
        spec: dict,
        params: dict,
        declared: DeclaredProtocol,
        series: Series,
    ) -> bool:
        """Run attached blades; return False when a screen flag skips record.

        Two-phase, all-or-nothing (atomicity rationale: a partial append of
        blade_reports would poison the append-only chain — retrying evaluate
        would then write duplicate reports, and a screened trial is identified
        by the presence of those reports). Phase 1 runs every blade and
        validates each report (schema, name match, JSON serializability) with
        zero declarations appended. Phase 2 appends the full batch, then
        decides record vs screen. An unexpected ``ValueError`` from
        ``append_declaration`` is re-raised as ``CertificationError``.

        Fail-closed before any blade runs or any declaration is appended:
        missing ``blade_calibration``, an attached roster that does not match
        a pinned ``blade_roster``, or an ``on_flag`` other than ``record`` /
        ``screen``. After those checks, a missing roster is pinned (once) from
        the attached blades, then blades run. A blade exception or invalid
        report also raises ``CertificationError`` with no evaluation recorded.
        """
        assert self._blades is not None
        cal_rec = find_blade_calibration_record(self._ledger)
        if cal_rec is None:
            raise CertificationError(
                "blades attached but no blade_calibration declaration on chain"
            )
        pinned = find_blade_roster(self._ledger)
        attached = _attached_roster_entries(self._blades)
        if pinned is not None and pinned != attached:
            raise CertificationError(
                "attached blades do not match the pinned blade roster on chain"
            )
        effects: list[str] = []
        for blade in self._blades:
            effects.append(_resolve_on_flag(spec, blade.name))
        if pinned is None:
            try:
                append_blade_roster(self._ledger, self._blades)
            except ValueError as exc:
                raise CertificationError(
                    f"blade_roster declaration append failed: {exc}"
                ) from exc

        reports: list[dict] = []
        for blade in self._blades:
            try:
                report = blade.run(trial_id, spec, params, declared, series)
            except CertificationError:
                raise
            except Exception as exc:
                raise CertificationError(f"blade {blade.name!r} raised: {exc}") from exc
            try:
                validate_blade_report(report)
            except ValueError as exc:
                raise CertificationError(
                    f"invalid blade report from {blade.name!r}: {exc}"
                ) from exc
            if report["blade"] != blade.name:
                raise CertificationError(
                    f"blade report name {report['blade']!r} != blade.name {blade.name!r}"
                )
            try:
                json.dumps(report, allow_nan=False)
            except (TypeError, ValueError) as exc:
                raise CertificationError(
                    f"blade {blade.name!r} report is not JSON-serializable: {exc}"
                ) from exc
            reports.append(report)

        for report in reports:
            try:
                self._ledger.append_declaration(
                    {
                        "kind": BLADE_REPORT_KIND,
                        "trial_id": trial_id,
                        "calibration_id": cal_rec.declaration_id,
                        "report": report,
                    }
                )
            except ValueError as exc:
                raise CertificationError(
                    f"blade_report declaration append failed: {exc}"
                ) from exc

        for report, on_flag in zip(reports, effects, strict=True):
            if report["flagged"] is True and on_flag == "screen":
                return False
        return True

    def judge(self, config: Sequence[Application]) -> Judgment:
        """Derive scope from all evaluated trials; run court.judge once.

        Empty scope → ``ValueError``. Second call → ``ValueError``. If
        ``court.judge`` raises for any reason the single judge slot is still
        consumed and **no** ``judgment`` declaration is written (orphan
        mid-battery verdicts cannot be sealed — rework-01 F-1). On success,
        appends a court-opaque judgment declaration with the battery and
        verdict_ids before returning.
        """
        if self._judge_consumed:
            raise ValueError(
                "judge may be called at most once per CertifiedRun "
                "(one Run = one family = one judge = one seal)"
            )
        # Consume the single judge slot before calling court (failure still bricks).
        self._judge_consumed = True
        scope = _derived_scope(self._ledger)
        if not scope:
            self._judge_failed = True
            raise ValueError(
                "judge scope is empty: no evaluated trials on this certified run"
            )
        try:
            judgment = court_judge(self._ledger, scope, config)
        except Exception:
            self._judge_failed = True
            self._judgment = None
            self._scope = None
            # Leave no judgment declaration — open() will refuse seal.
            raise
        # Only after court.judge returns successfully (rework-01).
        battery = _battery_from_config(config)
        self._ledger.append_declaration(
            {
                "kind": _JUDGMENT_KIND,
                "battery": battery,
                "verdict_ids": list(judgment.verdict_ids),
            }
        )
        self._judgment = judgment
        self._scope = list(scope)
        self._judge_failed = False
        self._incomplete_judgment = False
        return judgment

    def seal(self) -> str:
        """Append the seal event, pin the anchor, write ``run_manifest.json``.

        Requires a prior successful ``judge()`` and an on-chain ``judgment``
        declaration whose ``verdict_ids`` equal ALL verdict events (rework-01).
        Seal payload carries the chain head *before* the seal line, the derived
        scope, all judgment verdict ids, and the on-chain policy payload
        verbatim (prereg-gate.md §4.2; 09 handoff ⚠-2).
        """
        if self._incomplete_judgment:
            raise CertificationError(
                "judged run incomplete: verdicts without a judgment event"
            )
        if self._judgment is None or self._scope is None or self._judge_failed:
            raise ValueError(
                "seal requires a prior successful judge(); "
                "judge was not called, failed, or was consumed without success"
            )
        if self._ledger.seal() is not None:
            raise ValueError("ledger is already sealed")

        # Require covering judgment on chain (durable success marker).
        jpayloads = _find_judgment_payloads(self._ledger)
        if len(jpayloads) != 1:
            raise ValueError(
                f"seal requires exactly one judgment event on the chain, "
                f"found {len(jpayloads)}"
            )
        j_vids = jpayloads[0].get("verdict_ids")
        all_vids = [v.verdict_id for v in self._ledger.verdicts()]
        if j_vids != all_vids:
            raise ValueError(
                "judgment verdict_ids must equal ALL verdict events on the chain "
                f"(judgment={j_vids!r}, chain={all_vids!r})"
            )
        if list(self._judgment.verdict_ids) != all_vids:
            raise ValueError(
                "seal verdict_ids must equal ALL verdict events on the chain"
            )

        policy_pair = read_declared_policy(self._ledger)
        if policy_pair is None:
            raise ValueError("no aggregation policy declared on ledger at seal time")
        policy_declaration_id, _policy_obj = policy_pair
        # Verbatim on-chain payload — never re-serialize from AggregationPolicy.
        policy_payload = _policy_payload_from_ledger(
            self._ledger, policy_declaration_id
        )

        chain_head_before = self._ledger.chain_head
        if chain_head_before is None:
            raise ValueError("cannot seal a legacy/chainless ledger")

        anchor_ref_in_seal: str | None = None
        if self._anchor is not None:
            anchor_ref_in_seal = self._anchor.ref_before_seal()

        seal_payload = {
            "kind": _SEAL_KIND,
            "chain_head": chain_head_before,
            "scope": list(self._scope),
            "verdict_ids": list(self._judgment.verdict_ids),
            "policy_declaration_id": policy_declaration_id,
            "policy": policy_payload,
            "anchor_ref": anchor_ref_in_seal,
        }
        seal_id = self._ledger.append_seal(seal_payload)

        final_head = self._ledger.chain_head
        assert final_head is not None

        # seal_event_hash ≡ final chain head (last line's event_hash IS the head).
        seal_event_hash = final_head

        manifest_anchor_ref: str | None = None
        if self._anchor is not None:
            manifest_anchor_ref = self._anchor.pin(final_head)

        manifest = {
            "chain_head": final_head,
            "seal_event_hash": seal_event_hash,
            "anchor_ref": manifest_anchor_ref,
            "sealed_at": _utc_now_iso(),
            "env": {
                "python": platform.python_version(),
                "numpy": np.__version__,
                "scipy": _scipy_version(),
                "court": court.__version__,
            },
        }
        manifest_path = self.path.parent / "run_manifest.json"
        manifest_path.write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        return seal_id


def _scipy_version() -> str:
    try:
        import scipy

        return str(scipy.__version__)
    except Exception:  # pragma: no cover — scipy is a hard dep via court stack
        return "unknown"
