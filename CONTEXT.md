# alpha-court

Ubiquitous language for the statistical court: the vocabulary of trials, hypotheses,
and verdicts shared by `court/`, the harness, and all documentation. Glossary only —
no implementation detail lives here.

## Language

**Trial**:
One evaluation of one factor configuration (construction × parameter set × evaluation
window) producing one performance series. The atomic, append-only unit of the ledger —
a parameter sweep of k settings is k trials, never one.
_Avoid_: experiment, run, backtest, test (ambiguous with hypothesis test)

**Hypothesis**:
One economic claim about a return driver (e.g. "momentum predicts returns"). Groups
trials: one hypothesis has one or more trials; every trial belongs to exactly one
hypothesis.
_Avoid_: idea, factor family (family describes construction lineage, not the claim),
signal

**Verdict**:
One append-only judgment record: a court statistic applied to an explicit scope of
trials, with its inputs, intermediate values, and decision. Verdicts never mutate
trial records; a trial's status is derived from which records exist for it.
_Avoid_: result, evaluation (that is the series-producing step), score

**Declared protocol**:
The evaluation protocol (metric, test direction, window, frequency) locked into a
trial record at registration, before any performance series exists. The basis of the
v0.2 pre-registration gate.
_Avoid_: config (too broad), settings

**Effective trial count (N)**:
The multiplicity input each court statistic derives from the ledger at judgment time.
Never a stored field — PBO uses all columns in its selection pool, DSR derives a
ρ-adjusted independent count from the raw trial count M, BHY (v0.1) treats one trial
as one hypothesis test over the full family. There is no single "the N of the ledger."
_Avoid_: trial count (unqualified), number of tests (unqualified)

**Ledger**:
The append-only audit log of hypotheses, trials, and verdicts — the court's single
source of evidence. It has no verb that removes or hides a record.
_Avoid_: database, registry, log (unqualified)

**Scope**:
The explicit set of trial ids a verdict is computed over (PBO's selection pool, BHY's
FDR family). Every verdict names its scope; there is no implicit "everything."
_Avoid_: pool (unqualified), universe (market term, belongs to adapters)

**Null jury**:
The set of information-free control factors a noise-control verdict compares a
candidate against — in v0.1, circular time-shifts of the candidate's own score panel.
Jurors are evidence inside one verdict (statistic values + generation protocol recorded
there); they are never registered as trials and never enter any FDR family.
_Avoid_: null trials (jurors are not trials), controls (too generic)
