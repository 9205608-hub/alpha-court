# Deflated Sharpe Ratio (DSR) — Implementation-Grade Literature Note

**Ticket:** v0.1-04  
**Scope:** Formulas, citations, code-mapping plan, hand-worked test vectors, and implementation pitfalls for the Deflated Sharpe Ratio. **No code** in this document.  
**Purpose:** Enable a later implementer and reviewer to put the public papers and the kernel code side by side and check them line by line.

---

## 1. Sources

### Primary

1. **Bailey, D. H. & López de Prado, M. (2014).**  
   “The Deflated Sharpe Ratio: Correcting for Selection Bias, Backtest Overfitting and Non-Normality.”  
   *Journal of Portfolio Management*, 40(5), 94–107.  
   SSRN preprint: https://ssrn.com/abstract=2460551  
   Author PDF: https://www.davidhbailey.com/dhbpapers/deflated-sharpe.pdf  
   **Role in this note:** Expected maximum Sharpe ratio under multiple trials (Eq. 1; App. A.1 Eqs. 5–6); Deflated Sharpe Ratio as PSR at that threshold (Eq. 2); independent-trial count (App. A.3 Eqs. 7–9); numerical example (Section “A Numerical Example”).

2. **Bailey, D. H. & López de Prado, M. (2012).**  
   “The Sharpe Ratio Efficient Frontier.”  
   *Journal of Risk*, 15(2), 3–44.  
   SSRN preprint: https://ssrn.com/abstract=1821643  
   Author PDF: https://www.davidhbailey.com/dhbpapers/sharpe-frontier.pdf  
   **Role in this note:** Probabilistic Sharpe Ratio (PSR) (Eq. 11); sampling distribution of the Sharpe-ratio estimator under non-Normal returns (Eq. 8); standard-error estimate with Bessel correction (Section 2.5); Normal IID special case (Eq. 4).

### Auxiliary (cited in the primaries; used for variance of the SR estimator)

3. **Lo, A. W. (2002).**  
   “The Statistics of Sharpe Ratios.”  
   *Financial Analysts Journal*, 58(4), 36–52.  
   **Role:** Variance of the Sharpe-ratio estimator under Normal IID returns (the \(1 + \tfrac{1}{2}\mathrm{SR}^{2}\) term).

4. **Mertens, E. (2002).**  
   “Variance of the IID Estimator in Lo (2002).”  
   Working paper, University of Basel.  
   **Role:** Extension of Lo’s variance to non-Normal IID returns (skewness and kurtosis terms). Bailey & López de Prado (2012) note that Opdyke (2007) showed Mertens (2002) and Christie (2005) coincide, and that the result extends to stationary ergodic returns.

5. **Opdyke, J. D. (2007).**  
   “Comparing Sharpe Ratios: So Where Are the \(p\)-Values?”  
   *Journal of Asset Management*, 8(5), 308–336.  
   **Role:** Confirms Mertens’ variance formula under stationary/ergodic (not only IID) returns.

Notation in this note follows the **papers’ own symbols first**, then maps to intended Python names in Section 3.

---

## 2. Formulas

All displayed formulas carry a bracketed citation with equation number (or section when the paper’s display is unnumbered). Symbols are those of the cited paper unless noted.

### 2.a Sharpe ratio estimator and distribution under non-Normal returns

#### Point estimator (native frequency)

For a series of excess returns \(\{r_t\}_{t=1}^{n}\) at a single sampling frequency (daily, weekly, monthly, …), the **non-annualized** Sharpe ratio estimator is

\[
\widehat{\mathrm{SR}} \;=\; \frac{\hat\mu}{\hat\sigma},
\qquad
\hat\mu \;=\; \frac{1}{n}\sum_{t=1}^{n} r_t,
\qquad
\hat\sigma \;=\; \sqrt{\frac{1}{n-1}\sum_{t=1}^{n}(r_t-\hat\mu)^{2}}
\]

[Bailey & López de Prado 2012, Section 2; standard definition used throughout Eqs. 4–11].  
(If \(r_t\) are already excess returns, no further risk-free subtraction is needed.)

**Annualization (display only; not used inside PSR/DSR):** if there are \(q\) observations per year, the annualized point estimate is

\[
\widehat{\mathrm{SR}}_{\mathrm{ann}} \;=\; \sqrt{q}\,\widehat{\mathrm{SR}}
\]

[Bailey & López de Prado 2012, Eq. (5)].  
**PSR and DSR are computed in the native frequency of \(\widehat{\mathrm{SR}}\); do not plug annualized SR into Eqs. (8)/(11)/(2) without converting every other input consistently** (see Section 5).

#### Higher moments (paper notation)

\[
\hat\gamma_3 \;=\; \text{sample skewness of }\{r_t\},
\qquad
\hat\gamma_4 \;=\; \text{sample kurtosis of }\{r_t\}
\]

[Bailey & López de Prado 2012, Eq. (7) discussion; used in Eqs. (8)–(11)].  
**Convention used in the PSR/DSR formulas below:** \(\hat\gamma_4\) is **raw** (non-excess) kurtosis, so a Normal distribution has \(\hat\gamma_4 = 3\). This is required for the Normal special case of the variance formula to recover Lo’s \(1 + \tfrac12\mathrm{SR}^{2}\) term.

#### Sampling distribution under Normal IID returns

Under Normal IID returns,

\[
\sqrt{n}\bigl(\widehat{\mathrm{SR}} - \mathrm{SR}\bigr)
\;\xrightarrow{d}\;
\mathcal{N}\!\left(0,\; 1 + \tfrac12\mathrm{SR}^{2}\right)
\]

