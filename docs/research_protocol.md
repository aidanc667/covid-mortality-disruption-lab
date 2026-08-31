# Research Protocol

**Disease Trajectory Observatory — Diabetes Mellitus, County-Level Mortality Trajectories**
**Version 1.0 — locked prior to any change-point or heterogeneity analysis, per the project's confirmatory-analysis discipline.**
**Basis:** [`data_feasibility_audit.md`](data_feasibility_audit.md)

This protocol exists to reduce researcher degrees of freedom. Analytical choices below (inclusion criteria, methods, thresholds) are fixed before any results are inspected. Deviations discovered necessary during implementation must be logged in an addendum at the bottom of this file, not made silently.

---

## 1. Research question

**Primary:** When and where do U.S. county-level diabetes mortality trajectories undergo statistically significant structural changes, and what demographic, socioeconomic, healthcare, behavioral, and environmental factors are associated with differences in post-breakpoint trajectories?

**Stage 1 (Detection):** Are there detectable structural breaks in county-level diabetes mortality? Are they national, regional, or localized? Do independent methods agree? How large and how certain are they?

**Stage 2 (Heterogeneity):** Conditional on a detected breakpoint, are post-breakpoint trajectory differences associated with healthcare access, insurance coverage, smoking, obesity, physical inactivity, poverty, income, education, food environment, air pollution, demographic composition, or urban/rural status?

## 2. Hypotheses

- H1 (exploratory→confirmatory split, see §9): County-level diabetes age-adjusted mortality trajectories contain at least one statistically identifiable structural break within 1999–2020 for a non-trivial share of counties with sufficient data.
- H2: The estimated breakpoint year is not uniform nationally — there is meaningful geographic heterogeneity in *when* trajectories changed.
- H3: Counties with more favorable post-breakpoint trajectories (larger negative slope change) have systematically different levels of healthcare access, socioeconomic status, behavioral risk factors, or air quality than counties with less favorable trajectories.
- H3 is explicitly associational, not causal (see §11).

## 3. Primary outcome

CDC WONDER age-adjusted diabetes mortality rate (ICD-10 E10–E14, underlying cause), per 100,000, standardized to the 2000 U.S. standard population, at the county-year level.

## 4. Secondary outcomes

- Crude diabetes mortality rate (county-year), for the crude-vs-age-adjusted robustness comparison required by the brief.
- Raw death counts and population (needed for suppression/reliability handling, not as an analytic outcome themselves).

## 5. Temporal scope (revised per feasibility audit §16–17)

- **Primary analysis window: 1999–2020**, using the CDC WONDER "Underlying Cause of Death, 1999–2020" (bridged-race) database exclusively. This is the longest span obtainable from one methodologically consistent vintage.
- **Secondary/extension window: 2018–2024**, using the "Underlying Cause of Death, 2018–2024, Single Race" database, reported and visualized as a distinct series, never concatenated with the primary window into a single unbroken trend line. The 2018–2020 overlap years will be used to characterize (not correct) the magnitude of the vintage discontinuity.
- Heterogeneity/context analysis (Stage 2) is scoped to **2010–2020**, matching County Health Rankings' actual data availability. 1999–2009 is retained for outcome-only descriptive trend analysis but excluded from the covariate-driven heterogeneity models.

## 6. Inclusion / exclusion criteria

**County-year inclusion (descriptive analysis):** all county-years with a non-suppressed WONDER record.

**County inclusion (change-point analysis)** — a county is eligible for per-county change-point modeling only if it meets *all* of:
- At least 15 of the 22 years (1999–2020) have non-suppressed, non-"Unreliable" rate estimates.
- At least 5 non-suppressed years exist on each side of any candidate breakpoint under consideration.
- County population (mid-period, from PEP) is at least 50,000. (Sensitivity analysis will re-run at 20,000 and 100,000 thresholds per the robustness plan, §10.)

Counties failing these criteria are retained in the dataset and flagged `insufficient_data`, never dropped silently or imputed to zero — they appear in the app's Data Quality and Breakpoint Explorer views as an explicit category, not blank.

**Heterogeneity-analysis inclusion:** a county must additionally have a non-missing value (or defensible imputation, see §8) for the specific context variable(s) used in a given comparison.

## 7. Primary statistical methods

1. **Segmented (piecewise-linear) regression** — primary method for slope/breakpoint estimation, at national, state, and eligible-county levels. Breakpoint search via iterative estimation (Muggeo-style); confidence interval via bootstrap resampling of residuals.
2. **PELT** (`ruptures`, L2 cost, minimum segment length = 5 years) — independent algorithmic cross-check.
3. **Binary segmentation** (`ruptures`) — second independent cross-check.
4. **Bayesian single-change-point regression** — run at national and state level only (not per-county, for computational-cost reasons); used as a probabilistic corroboration of the frequentist estimate, not the primary reported number.

