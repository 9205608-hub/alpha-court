# Referee verification round 1 (output in referee-verify-output.txt)
import numpy as np, sys, json, tempfile, os
rng = np.random.default_rng(12345)
T = 480; R = 200_000
for target in (1.5, 2.0):
    lam = target / np.sqrt(252) * np.sqrt(T)
    t_sig = rng.normal(lam, 1.0, R)
    max_abs_noise = np.abs(rng.normal(0, 1, (R, 99))).max(axis=1)
    print(f"ICIR_ann={target}: lambda={lam:.4f}  P(win)={(t_sig > max_abs_noise).mean():.4f}")
from scipy.stats import norm
for target in (1.5, 2.0):
    lam = target / np.sqrt(252) * np.sqrt(T)
    print(f"fixed-mean approx ICIR={target}: P(max|Z|<lambda)={(2*norm.cdf(lam)-1)**99:.4f}")
sys.path.insert(0, "[HOME]/Desktop/alpha-court/.claude/worktrees/v02-design-audit-ro")
from court import Ledger, DeclaredProtocol, Window, Series
d = tempfile.mkdtemp(); path = os.path.join(d, "ledger.jsonl")
led = Ledger.open(path)
h = led.register_hypothesis("test")
dec = DeclaredProtocol(metric="ic", window=Window("2024-01-01","2024-12-31"), periods_per_year=252.0)
t1 = led.register(h, {"f":"a"}, {}, dec); t2 = led.register(h, {"f":"b"}, {}, dec)
s = Series(index=("d1","d2","d3"), values=(0.1,0.2,0.3))
led.record(t1, s); led.record(t2, s)
print("before attack:", led.status(t1), led.status(t2))
lines = open(path).read().splitlines(keepends=True)
open(path,"w").write("".join(lines[:-1]))
led2 = Ledger.open(path)
print("after attack: ", led2.status(t1), led2.status(t2), "| open() raised: NO")
