# Independent referee findings (parallel to grok, before grok re-run returned)

CONFIRMED real dynamic-import bypasses (reproduced against 92a1af6):
1. `from importlib import import_module\nim = import_module\nim('qlib')` — assignment rebind of
   import_module to a Name is NOT tracked (only `from importlib import import_module as X` is). MISSED.
2. `import importlib\nf = importlib.import_module\nf('qlib')` — assigning the .import_module ATTRIBUTE
   to a Name is not tracked. MISSED.
3. `import builtins\nbuiltins.__import__('qlib')` — Attribute attr=='__import__' not caught (only
   Name '__import__' and Attribute attr=='import_module' are). MISSED.

NOT bugs (verified correct):
- relative import resolution: escape needs level = depth+1 (court/ -> L2, court/sub/ -> L3,
  court/sub/deep/ -> L4). `from ...adapters` in court/sub/deep/ = court.adapters (within court) —
  correctly allowed. Confirmed with L4 escape flagged.
- scope: staged filter startswith('court/') excludes courtroom/, mycourt/, adapters/.
- import numpy.<anything> allowed (top=numpy) — declared limit (name trust), not a bug.

FIX PLAN (after reconciling with grok):
- add Attribute attr in {import_module, __import__} to dynamic detection (covers builtins.__import__).
- extend alias tracking to simple assignments (fixpoint): X = import_module / X = importlib.import_module
  / X = <known alias> / X = __import__ -> add X to alias set.
- red-tests for all three first.
