# Rework: v0.1-08e — one referee nit on court/noise.py

Your delivery passed adversarial review: both lenses pass, all four §8 hand
vectors match an independent reference exactly, every in-contract guard path
verified. One docstring-precision nit. Modify ONLY court/noise.py (and
tests/test_noise.py if you add a test), commit with message
`v0.1-08e: address referee findings`, and end with ONLY the JSON receipt
(ticket_id `v0.1-08e`, fresh commit hash).

## MINOR

1. `court/noise.py` (~lines 84-102, Raises docstring): out-of-contract input
   TYPES (e.g. a generator as `nulls`, observed=None) raise TypeError from
   inside numpy conversion, while the Raises section promises ValueError for
   all failure paths. Behavior is fine (always fail-closed); make the
   docstring precise: ValueError for in-contract guard violations (empty /
   non-1-D / non-finite nulls, non-finite observed, alpha outside (0,1));
   TypeError may propagate for arguments of the wrong type entirely.

## Delivery protocol

Run your full suite + ruff; record real exit codes; `git status --porcelain`
must be empty after the commit; final output = ONLY the JSON receipt.
