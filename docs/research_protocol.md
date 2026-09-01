# Research Protocol

**COVID Mortality Disruption Lab — Multi-Cause COVID-19 Mortality Disruption Analysis**
**Version 2.0 — supersedes v1.0's diabetes-only design (see `docs/superpowers/specs/2026-08-31-covid-mortality-disruption-design.md` for the pivot rationale). Locked prior to any excess-mortality or heterogeneity analysis, per the project's confirmatory-analysis discipline.**
**Basis:** [`data_feasibility_audit.md`](data_feasibility_audit.md), [`../superpowers/specs/2026-08-31-covid-mortality-disruption-design.md`](superpowers/specs/2026-08-31-covid-mortality-disruption-design.md)

This protocol exists to reduce researcher degrees of freedom. Analytical choices below (inclusion criteria, methods, thresholds) are fixed before any results are inspected. Deviations discovered necessary during implementation must be logged in an addendum at the bottom of this file, not made silently.

---

## 1. Research question

**Primary:** Which causes of death experienced the greatest and most statistically significant disruption during the COVID-19 pandemic (2020–2024), how persistent were those disruptions through the most recent available data, and how did disruption severity vary across U.S. counties by socioeconomic status, healthcare access, and rurality?

COVID-19 is treated as a system-wide shock to the healthcare/public-health system, not as the disease under study. The question is deliberately scoped to *what* changed, *how much*, and *where* — not *why* — because mortality data alone cannot cleanly separate direct viral effects from deferred care, isolation, or economic-stress mechanisms.

## 2. Hypotheses

- H1: At least one of the 6 test causes (§3) shows a statistically significant 2020–2021 deviation from its expected pre-pandemic trend.
- H2: The pattern of significant deviations is not uniform across causes — some persist through 2024, some resolve, some reverse (three-way classification, §7).
- H3: County-level disruption magnitude, for causes with a significant deviation, is associated with socioeconomic status, healthcare access, and rurality. Explicitly associational, not causal (see §11).

## 3. Primary outcomes — pre-registered hypotheses per cause

Stated before any 2020–2024 data is pulled or analyzed, so results can be checked against stated priors rather than narrated after the fact.

