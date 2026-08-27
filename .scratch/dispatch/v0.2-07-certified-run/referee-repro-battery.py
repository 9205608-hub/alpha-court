import sys, os, json, tempfile
WT="[HOME]/.alpha-court/dispatch-worktrees/v02-07-certified-run-20260716-200904"
sys.path.insert(0, WT)
import numpy as np
from court.ledger import DeclaredProtocol, Window, content_hash, link_event_hash
from court.judge import Application
from harness.run import CertifiedRun
from harness.verify import verify, CertificationError
from harness.aggregation_policy import AggregationPolicy
class FakeEval:
    def __init__(s): s.w=Window("2024-01-01","2024-12-31")
    def evaluate(s,scores,metric):
        rng=np.random.default_rng(abs(hash(scores))%2**32)
        class R:pass
        r=R();r.index=[f"d{i}" for i in range(60)];r.values=rng.normal(0,1,60)
        r.meta={"metric":metric,"window":{"start":s.w.start,"end":s.w.end},"universe":"csi300",
        "n_evaluation_dates":60,"data_version":"t1","adapter_version":"0.1.0","qlib_version":"0.9.7",
        "config":{"provider_uri":"/d","label_expr":"x","quantile":0.2,"min_cross_section":5}}
        return r
POL=AggregationPolicy("unanimous-discriminating-v1","unanimous-discriminating",{})
RC={"universe":"csi300","config":{"provider_uri":"/d","label_expr":"x","quantile":0.2,"min_cross_section":5}}
dec=DeclaredProtocol(metric="ic",window=Window("2024-01-01","2024-12-31"),periods_per_year=252.0)
d=tempfile.mkdtemp();p=os.path.join(d,"l.jsonl")
run=CertifiedRun.create(p,RC,POL,FakeEval())
for i in range(3):
    t=run.propose(f"c{i}",{"f":i},{},dec);run.evaluate(t,f"s{i}")
run.judge([Application("fdr_by",{"q":0.05}),Application("fdr_bh",{"q":0.05})]);run.seal()
ev=[json.loads(l) for l in open(p).read().splitlines()]
vstats=[e.get("statistic") for e in ev if e.get("type")=="verdict"]
jb=[e for e in ev if e.get("payload",{}).get("kind")=="judgment"][0]
print("actual verdict statistics:", vstats)
print("judgment.battery before:", [a.get("statistic") for a in jb["payload"]["battery"]])
# shrink battery to just fdr_by, reforge whole chain
jb["payload"]["battery"]=[{"statistic":"fdr_by","params":{"q":0.05}}]
prev="0"*64
for e in ev:
    for k in ("prev_hash","event_hash"):e.pop(k,None)
    if e.get("type")=="seal": e["payload"]["chain_head"]=prev  # payload-nested (panel-correct)
    ch=content_hash(e);eh=link_event_hash(prev,ch);e["prev_hash"]=prev;e["event_hash"]=eh;prev=eh
d2=tempfile.mkdtemp();p2=os.path.join(d2,"l.jsonl")
open(p2,"w").write("\n".join(json.dumps(e,separators=(",",":")) for e in ev)+"\n")
try:
    rep=verify(p2)
    print("shrunk-battery forged chain -> verify PASS (Finding 1 CONFIRMED: battery lies, uncross-checked)")
except CertificationError as e:
    print(f"shrunk-battery -> RAISES: {str(e)[:60]}")
