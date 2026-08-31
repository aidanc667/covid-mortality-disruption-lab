# Data + Methodology Feasibility Audit

**COVID Mortality Disruption Lab — Data Source Audit (originally conducted for the project's diabetes-only pilot phase; sources below — CDC WONDER, Census, CHR&R, USDA, HRSA, EPA — remain the same for the current multi-cause-of-death design; see `docs/superpowers/specs/2026-08-31-covid-mortality-disruption-design.md` for what changed).**
**Status:** Phase 1 deliverable, completed before any pipeline or application code was written.
**Prepared:** 2026-08-29

This audit answers the 17 questions posed in the project brief. It is based on direct verification of official CDC, Census, County Health Rankings & Roadmaps (CHR&R), EPA, USDA, and HRSA documentation — no URL, field name, or coverage claim below was assumed rather than checked. Where verification was incomplete, that is stated explicitly rather than guessed.

---

## 1. Exact CDC mortality dataset needed

CDC WONDER "Underlying Cause of Death" has **two non-concatenable vintages** that jointly span 1999–2024:

| Vintage | Years | Population basis | Race categories |
|---|---|---|---|
| Underlying Cause of Death, 1999–2020 | 1999–2020 | Bridged-race intercensal/postcensal estimates (discontinued by NCHS, frozen ~mid-2023) | 4 bridged categories |
| Underlying Cause of Death, 2018–2024, Single Race | 2018–2024 | Single-race Census estimates (1997 OMB standard) | 6/15/31 categories |

There is no official CDC product that delivers one consistent 1999–2024 series. See §9 and §17.

## 2. Exact diabetes definition

Underlying cause of death, ICD-10 codes **E10–E14** (Type 1, Type 2, malnutrition-related, other specified, unspecified diabetes mellitus), consistent with CDC/NCHS cause-of-death groupings. This code range is fixed by ICD-10 and has applied to all U.S. death certificates coded since 1999 (ICD-9 250.x was used before 1999 — pre-1999 data is not comparable without a bridging study, and is out of scope here since WONDER county data starts at 1999 anyway).

## 3. Years available

- County-level annual data: 1999–2020 (bridged-race db) and 2018–2024 (single-race db, most recent year finalized ~Feb 2026).
- Practical continuous, methodologically consistent span for a single database: **1999–2020 (22 years)**.

## 4. Geographic coverage

County-level (5-digit FIPS/GEOID) underlying-cause-of-death counts, rates, and population are available for both vintages, subject to suppression (§11).

## 5. Exact secondary datasets available

| Domain | Dataset | Access |
|---|---|---|
| Demographics/socioeconomic | Census Population Estimates Program (PEP) + ACS 5-Year Estimates | Free API (key required) |
| Health/behavioral/social determinants | County Health Rankings & Roadmaps annual release | Direct CSV/Excel download |
| Air pollution | EPA AQS (AirData) monitor data; CDC/EPA modeled PM2.5 (partial vintage) | Bulk download / API |
| Food environment | USDA ERS Food Environment Atlas | Direct download |
| Healthcare access | HRSA Area Health Resources File (AHRF); HPSA designations | Direct download / portal |

## 6–8. Variables, temporal coverage, and geographic resolution per source

**Census/ACS** (county, GEOID-keyed):
- PEP: annual population/age/sex/race, 1999–present.
- ACS 5-Year: median household income (S1901), poverty rate (S1701), educational attainment (S1501), health insurance coverage (S2701), demographics (DP05) — available from the 2005–2009 vintage forward only. **1999–2004 has no annual ACS equivalent**; only Census 2000 SF3 long-form (a single 2000 snapshot) plus PEP population totals exist for that window.

**County Health Rankings** (county, FIPS-keyed): uninsured %, primary care physician ratio, adult smoking %, adult obesity %, physical inactivity %, children/poverty, median income, education, food environment index, severe housing cost burden, PM2.5, % rural. Annual releases 2010–2025 (2025 is the most recent). Each measure has its own **measurement year that lags the release year by 1–4 years** (documented per-measure by CHR&R) — cannot merge by release year alone. Smoking/obesity/inactivity are PLACES model-based small-area estimates, not raw counts, starting mid-2010s. **No CHR&R data exists before 2010**, i.e. no direct contextual coverage for 1999–2009.

**PM2.5**: EPA AQS monitor data covers only ~20% of U.S. counties (monitor presence required) but has full 1998–2026 temporal range for the counties it does cover. CDC's modeled Downscaler product has broader but not confirmed nationwide county coverage, and the verified downloadable file only ran 2001–2014. **No single official source gives complete nationwide county-year PM2.5 for 1999–2024.**

**USDA Food Environment Atlas**: full county coverage, but only 2012–2025 (irregularly updated, not annual); no pre-2012 coverage.

**HRSA AHRF**: full county coverage, provider/facility counts, updated annually but individual variables (physician counts, NP counts, population) have different internal lag years within the same release. HPSA designations are point-in-time binary flags, not a continuous annual panel.

## 9. Potential merging problems

- **The core mortality series itself has a vintage break** (§1): 1999–2020 bridged-race vs 2018–2024 single-race use different population denominators and race categories, producing different age-adjusted rates for the same overlap years (2018–2020). They cannot be concatenated into one clean trend line without an explicit, documented harmonization step (e.g., using the overlap years to estimate and report an offset, or simply analyzing the two vintages as separate series). No such harmonization exists in an official CDC product.
- CHR&R's per-measure release-year vs. measurement-year lag means a naive "merge by year" will silently misalign context variables with mortality years by 1–4 years, per measure.
- ACS 5-year estimates are rolling windows (a "2015" estimate reflects 2011–2015 data); merging by nominal year requires documenting that the value represents a window, not a point estimate, and successive years' 5-year windows overlap (not independent draws).
- CHR&R measures are FIPS-keyed but a handful of states use non-standard units (Louisiana parishes, Alaska boroughs/census areas, Virginia independent cities, Connecticut planning regions post-2022) that must be checked against the mortality data's own geography for exact code alignment.
- Geographic coverage differs by source: mortality/Census/CHR&R are essentially universal-county; PM2.5 (AQS) and Food Environment Atlas / AHRF have partial or lagged coverage — a full-covariate analytic panel is necessarily a subset of all counties, not the full ~3,100.

## 10. Missing-data problems

- 1999–2009: essentially no CHR&R and no annual ACS coverage — pre-2010 heterogeneity analysis (Section 21 of the brief) is not supportable with these sources; only mortality + Census 2000/PEP population data exist for that decade.
- PLACES-modeled behavioral variables (smoking, obesity, inactivity) are themselves model outputs with their own uncertainty, not ground-truth counts — must be documented as such, not treated as measured quantities.
- Provider/food-environment sources update irregularly, creating gaps that must be forward/backward-filled or explicitly left missing (not silently imputed) per §28 of the brief.

## 11. Suppression problems

CDC WONDER suppresses death counts **<10** outright, and flags rates as unreliable when the underlying death count is **<20** or the relative CI width exceeds 160% of the rate. Diabetes-specific deaths in low-population counties, in a single year, will frequently fall below these thresholds — this is expected to affect a substantial share of the ~3,100 U.S. counties, especially smaller/rural ones, and must be handled as a first-class data-quality dimension (never coerced to zero), consistent with §4 and §9 of the brief.

## 12. County-boundary problems

Known issues to check against during geography harmonization: NCHS's urban-rural county classification scheme changed between the 2006 and 2013 versions (some counties reclassified); CHR&R switched to 2020-Census-based rural/urban definitions in its 2024 release; a small number of county boundary/FIPS changes occurred within 1999–2024 (e.g., Connecticut's 2022 shift from counties to planning regions for some federal reporting, Alaska borough reorganizations). These require an explicit crosswalk step rather than a naive FIPS join across years.

