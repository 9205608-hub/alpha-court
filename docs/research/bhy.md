# BHY multiple-testing control — implementation-grade literature note

**Ticket:** v0.1-06  
**Role in alpha-court:** one of four kernel statistics — false-discovery-rate (FDR)
control over a ledger of many factor trials.  
**Scope:** rewrite the public procedures cleanly enough that a later
implementation can be checked equation-by-equation against the papers.  
**No code in this note.**

Notation convention used below:

- Papers’ own symbols are introduced first.
- alpha-court ledger size is written \(N\) (one trial = one hypothesis);
  the papers often write \(m\) or \(M\) for the same quantity.
- Target FDR level is written \(q\) (Benjamini–Hochberg’s \(q^\ast\); Harvey–Liu–Zhu’s
  \(\alpha_d\)).

---

## 1. Sources

### Primary procedures

1. **Benjamini, Y. & Hochberg, Y. (1995).**  
   “Controlling the False Discovery Rate: A Practical and Powerful Approach to
   Multiple Testing.”  
   *Journal of the Royal Statistical Society, Series B (Methodological)*
   **57**(1), 289–300.  
   DOI: [10.1111/j.2517-6161.1995.tb02031.x](https://doi.org/10.1111/j.2517-6161.1995.tb02031.x)  
   Defines FDR and the linear step-up procedure (often called **BH**).
   Key locations: §2.1 (FDR definition, their \(Q_e\)); §3.1 procedure (1);
   Theorem 1 (FDR control under independence); Theorem 2 (post-hoc maximisation
   view).

2. **Benjamini, Y. & Yekutieli, D. (2001).**  
   “The Control of the False Discovery Rate in Multiple Testing under
   Dependency.”  
   *Annals of Statistics* **29**(4), 1165–1188.  
   DOI: [10.1214/aos/1013699998](https://doi.org/10.1214/aos/1013699998)  
   Extends BH to positive dependence (PRDS) and gives the more conservative
   procedure valid under **arbitrary** dependence (often called **BY**).
   Key locations: Property PRDS; Theorem 1.2 (BH under PRDS with \(c(m)=1\));
   Theorem 1.3 (arbitrary dependence with harmonic factor
   \(c(m)=\sum_{i=1}^{m} 1/i\)).

### Finance-context usage and thresholds

3. **Harvey, C. R., Liu, Y. & Zhu, H. (2016).**  
   “…and the Cross-Section of Expected Returns.”  
   *Review of Financial Studies* **29**(1), 5–68.  
   DOI: [10.1093/rfs/hhv059](https://doi.org/10.1093/rfs/hhv059)  
   (NBER Working Paper No. 20592 is the freely available draft of the same
   research programme.)  
   Applies Bonferroni, Holm, and **BHY** (their name for the BY-style
   sequential FDR procedure with \(c(M)=\sum 1/j\)) to the zoo of published
   factors; discusses correlation among trials on common return data; reports
   elevated \(t\)-ratio hurdles (often \(\approx 3\)) once multiplicity is
   acknowledged. Key locations (published RFS section numbering): §3.3.2
   (false discovery rate, journal p.14); §3.4.1–3.4.3 (Bonferroni, Holm, and
   BHY adjustments; BHY heading at journal p.20); §3.4.3 (BHY algorithm and
   choice of \(c(M)\)); §3.5 (summary statistics; two-sided \(t\)-tests in
   footnote 26); §3.7.2 (hidden tests / \(M>R\)).  
   **Pinpoint convention:** all HLZ citations in this note use the **published
   RFS** headings. The RFS typesetting itself retains some working-paper
   cross-references (e.g. it still prints “Example 4.4.1” inside the
   3.x-numbered sections), so text-searching either numbering finds the
   material; our pinpoints follow the published headings.

### Supporting citations used in §4

4. **Newey, W. K. & West, K. D. (1987).**  
   “A Simple, Positive Semi-Definite, Heteroskedasticity and Autocorrelation
   Consistent Covariance Matrix.”  
   *Econometrica* **55**(3), 703–708.  
   DOI: [10.2307/1913610](https://doi.org/10.2307/1913610)  
   HAC standard errors for serially correlated moment conditions (e.g. IC or
   return series).

5. **Sarkar, S. K. (2002).**  
   “Some Results on False Discovery Rate in Stepwise Multiple Testing
   Procedures.”  
   *Annals of Statistics* **30**(1), 239–257.  
   Further results on FDR of step-up / step-down procedures under dependence
   (cited by the finance literature alongside BY 2001 for the PRDS case).

---

## 2. The BH step-up procedure

### 2.1 FDR as the target error rate

Benjamini & Hochberg (1995, §2.1, Table 1) partition \(m\) tested nulls into true
nulls (\(m_0\)) and false nulls. After a multiple-test decision:

|  | Declared non-significant | Declared significant | Total |
|--|--------------------------|----------------------|-------|
| True null | \(U\) | \(V\) | \(m_0\) |
| Non-true null | \(T\) | \(S\) | \(m-m_0\) |
| Total | \(m-R\) | \(R\) | \(m\) |

Here \(R = V+S\) is the (observable) number of rejections / “discoveries”;
\(V\) is the (unobservable) number of false discoveries.

They define the false-discovery **proportion**
\[
Q \;=\; \frac{V}{V+S} \;=\; \frac{V}{R}
\]
with the convention \(Q=0\) when \(R=0\) (no rejection ⇒ no false discovery
proportion to speak of). The **false discovery rate** is the expectation
(Benjamini & Hochberg 1995, §2.1, display after the definition of \(Q\)):

\[
Q_e \;=\; E(Q) \;=\; E\!\left(\frac{V}{R}\right).
\]

Two structural facts they record (same subsection, properties (a)–(b)):

- If all nulls are true (\(m_0=m\)), then FDR coincides with the family-wise
  error rate (FWER) in the weak sense: \(Q_e = P(V\ge 1)\).
- If some nulls are false, FDR \(\le\) FWER, so controlling FDR can be less
  stringent (and more powerful) than controlling FWER.

Harvey, Liu & Zhu (2016, §3.3.2 “False discovery rate”, journal p.14) restate
the same objects for factor research as \(\mathrm{FDP}=N_{0|r}/R\) and
\(\mathrm{FDR}=E[\mathrm{FDP}]\), with \(R\) the number of factors declared
significant.

### 2.2 Ordered \(p\)-values and the linear step-up rule

**Setup** (Benjamini & Hochberg 1995, §3.1).  
Test \(m\) null hypotheses \(H_1,\ldots,H_m\) with corresponding \(p\)-values
\(P_1,\ldots,P_m\). Let
\[
P_{(1)}\;\le\; P_{(2)}\;\le\; \cdots \;\le\; P_{(m)}
\]
be the ordered \(p\)-values, and write \(H_{(i)}\) for the null associated with
\(P_{(i)}\). Fix a target FDR level \(q^\ast\in(0,1)\) (we write \(q\) below).

**Procedure (BH step-up)** — Benjamini & Hochberg (1995, §3.1, expression (1)):

1. Order the \(p\)-values as above.
2. Compute
   \[
   k \;=\; \max\Bigl\{\, i\in\{1,\ldots,m\} \;:\;
     P_{(i)}\;\le\; \frac{i}{m}\, q^\ast \,\Bigr\},
   \]
   or set \(k=0\) if no such \(i\) exists.
3. **Reject** \(H_{(1)},\ldots,H_{(k)}\) (the rejection set). If \(k=0\), reject
   nothing.

Equivalently, in alpha-court notation (\(N=m\), \(q=q^\ast\)):

\[
k^\ast \;=\; \max\Bigl\{\, i \;:\; p_{(i)}\;\le\; \frac{i}{N}\, q \,\Bigr\},
\qquad
\text{reject } \{\,H_{(1)},\ldots,H_{(k^\ast)}\,\}.
\]

**Step-up direction (modern terminology).** The defining search is for the
**largest** index \(i\) that still meets its critical value
\(\frac{i}{m}q^\ast\). Operationally one may scan from \(i=m\) downward until
the first success, then reject **all** ranks \(1,\ldots,k\) — including ranks
whose own \(p_{(i)}\) may exceed \(\frac{i}{m}q^\ast\). The rejection region is
a single initial segment of the ordered list. Benjamini & Yekutieli (2001)
call this family of rules **step-up** procedures throughout (e.g. “general
step-up procedures”, p.1169); Harvey–Liu–Zhu (2016, footnote 23) adopt the
same modern convention. **Caution:** Benjamini & Hochberg (1995, p.294)
themselves labelled expression (1) a “step-down” procedure — pre-2001
wording that is **opposite** to the later standard. This note uses the modern
(BY 2001 / HLZ) names while following BH 1995’s operational rule. Contrast
Holm’s step-down FWER rule (Harvey–Liu–Zhu 2016, §3.4.2).

### 2.3 What BH controls, and under what dependence

**Theorem (independence).**  
Benjamini & Hochberg (1995, Theorem 1): if the test statistics corresponding to
the true nulls are **independent**, and the \(p\)-values for true nulls are
Uniform\((0,1)\) (or stochastically larger), then the procedure of §2.2 controls
FDR at level
\[
Q_e \;\le\; \frac{m_0}{m}\, q^\ast \;\le\; q^\ast.
\]

**Extension to positive dependence (PRDS).**  
Benjamini & Yekutieli (2001, Property PRDS and Theorem 1.2; also Sarkar 2002):
the **same** critical values \(\frac{i}{m}q^\ast\) (i.e. \(c(m)=1\)) still control
FDR at \(q^\ast\) when the joint distribution of the test statistics is
**positive regression dependent on each one from the subset of true nulls**
(PRDS on the true-null index set). Many one-sided tests of positively correlated
normal means fall under PRDS.

**What PRDS does *not* cover.** Arbitrary (including negative) dependence is
**not** guaranteed by plain BH; that is the role of the BY correction in §3.

### 2.4 Adjusted \(p\)-values (reporting form of the same rule)

For implementation and reporting, an equivalent sequential **adjusted \(p\)-value**
(BH \(q\)-value style) is (cf. the sequential form used by Harvey–Liu–Zhu 2016,
§3.4.3, for the related BHY adjustment; the \(c(m)=1\) special case is BH):

\[
\tilde p_{(m)}^{\mathrm{BH}} \;=\; P_{(m)},
\qquad
\tilde p_{(i)}^{\mathrm{BH}}
  \;=\;
  \min\Bigl(\,
    \tilde p_{(i+1)}^{\mathrm{BH}},\;
    \frac{m}{i}\, P_{(i)}
  \,\Bigr)
  \quad (i=m-1,\ldots,1),
\]
then clip to \([0,1]\). Reject \(H_{(i)}\) at level \(q\) iff
\(\tilde p_{(i)}^{\mathrm{BH}}\le q\). The backward \(\min\) enforces
**monotonicity** of adjusted \(p\)-values in the ordered list (see §7).

---

## 3. The BY correction

### 3.1 The harmonic factor \(c(m)\)

Benjamini & Yekutieli (2001, Theorem 1.3) introduce a multiplier that shrinks
every critical value so that FDR control holds under **no assumption** on the
joint dependence of the \(p\)-values. With their notation, set

\[
c(m)
  \;=\;
  \sum_{i=1}^{m} \frac{1}{i}
  \;=\; H_m
  \qquad\text{(the \(m\)-th harmonic number).}
\]

Harvey, Liu & Zhu (2016, §3.4.3, journal pp.20–21) write the same object as
\[
c(M)\;=\;\sum_{j=1}^{M}\frac{1}{j}
\]
and adopt it explicitly because that choice “allows the procedure to work under
arbitrary dependency among the test statistics.”

### 3.2 Adjusted step-up criterion

**BY procedure** (Benjamini & Yekutieli 2001, Theorem 1.3; Harvey–Liu–Zhu 2016,
§3.4.3 “Benjamini, Hochberg, and Yekutieli’s adjustment”):

1. Order \(p\)-values \(P_{(1)}\le\cdots\le P_{(m)}\) as in BH.
2. Let
   \[
   k \;=\; \max\Bigl\{\, i \;:\;
     P_{(i)}
       \;\le\;
     \frac{i}{\,m\, c(m)\,}\, q
   \,\Bigr\}
   \]
   (or \(k=0\) if none).
3. Reject \(H_{(1)},\ldots,H_{(k)}\).

In alpha-court notation (\(N=m\)):

\[
p_{(i)}
  \;\le\;
  \frac{i\, q}{\,N\, c(N)\,},
  \qquad
  c(N)=\sum_{i=1}^{N}\frac{1}{i},
  \qquad
  k^\ast=\max\{i:\text{inequality holds}\}.
\]

**Adjusted \(p\)-values** (Harvey–Liu–Zhu 2016, §3.4.3, display for \(p^{\mathrm{BHY}}\)):

\[
p^{\mathrm{BY}}_{(m)} \;=\; \min\bigl(1,\; c(m)\, P_{(m)}\bigr),
\qquad
p^{\mathrm{BY}}_{(i)}
  \;=\;
  \min\Bigl(\,
    p^{\mathrm{BY}}_{(i+1)},\;
    \frac{m\, c(m)}{i}\, P_{(i)}
  \,\Bigr)
  \quad (i=m-1,\ldots,1),
\]
clip to 1; reject when \(p^{\mathrm{BY}}_{(i)}\le q\).

**Erratum against the printed HLZ display (referee ruling, 2026-07-10).** The
display as printed in Harvey–Liu–Zhu 2016 §3.4.3 initializes the recursion with
\(p^{\mathrm{BY}}_{(m)} = P_{(m)}\) — i.e. it omits the rank-\(m\) coefficient
\(m\,c(m)/m = c(m)\) at the top rank only. For \(c(m)>1\) that base case is
internally inconsistent: it breaks the identity "adjusted \(\le q\) ⟺ rejected
by the step-up \(k^\ast\)" that adjusted \(p\)-values exist to provide.
Counterexample: \(p=(0.04, 0.04)\), \(q=0.05\), \(m=2\), \(c(2)=1.5\): the BY
thresholds are \(\tau_1 \approx 0.0167\), \(\tau_2 \approx 0.0333\), so
\(k^\ast=0\) (reject nothing) — yet the printed recursion yields adjusted
values \((0.04, 0.04) \le q\), claiming two rejections. The base case above
(with the \(c(m)\) coefficient applied at rank \(m\) like every other rank) is
the unique self-consistent form; it is also the convention implemented by
R `p.adjust(method="BY")` and statsmodels `multipletests(method="fdr_by")`.
\(k^\ast\) and the rejection set are identical under both conventions — only
reported adjusted values differ.

### 3.3 Validity under arbitrary dependence

Benjamini & Yekutieli (2001, Theorem 1.3): with critical values
\(\frac{i}{m\,c(m)}\,q\) and \(c(m)=\sum_{i=1}^{m}1/i\), the step-up procedure
controls FDR at level \(q\) **under arbitrary dependence** among the test
statistics / \(p\)-values. (Harvey–Liu–Zhu 2016, §3.4.3 and footnote 24 —
“See Benjamini and Yekutieli (2001) for the proof” — restate and use this
guarantee.)

When \(c(m)=1\), one recovers BH, which is valid under independence
(Benjamini & Hochberg 1995, Theorem 1) and under PRDS
(Benjamini & Yekutieli 2001, Theorem 1.2), but **not** in general under
arbitrary dependence.

### 3.4 Power cost

Because \(c(m)>1\) for all \(m\ge 2\) and \(c(m)\sim \log m+\gamma\)
(\(\gamma\approx 0.57721\) Euler’s constant), every BY threshold is strictly
smaller than the corresponding BH threshold by the factor \(1/c(m)\):

\[
\frac{i\, q}{\,m\, c(m)\,}
  \;=\;
  \frac{1}{c(m)}
  \cdot
  \frac{i\, q}{m}
  \;<\;
  \frac{i\, q}{m}.
\]

Fewer hypotheses meet the tighter bar, so expected discoveries fall. Harvey,
Liu & Zhu (2016, §3.4.3) state the same trade-off in words: larger \(c(M)\)
makes \(p_{(k)}\le k\alpha_d/(M\,c(M))\) harder to satisfy, hence fewer
discoveries and an easier time keeping FDR below the target. That is the price of
a dependence-agnostic guarantee.

---

## 4. Where the \(p\)-values come from in our setting

BHY is a **map from a vector of \(p\)-values and a level \(q\) to a rejection
set**. It does not know about factors; the kernel must receive well-defined
\(p_i\) that match the trial ledger.

### 4.1 \(t\)-statistic of a mean IC (or return) series

For trial \(i\), let \(\{X_{i,t}\}_{t=1}^{T}\) be the time series of period
information coefficients (IC) or of portfolio returns that the trial produces.
Under the null of no predictive content / no premium,
\[
H_{0,i}:\; \mu_i \;=\; E[X_{i,t}] \;=\; 0.
\]
The classical one-sample \(t\)-statistic is
\[
t_i
  \;=\;
  \frac{\bar X_i}{\widehat{\mathrm{se}}(\bar X_i)},
  \qquad
  \bar X_i \;=\; \frac{1}{T}\sum_{t=1}^{T} X_{i,t}.
\]
With i.i.d. Gaussian \(X_{i,t}\) (or via standard asymptotic normal
approximation), \(t_i\) is referred to a Student-\(t\) or standard normal null
to produce \(p_i\).

Harvey, Liu & Zhu (2016, §3.4 opening and Table 4) take published factor
\(t\)-ratios as the primitive and convert them to two-sided \(p\)-values before
BHY; alpha-court does the same conversion from whatever \(t\) (or \(z\)) the
trial interface supplies.

### 4.2 One-sided vs two-sided

| Choice | Null / alternative (schematic) | Consequence for the ledger |
|--------|--------------------------------|----------------------------|
| **Two-sided** | \(H_0:\mu=0\) vs \(\mu\neq 0\) | \(p = 2(1-\Phi(|t|))\) (normal asymptotics). Matches HLZ’s “We usually calculate \(p\)-values based on two-sided \(t\)-tests” (Harvey–Liu–Zhu 2016, §3.5 footnote 26). Treats long and short predictive signs symmetrically. |
| **One-sided** | e.g. \(H_0:\mu\le 0\) vs \(\mu>0\) | \(p = 1-\Phi(t)\). More powerful when the sign is known *a priori*; **invalid** (anti-conservative) if the sign was chosen after seeing the data. |

**Court rule of thumb (for implementers):** default to **two-sided** unless the
trial record states a pre-registered direction. Mixing one- and two-sided
\(p\)-values inside one BHY call without documenting the choice makes the FDR
claim uninterpretable.

### 4.3 Autocorrelation: Newey–West / HAC standard errors

IC and return series are typically serially correlated. The classical
\(\widehat{\mathrm{se}}=\hat\sigma/\sqrt{T}\) then understates uncertainty and
inflates \(|t|\), which **feeds BHY over-optimistic \(p\)-values**.

Newey & West (1987) construct a heteroskedasticity- and
autocorrelation-consistent (HAC) estimator of the long-run variance of a moment
condition that is positive semi-definite by design (Bartlett kernel weights on
sample autocovariances up to a lag truncation \(L\)). For a scalar mean,
\[
\widehat{\mathrm{LRV}}
  \;=\;
  \hat\gamma_0
  + 2\sum_{\ell=1}^{L}
      \Bigl(1-\frac{\ell}{L+1}\Bigr)\hat\gamma_\ell,
  \qquad
  \widehat{\mathrm{se}}_{\mathrm{NW}}(\bar X)
  \;=\;
  \sqrt{\widehat{\mathrm{LRV}}/T},
\]
with \(\hat\gamma_\ell\) the sample autocovariance at lag \(\ell\)
(Newey & West 1987, main construction). Then
\(t_i^{\mathrm{NW}}=\bar X_i/\widehat{\mathrm{se}}_{\mathrm{NW}}\).

Using HAC SEs does not change the BHY algebra; it only changes the input
\(p\)-vector. The literature note’s contract is: **whatever SE is chosen must be
declared on the trial record**, so that the court can reproduce \(p_i\).

### 4.4 Aligning \(N\) with the trial ledger

In BH/BY, \(m\) (our \(N\)) is the number of hypotheses **in the family being
controlled** (Benjamini & Hochberg 1995, §2; Benjamini & Yekutieli 2001,
throughout). Harvey, Liu & Zhu (2016, §3.7.2) stress that published factors
under-represent the true number of trials \(M\), and that using too small an \(M\)
makes multiplicity corrections **too lenient**.

For alpha-court:

- \(N\) **must equal** the number of trials in the ledger that enter the FDR
  family — including null-archived failures, not only survivors.
- Dropping failed trials before BHY is a silent change of \(m\) and invalidates
  the FDR guarantee at the advertised \(q\).
- If a trial is excluded *a priori* by protocol (not by its \(p\)-value), document
  the restricted family; do not silently shrink \(N\).

---

## 5. BH vs BY decision guidance

### 5.1 What the statistics literature supports

| Regime | Supported procedure | Citation |
|--------|---------------------|----------|
| Independent true-null \(p\)-values | BH (\(c=1\)) controls FDR \(\le q\) | Benjamini & Hochberg (1995, Theorem 1) |
| PRDS / many positive-dependence structures | BH (\(c=1\)) still controls FDR \(\le q\) | Benjamini & Yekutieli (2001, Theorem 1.2); Sarkar (2002) |
| Arbitrary dependence (no PRDS claim) | BY with \(c(N)=\sum_{i=1}^{N}1/i\) | Benjamini & Yekutieli (2001, Theorem 1.3) |

### 5.2 Factor trials on shared data

Cross-sectional factor tests share the same return panel, overlapping stocks, and
often overlapping formation rules. Test statistics are therefore **dependent** —
typically positively correlated when factors load on common latent risks, but not
guaranteed to satisfy PRDS in every design (signed interactions, hedging
portfolios, and mechanically opposite constructions can induce negative
dependence).

Harvey, Liu & Zhu (2016):

- Explicitly adopt **BHY with** \(c(M)=\sum 1/j\) so control holds under
  **arbitrary** dependence (§3.4.3).
- Note that the original BH choice \(c(M)\equiv 1\) is valid when the test
  statistics are independent or positively dependent, whereas their harmonic
  \(c(M)\) “allows the procedure to work under arbitrary dependency among the
  test statistics” (§3.4.3, journal pp.20–21; proof pointer in footnote 24 to
  Benjamini & Yekutieli 2001).
- In their historical / simulation calibrations, multiplicity alone already
  pushes conventional \(t>2\) hurdles up to the neighbourhood of **\(t>3\)** for
  new factors once many trials are acknowledged (abstract and concluding
  discussion; BHY-implied cutoffs appear alongside Bonferroni/Holm in their
  tables).

### 5.3 Guidance for alpha-court

1. **Default for the kernel demo and for any ledger of correlated factors on one
   market panel:** run **BY** (harmonic \(c(N)\)). This matches HLZ’s conservative
   finance practice and does not require a PRDS proof for the IC design.
2. **BH (\(c=1\))** is acceptable only when dependence is argued to be
   independent or PRDS **and** that argument is recorded next to the verdict.
   Even then, reporting BY alongside BH is useful (power comparison).
3. Do not treat “factors are positively correlated, so BH is fine” as automatic:
   PRDS is a specific property of the joint law of the test statistics
   (Benjamini & Yekutieli 2001, Property PRDS), not a synonym for “corr \(>0\).”
4. Expect BY to reject **fewer** trials than BH at the same \(q\) (power cost,
   §3.4). That is a feature of the guarantee, not a bug.

---

## 6. Test vector (hand-worked, \(N=10\), \(q=0.05\))

This section is a fixed numerical fixture for a future `pytest` case. All
arithmetic uses exact rationals where noted; decimals are shown to enough places
to match an implementation’s float64 output for these inputs.

### 6.1 Harmonic factor \(c(10)\)

\[
c(10)
  \;=\;
  \sum_{i=1}^{10}\frac{1}{i}
  \;=\;
  1 + \tfrac12 + \tfrac13 + \tfrac14 + \tfrac15
  + \tfrac16 + \tfrac17 + \tfrac18 + \tfrac19 + \tfrac{1}{10}.
\]

Partial sums below are the IEEE-754 **float64** representations from an
ascending sum \(s \leftarrow s + (1/i)\) in double precision (Python/C `double`
`repr`). This is the convention an implementation’s self-test should match.

| \(i\) | \(1/i\) (float64) | cumulative sum (float64) |
|------:|------------------:|-------------------------:|
| 1 | 1.0 | 1.0 |
| 2 | 0.5 | 1.5 |
| 3 | 0.3333333333333333 | 1.8333333333333333 |
| 4 | 0.25 | 2.083333333333333 |
| 5 | 0.2 | 2.283333333333333 |
| 6 | 0.16666666666666666 | 2.4499999999999997 |
| 7 | 0.14285714285714285 | 2.5928571428571425 |
| 8 | 0.125 | 2.7178571428571425 |
| 9 | 0.1111111111111111 | 2.8289682539682537 |
| 10 | 0.1 | **2.9289682539682538** |

Exact rational value: \(c(10)=H_{10}=7381/2520\).  
Decimal (ticket check): \(c(10)\approx 2.928968\).

### 6.2 Critical-value sequences at \(q=0.05\), \(N=10\)

\[
\tau_i^{\mathrm{BH}}
  \;=\;
  \frac{i}{N}\,q
  \;=\;
  \frac{i}{10}\cdot 0.05
  \;=\;
  0.005\, i,
\]
\[
\tau_i^{\mathrm{BY}}
  \;=\;
  \frac{i\, q}{\,N\, c(10)\,}
  \;=\;
  \frac{i\cdot 0.05}{\,10\cdot c(10)\,}
  \;=\;
  \frac{0.005\, i}{c(10)}.
\]

| \(i\) | \(\tau_i^{\mathrm{BH}}=i\cdot q/N\) | \(\tau_i^{\mathrm{BY}}=i\cdot q/(N\cdot c(10))\) |
|------:|------------------------------------:|-----------------------------------------------:|
| 1 | 0.005000 | 0.00170709 |
| 2 | 0.010000 | 0.00341417 |
| 3 | 0.015000 | 0.00512126 |
| 4 | 0.020000 | 0.00682834 |
| 5 | 0.025000 | 0.00853543 |
| 6 | 0.030000 | 0.01024251 |
| 7 | 0.035000 | 0.01194960 |
| 8 | 0.040000 | 0.01365669 |
| 9 | 0.045000 | 0.01536377 |
| 10 | 0.050000 | 0.01707086 |

(\(\tau_i^{\mathrm{BY}}\) rounded to 8 d.p. from exact \(0.005\,i/(7381/2520)\).)

### 6.3 Chosen \(p\)-value vector

Unordered trial labels \(H_1,\ldots,H_{10}\) with raw \(p\)-values (include a
**tie**, a rank that **fails its own BH threshold but is still rejected** by
step-up, and **exact equality** borderline cases):

| Label | raw \(p\) |
|-------|----------:|
| \(H_1\) | 0.0400 |
| \(H_2\) | 0.0008 |
| \(H_3\) | 0.0280 |
| \(H_4\) | 0.0900 |
| \(H_5\) | 0.0050 |
| \(H_6\) | 0.0260 |
| \(H_7\) | 0.0100 |
| \(H_8\) | 0.0450 |
| \(H_9\) | 0.0030 |
| \(H_{10}\) | 0.0280 |

### 6.4 Sorted table and pass/fail marks

Ordered list \(p_{(i)}\) (ties at \(0.0280\): \(H_3\) and \(H_{10}\); either
stable ordering is fine for rejection **sets**, which depend only on ranks
through \(k^\ast\)):

| \(i\) | Label | \(p_{(i)}\) | \(\tau_i^{\mathrm{BH}}\) | \(p_{(i)}\le\tau_i^{\mathrm{BH}}\)? | \(\tau_i^{\mathrm{BY}}\) | \(p_{(i)}\le\tau_i^{\mathrm{BY}}\)? |
|------:|-------|------------:|-------------------------:|:----------------------------------:|------------------------:|:---------------------------------:|
| 1 | \(H_2\) | 0.0008 | 0.005000 | **yes** | 0.00170709 | **yes** |
| 2 | \(H_9\) | 0.0030 | 0.010000 | **yes** | 0.00341417 | **yes** |
| 3 | \(H_5\) | 0.0050 | 0.015000 | **yes** | 0.00512126 | **yes** |
| 4 | \(H_7\) | 0.0100 | 0.020000 | **yes** | 0.00682834 | no |
| 5 | \(H_6\) | 0.0260 | 0.025000 | **no** (own thr. fails) | 0.00853543 | no |
| 6 | \(H_3\) | 0.0280 | 0.030000 | **yes** | 0.01024251 | no |
| 7 | \(H_{10}\) | 0.0280 | 0.035000 | **yes** | 0.01194960 | no |
| 8 | \(H_1\) | 0.0400 | 0.040000 | **yes** (equality) | 0.01365669 | no |
| 9 | \(H_8\) | 0.0450 | 0.045000 | **yes** (equality) | 0.01536377 | no |
| 10 | \(H_4\) | 0.0900 | 0.050000 | no | 0.01707086 | no |

### 6.5 Rejection sets

**BH at \(q=0.05\):**
\[
k^\ast_{\mathrm{BH}}
  \;=\;
  \max\{i: p_{(i)}\le \tau_i^{\mathrm{BH}}\}
  \;=\;
  9
\]
(because \(p_{(9)}=0.0450=\tau_9^{\mathrm{BH}}\) and \(p_{(10)}=0.0900>\tau_{10}^{\mathrm{BH}}\)).

\[
\text{Reject}_{\mathrm{BH}}
  \;=\;
  \{H_{(1)},\ldots,H_{(9)}\}
  \;=\;
  \{H_2,\, H_9,\, H_5,\, H_7,\, H_6,\, H_3,\, H_{10},\, H_1,\, H_8\}.
\]

Notes for the future test:

- Rank \(i=5\) (\(H_6\), \(p=0.0260>0.025\)) **fails its own** BH critical value
  but is still rejected because \(k^\ast=9\ge 5\) (step-up property).
- Ranks \(i=8\) and \(i=9\) sit on the boundary \(p_{(i)}=\tau_i^{\mathrm{BH}}\);
  the rule uses \(\le\), so both are inside the rejection set
  (Benjamini & Hochberg 1995, expression (1)).

**BY at \(q=0.05\):**
\[
k^\ast_{\mathrm{BY}}
  \;=\;
  \max\{i: p_{(i)}\le \tau_i^{\mathrm{BY}}\}
  \;=\;
  3
\]
(because \(p_{(3)}=0.0050\le 0.00512126\) and \(p_{(4)}=0.0100>0.00682834\)).

\[
\text{Reject}_{\mathrm{BY}}
  \;=\;
  \{H_{(1)},H_{(2)},H_{(3)}\}
  \;=\;
  \{H_2,\, H_9,\, H_5\}.
\]

**Summary contrast:** BH rejects 9 of 10 trials; BY rejects 3 of 10. What
equals \(c(10)\) **exactly** for every rank \(i\) is the critical-value ratio
\[
\frac{\tau_i^{\mathrm{BH}}}{\tau_i^{\mathrm{BY}}}
  \;=\;
  c(10)
  \;\approx\; 2.928968,
\]
not the rejection-count ratio \(9/3=3\). The coarser rejection set under BY is
the discrete consequence of those uniformly tighter thresholds, not a count
that itself equals \(c(10)\).

### 6.6 Machine-check summary (no code)

Same numbers as §6.3–6.5, restated for a future automated check:

| Quantity | Value |
|----------|-------|
| \(N\) | 10 |
| \(q\) | 0.05 |
| \(c(10)\) (float64 ascending sum) | 2.9289682539682538 |
| \(k^\ast_{\mathrm{BH}}\) | 9 |
| Reject under BH | \(H_2, H_9, H_5, H_7, H_6, H_3, H_{10}, H_1, H_8\) |
| \(k^\ast_{\mathrm{BY}}\) | 3 |
| Reject under BY | \(H_2, H_9, H_5\) |

Raw \(p\)-values by label: as in the table of §6.3.

---

## 7. Implementation pitfalls

### 7.1 Step-up, not step-down

BH/BY search for the **largest** \(k\) with \(p_{(k)}\le\tau_k\) and then reject
**all** \(i\le k\) (Benjamini & Hochberg 1995, expression (1); Benjamini &
Yekutieli 2001, Theorem 1.3 and “step-up” terminology p.1169;
Harvey–Liu–Zhu 2016, §3.4.3).

Common bugs:

- Stopping at the **first** failure when scanning from small \(i\) upward
  (that is closer to a misspecified step-down rule and can under-reject).
- Rejecting only those \(i\) with \(p_{(i)}\le\tau_i\) individually, **without**
  filling the initial segment up to \(k^\ast\) (breaks the proof; also disagrees
  with §6 where \(i=5\) is rejected under BH despite failing its own line).

Holm’s FWER procedure **is** step-down (Harvey–Liu–Zhu 2016, §3.4.2); do not
mix the control directions.

### 7.2 Adjusted \(p\)-values / \(q\)-values and monotonicity

Rejection decisions at a fixed \(q\) only need \(k^\ast\). If the API also returns
per-hypothesis adjusted \(p\)-values (BH or BY), they must be

1. computed from the **ordered** list with the backward recurrence in §2.4 / §3.2
   (Harvey–Liu–Zhu 2016, §3.4.3), and
2. **monotone non-decreasing** in the ordered index:  
   \(\tilde p_{(1)}\le\tilde p_{(2)}\le\cdots\le\tilde p_{(m)}\).

Omitting the \(\min(\tilde p_{(i+1)},\,\cdot\,)\) step yields non-monotone
“adjusted \(p\)-values” that can disagree with the \(k^\ast\) rejection set
(rejecting \(i\) but not \(j<i\)). Always enforce monotonicity when reporting
\(q\)-values.

Map adjusted values back to original trial IDs via the sort permutation; never
assume the ledger is pre-sorted.

### 7.3 Numerical care with tiny \(p\)-values

- Compare in \(p\)-space with \(\le\) as in the theorems; do not convert to
  \(\log p\) unless both sides of every inequality are transformed consistently.
- With \(0 < p_{(i)}\le 1\), products such as \((N/i)\,p_{(i)}\) or
  \((N\,c(N)/i)\,p_{(i)}\) do **not** overflow float64 for any realistic
  ledger size \(N\). The real tiny-\(p\) hazards are (i) **underflow** /
  subnormal loss of precision when \(p_{(i)}\) is near machine zero, and
  (ii) adjusted values that exceed 1 before clipping. Always clip adjusted
  \(p\)-values at 1 after the recurrence (Harvey–Liu–Zhu 2016, §3.4.1–3.4.3
  all use \(\min[\cdot,1]\) forms).
- Exact boundary cases (\(p_{(i)}=\tau_i\)) must count as pass under \(\le\)
  (see ranks 8–9 in §6).
- Prefer computing \(c(N)=\sum_{i=1}^{N}1/i\) in a numerically stable way
  (ascending sum is fine for moderate \(N\); for very large \(N\), a compensated
  sum or \(\log N+\gamma\) expansion with documented error bound).

### 7.4 Behaviour at \(N=1\)

- \(c(1)=\sum_{i=1}^{1}1/i=1\), so **BH and BY coincide** when there is a single
  trial: reject \(H_{(1)}\) iff \(p_{(1)}\le q\).
- The family-wise and false-discovery problems are vacuous for a singleton
  family in the multiplicity sense, but the same code path should still run
  (no division by zero: \(N\,c(N)=1\)).
- Empty ledger (\(N=0\)): define rejection set \(=\emptyset\), \(k^\ast=0\); do not
  evaluate \(c(0)\) or \(i/N\).

### 7.5 Other traps (short list)

- **Wrong \(N\):** using only “survivors” or only published factors as \(N\)
  understates multiplicity (Harvey–Liu–Zhu 2016, §3.7.2). Ledger count wins.
- **One-sided \(p\) after peeking at the sign:** anti-conservative inputs; FDR
  control then fails even if BHY is coded perfectly (§4.2).
- **IID SE on autocorrelated IC:** \(p\)-values too small (§4.3; Newey & West
  1987).
- **Confusing FDR level \(q\) with a per-test α:** BH critical values grow with
  \(i\); the last critical value equals \(q\), not \(q/N\).
- **Name collision “BHY”:** Harvey–Liu–Zhu use “BHY” for the **BY** harmonic
  procedure. In code and docs, prefer explicit `bh` vs `by` (or
  `fdr_bh` / `fdr_by`) and cite which theorem is claimed.

---

## Cross-walk: paper symbols → alpha-court

| Concept | BH 1995 | BY 2001 | HLZ 2016 | This note / court |
|---------|---------|---------|----------|-------------------|
| Family size | \(m\) | \(m\) | \(M\) | \(N\) |
| FDR level | \(q^\ast\) | level \(q\) | \(\alpha_d\) | \(q\) |
| Ordered \(p\) | \(P_{(i)}\) | \(P_{(i)}\) | \(p_{(k)}\) | \(p_{(i)}\) |
| Harmonic factor | — (\(c=1\)) | \(c(m)=\sum 1/i\) | \(c(M)=\sum 1/j\) | \(c(N)\) |
| Step-up index | largest \(i\) in (1) | largest \(i\) in Thm 1.3 | max \(k\) in §3.4.3 | \(k^\ast\) |

---

*End of literature note. Implementation should cite this file and the primary
papers in code comments next to each formula.*
