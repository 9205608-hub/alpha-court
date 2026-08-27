# qlib China daily data — availability research & local smoke validation

**Ticket:** v0.1-09  
**Machine date:** 2026-07-10  
**Platform:** macOS arm64  
**Python used:** 3.11.2 (`python3.11 -m venv .venv`)  
**pyqlib:** 0.9.7 (wheel `pyqlib-0.9.7-cp311-cp311-macosx_10_9_universal2.whl`)

This note records what is downloadable **today on this machine**, with measured sizes, calendar ranges, and smoke-load stats. Claims that were not measured here are labeled as such.

---

## 1. Acquisition paths compared

| Route | How | Freshness (measured / claimed) | Size (measured) | Reliability on this machine | Notes |
| --- | --- | --- | --- | --- | --- |
| **A. Official `GetData` / CLI** | `python -m qlib.cli.data qlib_data --target_dir <dir> --region cn` (same as `qlib.tests.data.GetData`) | **Stale.** Calendar last day **2020-09-25** (probe dir measured) | Zip **187M**; unpacked tree **~510M** including leftover zip | **Works** (exit 0, ~90s download + unzip) | README still says official dataset is “disabled temporarily”; GitHub #1547 (2023) reported Azure `409 Public access is not permitted`. On 2026-07-10 the Azure blob **did** serve data, but the pack is the old Yahoo-sourced snapshot ending 2020. |
| **B. Community mirror (chenditc/investment_data)** | GitHub Release `qlib_bin.tar.gz` → extract into `~/.qlib/qlib_data/cn_data` | **Fresh.** Calendar last day **2026-07-03**; release tag **2026-07-05** | tarball **532M** (557 319 688 bytes); extracted **813M** | **Works** (curl exit 0, tar exit 0, **193s** end-to-end) | Currently the best default. Daily-ish releases via GitHub Actions + multi-source dump. Official README points here. |
| **C. Dump-your-own** | Collect CSV (Yahoo / Tushare / etc.) → `scripts/dump_bin.py` (qlib source tree) | As fresh as your source | Depends on universe | Not run in this ticket (out of smoke scope) | Needed if you want vendor-grade fields, PIT corporate actions, or independence from community packs. |

### Path details

#### A. Official CLI / `GetData`

Documented commands (README / docs):

```bash
python -m qlib.cli.data qlib_data --target_dir ~/.qlib/qlib_data/cn_data --region cn
# equivalent when working from a qlib source checkout:
python scripts/get_data.py qlib_data --target_dir ~/.qlib/qlib_data/cn_data --region cn
```

**This machine:** succeeded into a probe directory (kept separate so it would not overwrite the community pack used for validation):

```bash
python -m qlib.cli.data qlib_data \
  --target_dir ~/.qlib/qlib_data/cn_data_official_probe --region cn
# official_exit=0
```

Measured probe calendar (`calendars/day.txt`): **1999-11-10 → 2020-09-25**, **4943** sessions. `instruments/all.txt`: **3875** lines. Do **not** use this pack for a 2026 demo.

#### B. Community release (recommended)

```bash
wget https://github.com/chenditc/investment_data/releases/latest/download/qlib_bin.tar.gz
# or: curl -L --fail -o qlib_bin.tar.gz <same URL>
mkdir -p ~/.qlib/qlib_data/cn_data
tar -zxvf qlib_bin.tar.gz -C ~/.qlib/qlib_data/cn_data --strip-components=1
rm -f qlib_bin.tar.gz
```

Release used here: tag **2026-07-05**, published `2026-07-05T09:17:49Z`, asset `qlib_bin.tar.gz`.

#### C. Dump-your-own

High-level pipeline (from qlib docs / `scripts/data_collector` + `scripts/dump_bin.py`):

1. Download OHLCV CSV from a price source (Yahoo collector in-tree, or external Tushare/Baostock/etc.).
2. Normalize columns to qlib CSV layout.
3. `python scripts/dump_bin.py dump_all --csv_path <csv_dir> --qlib_dir ~/.qlib/qlib_data/cn_data --include_fields open,close,high,low,volume,factor,...`

Not exercised here. Treat as the escape hatch when community freshness or field quality is insufficient.

---

## 2. What was actually done on this machine

### 2.1 Install

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install pyqlib
```

| Item | Result |
| --- | --- |
| Default `python3` | 3.12.8 (not used for install) |
| Working interpreter | **Python 3.11.2** |
| Arch | **arm64** |
| `pyqlib` | **0.9.7**, prebuilt universal2 wheel — **no compile** |
| Install wall time | ~4 minutes (deps via Tsinghua PyPI mirror already configured on machine) |
| Tricks needed | None for 3.11. Not re-tested on 3.12 in this session. LightGBM/OpenMP notes in upstream README were not blockers for `import qlib` + data load. |

### 2.2 Downloads

**Community pack (written to `~/.qlib/qlib_data/cn_data`):**

```text
START_UTC=2026-07-10T09:27:22Z
END_UTC=2026-07-10T09:30:35Z
DURATION_SEC=193
download_exit=0
extract_exit=0
du -sh ~/.qlib/qlib_data/cn_data  →  813M
```

Exact command sequence:

```bash
curl -L --fail --retry 3 --retry-delay 5 \
  -o /tmp/qlib_bin.tar.gz \
  "https://github.com/chenditc/investment_data/releases/latest/download/qlib_bin.tar.gz"