[Bailey & López de Prado 2012, Eq. (4); Lo 2002].

#### Sampling distribution under non-Normal (stationary/ergodic) returns

Dropping Normality, Mertens’ result as printed in the PSR paper’s Eq. (8) uses the **expanded** asymptotic variance:

\[
\sqrt{n}\bigl(\widehat{\mathrm{SR}} - \mathrm{SR}\bigr)
\;\xrightarrow{d}\;
\mathcal{N}\!\Bigl(
  0,\;
  1 + \tfrac12\mathrm{SR}^{2}
    - \gamma_3\,\mathrm{SR}
    + \frac{\gamma_4 - 3}{4}\,\mathrm{SR}^{2}
\Bigr)
\]

[Bailey & López de Prado 2012, Eq. (8); Mertens 2002; Opdyke 2007].

**Algebraic collapse (same paper, later displays):** collect the \(\mathrm{SR}^{2}\) coefficients,

\[
\tfrac12 + \frac{\gamma_4 - 3}{4}
\;=\;
\frac{2}{4} + \frac{\gamma_4 - 3}{4}
\;=\;
\frac{\gamma_4 - 1}{4},
\]

so the Eq. (8) variance factor is **identical** to the collapsed form

\[
1 - \gamma_3\,\mathrm{SR} + \frac{\gamma_4 - 1}{4}\,\mathrm{SR}^{2}.
\]

That collapsed expression is what first appears in the paper’s estimated standard error \(\hat\sigma_{\widehat{\mathrm{SR}}}\) [Bailey & López de Prado 2012, §2.5, immediately after Eq. (8)] and again inside the PSR formula [Bailey & López de Prado 2012, Eq. (11)]. This note uses the collapsed form in denominators below for compactness; a line-by-line reviewer matching Eq. (8) should expand back via \(\tfrac12 + (\gamma_4-3)/4 = (\gamma_4-1)/4\).

**Check (Normal special case):** \(\gamma_3 = 0\), \(\gamma_4 = 3\) in either form gives

\[
1 + \tfrac12\mathrm{SR}^{2} - 0 + \frac{0}{4}\,\mathrm{SR}^{2}
\;=\;
1 + \tfrac12\mathrm{SR}^{2},
\]

matching Eq. (4) / Lo (2002).

#### Estimated standard error of \(\widehat{\mathrm{SR}}\)

After algebra and Bessel’s correction \(n \mapsto n-1\), the estimated standard deviation of \(\widehat{\mathrm{SR}}\) is (collapsed variance factor)

\[
\hat\sigma_{\widehat{\mathrm{SR}}}
\;=\;
\sqrt{
  \frac{
    1 - \hat\gamma_3\,\widehat{\mathrm{SR}}
      + \dfrac{\hat\gamma_4 - 1}{4}\,\widehat{\mathrm{SR}}^{2}
  }{n-1}
}
\]

[Bailey & López de Prado 2012, §2.5, immediately after Eq. (8); algebraically equivalent to substituting the expanded Eq. (8) factor \(1 + \tfrac12\widehat{\mathrm{SR}}^{2} - \hat\gamma_3\widehat{\mathrm{SR}} + (\hat\gamma_4-3)/4\,\widehat{\mathrm{SR}}^{2}\); the factor \(n-1\) is Bessel’s correction as stated there].

#### Symbol table (2.a)

| Paper symbol | Meaning |
|---|---|
| \(r_t\) | Excess return at observation \(t\) |
| \(n\) (also \(T\) in 2014 paper) | Sample length (number of return observations) |
| \(\hat\mu, \hat\sigma\) | Sample mean and sample std. dev. of returns |
| \(\widehat{\mathrm{SR}}\) | Estimated Sharpe ratio at **native** frequency |
| \(q\) | Observations per year (annualization factor) |
| \(\mathrm{SR}\) | True (unknown) Sharpe ratio |
| \(\gamma_3, \hat\gamma_3\) | Skewness of returns (true / sample) |
| \(\gamma_4, \hat\gamma_4\) | **Raw** kurtosis of returns (true / sample); Normal \(\Rightarrow 3\) |
| \(\hat\sigma_{\widehat{\mathrm{SR}}}\) | Estimated std. error of \(\widehat{\mathrm{SR}}\) |

---

### 2.b Probabilistic Sharpe Ratio (PSR)

Given a user-chosen benchmark Sharpe ratio \(\mathrm{SR}^{*}\) (same frequency as \(\widehat{\mathrm{SR}}\)), the Probabilistic Sharpe Ratio is the estimated probability that the true SR exceeds that benchmark:

\[
\widehat{\mathrm{PSR}}(\mathrm{SR}^{*})
\;=\;
Z\!\left[
  \frac{
    \bigl(\widehat{\mathrm{SR}} - \mathrm{SR}^{*}\bigr)\sqrt{n-1}
  }{
    \sqrt{
      1 - \hat\gamma_3\,\widehat{\mathrm{SR}}
        + \dfrac{\hat\gamma_4 - 1}{4}\,\widehat{\mathrm{SR}}^{2}
    }
  }
\right]
\]

[Bailey & López de Prado 2012, Eq. (11)],  
where \(Z(\cdot)\) is the standard Normal CDF [Bailey & López de Prado 2012, text after Eq. (11)].

Equivalently, with the standard-error form of §2.5,

\[
\widehat{\mathrm{PSR}}(\mathrm{SR}^{*})
\;=\;
Z\!\left(
  \frac{\widehat{\mathrm{SR}} - \mathrm{SR}^{*}}{\hat\sigma_{\widehat{\mathrm{SR}}}}
\right).
\]

