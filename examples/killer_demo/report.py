"""Four-part report.md (killer-demo.md §10). Ledger is the archive; report is the tour."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Any

from examples.killer_demo.aggregate import gates_faced_passed, trial_survives
from examples.killer_demo.config import COST_DECLARATION


def _decision_for(verdicts: Sequence[Any], trial_id: str, statistic: str) -> str | None:
    for v in verdicts:
        if v.statistic == statistic and trial_id in v.decisions:
            # Prefer mode-specific noise rows
            if statistic == "noise_control":
                mode = v.params.get("mode")
                if mode == "pool_max" and v.params.get("mode") == "pool_max":
                    return v.decisions[trial_id]
            else:
                return v.decisions[trial_id]
    return None


def _find_verdict(
    verdicts: Sequence[Any],
    *,
    statistic: str,
    mode: str | None = None,
    judged_trial_id: str | None = None,
) -> Any | None:
    for v in verdicts:
        if v.statistic != statistic:
            continue
        if mode is not None and v.params.get("mode") != mode:
            continue
        if judged_trial_id is not None:
            if v.params.get("judged_trial_id") != judged_trial_id and (
                v.computed.get("selected_trial_id") != judged_trial_id
                and judged_trial_id not in v.decisions
            ):
                # individual noise keys judged_trial_id
                if mode == "individual" and v.params.get("judged_trial_id") != judged_trial_id:
                    continue
                if mode == "pool_max":
                    pass
                else:
                    continue
        return v
    return None


def _role_of(v: Any) -> str:
    """Display role; legacy None and missing attr → discriminating."""
    role = getattr(v, "role", None)
    if role is None:
        return "discriminating"
    return str(role)


def _fdr_row(verdicts: Sequence[Any], accused_id: str) -> dict[str, Any]:
    v = _find_verdict(verdicts, statistic="fdr_by")
    if v is None:
        return {}
    tids = v.computed.get("trial_ids", [])
    p_adj = None
    if accused_id in tids:
        # Report raw p vs q line; adjusted display uses p and k_star context
        i = tids.index(accused_id)
        p_adj = v.computed["p"][i]
    return {
        "gate": "fdr_by",
        "key": f"p={p_adj:.4g}" if p_adj is not None else "—",
        "line": f"q={v.params.get('q')}",
        "verdict": v.decisions.get(accused_id, "—"),
        "role": _role_of(v),
        "computed": v.computed,
        "params": v.params,
    }


def _dsr_row(verdicts: Sequence[Any], accused_id: str) -> dict[str, Any]:
    v = _find_verdict(verdicts, statistic="dsr")
    if v is None:
        return {}
    c = v.computed
    role = _role_of(v)
    key = (
        f"DSR z-path: sr*={c.get('sr_star')}, N̂={c.get('n_trials_effective')}, "
        f"ρ̂={c.get('rho_hat')}, rho_ill_conditioned={c.get('rho_ill_conditioned')}; "
        f"sr_selected={c.get('sr_selected')}"
    )
    if role == "informational":
        key = (
            f"{key}; abstains under two-sided — one-sided DSR does not match a "
            f"|t| selection"
        )
    return {
        "gate": "dsr",
        "key": key,
        "line": f"confidence={v.params.get('confidence')}",
        "verdict": v.decisions.get(accused_id, "—"),
        "role": role,
        "computed": c,
        "params": v.params,
    }


def _pbo_row(verdicts: Sequence[Any], accused_id: str) -> dict[str, Any]:
    v = _find_verdict(verdicts, statistic="pbo_cscv")
    if v is None:
        return {}
    c = v.computed
    metric = v.params.get("metric")
    return {
        "gate": "pbo_cscv",
        "key": f"φ={c.get('phi'):.4g} (C={c.get('n_combinations')})",
        "line": f"φ ≤ {v.params.get('phi_threshold')}; metric={metric}",
        "verdict": v.decisions.get(accused_id, "—"),
        "role": _role_of(v),
        "computed": c,
        "params": v.params,
    }


def _pool_row(verdicts: Sequence[Any], accused_id: str) -> dict[str, Any]:
    for v in verdicts:
        if v.statistic == "noise_control" and v.params.get("mode") == "pool_max":
            c = v.computed
            return {
                "gate": "noise_control (pool_max)",
                "key": (
                    f"p̂={c.get('p_hat'):.4g}, observed={c.get('observed'):.4g}, "
                    f"n_at_least={c.get('n_at_least')}/{c.get('n_nulls')}"
                ),
                "line": f"α={v.params.get('alpha')}",
                "verdict": v.decisions.get(accused_id, "—"),
                "role": _role_of(v),
                "computed": c,
                "params": v.params,
            }
    return {}


def _indiv_row(verdicts: Sequence[Any], trial_id: str) -> dict[str, Any]:
    for v in verdicts:
        if (
            v.statistic == "noise_control"
            and v.params.get("mode") == "individual"
            and v.params.get("judged_trial_id") == trial_id
        ):
            c = v.computed
            return {
                "gate": "noise_control (individual)",
                "key": f"p̂={c.get('p_hat'):.4g}, observed={c.get('observed'):.4g}",
                "line": f"α={v.params.get('alpha')}",
                "verdict": v.decisions.get(trial_id, "—"),
                "role": _role_of(v),
                "computed": c,
                "params": v.params,
            }
    return {}


def battery_rows(verdicts: Sequence[Any], accused_id: str) -> list[dict[str, Any]]:
    """Battery table for the accused with Role column (§10 part 1; §6 v0.2).

    Five gate rows: discriminating gates vote on survival; under two-sided,
    DSR is informational (abstains) while PBO uses the absolute metric form.
    """
    rows = [
        _fdr_row(verdicts, accused_id),
        _dsr_row(verdicts, accused_id),
        _pbo_row(verdicts, accused_id),
        _pool_row(verdicts, accused_id),
        _indiv_row(verdicts, accused_id),
    ]
    return [r for r in rows if r]


def render_report(
    *,
    out_dir: str | Path,
    n_survivors: int,
    n_candidates: int,
    accused: Any,
    accused_spec: Any,
    trial_ids: Sequence[str],
    specs: Sequence[Any],
    abs_t_list: Sequence[float],
    t_list: Sequence[float],
    verdicts: Sequence[Any],
    ledger: Any,
    figure_caption: str,
    engine_version: str,
    master_seed: int,
    data_version: dict[str, Any],
    sweep_table: list[dict[str, Any]] | None = None,
) -> str:
    """Write report.md with four parts; return markdown text (§10)."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    battery = battery_rows(verdicts, accused.trial_id)
    survivor_note = (
        f"{n_survivors}/{n_candidates} survived"
        if n_survivors == 0
        else (
            f"{n_survivors}/{n_candidates} survived "
            f"(court's declared per-gate false-pass rate: 5%)"
        )
    )

    lines: list[str] = []
    # --- Part 1: Headline ---
    lines.append("# Killer demo report")
    lines.append("")
    lines.append("## 1. Headline")
    lines.append("")
    lines.append(f"**Survivors: {survivor_note}.**")
    lines.append("")
    lines.append(
        f"Accused (naive max |t|): `{accused_spec.name}` "
        f"(`{accused.trial_id}`), direction={accused.direction}, "
        f"|t|={accused.abs_t:.4f}, t={accused.t:.4f}, "
        f"naive p={accused.naive_p:.4g}, "
        f"annualized ICIR={accused.annualized_icir:.4f}."
    )
    lines.append("")
    lines.append(f"Figure: `figure.png` / `figure.svg`. Caption: {figure_caption}")
    lines.append("")
    lines.append("### Battery table (accused)")
    lines.append("")
    lines.append("| Gate | Key computed | Line | Verdict | Role |")
    lines.append("|---|---|---|---|---|")
    for row in battery:
        lines.append(
            f"| {row['gate']} | {row['key']} | {row['line']} | "
            f"**{row['verdict']}** | {row.get('role', 'discriminating')} |"
        )
    lines.append("")
    lines.append(
        "Footnotes (killer-demo.md §5.4 / §6 v0.2): DSR under two-sided is "
        "informational — one-sided DSR does not match a |t| selection "
        "(abstains; does not vote). "
        "PBO (abs metric under two-sided) judged the overfit probability of "
        "the selection process isomorphic to the naive scan on this matrix. "
        "DSR's ρ̂ is ill-conditioned when T < ½·M·(M−1)."
    )
    lines.append("")

    # --- Part 2: Morgue table ---
    lines.append("## 2. Morgue table")
    lines.append("")
    lines.append(
        "| trial_id | name | family | φ | |t| | naive p | FDR p | "
        "indiv noise p̂ | gates passed/faced | status |"
    )
    lines.append("|---|---|---|---|---|---|---|---|---|---|")

    fdr_v = _find_verdict(verdicts, statistic="fdr_by")
    fdr_p_map: dict[str, float] = {}
    if fdr_v is not None:
        for tid, p in zip(fdr_v.computed["trial_ids"], fdr_v.computed["p"], strict=True):
            fdr_p_map[tid] = float(p)

    indiv_pass_names: list[str] = []
    for i, tid in enumerate(trial_ids):
        spec = specs[i]
        at = abs_t_list[i]
        from scipy.stats import norm

        naive_p = float(2.0 * (1.0 - norm.cdf(at)))
        indiv = _indiv_row(verdicts, tid)
        indiv_p = indiv.get("computed", {}).get("p_hat", float("nan")) if indiv else float("nan")
        if indiv and indiv.get("verdict") == "pass":
            indiv_pass_names.append(spec.name)
        n_pass, n_face = gates_faced_passed(tid, verdicts)
        status = "SURVIVOR" if trial_survives(tid, verdicts) else "rejected"
        lines.append(
            f"| `{tid}` | {spec.name} | {spec.family} | {spec.phi:.6f} | "
            f"{at:.4f} | {naive_p:.4g} | {fdr_p_map.get(tid, float('nan')):.4g} | "
            f"{indiv_p:.4g} | {n_pass}/{n_face} | {status} |"
        )
    lines.append("")

    # --- Part 3: Specimen autopsy ---
    lines.append("## 3. Specimen autopsy (the accused)")
    lines.append("")
    t_rec = ledger.trials([accused.trial_id])[0]
    lines.append(f"### Registration (`{accused.trial_id}`)")
    lines.append("")
    lines.append(f"- registered_at: `{t_rec.registered_at}`")
    lines.append(f"- hypothesis_id: `{t_rec.hypothesis_id}`")
    lines.append(f"- statement: {accused_spec.statement}")
    lines.append(f"- spec (full recipe): `{t_rec.spec}`")
    lines.append(
        f"- declared protocol: metric={t_rec.declared.metric}, "
        f"direction={t_rec.declared.direction}, "
        f"se={t_rec.declared.se.kind}, "
        f"window=[{t_rec.declared.window.start}, {t_rec.declared.window.end}], "
        f"periods_per_year={t_rec.declared.periods_per_year}"
    )
    lines.append(f"- evaluated_at: `{t_rec.evaluated_at}`")
    lines.append(f"- series length T={len(t_rec.series.values) if t_rec.series else 0}")
    lines.append("")
    lines.append("### Verdicts (literature anchors in `docs/research/`)")
    lines.append("")
    for row in battery:
        lines.append(
            f"#### {row['gate']} → **{row['verdict']}** "
            f"(role={row.get('role', 'discriminating')})"
        )
        lines.append("")
        lines.append(f"- line: {row['line']}")
        lines.append(f"- key: {row['key']}")
        lines.append(f"- role: {row.get('role', 'discriminating')}")
        lines.append(f"- params: `{row['params']}`")
        # Truncate huge null_stats in display
        computed_show = dict(row["computed"])
        if "null_stats" in computed_show and isinstance(computed_show["null_stats"], list):
            ns = computed_show["null_stats"]
            computed_show["null_stats"] = {
                "n": len(ns),
                "head": ns[:5],
                "tail": ns[-3:],
            }
        lines.append(f"- computed: `{computed_show}`")
        lines.append("")
        if row["gate"] == "dsr":
            lines.append(
                "Literature: Bailey & López de Prado (DSR); see `docs/research/dsr.md`."
            )
            lines.append("")
        if row["gate"] == "pbo_cscv":
            lines.append(
                "Literature: CSCV / PBO; see `docs/research/pbo-cscv.md`."
            )
            lines.append("")
        if row["gate"] == "fdr_by":
            lines.append(
                "Literature: Benjamini–Yekutieli FDR; see `docs/research/bhy.md`."
            )
            lines.append("")

    # --- Part 4: Calibration appendix ---
    lines.append("## 4. Calibration appendix")
    lines.append("")
    lines.append(
        "Individual-noise passes (expected ≈5/100 at α=0.05; calibration evidence, "
        "not an accident — killer-demo.md §5.2):"
    )
    lines.append("")
    if indiv_pass_names:
        for name in indiv_pass_names:
            lines.append(f"- {name}")
    else:
        lines.append("- (none in this run)")
    lines.append("")
    lines.append(f"Count: {len(indiv_pass_names)}/{n_candidates}.")
    lines.append("")
    lines.append("### Seed-sweep table (§7.4)")
    lines.append("")
    if sweep_table:
        lines.append(
            "| seed | accused | sign | |t| | fdr | dsr | pbo | pool | indiv | survivors |"
        )
        lines.append("|---|---|---|---|---|---|---|---|---|---|")
        for row in sweep_table:
            g = row["accused_gate_verdicts"]
            lines.append(
                f"| {row['seed']} | {row.get('accused_name', '')} | "
                f"{row.get('sign', '')} | {row.get('abs_t', float('nan')):.4f} | "
                f"{g.get('fdr_by', '')} | {g.get('dsr', '')} | "
                f"{g.get('pbo_cscv', '')} | {g.get('noise_pool_max', '')} | "
                f"{g.get('noise_individual', '')} | {row['n_survivors']} |"
            )
    else:
        lines.append(
            "_Sweep not run in this invocation (`--sweep` off). "
            "Pre-registered seeds: 20260711–20260730._"
        )
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append(
        f"Declarations: {COST_DECLARATION}; master seed={master_seed}; "
        f"data_version={data_version}; engine_version={engine_version}."
    )
    lines.append("")

    text = "\n".join(lines)
    (out / "report.md").write_text(text, encoding="utf-8")
    return text


def report_has_four_sections(text: str) -> bool:
    """Smoke helper: all four §10 sections present."""
    return all(
        h in text
        for h in (
            "## 1. Headline",
            "## 2. Morgue table",
            "## 3. Specimen autopsy",
            "## 4. Calibration appendix",
        )
    )


def caption_is_complete(caption: str) -> bool:
    """Smoke helper: caption carries §8 mandatory items."""
    needles = [
        "gross paper series",
        "RankIC",
        "csi300",
        "T =",
        "Master seed",
        "Data tag",
        "engine_version",
    ]
    return all(n in caption for n in needles)