mkdir -p ~/.qlib/qlib_data/cn_data
tar -zxvf /tmp/qlib_bin.tar.gz -C ~/.qlib/qlib_data/cn_data --strip-components=1
```

**Official pack (probe only):** exit 0; last calendar day **2020-09-25**; not used for smoke below.

### 2.3 Smoke init

```python
import qlib
from qlib.constant import REG_CN
qlib.init(provider_uri="~/.qlib/qlib_data/cn_data", region=REG_CN, kernels=1)
```

`kernels=1` avoids a macOS multiprocessing spawn failure when loading large panels (joblib falls back to threading with a warning; loads still succeed).

---

## 3. Data quality findings (community pack @ `~/.qlib/qlib_data/cn_data`)

### 3.1 Calendar & universes

| Metric | Value |
| --- | --- |
| Trading days (`D.calendar`) | **6420** |
| First session | **2000-01-04** |
| Last session | **2026-07-03** |
| Instruments `all` | **6114** |
| Instruments `csi300` (full membership file, no date filter) | **939** |
| Instruments `csi500` | **1774** |
| `csi300` members with data in last ~2y window | **336** |
| On-disk feature fields (sample instrument) | `open, high, low, close, volume, amount, factor, change, vwap, adjclose` |
| Instrument lists present | `all`, `csi300`, `csi500`, `csi800`, `csi1000`, `csiall` |

Note: `csi300` file length **939** is historical membership (stocks that were in the index at some point with start/end dates), not “exactly 300 names today”. Point-in-time listing for 2024-07-03→2026-07-03 yields **336** symbols with feature rows.

### 3.2 CSI300 panel, last ~2 years

Window: **2024-07-03 → 2026-07-03** (485 trading days).

| Metric | Value |
| --- | --- |
| `D.features` fields | `$close $volume $open $high $low $factor $change $vwap $adjclose $amount` |
| Panel shape | **(145309, 10)** |
| Row count | **145309** |
| Instruments in panel | **336** |
| Dates in panel | **485** |
| Load time (`kernels=1`) | **10.44 s** |

**NaN rates (fraction of panel cells):**

| Field | NaN rate | NaN count |
| --- | --- | --- |
| `$close` | 0.001665 | 242 / 145309 |
| `$volume` | 0.001665 | 242 / 145309 |
| `$open` / `$high` / `$low` / `$change` / `$vwap` / `$adjclose` / `$amount` | 0.001665 each | 242 each |
| `$factor` | **0.0** | 0 |

Price-field NaNs co-occur: `both_nan_rows=242`, no close-only or volume-only NaN splits. `zero_volume_rows=0`.

### 3.3 Spot checks (well-known tickers)

Last 2y rows each: **485**. All `$close` values **positive**. `$factor` present and non-null.

**SH600519 (Kweichow Moutai) — last 5 sessions:**

| date | $close | $volume | $factor | $adjclose |
| --- | ---: | ---: | ---: | ---: |
| 2026-06-29 | 290.62 | 274983 | 0.2432 | 10331.67 |
| 2026-06-30 | 288.32 | 162856 | 0.2432 | 10249.79 |
| 2026-07-01 | 290.15 | 174640 | 0.2432 | 10314.81 |
| 2026-07-02 | 292.58 | 209163 | 0.2432 | 10401.18 |
| 2026-07-03 | 290.50 | 140898 | 0.2432 | 10327.26 |

- `$close` min/max/mean over 2y: **284.22 / 394.33 / 336.69** (all > 0).  
- `$factor` range: **0.2256 – 0.2432**.  
- **Adjustment convention (observed):** `$close` is the qlib-adjusted series used by most examples; `$factor` is the adjustment factor; `$adjclose` is a second price series on disk (values for Moutai are ~10k-scale, **not** the familiar ~1.4k CNY cash price — treat `$adjclose` carefully and prefer documenting which series the adapter will emit). Relationship check: `$close / $factor` ≈ 290.5 / 0.2432 ≈ **1194**, which is in the right order of magnitude for Moutai cash prices after recent years’ moves. **Do not assume `$adjclose` is raw CNY without a dedicated reconciliation.**

**SZ000001 (Ping An Bank):** `$close` 2y range ~3.05–4.38; last `$adjclose` ~1430; `$factor` ~0.351; all closes positive.

**SH601318 (Ping An Insurance):** `$close` 2y range ~2.48–4.98; last `$adjclose` ~159; `$factor` ~0.069; all closes positive.

### 3.4 Suspensions / missing data representation

Two mechanisms appear:

1. **Missing rows vs calendar (instrument not in panel for that day)**  
   - SH600519: **0** missing rows vs 485-day calendar.  
   - Across CSI300 panel: **72 / 336** instruments have fewer than 485 rows (shortest examples length **120** — consistent with late index inclusion / limited history in-window, not necessarily halts).

2. **NaN rows (row present, OHLCV null)**  
   - **242** panel rows with both `$close` and `$volume` NaN.  
   - No pure zero-volume trading days in this CSI300 window.  
   - `$factor` stays filled even when OHLCV is NaN.

**Practical takeaway for the adapter:** align on the trading calendar, forward-fill or mask NaNs explicitly, and do not assume “no row ⇒ suspended” only — both row-gaps and NaN rows exist.

### 3.5 Anomalies / caveats

- Official CLI pack is **years stale** (ends 2020-09-25) even though download succeeds — easy footgun if someone follows only the CLI snippet.  
- `csi300` membership file is multi-period; always filter by `start_time`/`end_time` for a stable universe size.  
- `$adjclose` scale is not obviously “raw CNY”; validate before using in reports.  
- Data provenance for the community pack is multi-source (see chenditc/investment_data); not a licensed exchange feed.

---

## 4. Recommendation for the v0.1 demo

| Choice | Recommendation | Why |
| --- | --- | --- |
| **Acquisition** | Community release (**path B**) into `~/.qlib/qlib_data/cn_data` | Fresh through **2026-07-03**, larger coverage (6114 names), README-endorsed, measured reproducible in **~3 minutes** here |
| **Universe** | **`csi300`** (point-in-time list in the demo window) | Standard A-share large-cap benchmark; ~300-class names; loads in ~10s; NaN rate &lt; 0.2% |
| **Time window** | **2024-07-03 → 2026-07-03** (or any contiguous ~2y ending at calendar last day) | Enough length for noise-factor / DSR-style demos; fully covered by current pack; avoid relying on post-last-day dates |
| **Avoid** | Official `GetData` pack as of this measurement | Ends **2020-09-25** — useless for a “current market” pitch |

### Reproduce on a fresh machine

```bash
# 1. Python env
python3.11 -m venv .venv && source .venv/bin/activate
pip install -U pip pyqlib