[Bailey & López de Prado 2012, Eq. (11) rewritten with \(\hat\sigma_{\widehat{\mathrm{SR}}}\) from §2.5; the two displays are identical once \(\hat\sigma_{\widehat{\mathrm{SR}}}\) is substituted.]

**Monotonicity (paper):** for fixed \(\mathrm{SR}^{*}\), \(\widehat{\mathrm{PSR}}\) increases with larger \(\widehat{\mathrm{SR}}\), larger \(n\), and more positive skewness; it decreases with fatter tails (larger \(\hat\gamma_4\)) [Bailey & López de Prado 2012, text after Eq. (11)].

**Default benchmark:** \(\mathrm{SR}^{*} = 0\) (no skill) is the usual default [Bailey & López de Prado 2012, footnote 4].

#### Symbol table (2.b)

| Paper symbol | Meaning |
|---|---|
| \(\mathrm{SR}^{*}\) | Benchmark Sharpe ratio (native frequency) |
| \(\widehat{\mathrm{PSR}}(\mathrm{SR}^{*})\) | Prob. that true SR exceeds \(\mathrm{SR}^{*}\) |
| \(Z(\cdot)\) / \(\Phi(\cdot)\) | Standard Normal CDF |
| \(n\) | Track-record length (observation count) |

---

### 2.c Expected maximum Sharpe ratio across \(N\) independent trials

#### Setup

Consider \(N\) **independent** trials from a strategy class, each producing an estimated Sharpe ratio \(\widehat{\mathrm{SR}}_i\). Model

\[
\{\widehat{\mathrm{SR}}_i\}_{i=1}^{N}
\;\sim\;
\text{i.i.d. }\mathcal{N}\!\bigl(
  \mathbb{E}[\{\widehat{\mathrm{SR}}\}],\;
  \mathbb{V}[\{\widehat{\mathrm{SR}}\}]
\bigr)
\]

[Bailey & López de Prado 2014, Section “Expected Sharpe Ratios under Multiple Trials”].

#### Expected maximum (main formula)

The paper states that, after \(N \gg 1\) independent trials, the expected maximum can be **approximated** as

\[
\mathbb{E}\bigl[\max\{\widehat{\mathrm{SR}}\}\bigr]
\;\approx\;
\mathbb{E}[\{\widehat{\mathrm{SR}}\}]
\;+\;
\sqrt{\mathbb{V}[\{\widehat{\mathrm{SR}}\}]}
\;\cdot\;
\Biggl(
  (1-\gamma)\,Z^{-1}\!\Bigl(1-\frac{1}{N}\Bigr)
  \;+\;
  \gamma\,Z^{-1}\!\Bigl(1-\frac{1}{N\,e}\Bigr)
\Biggr)
\]

[Bailey & López de Prado 2014, Eq. (1); derived as App. A.1 Eqs. (5)–(6)].  
**Approximation condition:** this is an extreme-value-theory (EVT) approximation conditioned on \(N \gg 1\). The paper does **not** give an analytic error bound for small \(N\); finite-sample accuracy is only checked by Monte Carlo in App. A.2. That matters for this note’s own test vector (\(N=10\)) and for §5.5 guards that contemplate \(N\) as low as 2—implementers should treat Eq. (1) as the paper’s working formula, not an identity at every \(N\).

**Symbols in Eq. (1):**

- \(\gamma \approx 0.5772156649\) is the **Euler–Mascheroni constant**,
- \(e\) is Euler’s number,
- \(Z^{-1}\) is the standard Normal **quantile** (inverse CDF),
- \(N\) is the number of **independent** trials.

**Notation note (2014 vs 2012 benchmark symbol):** the 2014 paper names the DSR multiple-testing threshold \(\widehat{\mathrm{SR}}_{0}\) and writes \(\widehat{\mathrm{DSR}} \equiv \widehat{\mathrm{PSR}}(\widehat{\mathrm{SR}}_{0})\) [Bailey & López de Prado 2014, Eq. (2)]. The 2012 paper uses \(\mathrm{SR}^{*}\) for a generic PSR benchmark. **This note renames** \(\widehat{\mathrm{SR}}_{0}\) **as** \(\widehat{\mathrm{SR}}^{*}\) when the DSR threshold is in view (same object; 2012 star notation kept so PSR and DSR share one benchmark symbol in the code-mapping tables). Wherever \(\widehat{\mathrm{SR}}^{*}\) appears in §2.c–§2.d as the *multiple-testing* hurdle, read it as the paper’s \(\widehat{\mathrm{SR}}_{0}\).

Under the null of no skill in the strategy class, \(\mathbb{E}[\{\widehat{\mathrm{SR}}\}] = 0\), so the threshold used by DSR reduces to

\[
\widehat{\mathrm{SR}}^{*}
\;\equiv\;
\widehat{\mathrm{SR}}_{0}
\;\approx\;
\sqrt{\mathbb{V}[\{\widehat{\mathrm{SR}}\}]}
\;\cdot\;
\Biggl(
  (1-\gamma)\,Z^{-1}\!\Bigl(1-\frac{1}{N}\Bigr)
  \;+\;
  \gamma\,Z^{-1}\!\Bigl(1-\frac{1}{N\,e}\Bigr)
\Biggr)
\]

[Bailey & López de Prado 2014, Eq. (2) definition of \(\widehat{\mathrm{SR}}_{0}\), here written \(\widehat{\mathrm{SR}}^{*}\); under null \(\mathbb{E}=0\); \(\approx\) inherits the \(N \gg 1\) EVT approximation of Eq. (1)].

#### Role of the cross-trial variance

