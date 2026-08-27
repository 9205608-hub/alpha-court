import numpy as np
from scipy.stats import norm
from scipy import integrate

# --- Dispute 1: 03 landmine-1 "N->2N is wrong"
# grok: verified ("错 2N 近似 |t|≈3.26 vs 真 E[max|SR|] |t|≈2.75")
# Panel A: refuted (E[max|Z|,100]=2.7470 vs E[max Z,200]=2.7460, diff 0.0009)
def e_max_signed(n):   # E[max of n iid N(0,1)]
    f = lambda x: 1 - norm.cdf(x)**n
    g = lambda x: norm.cdf(x)**n
    a, _ = integrate.quad(f, 0, 12); b, _ = integrate.quad(g, -12, 0)
    return a - b
def e_max_abs(n):      # E[max of n iid |N(0,1)|]
    f = lambda x: 1 - (2*norm.cdf(x)-1)**n
    a, _ = integrate.quad(f, 0, 12)
    return a
m_abs100 = e_max_abs(100); m_s200 = e_max_signed(200); m_s100 = e_max_signed(100)
print(f"E[max|Z|,100] = {m_abs100:.4f}")
print(f"E[max Z, 200] = {m_s200:.4f}   diff vs abs100 = {m_abs100-m_s200:+.4f}")
print(f"E[max Z, 100] = {m_s100:.4f}   (landmine-2 gap = {m_abs100-m_s100:.4f} SR-std)")
gamma = 0.5772156649015329
def evt_maxz(n):  # Bailey 2014 Eq.(1) EVT approx, mean 0 std 1
    return (1-gamma)*norm.ppf(1-1/n) + gamma*norm.ppf(1-1/(n*np.e))
print(f"EVT approx N=100: {evt_maxz(100):.4f} (exact {m_s100:.4f}, err {abs(evt_maxz(100)-m_s100):.4f})")
print(f"EVT approx N=200: {evt_maxz(200):.4f}")
print(f"sqrt(2 ln 200)  = {np.sqrt(2*np.log(200)):.4f}  <- grok's 3.26 looks like this asymptote")

# --- Dispute 2: seed-tree collision (Panel A minor-4)
from numpy.random import SeedSequence
cal = SeedSequence(20260711).spawn(64)
swp = SeedSequence(20260711).spawn(2)
same = (cal[0].generate_state(4).tolist() == swp[0].generate_state(4).tolist() and
        cal[1].generate_state(4).tolist() == swp[1].generate_state(4).tolist())
print(f"calibration children 0/1 == sweep-seed-20260711 children 0/1: {same}")

# --- Spot-check: Panel A BLOCKER-1 mechanism (light: S=8, 70 combos, iid daily IC)
rng = np.random.default_rng(7)
T, S, N, reps = 480, 8, 100, 40
from itertools import combinations
combos = list(combinations(range(S), S//2))
def phi(mat):
    blocks = mat.reshape(S, T//S, N)
    lam_neg = 0
    for c in combos:
        ins = blocks[list(c)].reshape(-1, N); oos = np.delete(blocks, list(c), 0).reshape(-1, N)
        met_is = ins.mean(0)/ins.std(0, ddof=1); met_oos = oos.mean(0)/oos.std(0, ddof=1)
        star = met_is.argmax()
        r = (met_oos <= met_oos[star]).sum()  # rank of star among oos (higher better)
        w = r/(N+1)
        if np.log(w/(1-w)) < 0: lam_neg += 1
    return lam_neg/len(combos)
def run(mu_daily, half):
    out = []
    for _ in range(reps):
        m = rng.normal(0, 1, (T, N))
        if half: m[:T//2, 0] += 2*mu_daily      # ON first half only, nominal 2x
        else:    m[:, 0] += mu_daily
        out.append(phi(m))
    return np.mean(out)
mu4 = 4.0/np.sqrt(252)   # daily mean IC for ICIR_ann=4 (unit IC vol)
print(f"phi const ICIR4        = {run(mu4, False):.3f}")
print(f"phi half nominal-match = {run(mu4, True):.3f}   (full-sample ICIR ~4: strength-matched half-window)")
print(f"phi const ICIR2        = {run(mu4/2, False):.3f}")
print(f"phi half nominal ICIR4->full2 = {run(mu4/2*2*0+mu4/2, False):.3f} placeholder")
