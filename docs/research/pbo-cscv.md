# PBO via CSCV — Implementation-Grade Literature Note

**Ticket:** v0.1-05  
**Scope:** Rewrite the Probability of Backtest Overfitting (PBO) estimator based on Combinatorially Symmetric Cross-Validation (CSCV) from the public literature, precise enough that later code can be checked line-by-line against this note and the cited paper.  
**Out of scope:** Any executable code; other kernel statistics (DSR, BHY); noise-control designs.

---

## 1. Sources

Primary source (algorithm, notation, and definitions used throughout this note):

1. **Bailey, D. H., Borwein, J. M., López de Prado, M., and Zhu, Q. J. (2017).**  
   “The Probability of Backtest Overfitting.”  
   *Journal of Computational Finance*, **20**(4), 39–69.  
   DOI: [10.21314/JCF.2016.322](https://doi.org/10.21314/JCF.2016.322).  
   SSRN preprint (first posted 2013; free PDF widely mirrored):  
   Bailey, D. H., Borwein, J. M., López de Prado, M., and Zhu, Q. J.,  
   “The Probability of Backtest Overfitting,” SSRN Working Paper, abstract id **2326253**,  
   <https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2326253>.  
   Author-hosted PDF (February 2015 revision used for section/equation numbers below):  
   <https://www.davidhbailey.com/dhbpapers/backtest-prob.pdf>.

   Equation and section numbers in this note follow the **February 2015 author PDF** (Algorithm 2.3, Definitions 2.1–2.2, Eq. (2.1)–(2.4), Sections 3–5). Journal pagination may differ; substance is the same.

Auxiliary sources actually used:

2. **Bailey, D. H., Borwein, J. M., López de Prado, M., and Zhu, Q. J. (2014).**  
   “Pseudo-Mathematics and Financial Charlatanism: The Effects of Backtest Overfitting on Out-of-Sample Performance.”  
   *Notices of the American Mathematical Society*, **61**(5), 458–471.  
   SSRN: abstract id 2308659.  
   *Use:* companion discussion of backtest overfitting and performance degradation; cited by [1] for related results. Not needed for the CSCV steps themselves.

3. **Bailey, D. H., Borwein, J. M., López de Prado, M., and Zhu, Q. J. (2015).**  
   Mathematical appendices to “The Probability of Backtest Overfitting.”  
   SSRN abstract id **2568435**.  
   *Use:* optional deeper mathematical material; core CSCV algorithm is self-contained in [1].

No proprietary sources were used. Text below is a fresh rewrite; formulas keep the paper’s notation and cite equation/section numbers.

---

## 2. The Input Matrix \(M\)

### 2.1 Shape and meaning

From Algorithm 2.3 (first step) of Bailey et al. [1]:

- Form a real matrix \(M\) of order \((T \times N)\).
- **Rows** \(t = 1,\ldots,T\): time-indexed observations of a *performance series* (period profits-and-losses / returns), aligned to a common calendar index.
- **Columns** \(n = 1,\ldots,N\): one column per **trial** (strategy configuration / model specification the researcher compared when selecting a “best” backtest).

So \(M_{t,n}\) is the period performance of trial \(n\) at time \(t\).

### 2.2 Hard requirements on \(M\)

Algorithm 2.3 imposes exactly two conditions [1, Alg. 2.3, items (i)–(ii)]:

1. **True matrix / equal length / synchronous rows.**  
   Every column has the same number of rows \(T\). Observation \(t\) is contemporaneous across all \(N\) trials (same timestamp index).  
   If configurations trade at different frequencies, aggregate them onto a common index \(t = 1,\ldots,T\) before building \(M\).

2. **Metric estimable on subsamples.**  
   The performance evaluation metric \(R\) used to pick the IS-optimal trial must be computable on *any* contiguous recombination of row-blocks (the IS and OOS halves formed below), not only on the full sample.

### 2.3 Performance metric \(R\) (default Sharpe; pluggable)

- The paper’s running example is the **Sharpe ratio** of a trial’s period returns on the relevant IS or OOS half [1, §2.1–2.2, Alg. 2.3(c)–(d)].
- The procedure is **metric-agnostic**: any scalar performance statistic \(R\) that can be estimated on a column subsample is admissible (Sortino, Jensen’s alpha, probabilistic Sharpe ratio, etc.) [1, §3.2].
- For a fixed combination \(c\), write:
  - \(R^c = (R^c_1,\ldots,R^c_N)\): IS performance of the \(N\) trials on the training half;
  - \(\bar{R}^c = (\bar{R}^c_1,\ldots,\bar{R}^c_N)\): OOS performance on the testing half.

Implementation note for v0.1 (not a paper claim): when code is written, document the exact Sharpe definition used (excess returns or not; sample vs population volatility; annualization factor). The algorithm only requires a total order on trials induced by \(R\).

### 2.4 Ranking convention (paper’s own)

[1, §2.1] maps performances to ranks in \(\{1,\ldots,N\}\) with **higher rank = better performance**, so the IS-best trial has rank \(N\).

Example from the paper: for \(N=3\), \(R^c = (0.5, 1.1, 0.7)\) yields ranks \(r^c = (1, 3, 2)\); for \(\bar{R}^c = (0.6, 0.7, 1.3)\) yields \(\bar{r}^c = (1, 2, 3)\).

Define \(\Omega_n^\* = \{ f \in \Omega : f_n = N \}\) — the set of ranking vectors in which trial \(n\) is best [1, §2.1].

---

## 3. The CSCV Algorithm (Step by Step)

### 3.1 Conceptual definition of PBO (before the estimator)

**Definition 2.1 (Backtest overfitting)** [1, Def. 2.1, Eq. (2.1)]:  
The strategy-selection process overfits if a strategy that is optimal IS has **expected OOS ranking below the median** of the \(N\) trials (paper’s prose; see threshold caveats under Def. 2.2 and §3.5).

**Definition 2.2 (PBO)** [1, Def. 2.2, Eq. (2.2)]:  
\[
\mathrm{PBO}
=
\sum_{n=1}^{N}
\mathrm{Prob}\!\left[\bar{r}_n < N/2 \;\middle|\; r \in \Omega_n^\*\right]
\mathrm{Prob}\!\left[r \in \Omega_n^\*\right].
\]
In words: probability that the IS-selected trial’s OOS rank falls **strictly below the threshold \(N/2\)** printed in Eq. (2.2).  
(Do **not** equate that printed threshold with “the median of ranks \(\{1,\ldots,N\}\)”: the midpoint of that set is \((N+1)/2\). The paper’s own prose says “median,” but Eq. (2.2) literally writes \(\bar{r}_n < N/2\). These agree for some \(N\) and diverge for others; §3.5 records the mismatch with the CSCV logit estimator.)

CSCV is the sampling scheme that estimates this probability from a single realized matrix \(M\) [1, §2.2].

### 3.2 Partition into \(S\) equal blocks

[1, Alg. 2.3, second step]

1. Choose an **even** integer \(S \ge 2\) (evenness is required so IS and OOS each get \(S/2\) blocks of equal total length \(T/2\)).
2. Require \(T\) divisible by \(S\), so each block has integer length \(T/S\).
3. Partition **rows** of \(M\) into \(S\) disjoint submatrices \(M_s\), \(s = 1,\ldots,S\), each of order \((T/S) \times N\), **preserving time order** (no random reshuffle of rows inside the partition step).  
   Contiguous blocks \(M_1,\ldots,M_S\) are the natural choice and preserve seasonal structure when \(S\) is not too large [1, §4].

**Paper’s recommendation on \(S\)** [1, §4]:

- \(S\) must be large enough that \(\binom{S}{S/2}\) logits give a stable estimate of the left-tail mass of \(f(\lambda)\).
- \(S\) must not be so large that seasonal / serial structure is shattered across tiny partitions.
- **\(S = 16\)** is presented as a practical default: for ~4 years of daily data it yields quarterly-sized blocks and \(\binom{16}{8} = 12{,}870\) logits (paper text prints “12,780” — see §4; the binomial coefficient is \(12{,}870\)).
- Also discussed: \(S=12\) (924 logits), \(S=24\) (\(\approx 2.7\times 10^6\) logits).

### 3.3 All symmetric combinations

[1, Alg. 2.3, third step; Eq. (2.3)]

Let \(\mathcal{C}_S\) be the set of all combinations of the \(S\) blocks taken \(S/2\) at a time:
\[
\#(\mathcal{C}_S)
=
\binom{S}{S/2}
=
\prod_{i=0}^{S/2-1}
\frac{S-i}{S/2-i}.
\]
Each combination \(c \in \mathcal{C}_S\) designates which \(S/2\) blocks form the **training / IS** half; the complementary \(S/2\) blocks form the **testing / OOS** half.

Because halves are equal-sized, every training combination is later reused as a testing set (and vice versa) — the “symmetric” property [1, §4].

### 3.4 Per-combination ranking, relative rank, and logit

[1, Alg. 2.3, fourth step, (a)–(g)]

For each \(c \in \mathcal{C}_S\):

**(a) Training matrix \(J\)**  
Concatenate the \(S/2\) blocks in \(c\) **in their original time order**.  
Shape: \(T/2 \times N\).

**(b) Testing matrix \(\bar{J}\)**  
Concatenate the complementary blocks, also in original order.  
Shape: \(T/2 \times N\).  
(Order matters for path-dependent metrics such as maximum drawdown; it does not matter for Sharpe or plain mean return [1, Alg. 2.3(b)].)

**(c) IS performances and ranks**  
Compute \(R^c_n = R(\text{column } n \text{ of } J)\) for each \(n\) (training / IS half).  
Let \(r^c\) be the rank vector of \(R^c\) under the convention of §2.4 (rank \(N\) = best).

**Paper typo (Alg. 2.3 step (c)):** the February 2015 PDF literally says the \(n\)th component of \(R^c\) reports “the performance associated with the \(n\)th column of \(J\) **(the testing set)**,” yet step (a) has just defined \(J\) as the **training** set, and the same sentence labels \(r^c\) the **IS** ranking. Step (d) then “repeat[s] (c) with \(J\) replaced by \(\bar{J}\) (the test set)” for OOS. The only consistent reading is that step (c) is IS on training \(J\), and the parenthetical “testing set” is a slip (train/test labels swapped in that one phrase). This note follows that corrected intent — same class of erratum as the printed \(\binom{16}{8}=12{,}780\) figure in §4. A line-by-line checker who takes step (c)’s “testing set” literally will incorrectly swap IS and OOS relative to steps (a)–(b) and (d).

**(d) OOS performances and ranks**  
Likewise \(\bar{R}^c\) and \(\bar{r}^c\) on \(\bar{J}\).

**(e) IS-best index \(n^\*\)**  
Choose \(n^\*\) such that \(r^c_{n^\*} = N\), i.e. \(r^c \in \Omega_{n^\*}^\*\) [1, Alg. 2.3(e)].  
(If several trials tie for best IS, the paper’s exposition assumes a unique maximizer; see tie conventions in §3.6.)

**(f) Relative OOS rank**
\[
\bar{\omega}_c
:=
\frac{\bar{r}^c_{n^\*}}{N+1}
\in (0,1).
\]
[1, Alg. 2.3(f)]. Dividing by \(N+1\) (not \(N\)) keeps \(\bar{\omega}_c\) strictly inside \((0,1)\) so the logit is always defined for finite ranks in \(\{1,\ldots,N\}\).

**(g) Logit**
\[
\lambda_c
=
\ln\!\left(
\frac{\bar{\omega}_c}{1-\bar{\omega}_c}
\right).
\]
[1, Alg. 2.3(g)].  
High \(\lambda_c\) means the IS-best trial also ranks well OOS (consistency → low overfitting signal).  
Algebraically, \(\lambda_c < 0\) iff \(\bar{\omega}_c < 1/2\) iff \(\bar{r}^c_{n^\*} < (N+1)/2\).  
That \((N+1)/2\) threshold is the natural midpoint of ranks \(\{1,\ldots,N\}\) implied by the \(N+1\) denominator in Alg. 2.3(f); it is **not** identical to the literal \(\bar{r}_n < N/2\) printed in Eq. (2.2) — see §3.5.

### 3.5 Aggregate to PBO

[1, Alg. 2.3, fifth step; Eq. (2.4); §3.1]

Collect all logits \(\{\lambda_c : c \in \mathcal{C}_S\}\). Define the empirical distribution
\[
f(\lambda)
=
\sum_{c \in \mathcal{C}_S}
\frac{\chi_{\{\lambda\}}(\lambda_c)}{\#(\mathcal{C}_S)},
\]
where \(\chi\) is the indicator (characterization) function [1, Eq. (2.4)].

**CSCV estimator of PBO** [1, §3.1]:
\[
\phi
=
\int_{-\infty}^{0} f(\lambda)\,d\lambda
=
\frac{
\#\{\, c \in \mathcal{C}_S : \lambda_c < 0 \,\}
}{
\binom{S}{S/2}
}.
\]
Equivalently: the fraction of combinations in which \(\bar{\omega}_c < 1/2\) (IS-best trial’s OOS relative rank below one half).  
Interpretation [1, §3.1]: \(\phi \approx 0\) → IS selection systematically places the chosen trial in the upper half of OOS ranks; \(\phi \approx 1\) → high estimated probability of backtest overfitting. The paper mentions a customary reject region \(\phi > 0.05\) in a Neyman–Pearson style rule of thumb (application choice, not a theorem).

**Operational rule for \(\phi\):** count combinations with **`\(\lambda_c < 0\)` only** (do not count \(\lambda_c = 0\) as overfitting events). This is the discrete realization of \(\phi = \int_{-\infty}^{0} f(\lambda)\,d\lambda\) in [1, §3.1]: mass **strictly below** zero. When \(\bar{\omega}_c = 1/2\) exactly, \(\lambda_c = 0\) and the combination does **not** contribute to \(\phi\).

**Paper-internal threshold mismatch (\(N/2\) vs \((N+1)/2\)):**  
Do **not** claim that this \(\lambda_c < 0\) rule is identical to a literal reading of Eq. (2.2). From Alg. 2.3(f)–(g),
\[
\lambda_c < 0
\;\Longleftrightarrow\;
\bar{\omega}_c < \tfrac12
\;\Longleftrightarrow\;
\bar{r}^c_{n^\*} < \tfrac{N+1}{2},
\]
whereas Eq. (2.2) prints the event \(\bar{r}_n < N/2\). The true midpoint of the discrete rank set \(\{1,\ldots,N\}\) is \((N+1)/2\) — the value implied by dividing by \(N+1\) in Alg. 2.3(f) — so the logit estimator is coherent with that midpoint. The printed \(N/2\) in Eq. (2.2) is a separate, slightly different threshold.

They diverge for **even** \(N\) at \(\bar{r}_{n^\*} = N/2\). Example: \(N=4\), \(\bar{r}_{n^\*}=2\):
- \(\bar{\omega}_c = 2/5\), \(\lambda_c = \ln(2/3) < 0\) → **counts** toward \(\phi\) under the operational \(\lambda_c < 0\) rule;
- literal Eq. (2.2): \(2 < 4/2 = 2\) is **false** → would **not** count.

For odd \(N\) with integer ranks the two strict inequalities can agree on the integer lattice (e.g. \(N=3\): \(\bar{r} < 2\) vs \(\bar{r} < 2\)), but implementers must still treat them as distinct paper statements. **v0.1 ground truth for code:** implement \(\phi\) via \(\lambda_c < 0\) (equivalently \(\bar{r}_{n^\*} < (N+1)/2\)), not via a separate \(\bar{r}_{n^\*} < N/2\) check.

### 3.6 Tie-handling and rank-normalization conventions

What the paper states explicitly:

| Item | Convention in [1] |
|------|-------------------|
| Rank direction | Larger rank = better; best gets \(N\) [§2.1] |
| Relative rank | \(\bar{\omega}_c = \bar{r}^c_{n^\*}/(N+1)\) [Alg. 2.3(f)] |
| Logit | \(\lambda_c = \ln(\bar{\omega}_c/(1-\bar{\omega}_c))\) [Alg. 2.3(g)] |
| PBO estimator \(\phi\) | Left-tail mass \(\int_{-\infty}^{0} f(\lambda)\,d\lambda\) [§3.1]; operational rule: strict \(\lambda_c < 0\) (i.e. \(\bar{r}_{n^\*} < (N+1)/2\)). Not identical to literal Eq. (2.2)’s \(\bar{r}_n < N/2\) — see §3.5 |

What the paper does **not** fully specify (implementer must document a choice):

1. **Ties in \(R\) (identical IS or OOS metrics across trials).**  
   The worked example assumes distinct performances. Reasonable, documented defaults for v0.1:
   - Prefer **average ranks** (midranks) for tied metric values so \(\sum_n r_n = N(N+1)/2\) still holds.
   - For selecting \(n^\*\) when several trials share the maximum IS metric: pick a **deterministic** rule (e.g. smallest column index). Average ranks alone may leave no trial with rank exactly \(N\) when the top is tied; then define \(n^\* = \arg\max_n R^c_n\) with the index tie-break, and use that trial’s (possibly mid-) OOS rank in \(\bar{\omega}_c\).

2. **NaN / infinite metric values.**  
   Not discussed in Alg. 2.3. Fail fast or drop the combination after documenting the rule (§6).

3. **\(T \bmod S \neq 0\).**  
   Paper assumes equal-size blocks of order \(T/S \times N\). Require divisibility or truncate/pad with an explicit policy before partitioning.

### 3.7 Pseudocode

```
CSCV_PBO(M, S, metric R):
    # M: T x N performance matrix (rows time, columns trials)
    # S: even integer, T divisible by S
    # R: performance metric (default: Sharpe on a column subsample)

    require S even and S >= 2
    require T % S == 0
    block_len <- T / S
    blocks[1..S] <- row-partition of M into S contiguous slices of block_len rows

    logits <- empty list
    for each combination c of {1..S} choose S/2 indices:
        J    <- vertical concat of blocks[i] for i in c, original order
        Jbar <- vertical concat of blocks[j] for j not in c, original order

        # Step (c): IS metrics on training J.
        # Paper PDF mislabels J as "the testing set" in (c); J is training (step a).
        R_is[n]  <- R(J[:, n])      for n = 1..N
        # Step (d): OOS metrics on testing Jbar
        R_oos[n] <- R(Jbar[:, n])  for n = 1..N

        r_is  <- ranks(R_is)    # 1 = worst, N = best; document ties
        r_oos <- ranks(R_oos)

        n_star <- argmax(R_is)  # IS-best; document index ties
        # equivalently: n_star such that r_is[n_star] is maximal

        omega_bar <- r_oos[n_star] / (N + 1)     # Alg. 2.3(f)
        lambda_c  <- ln( omega_bar / (1 - omega_bar) )  # Alg. 2.3(g)
        append lambda_c to logits

    # φ = ∫_{-∞}^0 f(λ) dλ → count strict λ < 0 only (§3.5); not literal Eq. (2.2) N/2
    phi <- (number of lambda in logits with lambda < 0) / len(logits)  # §3.1
    return phi, logits
```

Citations: partition and combinations [1, Alg. 2.3 steps 2–3, Eq. (2.3)]; per-combination steps [1, Alg. 2.3(a)–(g)] with step-(c) label correction noted in §3.4; \(\phi\) [1, §3.1, Eq. (2.4)].

---

## 4. Complexity Note

### 4.1 Combination counts

Number of logits = \(\binom{S}{S/2}\):

| \(S\) | \(\binom{S}{S/2}\) | Remark |
|------:|-------------------:|--------|
| 2 | 2 | Minimal toy |
| 4 | 6 | Hand test in §5 |
| 8 | 70 | Small |
| 10 | 252 | |
| 12 | 924 | Cited in [1, §4] |
| 16 | **12,870** | Default in [1, §4]; paper body prints “12,780” (typographical inconsistency with \(\binom{16}{8}\)) |
| 18 | 48,620 | |
| 20 | 184,756 | |
| 24 | 2,704,156 | Cited in [1, §4] |

Each combination requires two metric evaluations per trial (IS + OOS), i.e. \(O(N)\) metric calls, each typically \(O(T)\) for Sharpe/mean on a half-sample of length \(T/2\).

### 4.2 Time and memory

- **Time:** \(\Theta\bigl(\binom{S}{S/2} \cdot N \cdot \mathrm{cost}(R, T/2)\bigr)\).  
  For Sharpe on dense arrays, roughly \(\Theta\bigl(\binom{S}{S/2} \cdot N \cdot T\bigr)\).  
  At \(S=16\), \(N \sim 10^2\)–\(10^3\), \(T \sim 10^3\), this is routinely feasible on a laptop; at \(S=24\) the binomial coefficient jumps by \(\sim 200\times\).

- **Memory:**  
  - Store \(M\) once: \(O(TN)\).  
  - Prefer **index masks / block views** over materializing every \(J,\bar{J}\).  
  - Storing all logits: \(O\bigl(\binom{S}{S/2}\bigr)\) floats (≈100 KiB at \(S=16\); ≈20 MiB at \(S=24\)).  
  - Optional: stream logits and only accumulate the counter for \(\lambda_c < 0\) if the full histogram is not needed.

### 4.3 Resolution vs cost trade-off for \(S\)

[1, §4]:

- Larger \(S\) → more logits → finer estimate of \(f(\lambda)\) and smaller Monte-Carlo-style error on the proportion \(\phi\) (paper invokes \(\sigma[\hat{p}] = \sqrt{p(1-p)/N_{\mathrm{logits}}}\)).
- Larger \(S\) → shorter blocks \(T/S\) → seasonal patterns may be split; each block carries less information.
- Smaller \(S\) → cheap, but a coarse left tail (unstable \(\phi\) near 0 or 1).
- Practical default: **\(S=16\)** balances quarterly structure on multi-year daily series against \(\sim 1.3\times 10^4\) logits [1, §4].

Also: \(N\) must be large enough that \(\bar{\omega}_c = k/(N+1)\) is not too discrete; the paper suggests \(N \gg 10\) if one cares about \(\phi\) distinctions finer than \(0.1\) [1, §4].

---

## 5. Test Vector (Hand-Worked, \(S=4\), \(N=3\), \(T=8\))

This section is a fully recomputable fixture for a future unit test. No floating-point Sharpe is used: the **performance metric \(R\) is the arithmetic mean of period returns** on the relevant half-sample (allowed by metric pluggability [1, §3.2]). Ranks use the paper’s convention (higher = better). There are **no metric ties** in any split.

### 5.1 Matrix \(M\) (\(T=8\), \(N=3\))

| \(t\) | Trial 1 | Trial 2 | Trial 3 |
|------:|--------:|--------:|--------:|
| 1 | 3 | 0 | 4 |
| 2 | 3 | 2 | 1 |
| 3 | 3 | 4 | 6 |
| 4 | 3 | 1 | 5 |
| 5 | 4 | 4 | 0 |
| 6 | 2 | 5 | 5 |
| 7 | 3 | 5 | 5 |
| 8 | 2 | 6 | 2 |

### 5.2 Blocks (\(S=4\), block length \(T/S=2\))

| Block | Rows | Submatrix (rows × trials) |
|:-----:|-----:|---------------------------|
| \(A\) | 1–2 | \(\begin{bmatrix}3&0&4\\3&2&1\end{bmatrix}\) |
| \(B\) | 3–4 | \(\begin{bmatrix}3&4&6\\3&1&5\end{bmatrix}\) |
| \(C\) | 5–6 | \(\begin{bmatrix}4&4&0\\2&5&5\end{bmatrix}\) |
| \(D\) | 7–8 | \(\begin{bmatrix}3&5&5\\2&6&2\end{bmatrix}\) |

Number of combinations: \(\binom{4}{2} = 6\) [1, Eq. (2.3)].

### 5.3 All six combinations

Notation: means written as fractions; ranks as \((r_1,r_2,r_3)\); \(n^\*\) is 1-based trial index;  
\(\bar{\omega}_c = \bar{r}_{n^\*}/4\); \(\lambda_c = \ln(\bar{\omega}_c/(1-\bar{\omega}_c))\).

---

#### Combination 1 — IS = \(\{A,B\}\), OOS = \(\{C,D\}\)

IS rows \(1\)–\(4\):

| Trial | IS returns | Mean \(R\) |
|------:|------------|----------:|
| 1 | 3,3,3,3 | \(3\) |
| 2 | 0,2,4,1 | \(7/4 = 1.75\) |
| 3 | 4,1,6,5 | \(4\) |

IS ranks: \((2, 1, 3)\) → \(n^\* = 3\).

OOS rows \(5\)–\(8\):

| Trial | OOS returns | Mean \(\bar{R}\) |
|------:|-------------|-----------------:|
| 1 | 4,2,3,2 | \(11/4 = 2.75\) |
| 2 | 4,5,5,6 | \(5\) |
| 3 | 0,5,5,2 | \(3\) |

OOS ranks: \((1, 3, 2)\).  
\(\bar{r}_{n^\*} = \bar{r}_3 = 2\), \(\bar{\omega}_c = 2/4 = 1/2\), \(\lambda_c = \ln 1 = 0\).

---

#### Combination 2 — IS = \(\{A,C\}\), OOS = \(\{B,D\}\)

IS rows \(1,2,5,6\):

| Trial | Mean \(R\) |
|------:|----------:|
| 1 | \(3\) |
| 2 | \(11/4 = 2.75\) |
| 3 | \(5/2 = 2.5\) |

IS ranks: \((3, 2, 1)\) → \(n^\* = 1\).

OOS rows \(3,4,7,8\):

| Trial | Mean \(\bar{R}\) |
|------:|-----------------:|
| 1 | \(11/4 = 2.75\) |
| 2 | \(4\) |
| 3 | \(9/2 = 4.5\) |

OOS ranks: \((1, 2, 3)\).  
\(\bar{r}_{n^\*} = \bar{r}_1 = 1\), \(\bar{\omega}_c = 1/4\), \(\lambda_c = \ln\!\bigl((1/4)/(3/4)\bigr) = \ln(1/3)\).

---

#### Combination 3 — IS = \(\{A,D\}\), OOS = \(\{B,C\}\)

IS rows \(1,2,7,8\):

| Trial | Mean \(R\) |
|------:|----------:|
| 1 | \(11/4 = 2.75\) |
| 2 | \(13/4 = 3.25\) |
| 3 | \(3\) |

IS ranks: \((1, 3, 2)\) → \(n^\* = 2\).

OOS rows \(3\)–\(6\):

| Trial | Mean \(\bar{R}\) |
|------:|-----------------:|
| 1 | \(3\) |
| 2 | \(7/2 = 3.5\) |
| 3 | \(4\) |

OOS ranks: \((1, 2, 3)\).  
\(\bar{r}_{n^\*} = \bar{r}_2 = 2\), \(\bar{\omega}_c = 1/2\), \(\lambda_c = 0\).

---

#### Combination 4 — IS = \(\{B,C\}\), OOS = \(\{A,D\}\)

IS rows \(3\)–\(6\):

| Trial | Mean \(R\) |
|------:|----------:|
| 1 | \(3\) |
| 2 | \(7/2 = 3.5\) |
| 3 | \(4\) |

IS ranks: \((1, 2, 3)\) → \(n^\* = 3\).

OOS rows \(1,2,7,8\):

| Trial | Mean \(\bar{R}\) |
|------:|-----------------:|
| 1 | \(11/4 = 2.75\) |
| 2 | \(13/4 = 3.25\) |
| 3 | \(3\) |

OOS ranks: \((1, 3, 2)\).  
\(\bar{r}_{n^\*} = \bar{r}_3 = 2\), \(\bar{\omega}_c = 1/2\), \(\lambda_c = 0\).

---

#### Combination 5 — IS = \(\{B,D\}\), OOS = \(\{A,C\}\)

IS rows \(3,4,7,8\):

| Trial | Mean \(R\) |
|------:|----------:|
| 1 | \(11/4 = 2.75\) |
| 2 | \(4\) |
| 3 | \(9/2 = 4.5\) |

IS ranks: \((1, 2, 3)\) → \(n^\* = 3\).

OOS rows \(1,2,5,6\):

| Trial | Mean \(\bar{R}\) |
|------:|-----------------:|
| 1 | \(3\) |
| 2 | \(11/4 = 2.75\) |
| 3 | \(5/2 = 2.5\) |

OOS ranks: \((3, 2, 1)\).  
\(\bar{r}_{n^\*} = \bar{r}_3 = 1\), \(\bar{\omega}_c = 1/4\), \(\lambda_c = \ln(1/3)\).

---

#### Combination 6 — IS = \(\{C,D\}\), OOS = \(\{A,B\}\)

IS rows \(5\)–\(8\):

| Trial | Mean \(R\) |
|------:|----------:|
| 1 | \(11/4 = 2.75\) |
| 2 | \(5\) |
| 3 | \(3\) |

IS ranks: \((1, 3, 2)\) → \(n^\* = 2\).

OOS rows \(1\)–\(4\):

| Trial | Mean \(\bar{R}\) |
|------:|-----------------:|
| 1 | \(3\) |
| 2 | \(7/4 = 1.75\) |
| 3 | \(4\) |

OOS ranks: \((2, 1, 3)\).  
\(\bar{r}_{n^\*} = \bar{r}_2 = 1\), \(\bar{\omega}_c = 1/4\), \(\lambda_c = \ln(1/3)\).

---

### 5.4 Summary table and final PBO

| # | IS blocks | OOS blocks | \(n^\*\) | \(\bar{r}_{n^\*}\) | \(\bar{\omega}_c\) | \(\lambda_c\) | \(\lambda_c < 0\)? |
|--:|:---------:|:----------:|--------:|------------------:|------------------:|-------------:|:-----------------:|
| 1 | AB | CD | 3 | 2 | \(1/2\) | \(0\) | no |
| 2 | AC | BD | 1 | 1 | \(1/4\) | \(\ln(1/3)\) | **yes** |
| 3 | AD | BC | 2 | 2 | \(1/2\) | \(0\) | no |
| 4 | BC | AD | 3 | 2 | \(1/2\) | \(0\) | no |
| 5 | BD | AC | 3 | 1 | \(1/4\) | \(\ln(1/3)\) | **yes** |
| 6 | CD | AB | 2 | 1 | \(1/4\) | \(\ln(1/3)\) | **yes** |

Numeric check: \(\ln(1/3) \approx -1.0986122886681098\).

\[
\phi
=
\frac{3}{6}
=
\frac{1}{2}.
\]

**Expected pytest targets:** six logits \(\{0, \ln(1/3), 0, 0, \ln(1/3), \ln(1/3)\}\) (order as combinations above), \(\mathrm{PBO} = 0.5\).

---

## 6. Implementation Pitfalls

### 6.1 Unequal-length series

[1, Alg. 2.3(i)] requires a true \(T \times N\) matrix with synchronous rows.  
Do **not** silently align with outer joins that inject missing values, or compare trials on different effective sample sizes without aggregation to a common index.  
If live systems produce ragged histories, resample/aggregate first; reject the run if lengths still differ.

### 6.2 Sensitivity to \(S\)

[1, §4]: too small \(S\) under-samples the left tail of \(f(\lambda)\); too large \(S\) breaks seasonality and inflates combination cost.  
Report \(S\), \(\binom{S}{S/2}\), and (if affordable) a small sensitivity table \(\phi(S)\) for \(S \in \{8,12,16\}\).  
Changing \(S\) changes the estimator; it is not a free “tuning knob” to push \(\phi\) under 0.05.

### 6.3 NaN and non-finite metrics

Paper assumes finite performance statistics on every half-sample. Degenerate Sharpe cases (zero variance on a half) yield \(\mathrm{NaN}\) or \(\pm\infty\).  
v0.1 policy (implementation choice): treat non-finite \(R_n\) as **worst** rank (or fail the combination / fail the run — pick one and document). Never drop columns only on some combinations (that reintroduces selection bias).

### 6.4 Degenerate cases

| Case | Behavior |
|------|----------|
| \(N=1\) | Single trial always rank \(1\); \(\bar{\omega}_c = 1/2\); \(\lambda_c = 0\) always; \(\phi = 0\). PBO is vacuous: there is no selection among alternatives [cf. Def. 2.2]. Reject or special-case. |
| All trials identical on every half | All ranks tied; \(\bar{\omega}_c\) depends on midrank policy; \(\phi\) often near \(1/2\). High PBO among “equally skillful” strategies is discussed in [1, §5.2]. |
| \(N=2\), no ties | OOS ranks only \(\{1,2\}\); \(\bar{\omega}_c \in \{1/3, 2/3\}\); \(\lambda_c \in \{\ln(1/2), \ln 2\}\); coarse \(f(\lambda)\). |
| \(T < 2S\) or \(T \bmod S \neq 0\) | Cannot form equal blocks of length \(\ge 1\); reject inputs. |
| \(S\) odd | Symmetric equal IS/OOS split undefined in Alg. 2.3; reject. |

### 6.5 File-drawer / incomplete trial set

[1, §5.2]: hiding failed trials **underestimates** PBO (relative ranks of the published winner are biased upward OOS). Adding intentionally doomed trials to make one configuration look unique also biases \(\phi\).  
For guided/sequential optimizers, columns of \(M\) should be **final** outcomes of each search path, not intermediate iterates [1, §5.2, footnote].

### 6.6 PBO vs other overfit diagnostics in the paper — v0.1 scope

Section 3 of [1] lists **four** complementary analyses:

1. **PBO (\(\phi\))** — probability IS-best has \(\lambda_c < 0\) (OOS rank below \((N+1)/2\) under Alg. 2.3). **→ implement in v0.1.**
2. **Performance degradation** — scatter / regression of \((R_{n^\*}, \bar{R}_{n^\*})\) across \(c \in \mathcal{C}_S\); often negative slope [1, §3.2].
3. **Probability of loss** — \(\mathrm{Prob}[\bar{R}_{n^\*} < 0]\) [1, §3.2].
4. **Stochastic dominance** — whether OOS distribution of selected trials dominates the pooled OOS distribution of all trials [1, §3].

**v0.1 implements (1) only.**  
Diagnostics (2)–(4) share the same CSCV loop and can be added later without changing the definition of \(\phi\).  
Do not conflate “OOS mean is negative” with “PBO is high”: [1, Fig. 2 caption] notes that \(\phi \approx 0\) can coexist with high OOS loss probability when the whole set of strategies is weak for reasons other than selection overfitting.

### 6.7 Misuse: optimizing PBO

[1, §5.2]: CSCV must evaluate a selection process, **not** become the objective of that process (“when a measure becomes a target…”). PBO is a post-selection reliability score, not a hyperparameter to minimize while searching strategies.

### 6.8 Structural breaks outside the sample

[1, §5.2]: CSCV only sees breaks present inside the \(T\) rows of \(M\). Regime shifts outside the sample are invisible to \(\phi\).

---

## Appendix A — Quick reference (paper map)

| Concept | Paper locus |
|---------|-------------|
| Overfitting definition | Def. 2.1, Eq. (2.1) |
| PBO definition | Def. 2.2, Eq. (2.2) |
| CSCV algorithm | Alg. 2.3 |
| Combination count | Eq. (2.3) |
| Logit distribution | Eq. (2.4) |
| \(\phi = \int_{-\infty}^{0} f(\lambda)\,d\lambda\) | §3.1 |
| Other diagnostics | §3.2–3.3 |
| Choice of \(S\), \(N\), features of CSCV | §4 |
| Limitations | §5 |

---

## Appendix B — Notation cheat sheet

| Symbol | Meaning |
|--------|---------|
| \(M\) | \(T \times N\) performance matrix |
| \(T\) | Number of time observations |
| \(N\) | Number of trials / configurations |
| \(S\) | Even number of row-blocks |
| \(M_s\) | Block \(s\), shape \((T/S)\times N\) |
| \(\mathcal{C}_S\) | All combinations of \(S/2\) blocks |
| \(J, \bar{J}\) | IS / OOS halves for combination \(c\) |
| \(R^c, \bar{R}^c\) | IS / OOS metric vectors |
| \(r^c, \bar{r}^c\) | IS / OOS rank vectors (best = \(N\)) |
| \(n^\*\) | IS-optimal trial index |
| \(\bar{\omega}_c\) | \(\bar{r}^c_{n^\*}/(N+1)\) |
| \(\lambda_c\) | \(\ln(\bar{\omega}_c/(1-\bar{\omega}_c))\) |
| \(f(\lambda)\) | Empirical density of logits |
| \(\phi\) | CSCV estimate of PBO |

---

*End of literature note. No code beyond the required pseudocode and the hand arithmetic in §5.*