# 2. Community China daily pack (canonical for v0.1)
curl -L --fail -o /tmp/qlib_bin.tar.gz \
  "https://github.com/chenditc/investment_data/releases/latest/download/qlib_bin.tar.gz"
mkdir -p ~/.qlib/qlib_data/cn_data
tar -zxvf /tmp/qlib_bin.tar.gz -C ~/.qlib/qlib_data/cn_data --strip-components=1
rm -f /tmp/qlib_bin.tar.gz
du -sh ~/.qlib/qlib_data/cn_data   # expect ~0.8G class

# 3. Smoke
python - <<'PY'
import qlib
from qlib.constant import REG_CN
from qlib.data import D
qlib.init(provider_uri="~/.qlib/qlib_data/cn_data", region=REG_CN, kernels=1)
cal = D.calendar()
print(len(cal), cal[0], cal[-1])
print(len(D.list_instruments(D.instruments("all"), as_list=True)))
df = D.features(D.instruments("csi300"), ["$close", "$volume"],
                start_time="2024-07-03", end_time="2026-07-03")
print(df.shape, float(df["$close"].isna().mean()))
PY
```

Pin a **release tag** (e.g. `2026-07-05`) in CI if bit-for-bit reproducibility matters; `latest` moves.

---

## 5. Open risks

| Risk | Severity | Notes |
| --- | --- | --- |
| **Community mirror availability** | Medium | Depends on GitHub Releases + maintainer Actions. No SLA. Cache `~/.qlib` across machines when possible. |
| **Staleness of “latest”** | Low–Medium today | Pack through **2026-07-03** as of validation day **2026-07-10** (~1 week lag). Monitor release cadence. |
| **Official pack footgun** | High if misused | CLI works but data ends **2020-09-25**. Document must prefer community path. |
| **Field semantics (`$close` vs `$adjclose` vs `$factor`)** | Medium | Adjusted vs cash prices easy to confuse; adapter should pick one convention and unit-test against known names (e.g. SH600519). |
| **Yahoo / multi-source quality** | Medium | Upstream qlib warns Yahoo data “might not be perfect”; community pack merges sources — still not exchange-grade. Fine for statistical **method** demos; not for production PnL claims. |
| **Licensing** | Medium | qlib is MIT. Underlying market data redistribution rights for community dumps are **unclear / not a commercial license**. For public demos, prefer “research / community pack” language; do not claim licensed exchange data. |
| **macOS multiprocessing** | Low | Use `kernels=1` or script-file entrypoints; stdin one-liners can break joblib spawn. |
| **Universe PIT** | Low–Medium | `csi300` file is multi-period; demos must fix a date range when counting names. |

---

## 6. Self-check commands (acceptance)

```bash
test -f docs/research/qlib-cn-data.md          # expect exit 0
test -d ~/.qlib/qlib_data/cn_data              # expect exit 0
```

Measured: both exit **0** after this work.
