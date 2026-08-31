# COVID Disruption Core Engine Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build and fully test the new statistical engine (excess-mortality detection, persistence classification, FDR correction, county heterogeneity regression) and extend CDC WONDER ingestion for multi-cause exports, per `docs/superpowers/specs/2026-08-31-covid-mortality-disruption-design.md`.

**Architecture:** Three new/extended modules form a pipeline: `src/ingestion/cdc_wonder.py` (extended to parse multi-cause exports) → `src/cleaning/bridging.py` (new — quantifies the 1999-2020/2018-2024 database vintage discontinuity) → `src/analysis/excess_mortality.py` (new — fits each cause's pre-pandemic trend, projects it forward, flags significant deviations, classifies persistence) → `src/analysis/heterogeneity.py` (new — regresses county-level disruption magnitude against context variables). Every function operates on plain pandas/numpy inputs so it can be tested against synthetic fixtures now and pointed at real multi-cause WONDER exports later without changing signatures.

**Tech Stack:** Python 3.12, pandas, numpy, scipy.stats (linear regression, t-distribution, prediction intervals), pytest.

## Global Constraints

- Suppressed/unreliable values are never coerced to zero or silently dropped — always preserved as explicit NaN + boolean flag columns (research_protocol.md #8).
- No causal language in code comments, docstrings, or output labels — "associated with," never "caused" (research_protocol.md #11).
- Every new statistical function needs a test against a case with a *known, hand-computable* correct answer, not just "does it run."
- This plan covers the core engine only (ingestion extension + bridging + excess-mortality + heterogeneity modules). App redesign and real-data integration are a separate follow-up plan once real multi-cause WONDER exports exist (spec section 12, open risk).

---

### Task 1: Extend CDC WONDER ingestion for multi-cause exports

**Files:**
- Modify: `src/ingestion/cdc_wonder.py:99-147` (the `load_manual_export` function and its dedup logic)
- Modify: `scripts/run_synthetic_pipeline.py:24` (its call to `load_manual_export()` needs a `cause_label` now)
- Test: `tests/test_cdc_wonder_ingestion.py`

**Interfaces:**
- Consumes: nothing new
- Produces: `load_manual_export(subdir_files=None, cause_label=None) -> WonderLoadResult` where `WonderLoadResult.df` now has a `cause` column. Downstream tasks (bridging, excess_mortality) consume `df["cause"]`, `df["county_fips"]`, `df["year"]`, `df["age_adjusted_rate"]`, `df["age_adjusted_rate_suppressed"]`, `df["age_adjusted_rate_unreliable"]` — all unchanged names, `cause` is new.

Currently `load_manual_export` de-duplicates on `(county_fips, year)` only, which will silently and incorrectly collapse rows once the same county-year appears once per cause in a multi-cause export. It also has no way to label which cause a single-cause file (like the existing diabetes pull) belongs to.

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_cdc_wonder_ingestion.py`:

```python
def test_load_manual_export_requires_cause_label_for_single_cause_file(tmp_path):
    f = _write_fixture(tmp_path, "export1.txt", [
        "Autauga County, AL\t01001\t2010\t12\t54000\t22.2\t21.5",
    ])
    with pytest.raises(ValueError, match="no cause_label was passed"):
        load_manual_export(subdir_files=[f])


def test_load_manual_export_applies_cause_label_to_single_cause_file(tmp_path):
    f = _write_fixture(tmp_path, "export1.txt", [
        "Autauga County, AL\t01001\t2010\t12\t54000\t22.2\t21.5",
    ])
    result = load_manual_export(subdir_files=[f], cause_label="Diabetes mellitus")
    assert (result.df["cause"] == "Diabetes mellitus").all()


def test_load_manual_export_reads_cause_column_from_multi_cause_file(tmp_path):
    header = FIXTURE_HEADER + "\tCause of death"
    lines = [header] + [
        "Autauga County, AL\t01001\t2010\t12\t54000\t22.2\t21.5\tDiabetes mellitus (E10-E14)",
        "Autauga County, AL\t01001\t2010\t45\t54000\t83.3\t80.1\tDiseases of heart (I00-I09,I11,I13,I20-I51)",
    ]
    path = tmp_path / "multi_cause.txt"
    path.write_text("\n".join(lines + ["---", '"Total"']))
    result = load_manual_export(subdir_files=[path])
    assert set(result.df["cause"]) == {
        "Diabetes mellitus (E10-E14)",
        "Diseases of heart (I00-I09,I11,I13,I20-I51)",
    }
    assert len(result.df) == 2  # same county+year, different cause -> not deduped away


def test_load_manual_export_rejects_cause_label_when_file_has_own_column(tmp_path):
    header = FIXTURE_HEADER + "\tCause of death"
    lines = [header, "Autauga County, AL\t01001\t2010\t12\t54000\t22.2\t21.5\tDiabetes mellitus (E10-E14)"]
    path = tmp_path / "multi_cause.txt"
    path.write_text("\n".join(lines + ["---", '"Total"']))
    with pytest.raises(ValueError, match="cause_label"):
        load_manual_export(subdir_files=[path], cause_label="Diabetes mellitus")


def test_load_manual_export_dedup_key_includes_cause(tmp_path):
    header = FIXTURE_HEADER + "\tCause of death"
    lines = [header] + [
        "Autauga County, AL\t01001\t2010\t12\t54000\t22.2\t21.5\tDiabetes mellitus (E10-E14)",
        "Autauga County, AL\t01001\t2010\t12\t54000\t22.2\t21.5\tDiabetes mellitus (E10-E14)",
    ]
    path = tmp_path / "dup.txt"
    path.write_text("\n".join(lines + ["---", '"Total"']))
    with pytest.raises(ValueError, match="Duplicate"):
        load_manual_export(subdir_files=[path])
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/aidan/Desktop/covid-mortality-disruption-lab && source .venv/bin/activate && python -m pytest tests/test_cdc_wonder_ingestion.py -k "cause" -v`
Expected: 5 failures — `load_manual_export() got an unexpected keyword argument 'cause_label'` (or similar TypeError), since the parameter doesn't exist yet.

- [ ] **Step 3: Implement `cause_label` support and fix the dedup key**

Replace `src/ingestion/cdc_wonder.py:99-147` with:

```python
def load_manual_export(
    subdir_files: list[Path] | None = None, cause_label: str | None = None
) -> WonderLoadResult:
    """Load one or more manually-exported WONDER files (see
    docs/manual_data_acquisition.md), concatenate, de-duplicate on
    (county_code, year, cause), and standardize suppression/unreliability
    flags.

    `cause_label`: required for single-cause exports that have no
    "Cause of death" column of their own (e.g. the original diabetes-only
    pull) — every row is labeled with this string. Must be left as None
    for multi-cause exports, which carry their own "Cause of death"
    column instead; passing both raises, since only one source of truth
    for `cause` is allowed per file.

    Raw suppressed/unreliable cells are NEVER coerced to zero or dropped —
    they are preserved as explicit boolean flag columns alongside a NaN rate,
    per research_protocol.md #8.
    """
    files = sorted(CDC_WONDER_RAW_DIR.glob("*.txt")) if subdir_files is None else subdir_files
    if not files:
        raise FileNotFoundError(
            f"No WONDER export files found in {CDC_WONDER_RAW_DIR}. "
            "Follow docs/manual_data_acquisition.md to produce them first."
        )

    frames = []
    for f in files:
        df = _read_wonder_export(f)
        _validate_columns(df, f)
        if "Cause of death" in df.columns:
            if cause_label is not None:
                raise ValueError(
                    f"{f}: this file has its own 'Cause of death' column, but "
                    f"cause_label={cause_label!r} was also passed. Pass cause_label "
                    "only for single-cause exports that lack that column."
                )
            df = df.rename(columns={"Cause of death": "cause"})
        else:
            if cause_label is None:
                raise ValueError(
                    f"{f}: this file has no 'Cause of death' column and no "
                    "cause_label was passed. Single-cause exports (like the "
                    "original diabetes pull) must specify cause_label explicitly, "
                    "e.g. load_manual_export(cause_label='Diabetes mellitus')."
                )
            df["cause"] = cause_label
        df["_source_file"] = f.name
        frames.append(df)

    combined = pd.concat(frames, ignore_index=True)
    combined = combined.rename(columns={v: k for k, v in EXPECTED_COLUMNS.items()})

    combined["county_fips"] = combined["county_code"].astype(str).str.zfill(5)

    for col in ("deaths", "crude_rate", "age_adjusted_rate"):
        raw_col = combined[col].astype(str)
        combined[f"{col}_suppressed"] = raw_col.isin(SUPPRESSED_TOKENS)
        combined[f"{col}_unreliable"] = raw_col.isin(UNRELIABLE_TOKENS)
        combined[col] = pd.to_numeric(combined[col], errors="coerce")

    before = len(combined)
    combined = combined.drop_duplicates(subset=["county_fips", "year", "cause"], keep="first")
    if len(combined) != before:
        raise ValueError(
            f"Duplicate (county_fips, year, cause) rows found across {[f.name for f in files]} "
            "after concatenation — check for overlapping year ranges between exports."
        )

    return WonderLoadResult(
        df=combined,
        source_files=files,
        n_rows=len(combined),
        n_suppressed=int(combined["deaths_suppressed"].sum()),
        n_unreliable=int(combined["age_adjusted_rate_unreliable"].sum()),
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_cdc_wonder_ingestion.py -v`
Expected: all tests PASS, including the pre-existing ones (they call `load_manual_export` without `cause_label` on single-cause fixtures — check each pre-existing test fixture and add `cause_label="Diabetes mellitus"` to any call that doesn't already have a "Cause of death" column; the 7 pre-existing tests in this file all use single-cause fixtures via `_write_fixture`, so update each call site: `load_manual_export(subdir_files=[f])` → `load_manual_export(subdir_files=[f], cause_label="Diabetes mellitus")` throughout `tests/test_cdc_wonder_ingestion.py`).

- [ ] **Step 5: Fix the now-broken caller in the orchestration script**

Modify `scripts/run_synthetic_pipeline.py:24`:

```python
# before:
    mortality = load_manual_export()
# after:
    mortality = load_manual_export(cause_label="Diabetes mellitus")
```

- [ ] **Step 6: Run the full test suite**

Run: `python -m pytest tests/ -v`
Expected: all tests PASS (should be 54 pre-existing + 5 new = 59, all green).

- [ ] **Step 7: Commit**

```bash
git add src/ingestion/cdc_wonder.py scripts/run_synthetic_pipeline.py tests/test_cdc_wonder_ingestion.py
git commit -m "feat: support multi-cause WONDER exports in cdc_wonder ingestion

Adds cause_label parameter for single-cause files and reads a native
'Cause of death' column for multi-cause files. Dedup key extended from
(county_fips, year) to (county_fips, year, cause) to avoid silently
collapsing distinct causes sharing a county-year."
```

---

### Task 2: Vintage discontinuity calibration (`src/cleaning/bridging.py`)

**Files:**
- Create: `src/cleaning/bridging.py`
- Test: `tests/test_bridging.py`

**Interfaces:**
- Consumes: two `pd.DataFrame`s shaped like `WonderLoadResult.df` (from Task 1), one from each database vintage
- Produces: `estimate_vintage_offset(old_df, new_df, overlap_years, value_col="age_adjusted_rate", group_cols=None) -> pd.DataFrame` (one row per overlap year × group, with an `offset` column) and `is_bridging_reliable(offset_df, value_col="age_adjusted_rate", max_relative_offset=0.10) -> bool`. Task 3's excess-mortality module does not directly call these (baseline fitting only uses the old vintage), but the orchestration script (future task, not in this plan) will call `is_bridging_reliable` and surface a warning per spec section 9 if it returns `False`.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_bridging.py`:

```python
import pandas as pd
import pytest

from src.cleaning.bridging import estimate_vintage_offset, is_bridging_reliable


def _panel(rows):
    return pd.DataFrame(rows, columns=["county_fips", "year", "age_adjusted_rate"])


def test_estimate_vintage_offset_computes_difference_per_overlap_year():
    old_df = _panel([
        ("01001", 2018, 20.0),
        ("01001", 2019, 21.0),
        ("01001", 2020, 22.0),
    ])
    new_df = _panel([
        ("01001", 2018, 21.0),
        ("01001", 2019, 22.5),
        ("01001", 2020, 23.0),
    ])
    result = estimate_vintage_offset(old_df, new_df, overlap_years=[2018, 2019, 2020], group_cols=["county_fips"])
    assert len(result) == 3
    row_2019 = result[result["year"] == 2019].iloc[0]
    assert row_2019["offset"] == pytest.approx(1.5)


def test_estimate_vintage_offset_only_includes_overlap_years():
    old_df = _panel([("01001", 2017, 19.0), ("01001", 2018, 20.0)])
    new_df = _panel([("01001", 2018, 20.5), ("01001", 2021, 25.0)])
    result = estimate_vintage_offset(old_df, new_df, overlap_years=[2018], group_cols=["county_fips"])
    assert list(result["year"]) == [2018]


def test_is_bridging_reliable_true_for_small_offset():
    offset_df = pd.DataFrame({
        "county_fips": ["01001", "01001"],
        "year": [2018, 2019],
        "age_adjusted_rate_old": [20.0, 21.0],
        "age_adjusted_rate_new": [20.5, 21.4],
        "offset": [0.5, 0.4],
    })
    assert is_bridging_reliable(offset_df) is True


def test_is_bridging_reliable_false_for_large_offset():
    offset_df = pd.DataFrame({
        "county_fips": ["01001", "01001"],
        "year": [2018, 2019],
        "age_adjusted_rate_old": [20.0, 21.0],
        "age_adjusted_rate_new": [26.0, 27.0],
        "offset": [6.0, 6.0],
    })
    assert is_bridging_reliable(offset_df) is False
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_bridging.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'src.cleaning.bridging'`

- [ ] **Step 3: Implement `src/cleaning/bridging.py`**

```python
"""Quantifies the discontinuity between CDC WONDER's two mortality-data
vintages (1999-2020 bridged-race vs. 2018-2024 single-race — see
DATA_SOURCES.md #1-2) using the 2018-2020 years present in both, per
docs/superpowers/specs/2026-08-31-covid-mortality-disruption-design.md
section 4. This does NOT correct or adjust the data — it only measures
the size of the jump, so the orchestration pipeline can decide whether
treating 2020-2024 as continuous with the pre-2020 baseline trend is
defensible (spec section 9: a large offset must be surfaced explicitly,
not silently absorbed into the trend fit).
"""
from __future__ import annotations

import pandas as pd


def estimate_vintage_offset(
    old_df: pd.DataFrame,
    new_df: pd.DataFrame,
    overlap_years: list[int],
    value_col: str = "age_adjusted_rate",
    group_cols: list[str] | None = None,
) -> pd.DataFrame:
    group_cols = group_cols or []
    merge_cols = ["year"] + group_cols

    old_overlap = old_df[old_df["year"].isin(overlap_years)][merge_cols + [value_col]]
    new_overlap = new_df[new_df["year"].isin(overlap_years)][merge_cols + [value_col]]

    merged = old_overlap.merge(new_overlap, on=merge_cols, suffixes=("_old", "_new"))
    merged["offset"] = merged[f"{value_col}_new"] - merged[f"{value_col}_old"]
    return merged


def is_bridging_reliable(
    offset_df: pd.DataFrame,
    value_col: str = "age_adjusted_rate",
    max_relative_offset: float = 0.10,
) -> bool:
    """False if the median |offset| relative to the old-vintage value
    exceeds max_relative_offset (10% by default) — i.e. the database
    switch itself moves the series by more than a defensible margin."""
    old_col = f"{value_col}_old"
    relative = (offset_df["offset"] / offset_df[old_col]).abs()
    return bool(relative.median() <= max_relative_offset)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_bridging.py -v`
Expected: all 4 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/cleaning/bridging.py tests/test_bridging.py
git commit -m "feat: add vintage discontinuity calibration module

Measures the size of the jump between CDC WONDER's two mortality
database vintages using their 2018-2020 overlap years, per design
spec section 4. Does not correct the data -- only measures the jump
so it can be surfaced rather than silently absorbed."
```

---

### Task 3: Baseline trend fitting (`src/analysis/excess_mortality.py`, part 1)

**Files:**
- Create: `src/analysis/excess_mortality.py`
- Test: `tests/test_excess_mortality.py`

**Interfaces:**
- Consumes: `years: np.ndarray`, `values: np.ndarray` (a single cause/geography series)
- Produces: `BaselineTrend` dataclass with fields `slope: float`, `intercept: float`, `residual_std: float`, `n: int`, `x_mean: float`, `sxx: float` — consumed directly by Task 4's `compute_deviations`.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_excess_mortality.py`:

```python
import numpy as np
import pytest

from src.analysis.excess_mortality import fit_baseline_trend


def test_fit_baseline_trend_recovers_known_linear_relationship():
    years = np.arange(1999, 2020)
    values = 2.0 + 0.5 * (years - 1999)  # exact linear, no noise
    trend = fit_baseline_trend(years, values)
    assert trend.slope == pytest.approx(0.5, abs=1e-9)
    assert trend.intercept == pytest.approx(2.0 - 0.5 * 1999, abs=1e-6)
    assert trend.residual_std == pytest.approx(0.0, abs=1e-9)
    assert trend.n == 21


def test_fit_baseline_trend_ignores_nan_values():
    years = np.arange(1999, 2010)
    values = 2.0 + 0.5 * (years - 1999)
    values = values.astype(float)
    values[3] = np.nan  # a suppressed year
    trend = fit_baseline_trend(years, values)
    assert trend.n == 10
    assert trend.slope == pytest.approx(0.5, abs=1e-9)


def test_fit_baseline_trend_raises_with_too_few_points():
    years = np.array([2018, 2019])
    values = np.array([20.0, 21.0])
    with pytest.raises(ValueError, match="at least 3"):
        fit_baseline_trend(years, values)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_excess_mortality.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'src.analysis.excess_mortality'`

- [ ] **Step 3: Implement `fit_baseline_trend`**

Create `src/analysis/excess_mortality.py`:

```python
"""Known-date interrupted time series ("excess mortality") analysis, per
docs/superpowers/specs/2026-08-31-covid-mortality-disruption-design.md
sections 5.1, 5.2, and 5.5. The breakpoint (pandemic onset, 2020) is
fixed by the shock's known date, not searched for -- this is a more
defensible-against-p-hacking variant of the algorithmic breakpoint
search in src/analysis/changepoints.py, which is reused separately as
an independent cross-check (spec section 5.3), not as the primary method
here.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy import stats


@dataclass
class BaselineTrend:
    slope: float
    intercept: float
    residual_std: float
    n: int
    x_mean: float
    sxx: float  # sum((x - x_mean)^2) -- needed for prediction-interval width


def fit_baseline_trend(years: np.ndarray, values: np.ndarray) -> BaselineTrend:
    """Fit an OLS linear trend on baseline (pre-shock) years only.
    NaN values (suppressed/unreliable years) are dropped before fitting,
    never coerced to zero, per research_protocol.md #8."""
    years = np.asarray(years, dtype=float)
    values = np.asarray(values, dtype=float)
    mask = ~np.isnan(values)
    years, values = years[mask], values[mask]

    n = len(years)
    if n < 3:
        raise ValueError(f"Need at least 3 non-missing baseline years to fit a trend, got {n}.")

    slope, intercept = np.polyfit(years, values, 1)
    resid = values - (slope * years + intercept)
    residual_std = float(np.sqrt(np.sum(resid**2) / (n - 2)))
    x_mean = float(years.mean())
    sxx = float(np.sum((years - x_mean) ** 2))

    return BaselineTrend(
        slope=float(slope), intercept=float(intercept),
        residual_std=residual_std, n=n, x_mean=x_mean, sxx=sxx,
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_excess_mortality.py -v`
Expected: all 3 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/analysis/excess_mortality.py tests/test_excess_mortality.py
git commit -m "feat: add baseline trend fitting for excess-mortality analysis"
```

---

### Task 4: Deviation detection with prediction intervals

**Files:**
- Modify: `src/analysis/excess_mortality.py` (add after `fit_baseline_trend`)
- Test: `tests/test_excess_mortality.py` (add to existing file)

**Interfaces:**
- Consumes: `BaselineTrend` (from Task 3), `years: np.ndarray`, `observed: np.ndarray`, `alpha: float = 0.05`
- Produces: `list[DeviationResult]`, each with `year: int`, `observed: float`, `expected: float`, `deviation: float`, `pi_low: float`, `pi_high: float`, `significant: bool`. Consumed by Task 5's `classify_persistence`.

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_excess_mortality.py`:

```python
from src.analysis.excess_mortality import compute_deviations


def test_compute_deviations_flat_trend_no_shock_not_significant():
    years = np.arange(1999, 2020)
    values = np.full(21, 20.0)  # perfectly flat, zero residual
    trend = fit_baseline_trend(years, values)
    # projecting forward with a tiny residual_std of 0 would divide by
    # zero in the SE formula, so use a trend with slight noise instead
    values_noisy = 20.0 + np.array([0.1, -0.1, 0.05, -0.05, 0.0] * 4 + [0.02])
    trend = fit_baseline_trend(years, values_noisy)
    result = compute_deviations(trend, np.array([2020]), np.array([20.05]))
    assert result[0].significant is False


def test_compute_deviations_detects_large_upward_shock():
    years = np.arange(1999, 2020)
    values = 20.0 + np.array([0.1, -0.1, 0.05, -0.05, 0.0] * 4 + [0.02])
    trend = fit_baseline_trend(years, values)
    result = compute_deviations(trend, np.array([2020]), np.array([35.0]))
    assert result[0].significant is True
    assert result[0].deviation == pytest.approx(35.0 - result[0].expected)


def test_compute_deviations_handles_nan_observed_as_not_significant():
    years = np.arange(1999, 2020)
    values = 20.0 + np.array([0.1, -0.1, 0.05, -0.05, 0.0] * 4 + [0.02])
    trend = fit_baseline_trend(years, values)
    result = compute_deviations(trend, np.array([2020]), np.array([np.nan]))
    assert result[0].significant is False
    assert np.isnan(result[0].observed)


def test_compute_deviations_prediction_interval_widens_with_extrapolation_distance():
    years = np.arange(1999, 2020)
    values = 20.0 + np.array([0.1, -0.1, 0.05, -0.05, 0.0] * 4 + [0.02])
    trend = fit_baseline_trend(years, values)
    near = compute_deviations(trend, np.array([2020]), np.array([20.0]))[0]
    far = compute_deviations(trend, np.array([2050]), np.array([20.0]))[0]
    near_width = near.pi_high - near.pi_low
    far_width = far.pi_high - far.pi_low
    assert far_width > near_width
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_excess_mortality.py -k compute_deviations -v`
Expected: FAIL with `ImportError: cannot import name 'compute_deviations'`

- [ ] **Step 3: Implement `compute_deviations`**

Append to `src/analysis/excess_mortality.py`:

```python
@dataclass
class DeviationResult:
    year: int
    observed: float
    expected: float
    deviation: float
    pi_low: float
    pi_high: float
    significant: bool


def compute_deviations(
    trend: BaselineTrend, years: np.ndarray, observed: np.ndarray, alpha: float = 0.05
) -> list[DeviationResult]:
    """Project the baseline trend forward to each post-period year and
    test whether the observed value falls outside its prediction
    interval. Uses the standard OLS prediction-interval formula:
    SE_pred(x0) = residual_std * sqrt(1 + 1/n + (x0 - x_mean)^2 / Sxx),
    so the interval widens the further a year is extrapolated from the
    baseline period -- this is standard, not something invented for this
    project."""
    t_crit = stats.t.ppf(1 - alpha / 2, df=trend.n - 2)
    results = []
    for year, obs in zip(years, observed):
        expected = trend.slope * year + trend.intercept
        se_pred = trend.residual_std * np.sqrt(
            1 + 1 / trend.n + (year - trend.x_mean) ** 2 / trend.sxx
        )
        margin = t_crit * se_pred
        pi_low, pi_high = expected - margin, expected + margin

        obs_is_nan = np.isnan(obs)
        deviation = np.nan if obs_is_nan else float(obs - expected)
        significant = False if obs_is_nan else not (pi_low <= obs <= pi_high)

        results.append(DeviationResult(
            year=int(year),
            observed=float(obs) if not obs_is_nan else np.nan,
            expected=float(expected),
            deviation=deviation,
            pi_low=float(pi_low),
            pi_high=float(pi_high),
            significant=bool(significant),
        ))
    return results
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_excess_mortality.py -v`
Expected: all tests PASS (3 from Task 3 + 4 new = 7)

- [ ] **Step 5: Commit**

```bash
git add src/analysis/excess_mortality.py tests/test_excess_mortality.py
git commit -m "feat: add prediction-interval deviation detection to excess_mortality"
```

---

### Task 5: Three-way persistence classification

**Files:**
- Modify: `src/analysis/excess_mortality.py` (add after `compute_deviations`)
- Test: `tests/test_excess_mortality.py`

**Interfaces:**
- Consumes: `deviations: list[DeviationResult]` (from Task 4), `acute_years: tuple[int, int]`, `post_acute_years: tuple[int, int]`
- Produces: `str`, one of `"No significant disruption"`, `"Persisted"`, `"Resolved"`, `"Reversed"` — consumed by the (future, out of this plan's scope) orchestration script and app.

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_excess_mortality.py`:

```python
from src.analysis.excess_mortality import DeviationResult, classify_persistence


def _dev(year, deviation, significant):
    return DeviationResult(
        year=year, observed=20.0 + deviation, expected=20.0, deviation=deviation,
        pi_low=19.0, pi_high=21.0, significant=significant,
    )


def test_classify_persistence_no_significant_acute_disruption():
    deviations = [_dev(2020, 0.1, False), _dev(2021, -0.2, False), _dev(2022, 0.0, False)]
    result = classify_persistence(deviations, acute_years=(2020, 2021), post_acute_years=(2022, 2024))
    assert result == "No significant disruption"


def test_classify_persistence_persisted_same_direction():
    deviations = [
        _dev(2020, 5.0, True), _dev(2021, 6.0, True),
        _dev(2022, 4.0, True), _dev(2023, 4.5, True), _dev(2024, 5.0, True),
    ]
    result = classify_persistence(deviations, acute_years=(2020, 2021), post_acute_years=(2022, 2024))
    assert result == "Persisted"


def test_classify_persistence_resolved_when_post_acute_not_significant():
    deviations = [
        _dev(2020, 5.0, True), _dev(2021, 6.0, True),
        _dev(2022, 0.1, False), _dev(2023, -0.1, False), _dev(2024, 0.05, False),
    ]
    result = classify_persistence(deviations, acute_years=(2020, 2021), post_acute_years=(2022, 2024))
    assert result == "Resolved"


def test_classify_persistence_reversed_when_sign_flips():
    deviations = [
        _dev(2020, 8.0, True), _dev(2021, 9.0, True),
        _dev(2022, -6.0, True), _dev(2023, -7.0, True), _dev(2024, -5.0, True),
    ]
    result = classify_persistence(deviations, acute_years=(2020, 2021), post_acute_years=(2022, 2024))
    assert result == "Reversed"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_excess_mortality.py -k persistence -v`
Expected: FAIL with `ImportError: cannot import name 'classify_persistence'`

- [ ] **Step 3: Implement `classify_persistence`**

Append to `src/analysis/excess_mortality.py`:

```python
def classify_persistence(
    deviations: list[DeviationResult], acute_years: tuple[int, int], post_acute_years: tuple[int, int]
) -> str:
    """Three-way persistence classification per design spec section 5.2:
    "Persisted", "Resolved", or "Reversed" for causes with a significant
    acute-phase (2020-2021) disruption; "No significant disruption" if
    the acute phase itself never cleared significance. A binary
    persisted/resolved scheme would flatten a reversal pattern (e.g.
    overdose spiking, then declining below its pre-pandemic trend) into
    a false "resolved," which is why this is three-way, not two."""
    acute = [d for d in deviations if acute_years[0] <= d.year <= acute_years[1]]
    post_acute = [d for d in deviations if post_acute_years[0] <= d.year <= post_acute_years[1]]

    acute_significant = [d for d in acute if d.significant]
    if not acute_significant:
        return "No significant disruption"

    acute_sign = np.sign(np.mean([d.deviation for d in acute_significant]))

    post_significant = [d for d in post_acute if d.significant]
    if not post_significant:
        return "Resolved"

    post_sign = np.sign(np.mean([d.deviation for d in post_significant]))
    return "Persisted" if post_sign == acute_sign else "Reversed"
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_excess_mortality.py -v`
Expected: all tests PASS (7 from Tasks 3-4 + 4 new = 11)

- [ ] **Step 5: Commit**

```bash
git add src/analysis/excess_mortality.py tests/test_excess_mortality.py
git commit -m "feat: add three-way persistence classification (persisted/resolved/reversed)"
```

---

### Task 6: Benjamini-Hochberg FDR correction

**Files:**
- Modify: `src/analysis/excess_mortality.py` (add after `classify_persistence`)
- Test: `tests/test_excess_mortality.py`

**Interfaces:**
- Consumes: `p_values: dict[str, float]`, `alpha: float = 0.05`
- Produces: `dict[str, bool]` (same keys, True = survives FDR correction) — consumed by the (future) orchestration script for the 6-cause family test (spec section 5.5) and by Task 7's heterogeneity module for the context-variable family test.

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_excess_mortality.py`:

```python
from src.analysis.excess_mortality import benjamini_hochberg


def test_benjamini_hochberg_known_worked_example():
    # Hand-computed: alpha=0.05, m=5. BH critical value at rank k is
    # (k/5)*0.05 = 0.01, 0.02, 0.03, 0.04, 0.05 for ranks 1-5.
    # sorted p: a=.001<=.01 ok, b=.01<=.02 ok, c=.03<=.03 ok, d=.04<=.04 ok, e=.5<=.05 fails
    # -> a,b,c,d survive; e does not.
    p_values = {"a": 0.001, "b": 0.01, "c": 0.03, "d": 0.04, "e": 0.5}
    result = benjamini_hochberg(p_values, alpha=0.05)
    assert result == {"a": True, "b": True, "c": True, "d": True, "e": False}


def test_benjamini_hochberg_all_survive_when_all_tiny():
    p_values = {"a": 0.0001, "b": 0.0002, "c": 0.0003}
    result = benjamini_hochberg(p_values, alpha=0.05)
    assert all(result.values())


def test_benjamini_hochberg_none_survive_when_all_large():
    p_values = {"a": 0.9, "b": 0.8, "c": 0.95}
    result = benjamini_hochberg(p_values, alpha=0.05)
    assert not any(result.values())


def test_benjamini_hochberg_returns_all_original_keys():
    p_values = {"cancer": 0.3, "overdose": 0.001}
    result = benjamini_hochberg(p_values)
    assert set(result.keys()) == {"cancer", "overdose"}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_excess_mortality.py -k benjamini -v`
Expected: FAIL with `ImportError: cannot import name 'benjamini_hochberg'`

- [ ] **Step 3: Implement `benjamini_hochberg`**

Append to `src/analysis/excess_mortality.py`:

```python
def benjamini_hochberg(p_values: dict[str, float], alpha: float = 0.05) -> dict[str, bool]:
    """Standard Benjamini-Hochberg step-up FDR procedure. Sort p-values
    ascending; find the largest rank k where p(k) <= (k/m)*alpha; every
    p-value at or below that rank survives correction. Per design spec
    section 5.5, applied across the 6 substantive test causes (excluding
    the COVID-19 reference series and the drowning negative control)."""
    items = sorted(p_values.items(), key=lambda kv: kv[1])
    m = len(items)

    max_rank_significant = 0
    for rank, (_, p) in enumerate(items, start=1):
        if p <= (rank / m) * alpha:
            max_rank_significant = rank

    survives = {}
    for rank, (key, _) in enumerate(items, start=1):
        survives[key] = rank <= max_rank_significant
    return survives
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_excess_mortality.py -v`
Expected: all tests PASS (11 from Tasks 3-5 + 4 new = 15)

- [ ] **Step 5: Commit**

```bash
git add src/analysis/excess_mortality.py tests/test_excess_mortality.py
git commit -m "feat: add Benjamini-Hochberg FDR correction for multi-cause testing"
```

---

### Task 7: County-level heterogeneity analysis

**Files:**
- Create: `src/analysis/heterogeneity.py`
- Test: `tests/test_heterogeneity.py`

**Interfaces:**
- Consumes: `pre_period: pd.DataFrame`, `post_period: pd.DataFrame` (each with `county_fips` and a value column), `context_df: pd.DataFrame` (with `county_fips` and context variable columns), `context_vars: list[str]`
- Produces: `compute_county_disruption(...) -> pd.DataFrame` (one row per county, with a `disruption` column) and `regress_disruption_on_context(...) -> pd.DataFrame` (one row per context variable, with `slope`, `p_value`, `n`). The `p_value` column feeds directly into Task 6's `benjamini_hochberg` (keyed by variable name) — this module does not call it itself, the caller does, matching the existing heterogeneity design in `docs/research_protocol.md` where FDR correction is applied by whatever orchestrates the full family of comparisons.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_heterogeneity.py`:

```python
import numpy as np
import pandas as pd
import pytest

from src.analysis.heterogeneity import compute_county_disruption, regress_disruption_on_context


def test_compute_county_disruption_computes_difference_correctly():
    pre = pd.DataFrame({
        "county_fips": ["01001", "01001", "01003", "01003"],
        "year": [2018, 2019, 2018, 2019],
        "age_adjusted_rate": [20.0, 20.0, 30.0, 30.0],
    })
    post = pd.DataFrame({
        "county_fips": ["01001", "01001", "01003", "01003"],
        "year": [2020, 2021, 2020, 2021],
        "age_adjusted_rate": [25.0, 25.0, 30.0, 32.0],
    })
    result = compute_county_disruption(pre, post)
    row_01001 = result[result["county_fips"] == "01001"].iloc[0]
    assert row_01001["disruption"] == pytest.approx(5.0)
    row_01003 = result[result["county_fips"] == "01003"].iloc[0]
    assert row_01003["disruption"] == pytest.approx(1.0)


def test_compute_county_disruption_excludes_insufficient_years():
    pre = pd.DataFrame({
        "county_fips": ["01001"], "year": [2019], "age_adjusted_rate": [20.0],
    })
    post = pd.DataFrame({
        "county_fips": ["01001", "01001"], "year": [2020, 2021], "age_adjusted_rate": [25.0, 26.0],
    })
    result = compute_county_disruption(pre, post, min_years_each_period=2)
    assert len(result) == 0  # only 1 pre-period year, below the minimum


def test_regress_disruption_on_context_detects_known_linear_relationship():
    rng = np.random.default_rng(0)
    counties = [f"{i:05d}" for i in range(100)]
    poverty = rng.uniform(5, 30, size=100)
    disruption = 2.0 * poverty + rng.normal(0, 0.5, size=100)  # true slope = 2.0, low noise

    disruption_df = pd.DataFrame({"county_fips": counties, "disruption": disruption})
    context_df = pd.DataFrame({"county_fips": counties, "poverty_rate": poverty})

    result = regress_disruption_on_context(disruption_df, context_df, context_vars=["poverty_rate"])
    row = result[result["variable"] == "poverty_rate"].iloc[0]
    assert row["slope"] == pytest.approx(2.0, abs=0.1)
    assert row["p_value"] < 0.001
    assert row["n"] == 100


def test_regress_disruption_on_context_handles_missing_variable_data():
    disruption_df = pd.DataFrame({"county_fips": ["01001", "01003"], "disruption": [1.0, 2.0]})
    context_df = pd.DataFrame({"county_fips": ["01001", "01003"], "poverty_rate": [15.0, np.nan]})
    result = regress_disruption_on_context(disruption_df, context_df, context_vars=["poverty_rate"])
    assert result.iloc[0]["n"] == 1


def test_regress_disruption_on_context_flags_too_small_sample():
    disruption_df = pd.DataFrame({"county_fips": ["01001", "01003"], "disruption": [1.0, 2.0]})
    context_df = pd.DataFrame({"county_fips": ["01001", "01003"], "poverty_rate": [15.0, 18.0]})
    result = regress_disruption_on_context(disruption_df, context_df, context_vars=["poverty_rate"])
    row = result.iloc[0]
    assert np.isnan(row["slope"])
    assert np.isnan(row["p_value"])
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_heterogeneity.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'src.analysis.heterogeneity'`

- [ ] **Step 3: Implement `src/analysis/heterogeneity.py`**

```python
"""County-level heterogeneity analysis: does COVID-era mortality
disruption magnitude correlate with socioeconomic/healthcare-access
context variables? Per design spec section 5.7. Associational only --
see docs/research_protocol.md's causal-language policy; nothing here
establishes that a context variable caused a difference in disruption.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats

MIN_SAMPLE_SIZE = 10


def compute_county_disruption(
    pre_period: pd.DataFrame,
    post_period: pd.DataFrame,
    value_col: str = "age_adjusted_rate",
    min_years_each_period: int = 2,
) -> pd.DataFrame:
    """Per county: mean rate in pre_period vs. post_period, and their
    difference. Only counties with at least min_years_each_period
    non-missing observations in EACH period are included -- this manages
    suppression rather than letting a single noisy year drive the
    comparison (research_protocol.md #6 applies the same discipline to
    the primary change-point eligibility criteria)."""

    def summarize(df: pd.DataFrame, suffix: str) -> pd.DataFrame:
        g = df.groupby("county_fips")[value_col].agg(["mean", "count"])
        g.columns = [f"{value_col}_{suffix}", f"n_years_{suffix}"]
        return g

    pre = summarize(pre_period, "pre")
    post = summarize(post_period, "post")
    merged = pre.join(post, how="inner").reset_index()

    merged = merged[
        (merged["n_years_pre"] >= min_years_each_period)
        & (merged["n_years_post"] >= min_years_each_period)
    ].copy()

    merged["disruption"] = merged[f"{value_col}_post"] - merged[f"{value_col}_pre"]
    return merged


def regress_disruption_on_context(
    disruption_df: pd.DataFrame, context_df: pd.DataFrame, context_vars: list[str]
) -> pd.DataFrame:
    """Bivariate OLS of disruption magnitude on each context variable in
    turn (one row per variable): slope, p-value, sample size. FDR
    correction across context_vars is the caller's responsibility, via
    src.analysis.excess_mortality.benjamini_hochberg keyed by variable
    name -- this function does not apply it itself, matching how the
    6-cause disruption tests are corrected separately in the
    orchestration layer (design spec section 5.5)."""
    merged = disruption_df.merge(context_df, on="county_fips", how="inner")

    rows = []
    for var in context_vars:
        sub = merged[["disruption", var]].dropna()
        if len(sub) < MIN_SAMPLE_SIZE:
            rows.append({"variable": var, "slope": np.nan, "p_value": np.nan, "n": len(sub)})
            continue
        slope, intercept, r, p, se = stats.linregress(sub[var], sub["disruption"])
        rows.append({"variable": var, "slope": slope, "p_value": p, "n": len(sub)})

    return pd.DataFrame(rows)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_heterogeneity.py -v`
Expected: all 5 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/analysis/heterogeneity.py tests/test_heterogeneity.py
git commit -m "feat: add county-level heterogeneity regression module"
```

---

### Task 8: Rewrite `docs/research_protocol.md` for the multi-cause design

**Files:**
- Modify: `docs/research_protocol.md` (full rewrite of sections 3, 5, 6, 7, 13; sections 1, 2, 4, 9, 10, 11, 12, 14 are retitled/adjusted, not fully rewritten)

**Interfaces:** none (documentation only)

This task has no test cycle in the traditional sense; its "test" is the completion checklist in Step 2.

- [ ] **Step 1: Rewrite the protocol**

Replace the following sections of `docs/research_protocol.md` (keep the file's existing `## Addenda` section at the end, appending rather than replacing it):

- **§1 Research question** → the question from spec section 1 (verbatim).
- **§2 Hypotheses** → the pre-registered hypotheses table from spec section 3 (verbatim), plus H1/H2/H3 restated as: H1 — at least one of the 6 test causes shows a statistically significant 2020-2021 deviation from its expected trend; H2 — the pattern of significant deviations is not uniform across causes (some persist, some resolve, some reverse); H3 — county-level disruption magnitude for causes with significant deviations is associated with socioeconomic/healthcare-access variables (associational, not causal).
- **§3 Primary outcome** → each of the 6 test causes' age-adjusted rate (per spec section 3's ICD-10 codes), plus the COVID-19 reference series and the drowning negative control, all computed the same way CDC WONDER already provides them.
- **§5 Temporal scope** → baseline 1999-2019 (D76), post-shock 2020-2024 (D158), bridged via the 2018-2020 overlap (spec section 4) — replace the old primary/extension-window language entirely.
- **§6 Inclusion/exclusion criteria** → national and state level for the core disruption/persistence analysis (no county-level eligibility gate needed there, since national/state figures are far less suppression-prone); county level only for heterogeneity, gated by `min_years_each_period` per `src/analysis/heterogeneity.py`'s `compute_county_disruption` (Task 7), not the old `MIN_NONSUPPRESSED_YEARS`/`MIN_COUNTY_POPULATION` single-disease thresholds.
- **§7 Primary statistical methods** → replace with spec section 5.1-5.4 (known-date ITS, three-way persistence classification, PELT/binseg cross-check, negative control) verbatim.
- **§13 Placebo/negative control** → replace with spec section 5.4 (drowning, W65-W74) verbatim; this replaces the old accidental-injury placebo design entirely, since it's now a first-class part of the primary methodology rather than a separate robustness check.
- Add a new **§7a Multiple-testing strategy for cause-of-death family** citing spec section 5.5 (BH correction across the 6 test causes), distinct from the existing heterogeneity-stage FDR correction already described in the original §10.

- [ ] **Step 2: Verify completeness**

Confirm, by reading the rewritten file front to back, that:
- [ ] Every ICD-10 code in the pre-registered hypotheses table matches spec section 3 exactly
- [ ] No remaining references to "diabetes" as the sole outcome (search: `grep -in diabetes docs/research_protocol.md` should only return hits inside the pre-registered hypotheses table, not in the general framing)
- [ ] The causal-language policy section is unchanged (still bans "cause/led to/resulted in")

Run: `grep -in diabetes docs/research_protocol.md`
Expected: only lines from the hypotheses table (the "Diabetes mellitus" row) — if any other line matches, the rewrite missed a spot.

- [ ] **Step 3: Commit**

```bash
git add docs/research_protocol.md
git commit -m "docs: rewrite research protocol for multi-cause COVID disruption design"
```

---

### Task 9: Update `docs/data_dictionary.md` for the new columns

**Files:**
- Modify: `docs/data_dictionary.md`

**Interfaces:** none (documentation only)

- [ ] **Step 1: Add the new/changed columns**

Add rows to the data dictionary table for: `cause` (source: CDC WONDER, definition: which of the 8 series a row belongs to, per spec section 3's ICD-10 codes; status: planned), `disruption` (source: derived, `src/analysis/heterogeneity.py`'s `compute_county_disruption`; definition: post-period mean minus pre-period mean age-adjusted rate per county; status: planned), and the excess-mortality output fields (`expected`, `deviation`, `pi_low`, `pi_high`, `significant`, `persistence_class` — source: derived, `src/analysis/excess_mortality.py`; status: planned). Remove or clearly mark superseded the old `data_eligible_changepoint`, `breakpoint_year`, `trajectory_class` rows tied to the retired single-disease `src/analysis/trajectory.py` design (spec section 2).

- [ ] **Step 2: Commit**

```bash
git add docs/data_dictionary.md
git commit -m "docs: update data dictionary for multi-cause excess-mortality columns"
```

---

## Self-Review

**Spec coverage:**
- Spec §5.1 (known-date ITS) → Tasks 3-4 ✓
- Spec §5.2 (persistence classification) → Task 5 ✓
- Spec §5.3 (PELT/binseg cross-check) → already built (`src/analysis/changepoints.py`), reused unmodified per spec §2 — no new task needed ✓
- Spec §5.4 (negative control) → the *method* to run it is Tasks 3-5 (same functions, drowning as input); the actual real-data pull is spec §12's open risk, out of this plan's scope by design ✓
- Spec §5.5 (FDR correction) → Task 6 ✓
- Spec §5.6 (sensitivity analysis) → NOT covered by a dedicated task; this is a re-run of Task 3-4's functions with a different baseline window, not new code, so no separate module is needed — flagged here rather than silently dropped.
- Spec §5.7 (heterogeneity) → Task 7 ✓
- Spec §6 (module changes) → `mortality.py` extension for multi-cause panels is NOT in this plan — `src/analysis/excess_mortality.py` and `src/analysis/heterogeneity.py` operate directly on `WonderLoadResult.df` (Task 1's output) without needing the old `compute_county_eligibility`/`build_county_series` single-disease shape, so that extension turned out to be unnecessary rather than deferred. `src/analysis/trajectory.py` retirement is a deletion, not implemented here — add as a final cleanup step in the follow-up app-redesign plan instead, since it's still imported by the (soon to be replaced) Streamlit pages.
- Spec §7 (app redesign), §8 (data flow orchestration script), §11/§12 report generation → explicitly out of scope for this plan (see Global Constraints); follow-up plan once real multi-cause WONDER data exists.

**Placeholder scan:** No TBD/TODO strings in any task; every code step has complete, runnable code; every test has real assertions with hand-computable expected values (the BH test in Task 6 and the linear-trend tests in Task 3 are worked examples, not just "assert no error").

**Type consistency:** `DeviationResult` (Task 4) is the type Task 5's `classify_persistence` consumes — field names (`year`, `deviation`, `significant`) match across both. `WonderLoadResult.df["cause"]` (Task 1) is a plain string column consumed the same way by both `excess_mortality.py` (filtering a series to one cause before calling `fit_baseline_trend`) and `heterogeneity.py` (Task 7 doesn't reference `cause` directly — it's called once per cause by the orchestration layer, matching how Task 6's FDR correction is applied once per family by the caller, not internally).

**Scope check:** This plan is self-contained and produces working, independently-testable software (the full excess-mortality + heterogeneity engine, runnable against synthetic fixtures today). App redesign and real multi-cause data integration are intentionally a separate follow-up plan, per the writing-plans skill's guidance to split large specs rather than let quality degrade into placeholder-heavy late tasks.
