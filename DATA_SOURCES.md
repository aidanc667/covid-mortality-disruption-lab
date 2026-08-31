# Data Sources

Formal data-source inventory, per project brief §4. Every entry below was verified against the cited official documentation during the Phase 1 feasibility audit ([`docs/data_feasibility_audit.md`](docs/data_feasibility_audit.md)); nothing here is assumed. "Exact transformation performed" is filled in as each ingestion module is built (Phase 2/3) — entries marked *(pending implementation)* describe the planned transformation, not yet code-verified.

---

## 1. CDC WONDER — Underlying Cause of Death, 1999–2020 (primary mortality source)

- **Source name:** CDC WONDER, National Center for Health Statistics
- **URL:** https://wonder.cdc.gov/wonder/help/ucd.html (API: https://wonder.cdc.gov/wonder/help/wonder-api.html)
- **Dataset name:** Underlying Cause of Death, 1999–2020
- **Variables:** deaths, population, crude rate, age-adjusted rate (2000 U.S. standard population), 95% CI, standard error — by county, year, age group, sex, race (bridged, 4 categories)
- **Geographic resolution:** County (5-digit FIPS)
- **Temporal coverage:** 1999–2020, annual
- **Download method:** **Manual, not API.** CDC's own API documentation and a CDC-authored *Preventing Chronic Disease* methods article ("Estimating County-Level Mortality Rates Using Highly Censored Data From CDC WONDER") confirm that, per NVSS public-data-sharing policy, WONDER's XML API **cannot group or limit mortality queries by Region, Division, State, County, or Urbanization** — those geography fields exist only in the interactive web interface. County-level data must be pulled via a manual query at wonder.cdc.gov (group by County + Year, filter ICD-10 E10–E14, check Deaths/Population/Crude Rate/Age-Adjusted Rate/CI, "Export Results"), then ingested/validated/cached programmatically from the resulting file. An earlier research pass on this project incorrectly reported full API scriptability for this step; that was caught and corrected before any ingestion code was written. The national-level API remains usable as an independent cross-check that the manually-exported county data aggregates to the same national totals.
- **Update date:** Frozen (bridged-race series discontinued by NCHS, final release ~mid-2023)
- **Licensing/access restrictions:** Public-use aggregate data, no data-use agreement required; suppression rules (see limitations) must be respected — counts <10 may not be presented.
- **Known limitations:** Counts <10 suppressed; rates flagged "Unreliable" if death count <20 or relative CI width >160% of the rate; uses bridged-race population denominators (1977 OMB standard) that are methodologically distinct from the 2018–2024 database.
- **Exact transformation performed:** *(pending implementation — planned: filter to ICD-10 E10–E14 underlying cause; retain suppressed/unreliable flags as explicit categorical fields, never coerced to zero or dropped)*

## 2. CDC WONDER — Underlying Cause of Death, 2018–2024, Single Race (secondary/extension mortality source)

