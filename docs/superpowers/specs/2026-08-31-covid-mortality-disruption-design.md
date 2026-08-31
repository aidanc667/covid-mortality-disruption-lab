# Design Spec: COVID-19 Mortality Disruption Analysis

**Status:** Approved by user, pending write-up into implementation plan.
**Supersedes:** The original single-disease (diabetes breakpoint) framing. This is a pivot, not an addition — see "What this replaces" below.
**Date:** 2026-08-31

---

## 1. Research question

*Which causes of death experienced the greatest and most statistically significant disruption during the COVID-19 pandemic (2020–2024), how persistent were those disruptions through the most recent available data, and how did disruption severity vary across U.S. counties by socioeconomic status, healthcare access, and rurality?*

COVID-19 is treated as a system-wide shock to the healthcare/public-health system, not as the disease under study. The question is deliberately scoped to *what* changed, *how much*, and *where* — not *why* — because mortality data alone cannot cleanly separate direct viral effects from deferred care, isolation, or economic-stress mechanisms. This scoping avoids the confounding problem a causal-mechanism claim would face.

## 2. What this replaces

The prior version of this project (Disease Trajectory Observatory, diabetes-only) is superseded by this design. Retained without change:
- All ingestion modules (`src/ingestion/*.py`) — CDC WONDER, Census, CHR&R, USDA, HRSA, EPA PM2.5
- `src/cleaning/geography.py`
- `src/analysis/changepoints.py` (segmented regression, PELT, binary segmentation) — reused as a cross-check method, not the primary method
- The manual-export workflow for CDC WONDER (`docs/manual_data_acquisition.md`)

Redesigned:
- `src/cleaning/mortality.py` — extended for multi-cause panels instead of single-disease
- `src/analysis/trajectory.py` — replaced by the excess-mortality/deviation module (Section 6)
- The Streamlit app's page structure (Section 8)
- `docs/research_protocol.md` and `docs/data_dictionary.md` — updated for the new design

## 3. Pre-registered hypotheses

Stated before any 2020–2024 data is pulled or analyzed, so results can be checked against stated priors rather than narrated after the fact.

