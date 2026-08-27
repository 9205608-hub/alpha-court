# CR-NN — <short title>

A commander-rework entry is **not a confession paragraph**. A file that only says
cause/fix/prevention passes an existence check and is compliance theater (grok
RP-1 review). The four fields below are the content contract; `scripts/reflow-gate.sh`
fails if any is missing or if `root_cause_id` is not in the frozen vocab.

- **root_cause_id**: `<one id from .scratch/reflow/root-cause-vocab.md>`
- **attribution**: worker-fault | contract-fault | referee-fault | tooling | framework-fault
- **occurrences**: `<n>` (≥2 ⇒ promoted by recurrence D3(a); n=1 ⇒ must be expensive+systemic D3(b))
- **evidence**: `<file:line / TIMELINE date / worker-bridge incident / meta-review pointer>`
- **fix**: `<what changed — commit / file:line — not an intention>`
- **anti-recurrence**: `<a re-runnable check that FAILS if this class recurs — a command, a red-test, a tripwire. If it cannot be mechanized, say so and name the process rule that stands in.>`
- **polluted-rework**: `<link to the worker rework this fault caused, or "none">`