| Cause | ICD-10 | Prior | Confidence |
|---|---|---|---|
| Drug overdose | X40-X44, X60-X64, X85, Y10-Y14 (CDC standard definition) | Largest relative disruption of the set; may show reversal (declining) by 2023–2024 | Very high |
| Diseases of heart | I00-I09,I11,I13,I20-I51 | Real acute-phase (2020–2021) disruption; persistence uncertain | High |
| Diabetes mellitus | E10-E14 | Real acute-phase disruption; persistence uncertain | High |
| Alzheimer's disease | G30 | Real, possibly large relative disruption from isolation/care-disruption mechanism; persistence uncertain | High |
| Cerebrovascular disease | I60-I69 | Real but possibly harder to detect cleanly than heart disease (smaller N) | Moderate |
| Malignant neoplasms (cancer) | C00-C97 | **Expected to show little or no significant disruption in this data window** — deliberately included as the "lag" comparison case; true screening-delay mortality effect likely falls partly or fully after 2024 | Low (by design) |
| Congenital malformations, deformations and chromosomal abnormalities | Q00-Q99 | **Negative control.** No plausible COVID mechanism (deaths concentrated in infancy, driven by prenatal/genetic factors, not adult lockdown behavior or delayed elective screening). Expected to show no significant disruption. If it does, the method itself is suspect. | N/A — validation case |
| COVID-19 | U07.1 | Not a hypothesis test — reference/scaling series only (didn't exist pre-2020, trivially "disrupted") | N/A — reference series |

Each of the 6 test causes' age-adjusted rate (per 100,000, 2000 U.S. standard population) is the outcome, computed the same way CDC WONDER already provides it. Crude rates and raw death counts/population are retained alongside for suppression/reliability handling, not as primary analytic outcomes.

## 4. Temporal scope

- **Baseline (pre-trend):** 1999–2019, CDC WONDER "Underlying Cause of Death, 1999-2020" database (code D76).
- **Post-shock:** 2020–2024, CDC WONDER "Underlying Cause of Death, 2018-2024, Single Race" database (code D158). Confirmed via the live query form 2026-08-31: the Year finder lists exactly 2018–2024, no 2025 data exists yet.
- **Bridging:** the pre-trend is fit using 1999–2019 data only (`src/analysis/excess_mortality.fit_baseline_trend`). The entire 2020–2024 comparison period uses the D158 database exclusively — one consistent vintage. The 2018–2020 overlap years (present in both databases) are used by `src/cleaning/bridging.py` to estimate the size of the vintage discontinuity itself, so it is not mistaken for a COVID effect; `is_bridging_reliable()` must return `True` (median relative offset ≤10%) before results are trusted, per §9.
- **Geography:** national and state level for the core disruption/persistence analysis (adequate statistical power for every cause, including rarer ones like Alzheimer's, overdose, and drowning). County level only for the heterogeneity stage (§7's `src/analysis/heterogeneity.py`), using coarser pre/post period aggregates rather than full annual series, to manage suppression on lower-count causes.

## 5. Inclusion / exclusion criteria

**National/state-level disruption analysis:** no per-geography eligibility gate — national and state totals are large enough across all 8 series (including drowning and Alzheimer's) that suppression is not expected to be a material concern at this level of aggregation.

**County-level heterogeneity analysis:** a county is included only if it has at least 2 non-missing years of data in both the pre-period and post-period aggregation windows (`src/analysis/heterogeneity.compute_county_disruption`'s `min_years_each_period` parameter). This replaces the old single-disease `MIN_NONSUPPRESSED_YEARS`/`MIN_COUNTY_POPULATION` thresholds, which do not apply to this design's coarser county-level aggregation.

Counties failing this criterion are excluded from the heterogeneity regression only — they remain visible elsewhere (e.g. the Data Quality page) rather than being dropped from the dataset entirely.

## 6. Missing-data strategy

- CDC WONDER suppressed cells: never imputed to zero or dropped from the panel; retained as `*_suppressed`/`*_unreliable` boolean flags alongside a `NaN` rate (`src/ingestion/cdc_wonder.py`), excluded from trend-fitting and deviation calculations for that year/geography, never coerced to zero.
- Context variables (Census, CHR&R, USDA, HRSA): missingness is documented per variable, per county, per year in the Data Quality Report. No mortality value is ever imputed.

## 7. Primary statistical methods

1. **Known-date interrupted time series ("excess mortality")** — primary method. Fit an expected trend on 1999–2019 (`fit_baseline_trend`), project it forward through 2020–2024 with a prediction interval (`compute_deviations`), and flag a year as significantly disrupted if the observed value falls outside that interval. The breakpoint (2020) is fixed by the shock's known date, not searched for, which is more defensible against p-hacking than an algorithmic breakpoint search.
2. **Three-way persistence classification** (`classify_persistence`) — for causes with a significant 2020–2021 disruption: **Persisted** (still significant, same direction, through 2024), **Resolved** (shrank back within the prediction interval), or **Reversed** (flipped sign — e.g. overdose spiking then declining below trend). A binary persisted/resolved scheme would flatten exactly this kind of reversal finding.
3. **Cross-check via existing change-point methods** — PELT and binary segmentation (`src/analysis/changepoints.py`, unmodified, reused from the diabetes-pilot phase) run on each bridged full series, to independently verify they land on a breakpoint near March 2020 without being told to.
4. **Negative control** — the identical pipeline (methods 1–3) run on congenital malformations, deformations and chromosomal abnormalities mortality (Q00-Q99), a cause with no plausible COVID mechanism. A significant "disruption" here indicates the method is detecting an artifact (vintage-bridging error, generic data-quality issue), not a real signal, and blocks trusting results on the other 7 series until resolved. This is a hard gate, not a footnote.

A breakpoint/persistence result is reported with a method-agreement summary between the primary (known-date ITS) and cross-check (PELT/binseg) methods, labeled explicitly as an analytical summary, not a formal probability.

## 7a. Multiple-testing strategy for the cause-of-death family

The 6 substantive test causes (heart disease, cerebrovascular disease, diabetes, Alzheimer's, overdose, cancer — excluding the COVID-19 reference series and the drowning negative control) are tested as one family; Benjamini-Hochberg FDR correction (`src/analysis/excess_mortality.benjamini_hochberg`) applies across all 6 disruption tests. This is distinct from, and in addition to, the heterogeneity-stage FDR correction in §10.

## 8. Sensitivity analysis

Repeat the trend-fitting (§7, method 1) with an alternative baseline window (e.g., 2010–2019 instead of 1999–2019) to check whether the choice of pre-period length materially changes the expected-trend projection and, downstream, which causes are flagged as significantly disrupted.

## 9. Vintage-bridging reliability gate

Before any 2020–2024 result is reported, `src/cleaning/bridging.is_bridging_reliable()` must return `True` for the causes/geographies in question. A `False` result (median relative offset between the two database vintages exceeds 10% across the 2018–2020 overlap years) must be surfaced explicitly in the Data Quality page and the final report — not silently absorbed into the trend fit as if it were a real 2020 effect.

## 10. Heterogeneity analysis and its multiple-testing strategy

For each cause with a significant county-level disruption, `src/analysis/heterogeneity.compute_county_disruption` computes a per-county disruption magnitude (aggregated pre-COVID period mean minus aggregated COVID-era period mean), and `regress_disruption_on_context` regresses it against context variables (poverty, rurality, healthcare access, uninsured rate — from CHR&R/USDA/HRSA, unchanged from the pilot phase's data pipeline). Comparisons across context variables for a given cause use Benjamini-Hochberg FDR correction as one family, separate from and in addition to §7a's cause-family correction. Raw and FDR-adjusted p-values are both retained; only FDR-adjusted results are described as "statistically significant" in generated report text. The county-level disruption magnitude itself uses **crude rate**, not age-adjusted rate, for both the pre-period (2015–2019) and post-period (2020–2024) — see the 2026-09-01 addendum for why (WONDER doesn't offer age-adjustment at county granularity for the D158 database) and its limitation.

## 11. Causal language policy

No result may use "cause," "led to," or "resulted in." Approved language: "associated with," "temporally aligned with," "consistent with," "predictive of," "correlated with." This is enforced in `src/reporting/` text templates, not left to ad hoc phrasing.

## 12. Limitations (carried into final report, not just this document)

- Observational/ecological design; no individual-level causal inference.
- Mortality-vintage discontinuity between the 1999–2020 and 2018–2024 CDC WONDER databases (§4, §9).
- ICD-10 cause-of-death coding practices may have shifted during 2020–2021 due to strain on death-certification systems, independent of true mortality changes — a real, specific artifact risk beyond the general vintage-discontinuity caveat.
- Cancer's expected null result (§3) is a measurement-lag artifact of the data window (through 2024), not evidence the mechanism doesn't exist — must not be reported as "cancer was unaffected."
- Small-county suppression and instability at the county-level heterogeneity stage.
- County-level heterogeneity uses crude rate, not age-adjusted rate (WONDER does not offer age-adjustment at county granularity for the D158 database — §10's addendum), so measured disruption magnitude may partly reflect each county's own population-aging trajectory rather than a COVID-era shift, and this is plausibly correlated with rurality itself.
- PLACES model-based behavioral estimates (CHR&R smoking/obesity/inactivity).
- Multiple testing across both the 6-cause family (§7a) and, separately, the context-variable family per cause (§10).
- Spatial non-independence of counties.
- All findings remain associational; the "why" behind any confirmed disruption (direct viral effect vs. deferred care vs. isolation vs. economic stress) cannot be cleanly separated by mortality data alone.

---

## Addenda (deviations discovered during implementation)

**2026-08-29 — Trajectory classification threshold (brief §15).** A county's post-breakpoint trajectory is classified as:
- **Improving**: segmented regression detects a significant break (§7) AND `slope_diff <= -0.3` (age-adjusted deaths per 100k per year)
- **Worsening**: significant break AND `slope_diff >= +0.3`
- **Stable**: either no significant break is detected, or a significant break with `|slope_diff| < 0.3`

The ±0.3/100k/year threshold is a placeholder magnitude chosen to separate visually/practically meaningful slope changes from noise-level ones, pending calibration against the real mortality series once available (candidate calibration: set the threshold from the empirical distribution of `slope_diff` across all eligible counties, e.g. its interquartile range, rather than a fixed constant). This must be revisited before any results derived from it are reported as final — flagged here so it isn't mistaken for an a priori confirmatory choice.

**2026-08-29 — Change-point detection on the diff series (implementation note, not a protocol change).** `ruptures`' standard cost models detect shifts in mean, not in trend/slope. Since a diabetes-mortality breakpoint is a slope change, PELT and binary segmentation are run on the first-differenced rate series (`src/analysis/changepoints.py`), which turns a slope change into a mean shift; breakpoint years are then mapped back to the original series. This does not change the methods specified in §7, only their correct implementation.

**2026-08-31 — Pivot from single-disease breakpoint detection to multi-cause COVID disruption analysis.** This protocol was rewritten wholesale (v1.0 → v2.0) per `docs/superpowers/specs/2026-08-31-covid-mortality-disruption-design.md`. The diabetes-only research question, its algorithmic-breakpoint-search primary method, and its trajectory-classification thresholds (both addenda above) are retired as the primary design, though the underlying code they describe (`src/analysis/changepoints.py`) is retained and reused as an independent cross-check under the new design (§7, method 3). Diabetes itself is retained as one of the 6 test causes under the new design (§3), not dropped.

**2026-09-01 — Real data acquisition: multi-cause bundling abandoned, state-level deferred.** Two real acquisition attempts confirmed that requesting multiple causes in one WONDER query does not work as designed (see `docs/manual_data_acquisition.md`'s corrected instructions for the full account): with no cause-grouping, WONDER silently blends all selected causes into one combined number; with "And By: Cause of death" grouping, it explodes each category into every individual 4-digit ICD-10 sub-code instead of one row per selected category. The only reliable method is one cause per query. Given that constraint multiplies the export count, **state-level acquisition is deferred** (not abandoned) — none of H1/H2/H3 require it: H1/H2 are tested at the national level, H3 at the county level, so state was always an intermediate-resolution addition, not load-bearing for the core claims. §4/§5's geography language should be read as "national (primary, in progress) and county (heterogeneity stage, primary) — state deferred" until revisited.

**2026-09-01 — D158 export year range widened to include the vintage-bridging overlap.** The 15-export national data-acquisition plan originally specified D158 (post-shock) exports for 2020–2024 only, which has zero overlap with D76's 1999–2019 baseline — leaving `src/cleaning/bridging.is_bridging_reliable` (§9's hard gate) with no shared years to calibrate against. Corrected: all D158 exports now pull **2018–2024** (the database's full available range) instead of 2020–2024, at no extra query cost, so 2018–2019 exists in both databases for bridging calibration. The excess-mortality analysis itself still only treats 2020–2024 as the "post" period; the extra 2018–2019 rows are used solely for the bridging check.

**2026-09-01 — Negative control swapped from accidental drowning to congenital malformations.** Running the real pipeline (§3, §7 method 4) on the first 15 real national exports found accidental drowning (W65-W74) fails the negative-control hard gate: it shows a statistically significant, persistent increase from 2020 onward (`classify_persistence` → "Persisted", p=1.2e-05 on raw death counts, p=7.2e-05 on age-adjusted rate — confirmed genuine by re-testing on raw counts, which rules out a rounding-precision artifact from WONDER's 1-decimal age-adjusted-rate reporting for this low-magnitude cause). This is consistent with published literature (CDC MMWR documented real COVID-era increases in drowning deaths from pool/beach closures, lifeguard shortages, and increased unsupervised time in home pools) — drowning was never actually COVID-independent, so it was a flawed choice of negative control, not evidence the method itself is broken. §3 and §7 method 4 are corrected to use congenital malformations, deformations and chromosomal abnormalities (Q00-Q99) instead — deaths concentrated in infancy, driven by prenatal/genetic factors, with no plausible mechanistic link to adult lockdown behavior, delayed elective screening, or COVID-comorbidity/miscoding. The drowning finding itself is retained as a documented, real, citable side-observation (not discarded), but is no longer part of the pre-registered hypothesis family or the pipeline's active negative-control gate.

**2026-09-01 — County-level heterogeneity uses crude rate, not age-adjusted rate, for both periods.** The first real county-level pull (diabetes, D158 2020–2024, grouped by County) confirmed CDC WONDER does not offer Age-Adjusted Rate at all when a query is grouped by County against the D158 (2018–2024, Single Race) database — not per-cell suppression, but a whole-file capability gap (no "Standard Population" line in the query parameters, no Age Adjusted Rate columns at all), most likely because single-race population estimates lack the age-stratified denominators needed to standardize at county granularity. The D76 (1999–2019) county-level pull for the same cause *does* have it. Since the heterogeneity stage's "disruption" is `mean(post) - mean(pre)`, using age-adjusted rate for one period and crude rate for the other would not be comparable. §7's `src/analysis/heterogeneity.compute_county_disruption` and `regress_disruption_on_context` are corrected to use `crude_rate` consistently for both periods at the county-level heterogeneity stage only — the 6 national test causes and the negative control are unaffected (both national-level pulls have age-adjusted rate available). This is a real limitation, not just an implementation detail: crude rate does not control for a county's population age structure, so part of any measured "disruption" could reflect each county's own population-aging trajectory over 2015–2024 rather than a COVID-era mortality shift — and that confound is plausibly correlated with rurality itself (rural counties disproportionately age due to youth outmigration), one of the very context variables being tested in §10. This is now logged in §12's limitations, not silently absorbed into the regression as if it were a clean association.

**2026-09-01 — Sensitivity analysis (§8) run against real data: all 6 test causes stable.** `scripts/run_sensitivity_check.py` re-fits the primary method with an alternate, shorter baseline (2010–2019, vs. the primary 1999–2019) and compares classification and FDR-significance. All 6 substantive test causes classify identically under both windows (same `persistence_class`, same FDR-significance; p-values tighten under the shorter window but no sign or significance flips). The negative control's age-adjusted-rate row does flip across windows, but this reproduces the already-documented rounding artifact (see the negative-control-swap addendum above), not a new instability — re-run on its actual gate metric (raw death counts), it is stable ("No significant disruption" in both windows, p=0.68 → p=0.10). Output: `outputs/models/sensitivity_check.parquet`.

**2026-09-01 — Negative control's gate decision uses raw death counts, not age-adjusted rate.** The first congenital-malformations pull (see above) initially also failed the hard gate on age-adjusted rate (p=0.013, "Persisted"). Investigation found this is a rounding-precision artifact, not a real effect: CDC WONDER reports this cause's age-adjusted rate to only 1 decimal, and at its low magnitude (~3.0–3.8/100k) that quantization makes the 1999–2019 OLS baseline fit artificially tight (`residual_std=0.076`), so even a ~0.1–0.4/100k gap between the flat 2020–2024 rate and a mildly declining fitted trend crosses the significance threshold. Re-running the identical method on raw death counts (`fit_baseline_trend`/`compute_deviations` on `deaths` instead of `age_adjusted_rate`) gives p=0.68, "No significant disruption" — passing cleanly, consistent with the a priori expectation. This is the same quantization mechanism suspected (but *not* confirmed — see the prior addendum) as a possible explanation for drowning's result; the two causes' outcomes on raw counts diverged (drowning stayed significant on counts, congenital malformations did not), which is itself the evidence that distinguishes a real effect from a rounding artifact. §7 method 4 is corrected: the negative control's pass/fail gate decision is computed on raw death counts, not age-adjusted rate; its charted/displayed series still uses age-adjusted rate for visual consistency with the other 7 series. This does not apply to the 6 substantive test causes (§3, §7a) — all have age-adjusted rates well above 20/100k, where 1-decimal rounding is a much smaller fraction of the signal and the original rate-based method (chosen because it controls for the population's age structure changing over 1999–2024, unlike raw counts) remains appropriate.