## 13. Recommended primary statistical methodology

- **Outcome:** CDC WONDER age-adjusted rate (2000 U.S. standard population, as WONDER already computes it) as the primary outcome; crude rate carried in parallel for the required crude-vs-age-adjusted robustness comparison (§11 of the brief).
- **Primary change-point method:** Segmented (piecewise-linear) regression, fit per county/national/state series, via an iterative Muggeo-style estimator (`statsmodels` OLS with a search over candidate breakpoints, or R's `segmented` package if higher precision on breakpoint CIs is needed) — most interpretable, gives directly reportable slope-before/slope-after/CI outputs required in §18 and §35.
- **Cross-check methods:** PELT and binary segmentation, both via the `ruptures` Python library, using an L2 (or, if variance is expected to shift, a normal-mean-and-variance) cost function with a minimum-segment-length constraint tied to the minimum pre/post-year rules in §14.
- **Bayesian method:** Feasible only as a national/state-level check (not per-county at scale, for compute-cost reasons) — a Bayesian single-change-point regression (e.g., via `PyMC`) run on the national and state series only, not proposed for all ~3,100 counties.

## 14. Recommended secondary methodologies

- Trajectory classification (§15) via a pre-specified minimum-effect threshold on slope change (e.g., a magnitude and significance cutoff decided in the research protocol, not post hoc).
- Heterogeneity analysis (§21–22) via descriptive comparison + linear/logistic regression of post-break slope or trajectory class on context variables, with FDR correction for the resulting multiple comparisons (§24).
- Spatial autocorrelation check (§23) via global/local Moran's I on county-level slope estimates.
- Robustness suite (§25) run across: crude vs. age-adjusted outcome, full vs. restricted time window, alternative minimum-population thresholds, and the three change-point methods against each other.

## 15. Potential threats to validity

- The mortality-vintage break (§9) is the single largest threat: any apparent "breakpoint" near 2018–2020 could be a data-vintage artifact rather than a real trajectory change, and must be explicitly tested for in the "Could This Be an Artifact?" section (§27 of the brief).
- Small-county suppression creates systematic missingness correlated with population size — this is not missing-at-random and must be tested (§28).
- PLACES-modeled behavioral covariates carry model uncertainty that could induce spurious associations if treated as exact.
- Ecological inference: all associations are county-level, not individual-level — the brief's causal-language restrictions (§56, §21) are essential here given the observational, aggregate design.

## 16. Is the full research question feasible as originally scoped?

**Mostly yes, with one necessary scope adjustment.** Diabetes mortality breakpoint detection is feasible and well-supported by data for **1999–2020** using a single consistent CDC WONDER vintage. Extending the outcome series through 2024 using the newer single-race database is possible only as a *secondary, explicitly-flagged extension*, not a seamless continuation — the two vintages must be presented and analyzed as what they are: two overlapping-but-distinct series. Heterogeneity/context analysis (Stage 2) is well-supported from **2010 forward** (CHR&R's start), but not for 1999–2009, where socioeconomic/behavioral context data essentially does not exist at annual county resolution. A nationwide, complete PM2.5 panel is not achievable from official sources; PM2.5 must be scoped as a monitored-counties-only covariate, not a full-panel variable.

## 17. Recommended changes before implementation

1. **Reframe the temporal scope**: title/analysis should present **1999–2020 as the primary, methodologically consistent mortality trend window**, with **2018–2024 (single-race db) as a clearly labeled secondary/extension analysis**, not implied continuity. The homepage and report language (brief §29, §52) should say "1999–2020 (primary) with a 2018–2024 extension" rather than an unqualified "1999–2024."
2. **Heterogeneity/context analysis (Stage 2) should be scoped to 2010–2020**, matching CHR&R's actual availability, rather than the full mortality window.
3. **Drop PM2.5 from the required covariate set**; retain it only as an optional, monitored-counties-only sensitivity variable, explicitly labeled with its reduced coverage.
4. **Pre-2005 socioeconomic covariates** should rely on Census 2000 SF3 + PEP population only; ACS-based covariates begin at the 2005–2009 5-year vintage. This should be stated in the research protocol's inclusion criteria, not discovered later.
5. **Merge mortality-context data by each variable's CHR&R-documented measurement year, not by release year** — a small but important pipeline design decision (`src/cleaning/missingness.py` / merge logic should carry a per-variable measurement-year field, not a single "year" join key for context sources).
6. **CHR&R data is licensed for non-commercial academic/research/educational use with required attribution** — compatible with a public research-portfolio project, but the required citation string must appear in the app and report, and CHR&R trademarks may not be used in promotional material.
7. All of the above should be written into `docs/research_protocol.md` (brief §42) *before* looking at any change-point results, to lock in these inclusion/exclusion decisions ahead of analysis.

---

### Sources consulted (representative; full lists preserved per-domain in `DATA_SOURCES.md`)

CDC WONDER: wonder.cdc.gov (Underlying Cause of Death 1999–2020 and 2018–2024 Single Race help pages, API docs, data-use restrictions, age-adjustment methodology, 2013 urban-rural classification). Census: census.gov/programs-surveys/popest, census.gov/programs-surveys/acs, api.census.gov developer docs. CHR&R: countyhealthrankings.org data-documentation, measures pages, methods, terms of use. EPA: aqs.epa.gov/aqsweb/airdata, data.cdc.gov (Daily County-Level PM2.5 Concentrations). USDA: ers.usda.gov/data-products/food-environment-atlas. HRSA: data.hrsa.gov (AHRF, HPSA Find).