\(\mathbb{V}[\{\widehat{\mathrm{SR}}\}]\) is the **variance of estimated SRs across trials** (same frequency as the SRs used in PSR), **not** the variance of a single return series. Larger cross-trial dispersion or larger \(N\) raises \(\mathbb{E}[\max\{\widehat{\mathrm{SR}}\}]\) and therefore tightens the DSR hurdle [Bailey & López de Prado 2014, Eq. (1) and discussion after Eq. (2)].

#### Independent vs raw trial count (preview of pitfalls)

If \(M\) raw ledger trials are dependent with average pairwise correlation \(\hat\rho\), the paper’s equal-correlation interpolation for the **implied independent** count is

\[
\hat N \;=\; \hat\rho + (1-\hat\rho)\,M
\;=\; 1 + (M-1)(1-\hat\rho)
\]

[Bailey & López de Prado 2014, App. A.3 Eq. (9); limits \(\hat\rho\to 0\Rightarrow\hat N\to M\), \(\hat\rho\to 1\Rightarrow\hat N\to 1\)].  
Using raw \(M\) when trials are correlated **overstates** \(\mathbb{E}[\max]\) and over-deflates DSR.

#### Symbol table (2.c)

| Paper symbol | Meaning |
|---|---|
| \(N\) | Number of **independent** trials |
| \(M\) | Raw number of (possibly dependent) trials |
| \(\widehat{\mathrm{SR}}_i\) | Estimated SR of trial \(i\) |
| \(\mathbb{E}[\{\widehat{\mathrm{SR}}\}]\) | Mean of trial SRs (strategy-class location) |
| \(\mathbb{V}[\{\widehat{\mathrm{SR}}\}]\) | Variance of trial SRs (strategy-class scale) |
| \(\gamma\) | Euler–Mascheroni constant \(\approx 0.5772156649\) |
| \(e\) | Euler’s number \(\approx 2.718281828459\) |
| \(Z^{-1}\) | Standard Normal quantile function |
| \(\hat\rho\) | Average pairwise correlation among trials |
| \(\hat N\) | Implied independent trial count |
| \(\widehat{\mathrm{SR}}_{0}\) (paper) / \(\widehat{\mathrm{SR}}^{*}\) (this note) | Expected-max / DSR benchmark under the null (when \(\mathbb{E}=0\)); see notation note above |

---

### 2.d Deflated Sharpe Ratio (DSR)

DSR is **PSR evaluated at the multiple-testing benchmark** \(\widehat{\mathrm{SR}}_{0}\) from Section 2.c (this note’s alias: \(\widehat{\mathrm{SR}}^{*}\)):

\[
\widehat{\mathrm{DSR}}
\;\equiv\;
\widehat{\mathrm{PSR}}\!\bigl(\widehat{\mathrm{SR}}_{0}\bigr)
\;=\;
\widehat{\mathrm{PSR}}\!\bigl(\widehat{\mathrm{SR}}^{*}\bigr)
\;=\;
Z\!\left[
  \frac{
    \bigl(\widehat{\mathrm{SR}} - \widehat{\mathrm{SR}}^{*}\bigr)\sqrt{T-1}
  }{
    \sqrt{
      1 - \hat\gamma_3\,\widehat{\mathrm{SR}}
        + \dfrac{\hat\gamma_4 - 1}{4}\,\widehat{\mathrm{SR}}^{2}
    }
  }
\right]
\]

with

\[
\widehat{\mathrm{SR}}^{*}
\;\equiv\;
\widehat{\mathrm{SR}}_{0}
\;\approx\;
\sqrt{\mathbb{V}[\{\widehat{\mathrm{SR}}\}]}
\;\cdot\;
\Biggl(
  (1-\gamma)\,Z^{-1}\!\Bigl(1-\frac{1}{N}\Bigr)
  \;+\;
  \gamma\,Z^{-1}\!\Bigl(1-\frac{1}{N\,e}\Bigr)
\Biggr)
\]

under \(\mathbb{E}[\{\widehat{\mathrm{SR}}\}]=0\)  
[Bailey & López de Prado 2014, Eq. (2); “Essentially, DSR is a PSR where the rejection threshold is adjusted to reflect the multiplicity of trials”; \(\widehat{\mathrm{SR}}_{0}\) is the paper’s symbol, written \(\widehat{\mathrm{SR}}^{*}\) in this note; \(\approx\) is the Eq. (1) EVT approximation for \(N \gg 1\)].

Here \(T\) is the selected strategy’s sample length (same role as \(n\) in the 2012 paper), and \(\widehat{\mathrm{SR}}, \hat\gamma_3, \hat\gamma_4\) are computed on the **selected** strategy’s return series [Bailey & López de Prado 2014, text after Eq. (2)].

**Decision rule (as used in the paper’s example):** reject the null of “selection-bias artifact” at confidence level \(c\) (e.g. \(c=0.95\)) when \(\widehat{\mathrm{DSR}} \ge c\) [Bailey & López de Prado 2014, “A Numerical Example”].

**Five inputs beyond the classical SR** (paper list): non-Normality \((\hat\gamma_3,\hat\gamma_4)\), sample length \(T\), cross-trial SR variance \(\mathbb{V}[\{\widehat{\mathrm{SR}}\}]\), and independent trial count \(N\) [Bailey & López de Prado 2014, paragraph after Eq. (2)].

#### Symbol table (2.d)