- **Source name:** CDC WONDER, National Center for Health Statistics
- **URL:** https://wonder.cdc.gov/wonder/help/ucd-expanded.html
- **Dataset name:** Underlying Cause of Death, 2018–2024, Single Race
- **Variables:** Same as above, with single-race population denominators (6/15/31 category options)
- **Geographic resolution:** County (5-digit FIPS)
- **Temporal coverage:** 2018–2024 (2024 finalized ~Feb 2026)
- **Download method:** Same manual-export requirement as Source 1 (different database on wonder.cdc.gov's interactive interface); API is national-level-only for this database too. **Verified 2026-08-31:** database code is **D158**; the query form's structure (measure checkboxes, field naming) is nearly identical to Source 1's, so the same ingestion code parses both without changes.
- **Update date:** Actively updated annually. **Verified 2026-08-31: the Year finder lists exactly 2018–2024 — no 2025 data exists in this database yet** (CDC WONDER mortality data typically has a 12–24 month finalization lag; 2025 deaths are presumably still being coded).
- **Licensing/access restrictions:** Same as above
- **Known limitations:** Not concatenable with Source 1 for 2018–2020 overlap years due to differing population bases — see [`research_protocol.md`](docs/research_protocol.md) §5.
- **Exact transformation performed:** *(pending implementation — used only for the labeled 2018–2024 extension analysis, never merged into the primary 1999–2020 series)*

## 3. U.S. Census Bureau — Population Estimates Program (PEP)

- **Source name:** U.S. Census Bureau
- **URL:** https://www.census.gov/programs-surveys/popest.html
- **Dataset name:** Population and Housing Unit Estimates
- **Variables:** total population, age/sex/race breakdowns, components of change
- **Geographic resolution:** County (GEOID)
- **Temporal coverage:** Annual, 1999–present
- **Download method:** Census API (`api.census.gov`, free key via https://api.census.gov/data/key_signup.html) and direct CSV downloads
- **Update date:** Annual vintage releases; historical years subject to periodic revision
- **Licensing/access restrictions:** Public domain
- **Known limitations:** Historical estimates are revised as new vintages incorporate updated birth/death/migration data; a given past year's population can differ slightly across vintages.
- **Exact transformation performed:** *(pending implementation — planned: mortality-rate denominators taken from the same vintage as each WONDER database to keep rate calculations internally consistent)*

## 4. U.S. Census Bureau — American Community Survey (ACS) 5-Year Estimates

- **Source name:** U.S. Census Bureau
- **URL:** https://www.census.gov/programs-surveys/acs/
- **Dataset name / tables:** S1901 (median household income), S1701 (poverty), S1501 (educational attainment), S2701 (health insurance coverage), DP05 (demographics/density)
- **Geographic resolution:** County (GEOID)
- **Temporal coverage:** 2005–2009 vintage forward (annual rolling 5-year windows); **no equivalent exists for 1999–2004**
- **Download method:** Census API, key required
- **Update date:** Annual
- **Licensing/access restrictions:** Public domain
- **Known limitations:** Each "year" is a 5-year rolling average (e.g., "2015" = 2011–2015 data), not a point-in-time value; successive years' windows overlap and are not statistically independent; margins of error can be large for small counties.
- **Exact transformation performed:** *(pending implementation — planned: retain the 5-year window label explicitly in the analytic table's column name, e.g. `median_income_acs5_2011_2015`, rather than a bare year, to prevent false precision)*

## 5. County Health Rankings & Roadmaps (CHR&R)

- **Source name:** University of Wisconsin Population Health Institute (RWJF-funded)
- **URL:** https://www.countyhealthrankings.org/health-data/methodology-and-sources/data-documentation
- **Dataset name:** County Health Rankings & Roadmaps Annual Data Release
- **Variables:** % uninsured, primary care physician ratio, % adult smokers, % adult obesity, % physically inactive, % children in poverty, median household income, education, food environment index, severe housing cost burden, PM2.5, % rural
- **Geographic resolution:** County (FIPS), with known non-standard units in LA (parishes), AK (boroughs/census areas), VA (independent cities), CT (planning regions post-2022)
- **Temporal coverage:** Annual releases 2010–2025; **each measure has its own measurement year, lagging the release year by 1–4 years** (documented per-measure by CHR&R)
- **Download method:** Direct CSV/Excel/SAS download from the data-documentation page
- **Update date:** 2025 release (with a March 2026 supplemental update for select PLACES-modeled measures)
- **Licensing/access restrictions:** Free for non-commercial academic/research/educational/public-health use with required attribution: *"University of Wisconsin Population Health Institute. County Health Rankings & Roadmaps [year]. www.countyhealthrankings.org"*. Commercial use and use of CHR&R trademarks in promotional material require written consent — not applicable to this research/educational project, but the attribution requirement is enforced in the app footer and report.
- **Known limitations:** Smoking/obesity/physical-inactivity are PLACES multilevel-regression-and-poststratification model estimates, not raw counts; no data before 2010; methodology changes in the 2024 release (rural/urban definition, race-bridging discontinuation) affect cross-year comparability for some measures.
- **Exact transformation performed:** *(pending implementation — planned: merge by each variable's documented measurement year, not release year; small-population/unreliable flags per CHR&R's own suppression rules preserved as explicit fields)*

## 6. EPA Air Quality System (AQS) — AirData PM2.5

- **Source name:** U.S. Environmental Protection Agency
- **URL:** https://aqs.epa.gov/aqsweb/airdata/download_files.html
- **Dataset name:** AirData PM2.5 Monitor Data (annual county summary files)
- **Variables:** annual average PM2.5 concentration (monitor-based)
- **Geographic resolution:** County, limited to counties with an active monitor (~20% of U.S. counties)
- **Temporal coverage:** 1998–2026 (for monitored counties only)
- **Download method:** Bulk ZIP download; EPA AQS API also available
- **Update date:** Annually updated
- **Licensing/access restrictions:** Public domain
- **Known limitations:** No official nationwide-coverage county-level PM2.5 panel exists; per the research protocol, this variable is retained only as a monitored-counties-only sensitivity covariate, not a full-panel variable.
- **Exact transformation performed:** *(pending implementation — planned: `pm25_monitored` flag column added alongside the value so downstream analyses can distinguish "not polluted" from "not monitored")*

## 7. USDA ERS Food Environment Atlas

- **Source name:** USDA Economic Research Service
- **URL:** https://www.ers.usda.gov/data-products/food-environment-atlas/data-access-and-documentation-downloads
- **Dataset name:** Food Environment Atlas
- **Variables:** food insecurity rate, low-income/low-access population share, grocery/supermarket density, fast-food density
- **Geographic resolution:** County (FIPS), full national coverage
- **Temporal coverage:** 2012–2025, updated irregularly (not annual); **no coverage before 2012**
- **Download method:** Direct Excel/CSV download (ZIP archive)
- **Update date:** Last known update 2025-07-30
- **Licensing/access restrictions:** Public domain
- **Known limitations:** Not annually updated; some variable definitions have changed across releases.
- **Exact transformation performed:** *(pending implementation)*

## 8. HRSA Area Health Resources File (AHRF)

- **Source name:** Health Resources and Services Administration
- **URL:** https://data.hrsa.gov/topics/health-workforce/nchwa/ahrf (downloads: https://data.hrsa.gov/data/download)
- **Dataset name:** Area Health Resources File
- **Variables:** physician counts/ratios, nurse practitioner counts, facility counts, population characteristics
- **Geographic resolution:** County, full national coverage
- **Temporal coverage:** Annual release; individual variables carry different internal lag years within the same release (e.g., 2023 physician data inside a 2024 file)
- **Download method:** Direct download (SAS/CSV/ASCII) from the HRSA data portal
- **Update date:** Most recent release referenced 2024 data, published 2026
- **Licensing/access restrictions:** Public domain
- **Known limitations:** Provider counts are not real-time; each variable's true reference year must be checked in HRSA's technical documentation rather than assumed from the file's nominal release year.
- **Exact transformation performed:** *(pending implementation)*

---

*All entries above will be re-verified for URL/format drift at the start of Phase 2 implementation, since documentation portals for these sources are periodically restructured.*