| Cause | ICD-10 | Prior | Confidence |
|---|---|---|---|
| Drug overdose | X40-X44, X60-X64, X85, Y10-Y14 (CDC standard definition) | Largest relative disruption of the set; may show reversal (declining) by 2023–2024 | Very high |
| Diseases of heart | I00-I09,I11,I13,I20-I51 | Real acute-phase (2020–2021) disruption; persistence uncertain | High |
| Diabetes mellitus | E10-E14 | Real acute-phase disruption; persistence uncertain | High |
| Alzheimer's disease | G30 | Real, possibly large relative disruption from isolation/care-disruption mechanism; persistence uncertain | High |
| Cerebrovascular disease | I60-I69 | Real but possibly harder to detect cleanly than heart disease (smaller N) | Moderate |
| Malignant neoplasms (cancer) | C00-C97 | **Expected to show little or no significant disruption in this data window** — deliberately included as the "lag" comparison case; true screening-delay mortality effect likely falls partly or fully after 2024 | Low (by design) |
| Accidental drowning (W65-W74) | — | **Negative control.** No plausible COVID mechanism. Expected to show no significant disruption. If it does, the method itself is suspect. | N/A — validation case |
| COVID-19 | U07.1 | Not a hypothesis test — reference/scaling series only (didn't exist pre-2020, trivially "disrupted") | N/A — reference series |

## 4. Data sources and scope

Per `DATA_SOURCES.md` #1–2, verified 2026-08-29/31:

- **Baseline (pre-trend):** 1999–2019, CDC WONDER "Underlying Cause of Death, 1999-2020" (database code D76).
- **Post-shock:** 2020–2024, CDC WONDER "Underlying Cause of Death, 2018-2024, Single Race" (database code D158). Confirmed via the live query form: Year finder lists exactly 2018–2024, no 2025 data exists yet.
- **Bridging:** the pre-trend is fit using 1999–2019 data only. The entire 2020–2024 "post" comparison period uses D158 exclusively (one consistent vintage). The 2018–2020 overlap years (present in both databases) are used to estimate the size of the vintage discontinuity itself, so it is not mistaken for a COVID effect.
- **Geography:** national and state level for the core disruption/persistence analysis (adequate power for every cause, including rarer ones). County level only for the heterogeneity stage, using coarser pre/post period aggregates rather than full annual series, to manage suppression on lower-count causes (Alzheimer's, overdose, drowning).
- **Query consolidation:** WONDER supports selecting multiple cause-of-death groups in one query, grouped by an additional "cause of death" dimension. All 8 series (6 test causes + COVID-19 reference + drowning negative control) should be pulled in as few manual exports as geography/year-range batching allows, not one export per cause.

## 5. Statistical methodology

### 5.1 Primary method: known-date interrupted time series (excess mortality)

For each of the 8 series, at national and state level:
1. Fit an expected trend (linear, or with a seasonal term if monthly-resolution data is used) on 1999–2019.
2. Project the expected trend forward through 2020–2024, with a prediction interval.
3. Compute observed − expected = disruption, for each post-period year.
4. A disruption is "significant" if observed falls outside the prediction interval.

This is a pre-registered-breakpoint variant of the segmented-regression code already built (`src/analysis/changepoints.py`) — the breakpoint (2020) is fixed by the shock's known date, not searched for, which is more defensible against p-hacking than an algorithmic breakpoint search.

### 5.2 Persistence classification (three-way, not binary)

For each cause with a significant 2020–2021 disruption, classify its 2022–2024 pattern as:
- **Persisted** — disruption remained significant and same-direction through 2024
- **Resolved** — disruption shrank back within the expected-trend prediction interval
- **Reversed** — disruption flipped sign (e.g., overdose spiking then declining below its pre-pandemic trend)

A binary persisted/resolved scheme would flatten exactly the kind of finding the overdose prior anticipates.

### 5.3 Cross-check

Run PELT and binary segmentation (already built, unmodified) on each bridged full series as an independent check that they land on a breakpoint near March 2020 without being told to. This validates the known-date approach isn't missing a differently-timed real break.

### 5.4 Negative control

Run the identical pipeline (Sections 5.1–5.3) on accidental drowning mortality (W65-W74), a cause with no plausible COVID mechanism. A significant "disruption" here would indicate the method is detecting an artifact (vintage-bridging error, generic 2020 data-quality issue, etc.), not a real signal, and must be resolved before trusting results on the other 7 causes.

### 5.5 Multiple-testing correction

The 6 substantive test causes (heart disease, cerebrovascular disease, diabetes, Alzheimer's, overdose, cancer — excluding the reference COVID-19 series and the drowning negative control) are tested as one family; Benjamini-Hochberg FDR correction applies across all 6 disruption tests, not just within the heterogeneity stage (which already has its own FDR correction per the original research protocol).

### 5.6 Sensitivity analysis

Repeat the trend-fitting with an alternative baseline window (e.g., 2010–2019 instead of 1999–2019) to check whether the choice of pre-period length materially changes the expected-trend projection.

### 5.7 Heterogeneity analysis

For each cause with a significant county-level disruption, compute a per-county disruption magnitude (comparing an aggregated pre-COVID period to an aggregated COVID-era period, to manage suppression), then regress/correlate against existing CHR&R/USDA/HRSA context variables (poverty, rurality, healthcare access, uninsured rate). Reuses the Stage 2 heterogeneity design already in `docs/research_protocol.md`, with FDR correction applied across the context-variable comparisons as already specified there.

## 6. New/changed modules

| Module | Change |
|---|---|
| `src/cleaning/mortality.py` | Extend to handle multi-cause panels (currently single-disease-shaped) |
| `src/analysis/excess_mortality.py` (new) | Implements Section 5.1–5.2: trend fit, projection, deviation, persistence classification |
| `src/analysis/changepoints.py` | No changes — reused as-is for the Section 5.3 cross-check |
| `src/analysis/trajectory.py` | Retired — replaced by `excess_mortality.py`'s persistence classification |
| `src/analysis/heterogeneity.py` (new) | Implements Section 5.7 |
| `src/ingestion/cdc_wonder.py` | Extend `EXPECTED_COLUMNS`/parsing to handle a "Cause of death" grouping column when multiple causes are pulled in one export |
| `docs/research_protocol.md` | Rewrite for the new design; retire diabetes-specific eligibility/classification language |
| `docs/data_dictionary.md` | Add per-cause columns |

## 7. App redesign

Replaces the current 6-page structure:

- **Home** — updated headline stats (how many of 6 test causes showed significant disruption, largest disruption, negative-control pass/fail)
- **Disruption Overview** — small-multiples chart, one panel per cause, observed vs. expected with shaded deviation. The single most important visualization in the app.
- **Persistence Explorer** — per-cause classification (persisted/resolved/reversed) with the 2020–2024 trajectory
- **Geographic Heterogeneity** — replaces Breakpoint Explorer; county-level disruption magnitude, filterable by cause and context variable
- **County Deep Dive** — retained concept, now shows all 8 series (6 test causes + COVID-19 reference + drowning negative control) per selected county
- **Data Quality** — retained, extended to show suppression rates per cause (Alzheimer's/overdose/drowning will suppress far more than heart disease at county level)
- **Methods** — rewritten for the new design (excess-mortality methodology, vintage-bridging, cause list and rationale, negative control, pre-registered hypotheses table)

## 8. Data flow

1. Manual WONDER exports (D76 for 1999–2019, D158 for 2020–2024) → `data/raw/cdc_wonder/`
2. `src/ingestion/cdc_wonder.py` (extended) → standardized long-format panel with suppression flags, one row per (geography, year, cause)
3. `src/cleaning/mortality.py` (extended) → vintage-bridged, calibrated panel
4. `src/analysis/excess_mortality.py` → per-cause disruption/persistence results
5. `src/analysis/changepoints.py` → per-cause cross-check breakpoints
6. `src/analysis/heterogeneity.py` → per-cause, per-county heterogeneity regression results
7. Orchestration script → precomputed parquet outputs to `outputs/models/`
8. Streamlit app reads only precomputed outputs (no live recomputation), per brief §46

## 9. Error handling / data quality

- Suppressed and unreliable county-year-cause cells: never coerced to zero, never dropped — same discipline as the existing pipeline, extended per-cause.
- Vintage-bridging calibration failure (e.g., 2018–2020 overlap shows an implausibly large jump): surfaced explicitly in the Data Quality page, not silently absorbed into the trend fit.
- Negative control failure (drowning shows significant "disruption"): blocks trusting results on the other 7 causes until resolved — this is a hard gate, not a footnote.

## 10. Testing strategy

- Unit tests for `excess_mortality.py` against synthetic series with known injected deviations (analogous to the existing `test_changepoints.py` ground-truth tests)
- Unit test confirming the negative-control series (synthetic, no injected deviation) returns "not significant"
- Unit tests for the three-way persistence classification (persisted/resolved/reversed cases)
- Unit tests for FDR correction across the 7-cause family
- Extend `test_cdc_wonder_ingestion.py` for the multi-cause export format once a real multi-cause file is available

## 11. Limitations specific to this design (to carry into the final report)

- ICD-10 cause-of-death coding practices may have shifted during 2020–2021 due to strain on death-certification systems, independent of true mortality changes — a real, specific artifact risk beyond the general suppression/vintage caveats already documented.
- The vintage-bridging approach (Section 4) assumes the 2018–2020 overlap years reasonably characterize the size of the database discontinuity; if that assumption is wrong, the bridging adjustment itself becomes a source of error.
- Cancer's expected null result is a measurement-lag artifact of the data window (through 2024), not evidence the mechanism doesn't exist — must not be reported as "cancer was unaffected."
- All findings remain observational/associational; the "why" behind any confirmed disruption (direct viral effect vs. deferred care vs. isolation vs. economic stress) cannot be cleanly separated by mortality data alone.

## 12. Open risks / decisions carried forward

- Actual data pull for 8 series × (national + state + county) across two databases is a substantially larger manual-export task than the single-disease pilot; batching strategy (Section 4) needs to be validated against WONDER's export row limits in practice.
- The negative control (drowning) needs its own real WONDER pull; not yet attempted.
- Real multi-cause export file format (does WONDER's "Cause of death" grouping column match the assumed structure) needs verification against an actual export before `cdc_wonder.py`'s extension is finalized.