| Paper symbol | Meaning |
|---|---|
| \(\widehat{\mathrm{DSR}}\) | Deflated Sharpe Ratio \(\equiv \widehat{\mathrm{PSR}}(\widehat{\mathrm{SR}}_{0})\); paper Eq. (2) |
| \(\widehat{\mathrm{SR}}\) | Estimated SR of the **selected** strategy (native freq.) |
| \(\widehat{\mathrm{SR}}_{0}\) / \(\widehat{\mathrm{SR}}^{*}\) | Multiple-testing / expected-max benchmark (paper / this note) |
| \(T\) | Sample length of the selected strategy |
| \(N, \mathbb{V}[\{\widehat{\mathrm{SR}}\}]\) | Independent trials; cross-trial SR variance |
| \(\hat\gamma_3, \hat\gamma_4\) | Skewness and **raw** kurtosis of selected returns |

---

## 3. Code-mapping plan

No code in this ticket. The tables below are the intended contract for a later implementation. All Sharpe ratios and moments are at **native return frequency** unless a column says otherwise.

### 3.a Sharpe estimator and SE

| Paper symbol | Intended Python name | Runtime source |
|---|---|---|
| \(\{r_t\}\) | `returns` | Excess-return series of one trial / selected strategy |
| \(n\) or \(T\) | `n_obs` | Observation count of that return series after cleaning |
| \(\hat\mu\) | `mu_hat` | Sample mean of the return series |
| \(\hat\sigma\) | `sigma_hat` | Sample standard deviation of the return series (Bessel \(n-1\)) |
| \(\widehat{\mathrm{SR}}\) | `sr_hat` | \(\hat\mu / \hat\sigma\) at native frequency |
| \(q\) | `periods_per_year` | Calendar config (e.g. 252 or 250 daily, 12 monthly); **display only** for \(\widehat{\mathrm{SR}}_{\mathrm{ann}} = \sqrt{q}\,\widehat{\mathrm{SR}}\) |
| \(\hat\gamma_3\) | `skew_hat` | Sample skewness of the return series |
| \(\hat\gamma_4\) | `kurt_hat` | Sample **raw** kurtosis of the return series (Normal \(\rightarrow 3\); if a library yields excess kurtosis, add 3) |
| \(\hat\sigma_{\widehat{\mathrm{SR}}}\) | `sr_se` | \(\sqrt{\bigl(1 - \hat\gamma_3\widehat{\mathrm{SR}} + (\hat\gamma_4-1)/4\,\widehat{\mathrm{SR}}^{2}\bigr)/(n-1)}\) [2012 §2.5] |
| Lo/Mertens variance factor | `sr_var_factor` | \(1 - \hat\gamma_3\widehat{\mathrm{SR}} + (\hat\gamma_4-1)/4\,\widehat{\mathrm{SR}}^{2}\) (collapsed form of 2012 Eq. (8); see §2.a) |

### 3.b PSR

| Paper symbol | Intended Python name | Runtime source |
|---|---|---|
| \(\mathrm{SR}^{*}\) | `sr_star` | User-chosen PSR benchmark at native frequency; default 0 for no-skill tests |
| \(\widehat{\mathrm{PSR}}(\mathrm{SR}^{*})\) | `psr` | \(\Phi\!\bigl((\widehat{\mathrm{SR}} - \mathrm{SR}^{*})\,\sqrt{n-1}\,/\,\sqrt{\text{variance factor}}\bigr)\) [2012 Eq. (11)] |
| \(Z\) / \(\Phi\) | (CDF primitive) | Standard Normal CDF from a numerical library |

### 3.c Expected maximum SR

| Paper symbol | Intended Python name | Runtime source |
|---|---|---|
| \(N\) | `n_trials_indep` | Independent trial count (from ledger after dependence adjustment) |
| \(M\) | `n_trials_raw` | Raw trial count in the trial ledger |
| \(\hat\rho\) | `avg_trial_corr` | Average pairwise correlation of trial return series or SR estimates [2014 App. A.3] |
| \(\hat N\) | `n_trials_indep` | \(1 + (M-1)(1-\hat\rho)\) when using 2014 Eq. (9) |
| \(\mathbb{E}[\{\widehat{\mathrm{SR}}\}]\) | `sr_trials_mean` | Mean of the trial SR estimates; under the no-skill null set to 0 for DSR |
| \(\mathbb{V}[\{\widehat{\mathrm{SR}}\}]\) | `sr_trials_var` | Sample variance of the **vector of trial SRs** (same frequency as \(\widehat{\mathrm{SR}}\)) |
| \(\sqrt{\mathbb{V}}\) | `sr_trials_std` | Square root of that cross-trial variance |
| \(\gamma\) | `EULER_MASCHERONI` | Euler–Mascheroni constant \(0.5772156649\) |
| \(e\) | (Euler’s number) | Euler’s number \(e\) |
| \(Z^{-1}(1-1/N)\) | `z1` | Standard Normal quantile at \(1 - 1/N\) |
| \(Z^{-1}(1-1/(N e))\) | `z2` | Standard Normal quantile at \(1 - 1/(N e)\) |
| max standardized term | `max_z` | \((1-\gamma)\,z_1 + \gamma\,z_2\) [2014 Eq. (1)] |
| \(\mathbb{E}[\max\{\widehat{\mathrm{SR}}\}]\) | `expected_max_sr` | \(\mathbb{E}[\{\widehat{\mathrm{SR}}\}] + \sqrt{\mathbb{V}}\,\max_Z\) (EVT approximation, \(N \gg 1\)) |
| \(\widehat{\mathrm{SR}}_{0}\) / \(\widehat{\mathrm{SR}}^{*}\) (null) | `sr_star` | Expected-max SR under \(\mathbb{E}[\{\widehat{\mathrm{SR}}\}]=0\); paper symbol \(\widehat{\mathrm{SR}}_{0}\) |

### 3.d DSR