A breakpoint is reported with a method-agreement summary (e.g., "3/4 methods agree within ±1 year") labeled explicitly as an analytical summary, not a formal probability (per brief §13).

## 8. Missing-data strategy

- CDC WONDER suppressed cells: never imputed to zero or dropped from the panel; retained as `suppressed` with the county-year excluded from rate-based calculations for that year, and factored into the county's eligibility count (§6).
- Context variables (Census, CHR&R, USDA, HRSA): missingness is documented per variable, per county, per year in the Data Quality Report. No mortality value is ever imputed. Context variables may be forward/backward-filled only within CHR&R's own documented measurement-year alignment (i.e., using the correct source year, not an adjacent nominal year), and any such fill is flagged in the analytic table with a `_imputed` indicator column, never silently merged.
- PM2.5 is included only for counties with EPA AQS monitor coverage; non-monitored counties are `NA` for this variable, not estimated.

## 9. Exploratory vs. confirmatory analysis

- **Confirmatory:** national- and state-level breakpoint existence, location, and method agreement (H1, H2) — pre-specified methods and thresholds above, results reported regardless of direction/significance.
- **Exploratory:** all Stage 2 heterogeneity associations (H3) — reported with FDR-adjusted p-values (§10) and explicitly labeled hypothesis-generating, not confirmatory, since context-variable selection and the outcome (post-break slope) are both derived from the same detection step.

## 10. Multiple-testing strategy

Heterogeneity comparisons across context variables and trajectory groups will use Benjamini-Hochberg FDR correction across the full family of tests run for a given analysis page (e.g., all context-variable comparisons on the Trajectory Atlas page are one family). Raw and FDR-adjusted p-values are both displayed; only FDR-adjusted results are described as "statistically significant" in generated report text.

## 11. Causal language policy

No result may use "cause," "led to," or "resulted in." Approved language: "associated with," "temporally aligned with," "consistent with," "predictive of," "correlated with." This is enforced in `src/reporting/` text templates, not left to ad hoc phrasing.

## 12. Sensitivity / robustness analyses (planned)

Per brief §25: outcome (crude vs. age-adjusted), time window (full vs. 1999–2010 vs. 2011–2020), county population threshold (20k/50k/100k), change-point method (segmented vs. PELT vs. binary segmentation), and model specification (with/without demographic controls, with/without healthcare-access controls).

## 13. Placebo / negative control (planned)

A cause-of-death series with no specific mechanistic reason to share diabetes's breakpoint timing (candidate: accidental/unintentional injury mortality, ICD-10 V01–X59, chosen because it is common enough to avoid suppression in most counties and is not plausibly driven by the same diabetes-care-delivery changes) will be run through the identical change-point pipeline as a falsification check. If the same breakpoint pattern appears, that is evidence the methodology is detecting a shared artifact (e.g., the vintage break) rather than a diabetes-specific signal.

## 14. Limitations (carried into final report, not just this document)

Observational/ecological design; no individual-level causal inference; mortality-vintage discontinuity (1999–2020 vs. 2018–2024); small-county suppression and instability; PLACES model-based behavioral estimates; incomplete PM2.5 coverage; CHR&R measurement-year lags; pre-2010 absence of context data; multiple testing; spatial non-independence of counties; potential county-boundary/classification changes over the study period.

---

## Addenda (deviations discovered during implementation)

**2026-08-29 — Trajectory classification threshold (brief §15).** A county's post-breakpoint trajectory is classified as:
- **Improving**: segmented regression detects a significant break (§7) AND `slope_diff <= -0.3` (age-adjusted deaths per 100k per year)
- **Worsening**: significant break AND `slope_diff >= +0.3`
- **Stable**: either no significant break is detected, or a significant break with `|slope_diff| < 0.3`

The ±0.3/100k/year threshold is a placeholder magnitude chosen to separate visually/practically meaningful slope changes from noise-level ones, pending calibration against the real mortality series once available (candidate calibration: set the threshold from the empirical distribution of `slope_diff` across all eligible counties, e.g. its interquartile range, rather than a fixed constant). This must be revisited before any results derived from it are reported as final — flagged here so it isn't mistaken for an a priori confirmatory choice.

**2026-08-29 — Change-point detection on the diff series (implementation note, not a protocol change).** `ruptures`' standard cost models detect shifts in mean, not in trend/slope. Since a diabetes-mortality breakpoint is a slope change, PELT and binary segmentation are run on the first-differenced rate series (`src/analysis/changepoints.py`), which turns a slope change into a mean shift; breakpoint years are then mapped back to the original series. This does not change the methods specified in §7, only their correct implementation.
