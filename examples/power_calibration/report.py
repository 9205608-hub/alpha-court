"""Power-calibration report.md (power-calibration.md §6).

First-screen honesty: §1 claim scope + §4.3 unit footnote. Size beside power.
Hero = A (P(pass|won)) with B beside; per-gate TPR default panel; submission
table; β_t appendix hooks; calibration decomposition.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from examples.power_calibration.calibrate import CalibrationResult
from examples.power_calibration.config import (
    CLAIM_SCOPE,
    COST_DECLARATION,
    UNIT_FOOTNOTE,
    PowerConfig,
)


def render_report(
    *,
    out_dir: str | Path,
    summaries: list[Any],
    calibration: CalibrationResult,
    cfg: PowerConfig,
    run_config: dict[str, Any],
    beta_t_payload: dict[str, Any] | list[dict[str, Any]] | None = None,
) -> str:
    """Write report.md; return text."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []

    # --- First screen honesty (§1 + §4.3) ---
    lines.append("# Power calibration — court ROC on a known signal")
    lines.append("")
    lines.append("## First-screen honesty (mandatory)")
    lines.append("")
    lines.append(CLAIM_SCOPE)
    lines.append("")
    lines.append(UNIT_FOOTNOTE)
    lines.append("")
    lines.append(
        f"Cost declaration: {COST_DECLARATION}. "
        "Aggregation: unanimous-over-discriminating "
        f"(`harness.aggregation_policy`, policy_id="
        f"{run_config.get('aggregation_policy_id')})."
    )
    lines.append("")
    lines.append(
        "Caption: **A** is the court ROC *given the signal already won naive "
        "directed selection* (`argmax t`); **B = P(win)** is plotted beside it. "
        "A alone is optimistic (conditions on stronger realizations)."
    )
    lines.append("")

    # --- Hero table: A, B ---
    lines.append("## Hero: power curve data (A) and natural win rate (B)")
    lines.append("")
    lines.append(
        "| target ICIR | β* | n | n_won | A=P(pass|won) | Wilson A | "
        "B=P(win) R₀ | submission | underpowered |"
    )
    lines.append("|---:|---:|---:|---:|---:|---:|---:|---:|:---:|")
    for s in summaries:
        a_ci = f"[{s.a_lo:.3f}, {s.a_hi:.3f}]"
        flag = "yes" if s.underpowered else "no"
        lines.append(
            f"| {s.strength:.2f} | {s.beta:.4f} | {s.n_seeds} | {s.n_won} | "
            f"{s.a_hat:.3f} | {a_ci} | {s.b_hat:.3f} | "
            f"{s.submission_hat:.3f} | {flag} |"
        )
    lines.append("")
    lines.append(
        "Under-powered strengths (n_won small) show wide Wilson CIs and are "
        "flagged; never smoothed or extrapolated (power-calibration.md §6)."
    )
    lines.append("")

    # --- Directional size (β=0) ---
    # FIX 1 / amended §6: size panel = unconditional champion rates over all R₀;
    # hero A at β=0 stays P(unanimous|won) and is a different estimand.
    size_rows = [s for s in summaries if float(s.strength) == 0.0]
    if not size_rows:
        raise ValueError(
            "directional-size panel requires β=0 on the strength grid "
            "(power-calibration.md §6 / iron law: size beside power always)"
        )
    s0 = size_rows[0]
    lines.append("## Directional size (β=0, same greater-battery)")
    lines.append("")
    lines.append(
        "This is a re-run of **this** greater-battery at zero signal, "
        "labeled *directional size*. It is **not** the killer demo's "
        "two-sided size (different battery form: DSR votes here, PBO is "
        "signed, p one-sided)."
    )
    lines.append("")
    lines.append(
        "Estimand: **unconditional champion** per-gate pass rate over all R₀ "
        "seeds (amended §6, 2026-07-17). One directed-scan champion exists every "
        "seed; size-type gates (FDR / pool-max / individual) should sit near "
        "nominal α on this estimand. PBO is excluded from the ≈α assertion "
        "(φ≤0.2 is a rule threshold, not a size guarantee). "
        "Hero-curve β=0 point stays `P(unanimous | won)` — a different estimand "
        "with wide CI when n_won is small; never conflated with the size panel."
    )
    lines.append("")
    lines.append(
        f"size_panel_n_seeds={s0.n_champion_samples} "
        f"size_panel_champion_unanimous={s0.champion_unanimous_hat:.3f} "
        f"Wilson [{s0.champion_unanimous_lo:.3f}, {s0.champion_unanimous_hi:.3f}]"
    )
    lines.append(
        f"- n_seeds={s0.n_seeds}, n_won(injected)={s0.n_won}, "
        f"n_champion_samples={s0.n_champion_samples}"
    )
    lines.append(
        f"- hero A (unanimous|won, informational at β=0)={s0.a_hat:.3f} "
        f"Wilson [{s0.a_lo:.3f}, {s0.a_hi:.3f}]"
    )
    lines.append(f"- B (P(injected wins))={s0.b_hat:.3f}")
    lines.append(f"- champion_gate_tpr: {s0.champion_gate_tpr}")
    lines.append("")

    # --- Per-gate TPR ---
    lines.append("## Per-gate TPR among won (default panel)")
    lines.append("")
    gate_keys: list[str] = []
    for s in summaries:
        for g in s.gate_tpr:
            if g not in gate_keys:
                gate_keys.append(g)
    if gate_keys:
        header = "| target ICIR | " + " | ".join(gate_keys) + " |"
        sep = "|---:|" + "|".join(["---:" for _ in gate_keys]) + "|"
        lines.append(header)
        lines.append(sep)
        for s in summaries:
            cells = []
            for g in gate_keys:
                v = s.gate_tpr.get(g, float("nan"))
                cells.append("—" if v != v else f"{v:.3f}")  # NaN check
            lines.append(f"| {s.strength:.2f} | " + " | ".join(cells) + " |")
    else:
        lines.append("*No won runs; per-gate TPR empty.*")
    lines.append("")

    # --- Submission power table ---
    lines.append("## Submission power (secondary; never overlaid on A)")
    lines.append("")
    lines.append(
        "P(unanimous pass | injected forced as the judged candidate). "
        "DSR is conservative off-champion (power-calibration.md §5 / §9). "
        "**Gate set (FIX 4):** fdr_by, dsr, pbo_cscv, noise_individual — "
        "pool_max is **excluded** from the submission unanimous denominator "
        "because pool_max has no force knob (it always judges the argmax "
        "champion; a forced non-champion never appears in its decisions)."
    )
    lines.append("")
    lines.append("| target ICIR | β* | P(pass) | Wilson |")
    lines.append("|---:|---:|---:|---:|")
    for s in summaries:
        lines.append(
            f"| {s.strength:.2f} | {s.beta:.4f} | {s.submission_hat:.3f} | "
            f"[{s.submission_lo:.3f}, {s.submission_hi:.3f}] |"
        )
    lines.append("")

    # --- Calibration decomposition ---
    lines.append("## Calibration decomposition (§4.2 / §7)")
    lines.append("")
    lines.append(f"Shell φ (median of 100 demo shells) = **{calibration.shell_phi:.6f}**")
    lines.append("")
    lines.append(
        f"Calibration seeds: SeedSequence({calibration.calibration_seed_root})"
        f".spawn({calibration.calibration_k})"
    )
    lines.append("")
    if calibration.beta_grid and calibration.mean_icir:
        lines.append("| β | E[IC] | ICvol | mean annualized ICIR | SE(mean ICIR) |")
        lines.append("|---:|---:|---:|---:|---:|")
        for i, b in enumerate(calibration.beta_grid):
            mic = calibration.mean_ic[i] if i < len(calibration.mean_ic) else float("nan")
            vol = (
                calibration.mean_ic_vol[i]
                if i < len(calibration.mean_ic_vol)
                else float("nan")
            )
            mir = calibration.mean_icir[i]
            se = calibration.se_icir[i] if i < len(calibration.se_icir) else float("nan")
            lines.append(f"| {b:.2f} | {mic:.5f} | {vol:.5f} | {mir:.4f} | {se:.4f} |")
    else:
        lines.append(
            "*Calibration curve not recomputed (β* supplied from frozen table).*"
        )
    lines.append("")
    lines.append("### Frozen β* table (axis = target ICIR; never overwritten by realized)")
    lines.append("")
    lines.append("| target ICIR | β* |")
    lines.append("|---:|---:|")
    for k in sorted(calibration.beta_star.keys(), key=lambda x: float(x)):
        lines.append(f"| {float(k):.2f} | {calibration.beta_star[k]:.6f} |")
    lines.append("")

    # --- β_t appendix (matched-ICIR + greater-battery TPR drops; §7 / FIX 2) ---
    lines.append("## Appendix: β_t regime-switch (PBO-optimism corrector)")
    lines.append("")
    lines.append(
        "Primary contrast = **matched realized ICIR** half-window "
        "(forward-off / backward-off); secondary = same-nominal-β; "
        "sensitivity = random-block (honestly scoped). Answers: points "
        "unanimous/PBO-TPR drops constant → matched episodic "
        "(power-calibration.md §7). Greater battery via court.judge + "
        "harness.aggregation_policy (same path as the main sweep)."
    )
    lines.append("")
    # Normalize legacy list payload
    payload: dict[str, Any]
    if beta_t_payload is None:
        payload = {}
    elif isinstance(beta_t_payload, list):
        payload = {"arms": beta_t_payload, "drops": [], "battery_ran": False}
    else:
        payload = beta_t_payload
    arms = list(payload.get("arms") or [])
    drops = list(payload.get("drops") or [])
    if drops:
        lines.append("### TPR drops (constant → mean matched episodic)")
        lines.append("")
        lines.append(
            "| ref ICIR | unan_const | unan_matched | **unan_drop** | "
            "pbo_const | pbo_matched | **pbo_drop** |"
        )
        lines.append("|---:|---:|---:|---:|---:|---:|---:|")
        for d in drops:
            lines.append(
                f"| {d['reference_icir']:.2f} | {d['unanimous_tpr_constant']:.3f} | "
                f"{d['unanimous_tpr_matched']:.3f} | **{d['unanimous_drop']:.3f}** | "
                f"{d['pbo_tpr_constant']:.3f} | {d['pbo_tpr_matched']:.3f} | "
                f"**{d['pbo_drop']:.3f}** |"
            )
        lines.append("")
        if drops:
            d0 = drops[0]
            lines.append(
                f"**Headline drop (ref ICIR={d0['reference_icir']:.2f}):** "
                f"unanimous TPR drops by {d0['unanimous_drop']:.3f} points; "
                f"PBO TPR drops by {d0['pbo_drop']:.3f} points "
                f"(constant → matched episodic)."
            )
            lines.append("")
    if arms:
        lines.append(
            "| arm | ref ICIR | β used | realized ICIR | n_seeds | "
            "unan_tpr | pbo_tpr | note |"
        )
        lines.append("|---|---:|---:|---:|---:|---:|---:|---|")
        for a in arms:
            ut = a.get("unanimous_tpr", float("nan"))
            pt = a.get("pbo_tpr", float("nan"))
            ns = a.get("n_seeds", 0)
            lines.append(
                f"| {a['arm']} | {a['reference_icir']:.2f} | "
                f"{a['beta_used']:.4f} | {a['realized_icir']:.4f} | {ns} | "
                f"{ut:.3f} | {pt:.3f} | {a['note']} |"
            )
        lines.append("")
        lines.append(
            f"battery_ran={payload.get('battery_ran', False)}. "
            "Primary arms (`*_matched`) solve β so full-sample ICIR matches the "
            "constant-β reference; secondary `same_nominal_*` confounds strength "
            "with episodicity. Random-block sensitivity remains a real-data hook."
        )
    elif cfg.run_beta_t_appendix:
        lines.append(
            f"*β_t appendix enabled but no arms recorded "
            f"(targets {cfg.beta_t_icir_targets}).*"
        )
    else:
        lines.append("*β_t appendix disabled for this config.*")
    lines.append("")

    # --- Pre-registration ---
    lines.append("## Pre-registration & no-victory-theater (§8)")
    lines.append("")
    lines.append(
        "- Frozen ICIR grid, β→ICIR calibration, seed budget, adaptive re-seed "
        "algorithm, decision lines, and aggregation were fixed **before** results."
    )
    lines.append(
        "- Realized ICIR is **never** written back onto the strength axis."
    )
    lines.append("- Size is reported beside power (when β=0 is on the grid).")
    lines.append(
        f"- Power seed root={run_config.get('power_seed_root')}; "
        f"R₀={run_config.get('r0')}; R_max={run_config.get('r_max')}."
    )
    lines.append("")

    text = "\n".join(lines) + "\n"
    (out / "report.md").write_text(text)
    return text


def report_has_honesty(text: str) -> bool:
    """True if first-screen honesty markers are present."""
    return (
        "Constructed oracle" in text or "constructed oracle" in text.lower()
    ) and ("annualized ICIR" in text or "√252" in text or "× 16" in text or "×16" in text)


def report_has_size_beside_power(text: str) -> bool:
    """True iff the β=0 size **DATA** row is present (FIX 3).

    Header alone (or an omission note) is **not** enough — the iron law requires
    the unconditional-champion size numbers to be rendered.
    """
    if "size_panel_n_seeds=" not in text:
        return False
    if "unconditional champion" not in text.lower():
        return False
    if "champion_gate_tpr" not in text:
        return False
    # Omission note must not pass
    if "size panel omitted" in text.lower():
        return False
    return True