| Paper symbol | Intended Python name | Runtime source |
|---|---|---|
| \(\widehat{\mathrm{SR}}\) (selected) | `sr_hat` | Native-frequency SR of the **selected** strategy |
| \(\widehat{\mathrm{SR}}_{0}\) / \(\widehat{\mathrm{SR}}^{*}\) | `sr_star` | Expected-max benchmark under the null (§3.c) |
| \(T\) | `n_obs` | Length of the selected strategy’s return series |
| \(\hat\gamma_3, \hat\gamma_4\) | `skew_hat`, `kurt_hat` | Moments of **selected** returns |
| \(\widehat{\mathrm{DSR}}\) | `dsr` | \(\widehat{\mathrm{PSR}}(\widehat{\mathrm{SR}}_{0})\): same map as §3.b with benchmark = expected-max SR [2014 Eq. (2)] |
| confidence level \(c\) | `confidence` | Configuration threshold (e.g. 0.95); pass when \(\widehat{\mathrm{DSR}} \ge c\) |

**Pipeline (logical order for later implementation):**  
(1) per-trial \(\widehat{\mathrm{SR}}\) → (2) cross-trial variance and independent trial count → (3) expected-max / \(\widehat{\mathrm{SR}}_{0}\) → (4) selected \(\widehat{\mathrm{SR}}\), skewness, kurtosis, \(T\) → (5) \(\widehat{\mathrm{DSR}}\).

---

## 4. Test vectors (hand-worked)

All values shown to at least **6 significant digits**. Constants:

\[
\gamma = 0.5772156649,\qquad e = 2.718281828459,\qquad \sqrt{23} = 4.79583152331
\]

Standard Normal CDF/quantile values below are the usual high-precision library values (as in SciPy `scipy.stats.norm`); a reviewer can recompute with any IEEE-754 Normal implementation.

---

### 4.1 PSR — Normal returns

**Inputs**

| Input | Value |
|---|---|
| \(n = T\) | 24 |
| \(\widehat{\mathrm{SR}}\) | 0.5 (native) |
| \(\mathrm{SR}^{*}\) | 0.0 |
| \(\hat\gamma_3\) | 0.0 |
| \(\hat\gamma_4\) | 3.0 (Normal raw kurtosis) |

**Step 1 — variance factor**

\[
1 - \hat\gamma_3\,\widehat{\mathrm{SR}} + \frac{\hat\gamma_4-1}{4}\,\widehat{\mathrm{SR}}^{2}
= 1 - 0 + \frac{2}{4}(0.5)^{2}
= 1 + 0.5\cdot 0.25
= 1.125
\]

\[
\sqrt{1.125} = 1.06066017178
\]

**Step 2 — numerator**

\[
\bigl(\widehat{\mathrm{SR}} - \mathrm{SR}^{*}\bigr)\sqrt{n-1}
= (0.5 - 0)\sqrt{23}
= 0.5 \times 4.79583152331
= 2.39791576166
\]

**Step 3 — \(z\)-score**

\[
z = \frac{2.39791576166}{1.06066017178} = 2.26077666104
\]

**Step 4 — PSR**

\[
\widehat{\mathrm{PSR}}(0) = Z(2.26077666104) = 0.98811345473
\]

[Formula: Bailey & López de Prado 2012, Eq. (11).]

**Expected pytest anchors:** `sr_var_factor == 1.125`, `z ≈ 2.260776661`, `psr ≈ 0.988113455`.

---

### 4.2 PSR — non-Normal returns (clean \(z = 2\))

**Inputs**

| Input | Value |
|---|---|
| \(n\) | 24 |
| \(\widehat{\mathrm{SR}}\) | 0.5 |
| \(\mathrm{SR}^{*}\) | 0.0 |
| \(\hat\gamma_3\) | −0.5 |
| \(\hat\gamma_4\) | 4.0 |

**Step 1 — variance factor**

\[
1 - (-0.5)(0.5) + \frac{4-1}{4}(0.5)^{2}
= 1 + 0.25 + 0.75\cdot 0.25
= 1 + 0.25 + 0.1875
= 1.4375
\]

\[
\sqrt{1.4375} = 1.19895788083
\]

**Step 2 — numerator** (same as 4.1)

\[
0.5 \times \sqrt{23} = 2.39791576166
\]

**Step 3 — \(z\)-score**

\[
z = \frac{2.39791576166}{1.19895788083} = 2.00000000000
\]

**Step 4 — PSR**

\[
\widehat{\mathrm{PSR}}(0) = Z(2) = 0.97724986805
\]

Negative skew and excess kurtosis **lower** PSR relative to the Normal case (0.98811 → 0.97725), matching the paper’s comparative statics [Bailey & López de Prado 2012, text after Eq. (11)].

**Expected pytest anchors:** `z == 2.0` (within float tolerance), `psr ≈ 0.977249868`.

---

### 4.3 Expected maximum SR

**Inputs**

| Input | Value |
|---|---|
| \(N\) | 10 |
| \(\mathbb{E}[\{\widehat{\mathrm{SR}}\}]\) | 0.0 |
| \(\sqrt{\mathbb{V}[\{\widehat{\mathrm{SR}}\}]}\) | 0.5 (i.e. \(\mathbb{V}=0.25\)) |

**Step 1 — Normal quantiles**

\[
Z^{-1}\!\Bigl(1 - \frac{1}{10}\Bigr) = Z^{-1}(0.9) = 1.28155156554
\]

\[
\frac{1}{N e} = \frac{1}{10 \times 2.71828182846} = 0.03678794412,
\qquad
1 - \frac{1}{N e} = 0.96321205588
\]

\[
Z^{-1}\!\Bigl(1 - \frac{1}{N e}\Bigr) = Z^{-1}(0.96321205588) = 1.78924176458
\]

**Step 2 — standardized expected maximum**

