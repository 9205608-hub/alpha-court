import sys, os, json, tempfile
WT = "[HOME]/.alpha-court/dispatch-worktrees/v02-07-certified-run-20260716-200904"
sys.path.insert(0, WT)
import numpy as np
from court.ledger import DeclaredProtocol, Window, canonical_json, content_hash, link_event_hash
from court.judge import Application
from harness.run import CertifiedRun, CertificationError
from harness.verify import verify
from harness.aggregation_policy import AggregationPolicy
from harness import anchor as anchor_mod

class FakeEval:
    def __init__(self): self.w = Window("2024-01-01","2024-12-31")
    def evaluate(self, scores, metric):
        rng = np.random.default_rng(abs(hash(scores)) % 2**32)
        class R: pass
        r = R(); r.index=[f"d{i}" for i in range(60)]; r.values=rng.normal(0,1,60)
        r.meta={"metric":metric,"window":{"start":self.w.start,"end":self.w.end},
                "universe":"csi300","n_evaluation_dates":60,"data_version":"t1",
                "adapter_version":"0.1.0","qlib_version":"0.9.7",
                "config":{"provider_uri":"/d","label_expr":"x","quantile":0.2,"min_cross_section":5}}
        return r
POL = AggregationPolicy("unanimous-discriminating-v1","unanimous-discriminating",{})
RC = {"universe":"csi300","config":{"provider_uri":"/d","label_expr":"x","quantile":0.2,"min_cross_section":5}}
dec = DeclaredProtocol(metric="ic", window=Window("2024-01-01","2024-12-31"), periods_per_year=252.0)

def honest(path, anchor=None):
    run = CertifiedRun.create(path, RC, POL, FakeEval(), anchor=anchor)
    for i in range(3):
        t = run.propose(f"claim {i}", {"f":i}, {}, dec); run.evaluate(t, f"s{i}")
    run.judge([Application("fdr_by", {"q":0.05})]); run.seal()
    return run

print("=== F-1 must now be CLOSED (brick -> reopen -> seal must RAISE) ===")
d=tempfile.mkdtemp(); p=os.path.join(d,"l.jsonl")
run=CertifiedRun.create(p, RC, POL, FakeEval())
for i in range(3):
    t=run.propose(f"c{i}",{"f":i},{},dec); run.evaluate(t,f"s{i}")
try: run.judge([Application("fdr_by",{"q":0.05}), Application("nonsense",{})])
except Exception as e: print(f"  judge bricked: {type(e).__name__}")
try:
    run2=CertifiedRun.open(p, FakeEval()); run2.seal(); verify(p)
    print("  STILL FAIL-OPEN (bad)")
except (CertificationError, ValueError) as e:
    print(f"  reopen seal now RAISES: {type(e).__name__}: {str(e)[:60]} -> F-1 CLOSED")

print("=== Finding A: honest run passes, forged head fails, empty backend fails ===")
# honest + matching anchor, delete manifest -> should PASS (worker's deviation)
d2=tempfile.mkdtemp(); p2=os.path.join(d2,"l.jsonl"); af=os.path.join(d2,"anc.jsonl")
fa=anchor_mod.FileAnchor(af); honest(p2, fa)
os.remove(os.path.join(d2,"run_manifest.json"))
try: verify(p2, anchor=fa); print("  honest run + real anchor + no manifest -> PASS (correct: genuinely anchored)")
except CertificationError as e: print(f"  honest run RAISED (would be false-positive): {str(e)[:50]}")
# empty backend -> must RAISE
fa_empty=anchor_mod.FileAnchor(os.path.join(tempfile.mkdtemp(),"empty.jsonl"))
try: verify(p2, anchor=fa_empty); print("  empty backend -> PASS (BAD fail-open)")
except CertificationError as e: print(f"  empty backend -> RAISES: {str(e)[:55]} -> fail-closed OK")
# forged chain + real anchor of original -> must RAISE
lines=open(p2).read().splitlines()
ev=[json.loads(l) for l in lines]
# forge: change a trial's spec, rebuild the whole chain
for e in ev:
    if e.get("type")=="trial": e["spec"]={"f":"FORGED"}; break
prev="0"*64
for e in ev:
    for k in ("prev_hash","event_hash"): e.pop(k,None)
    ch=content_hash(e); eh=link_event_hash(prev,ch); e["prev_hash"]=prev; e["event_hash"]=eh; prev=eh
d3=tempfile.mkdtemp(); p3=os.path.join(d3,"l.jsonl")
open(p3,"w").write("\n".join(json.dumps(e,separators=(",",":")) for e in ev)+"\n")
try: verify(p3, anchor=fa); print("  forged chain + real anchor -> PASS (BAD: Finding A still open)")
except CertificationError as e: print(f"  forged chain + real anchor -> RAISES: {str(e)[:55]} -> Finding A CLOSED")
