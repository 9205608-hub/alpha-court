import sys, os, json, shutil, tempfile
WT = "[HOME]/.alpha-court/dispatch-worktrees/v02-07-certified-run-20260716-200904"
sys.path.insert(0, WT)
import numpy as np
from court.ledger import DeclaredProtocol, Window
from court.judge import Application
from harness.run import CertifiedRun, CertificationError
from harness.verify import verify
from harness.aggregation_policy import AggregationPolicy
from harness import anchor as anchor_mod

class FakeEval:
    def __init__(self): self.w = Window("2024-01-01","2024-12-31")
    def evaluate(self, scores, metric):
        rng = np.random.default_rng(abs(hash(scores)) % 2**32)
        vals = rng.normal(0, 1, 60)
        class R: pass
        r = R(); r.index=[f"d{i}" for i in range(60)]; r.values=vals
        r.meta={"metric":metric,"window":{"start":self.w.start,"end":self.w.end},
                "universe":"csi300","n_evaluation_dates":60,"data_version":"t1",
                "adapter_version":"0.1.0","qlib_version":"0.9.7",
                "config":{"provider_uri":"/d","label_expr":"x","quantile":0.2,"min_cross_section":5}}
        return r

POL = AggregationPolicy("unanimous-discriminating-v1","unanimous-discriminating",{})
RC = {"universe":"csi300","config":{"provider_uri":"/d","label_expr":"x","quantile":0.2,"min_cross_section":5}}
dec = DeclaredProtocol(metric="ic", window=Window("2024-01-01","2024-12-31"), periods_per_year=252.0)

# ---- Finding F-1: judge brick -> reopen -> seal -> verify PASS ----
print("=== F-1: mid-battery brick revived via open() ===")
d = tempfile.mkdtemp(); p = os.path.join(d, "l.jsonl")
run = CertifiedRun.create(p, RC, POL, FakeEval())
for i in range(3):
    t = run.propose(f"claim {i}", {"f":i}, {}, dec); run.evaluate(t, f"s{i}")
try:
    run.judge([Application("fdr_by", {"q":0.05}), Application("nonsense_stat", {})])
    print("  judge did NOT raise (?!)")
except Exception as e:
    print(f"  judge raised: {type(e).__name__} — bricked in-memory")
try:
    run.seal(); print("  in-memory seal SUCCEEDED (bad)")
except Exception as e:
    print(f"  in-memory seal blocked: {type(e).__name__}")
# reopen
try:
    run2 = CertifiedRun.open(p, FakeEval())
    sid = run2.seal()
    rep = verify(p)
    print(f"  REOPEN seal SUCCEEDED sid={sid}, verify PASS -> FAIL-OPEN CONFIRMED (n_verdicts={rep.n_verdicts})")
except Exception as e:
    print(f"  reopen/seal/verify blocked: {type(e).__name__}: {str(e)[:70]}")

# ---- Finding A: anchor disabled by deleting manifest ----
print("=== Finding A: anchor silently disabled by deleting manifest ===")
d2 = tempfile.mkdtemp(); p2 = os.path.join(d2, "l.jsonl")
anchor_file = os.path.join(d2, "anchors.jsonl")
fa = anchor_mod.FileAnchor(anchor_file)
run = CertifiedRun.create(p2, RC, POL, FakeEval(), anchor=fa)
for i in range(3):
    t = run.propose(f"claim {i}", {"f":i}, {}, dec); run.evaluate(t, f"s{i}")
run.judge([Application("fdr_by", {"q":0.05})]); run.seal()
rep = verify(p2, anchor=fa); print(f"  honest verify(anchor) PASS, head={rep.chain_head[:12]}")
# now delete the manifest, re-verify with the real anchor
mani = os.path.join(d2, "run_manifest.json")
os.remove(mani)
try:
    rep = verify(p2, anchor=fa)
    print(f"  after DELETING manifest, verify(anchor=real) STILL PASS -> Finding A CONFIRMED (anchor not consulted)")
except CertificationError as e:
    print(f"  after deleting manifest, verify raised: {str(e)[:70]}")