\[
1 - \gamma = 1 - 0.5772156649 = 0.4227843351
\]

\[
(1-\gamma)\,Z^{-1}(0.9) = 0.4227843351 \times 1.28155156554 = 0.54181992654
\]

\[
\gamma\,Z^{-1}\!\Bigl(1-\frac{1}{Ne}\Bigr) = 0.5772156649 \times 1.78924176458 = 1.03277837481
\]

\[
\max_Z = 0.54181992654 + 1.03277837481 = 1.57459830135
\]

**Step 3 — expected maximum SR**

\[
\mathbb{E}[\max\{\widehat{\mathrm{SR}}\}]
= 0 + 0.5 \times 1.57459830135
= 0.78729915067
\]

[Formula: Bailey & López de Prado 2014, Eq. (1) / App. A.1 Eq. (6).]

**Expected pytest anchors:** `max_z ≈ 1.574598301`, `expected_max_sr ≈ 0.787299151`.

---

### 4.4 DSR (PSR at expected-max benchmark)

**Inputs**

| Input | Value |
|---|---|
| \(T\) | 24 |
| \(\widehat{\mathrm{SR}}\) (selected) | 1.0 (native) |
| \(\hat\gamma_3\) | −0.2 |
| \(\hat\gamma_4\) | 3.5 |
| \(N\) | 10 |
| \(\mathbb{E}[\{\widehat{\mathrm{SR}}\}]\) | 0.0 |
| \(\sqrt{\mathbb{V}[\{\widehat{\mathrm{SR}}\}]}\) | 0.5 |

**Step 1 — benchmark** (reuse 4.3)

\[
\widehat{\mathrm{SR}}^{*} = 0.78729915067
\]

**Step 2 — numerator**

\[
\widehat{\mathrm{SR}} - \widehat{\mathrm{SR}}^{*} = 1.0 - 0.78729915067 = 0.21270084933
\]

\[
\bigl(\widehat{\mathrm{SR}} - \widehat{\mathrm{SR}}^{*}\bigr)\sqrt{T-1}
= 0.21270084933 \times 4.79583152331
= 1.02007743824
\]

**Step 3 — denominator (variance factor)**

\[
1 - (-0.2)(1.0) + \frac{3.5-1}{4}(1.0)^{2}
= 1 + 0.2 + 0.625
= 1.825
\]

\[
\sqrt{1.825} = 1.35092560861
\]

**Step 4 — \(z\) and DSR**

\[
z = \frac{1.02007743824}{1.35092560861} = 0.75509519676
\]

\[
\widehat{\mathrm{DSR}} = Z(0.75509519676) = 0.77490406751
\]

[Formula: Bailey & López de Prado 2014, Eq. (2).]  
At a 95% threshold this trial would **not** clear DSR (\(0.775 < 0.95\)), despite a raw native SR of 1.0 after only 10 independent noise-scale trials.

**Expected pytest anchors:** `sr_star ≈ 0.787299151`, `z ≈ 0.755095197`, `dsr ≈ 0.774904068`.

---

### 4.5 Cross-check: paper numerical example (published DSR levels)

This reproduces the confidence levels stated in Bailey & López de Prado (2014), “A Numerical Example” (DSR \(\approx 0.90\) at the reported trial count; DSR \(= 0.9505\) at \(N=46\); Normal returns would still clear 95% at \(N=88\)).

**Inputs (native-frequency form)**

| Input | Value | Notes |
|---|---|---|
| Annualized \(\widehat{\mathrm{SR}}\) | 2.5 | Paper narrative |
| \(q\) | 250 | Paper: 250 obs/year |
| Native \(\widehat{\mathrm{SR}}\) | \(2.5/\sqrt{250} = 0.15811388301\) | Convert before PSR/DSR |
| \(T\) | 1250 | 5 years × 250 |
| \(\hat\gamma_3\) | −3 | Non-Normal left tail |
| \(\hat\gamma_4\) | 10 | Raw kurtosis |
| \(\mathbb{E}[\{\widehat{\mathrm{SR}}\}]\) | 0 | Null of no skill |
| Annualized cross-trial variance | \(1/2\) | \(\Rightarrow\) native \(\sqrt{\mathbb{V}} = \sqrt{(1/2)/250} = 0.04472135955\) |

**For \(N = 100\):**

\[
\widehat{\mathrm{SR}}^{*} = 0.11317200187
\quad(\text{native}),
\qquad
\sqrt{\text{var factor}} = 1.23717082451,
\]

\[
z = 1.28381603653,
\qquad
\widehat{\mathrm{DSR}} = 0.90039683445
\;\approx\; 0.90
\]

(matches the paper’s “only a 90% chance” language).

**For \(N = 46\):** \(\widehat{\mathrm{DSR}} = 0.95050170688 \approx 0.9505\) (paper’s stated figure).

**For Normal returns** \(\hat\gamma_3=0,\hat\gamma_4=3\) **and \(N=88\):** \(\widehat{\mathrm{DSR}} \approx 0.9505\) (paper: still above 95% at \(N=88\) if Normal).

---

## 5. Implementation pitfalls

### 5.1 Annualization vs native frequency

- PSR/DSR formulas assume \(\widehat{\mathrm{SR}}\), \(\mathrm{SR}^{*}\), \(\widehat{\mathrm{SR}}^{*}\), and \(\mathbb{V}[\{\widehat{\mathrm{SR}}\}]\) are in the **same** frequency as the return series used for moments [Bailey & López de Prado 2012, text after Eq. (11): “All calculations are done in the original frequency of the data, and there is no annualization”].
- **Wrong:** feed annualized SR into Eq. (11)/(2) while using daily \(T\) and daily skew/kurtosis without converting the benchmark and cross-trial variance.
- **Right:** compute everything at native frequency; annualize only for human-readable reporting via \(\sqrt{q}\).
- If the trial ledger stores annualized SRs, convert: \(\widehat{\mathrm{SR}} = \widehat{\mathrm{SR}}_{\mathrm{ann}}/\sqrt{q}\) and \(\mathbb{V}_{\mathrm{native}} = \mathbb{V}_{\mathrm{ann}}/q\) before Eq. (1)–(2).

### 5.2 Autocorrelated returns

- The Mertens/PSR standard error used here is the stationary-ergodic formula highlighted by Opdyke (2007); it is **not** Lo’s (2002) full HAC correction for overlapping or strongly autocorrelated returns.
- If returns are overlapping (e.g. \(k\)-day holding-period returns sampled daily), effective sample size is smaller than \(T\), and \(\hat\sigma_{\widehat{\mathrm{SR}}}\) is understated → PSR/DSR overstated.
- Mitigation for v0.1: document the assumption (non-overlapping, approximately stationary returns at the chosen bar size); defer HAC/GMM SE variants unless a later ticket adopts them.

### 5.3 Independent trials vs raw ledger count

- \(N\) in Eq. (1)–(2) is the number of **independent** trials, not the raw row count \(M\) in the trial ledger [Bailey & López de Prado 2014, App. A.3].
- Using \(M \gg N\) when trials share data, parameters, or correlated signals **overstates** \(\widehat{\mathrm{SR}}^{*}\) and **understates** DSR (over-deflation).
- Paper’s simple correction: \(\hat N = 1 + (M-1)(1-\hat\rho)\) [2014, Eq. (9)].
- Caveats from the paper: correlation is only linear dependence; the correlation matrix is ill-conditioned when the sample is short relative to the number of pairwise correlations, specifically when \(T < \tfrac12 M(M-1)\) (more unknown pairs than independent observation pairs), so \(\hat\rho\) itself may be overfit [2014, App. A.3]. The common special case \(M > T\) is sufficient for that inequality at moderate \(M\) but is **not** the paper’s stated condition—ill-conditioning can hold even when \(T > M\). Information-theoretic redundancy estimates are suggested as an alternative.

### 5.4 Estimating the cross-trial SR variance \(\mathbb{V}[\{\widehat{\mathrm{SR}}\}]\)

- This is the sample variance of the **list of trial SR estimates**, not \(\hat\sigma^{2}\) of the selected return series.
- Under the null used for DSR, location is set to \(\mathbb{E}=0\); scale \(\mathbb{V}\) still comes from the empirical dispersion of trials (or a conservative prior if the ledger is incomplete).
- With few trials, \(\widehat{\mathbb{V}}\) is noisy; a downward-biased \(\widehat{\mathbb{V}}\) understates the hurdle and inflates DSR (false discovery risk).
- Units must match native SR (see 5.1). Heterogeneous track lengths across trials complicate a single \(\mathbb{V}\); v0.1 should prefer a common evaluation window or document the mixture.

### 5.5 Numerical issues in the inverse Normal CDF tails

- Eq. (1) evaluates \(Z^{-1}(1 - 1/N)\) and \(Z^{-1}(1 - 1/(N e))\). For large \(N\) (e.g. \(10^{6}\)–\(10^{9}\) parameter grids), both arguments approach 1 and lie deep in the right tail.
- Use a numerically stable `ppf` / `erfinv` implementation; avoid constructing `1 - 1/N` in low precision when \(N\) is huge (use `norm.ppf` with a complementary tail API if available).
- For \(N = 1\): \(1 - 1/N = 0\) and \(Z^{-1}(0) = -\infty\). Guard: require \(N \ge 2\), or define \(\mathbb{E}[\max] = \mathbb{E}[\{\widehat{\mathrm{SR}}\}]\) when \(N=1\) (no multiple-testing inflation).
- Intermediate \(\max_Z\) grows slowly (\(\sim\sqrt{2\log N}\)); still validate against App. A.2-style Monte Carlo for extreme \(N\) if the court accepts billion-scale ledgers.

### 5.6 Additional practical guards (implementation-facing)

| Issue | Failure mode | Guard |
|---|---|---|
| \(\hat\sigma = 0\) | `sr_hat` undefined | Reject series; no DSR |
| Variance factor \(\le 0\) | SE not real (extreme skew/kurt + SR) | Clamp or fail closed (DSR undefined) |
| Excess vs raw kurtosis | Off-by-one in \((\gamma_4-1)/4\) vs \((\gamma_4^{\mathrm{ex}})/4\) | Enforce raw kurtosis; unit-test Normal case → factor \(1+\tfrac12\mathrm{SR}^{2}\) |
| Bessel \(n-1\) | Using \(n\) instead of \(n-1\) shifts PSR slightly | Match paper Section 2.5 / Eq. (11) with \(n-1\) |
| Incomplete trial ledger | Hidden trials understate \(N\) and \(\mathbb{V}\) | Court must require a full trial ledger (project iron law) |
| Selecting on annualized SR then deflating in native units inconsistently | Silent bias | Single frequency pipeline (Section 3 pipeline) |

---

## Document status

| Item | Status |
|---|---|
| Sources with bibliographic detail | Done |
| Formulas 2.a–2.d with citations + symbol tables | Done |
| Code-mapping plan (no code) | Done |
| Hand-worked test vectors (PSR, E[max], DSR) | Done |
| Implementation pitfalls | Done |

This note is the sole deliverable of ticket **v0.1-04**. Implementation belongs to a later ticket that must cite this document and the equation numbers above.
