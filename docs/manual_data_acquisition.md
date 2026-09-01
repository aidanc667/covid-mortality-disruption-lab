# Manual Data Acquisition Steps

Per brief §43: "Where APIs/downloads are unavailable or require manual access, clearly document the required manual step." This file is the single place those steps live. Everything downstream of the files produced here is scripted and reproducible; the steps themselves are not automatable because the source restricts them to its interactive web interface (see `DATA_SOURCES.md` #1–2 for why).

## CDC WONDER mortality exports (multi-cause COVID disruption design)

CDC WONDER's public API cannot group or limit National Vital Statistics System mortality queries by County, State, Region, or Urbanization — confirmed against CDC's own API documentation and a CDC-authored *Preventing Chronic Disease* article on county-level WONDER estimation. National/state/county-level data is only obtainable through the interactive web query tool.

### What needs to be pulled — and a real mistake worth documenting

Per `docs/research_protocol.md` §3–4: **two databases** (1999–2019 baseline, 2020–2024 post-shock) and **8 cause-of-death series**.

**Multi-cause bundling does not work and should not be attempted.** Two approaches were tried and both failed on a real pull (2026-09-01):
- Selecting multiple causes with **no** "And By: Cause of death" grouping → WONDER silently **blends all selected causes into one combined number per year** — you cannot tell which cause contributed what.
- Selecting multiple causes **with** "And By: Cause of death" → WONDER **explodes each category into every individual 4-digit ICD-10 sub-code inside it** (e.g. "Malignant neoplasms" became ~400 separate rows — one per specific cancer site, down to "external upper lip" vs. "external lower lip"). Re-aggregating this yourself is not safe: some sub-codes are suppressed, and summing while dropping suppressed rows silently *undercounts* the true category total — exactly the kind of bias this project's suppression discipline exists to prevent.

**The only reliable method: one cause per query**, exactly like the original single-disease pull that worked correctly on the first try. With only one category selected, WONDER returns its own correctly-computed, suppression-aware total directly — no blending, no explosion, no re-aggregation risk.

**Geography: national only, for now.** State-level would multiply every export below by roughly 2 (up to 30 exports total) and isn't needed to validate the core national disruption/persistence analysis — the research question's more central heterogeneity claims are at the *county* level anyway. Revisit state-level once the national numbers are confirmed trustworthy.

### The 15 exports

Every one of these is a single-cause, national-level, single-database query — no "And By" grouping of any kind needed (no State, no Cause of death).

**D76 database (1999–2019 baseline) — 7 exports, one per cause below:**

| Cause | ICD-10 Codes finder selection |
|---|---|
| Diabetes mellitus | `E10-E14` |
| Diseases of heart | `I00-I09,I11,I13,I20-I51` |
| Cerebrovascular diseases | `I60-I69` |
| Alzheimer disease | `G30` |
| Malignant neoplasms | `C00-C97` |
| Accidental drowning and submersion | `W65-W74` |
| Drug overdose | *(use the Drug/Alcohol Induced Causes finder instead — see below)* |

**D158 database (2018–2024) — the same 7, plus COVID-19 = 8 exports.** Note: pull **2018–2024**, not just 2020–2024 — the extra 2018–2019 years cost nothing extra and are required so `src/cleaning/bridging.py` has years that exist in *both* databases to calibrate the size of the vintage discontinuity (§9's hard gate in `research_protocol.md`). The excess-mortality analysis itself still only treats 2020–2024 as the post-shock period; 2018–2019 is used solely for that calibration.

### Steps for every export

1. Go to https://wonder.cdc.gov/ucd-icd10.html for the 7 D76 exports, or https://wonder.cdc.gov/ucd-icd10-expanded.html for the 8 D158 exports.
2. Accept the data-use terms (reappears each fresh page load).
3. **Organize table layout:** Group Results By **Year**. That's the only grouping — leave And By fields at "None."
4. **Select year and month:** use the finder tool — click your first year, then Shift+click your last year to select the whole range (1999 through 2019 for D76, **2018** through 2024 for D158 — not 2020, see the note above).
5. **Select cause of death:** for the 6 causes in the table above, use the **ICD-10 Codes** finder and select **exactly one** code per query — verify the "Currently selected" box shows only that one item before sending. For **drug overdose**, switch to the **Drug/Alcohol Induced Causes** finder, expand "Drug-induced causes," and Ctrl+click all four: Unintentional (X40-X44), Suicide (X60-X64), Homicide (X85), Undetermined (Y10-Y14) — this one query legitimately needs multiple selections, since the standard CDC overdose definition itself spans four intent categories; unlike the 6-cause bundling attempt, this works because it's the *same* underlying measure split by intent, not different diseases being merged. For **COVID-19** (D158 exports only), ICD-10 Codes finder → `U07.1`.
6. **Other options:** check **Age-Adjusted Rate** and its 95% CI, keep **Crude Rate** checked, check **Show Zero Values** and **Show Suppressed Values**, uncheck **Show Totals**.
7. Check **Export Results**, set Export Type to **CSV** (verified working against a real export; the loader auto-detects delimiter either way).
8. Click **Send**.

### If a query times out or errors

Split by year range (e.g. 1999–2009 and 2010–2019) — unlikely to be needed at national level for a single cause, but the state-level exports hit this during earlier testing even for narrower queries. The ingestion loader concatenates multiple files automatically and de-duplicates on `(year, cause)`.

### File naming and provenance

Save to `data/raw/cdc_wonder/`, named by database + cause, e.g. `d76_national_diabetes_1999_2019.csv`, `d158_national_covid19_2018_2024.csv` (note the D158 files span 2018–2024 per the note above, not 2020–2024, even though the analysis only uses 2020–2024 of it). Record in a sibling `.meta.json` (see `src/utils/caching.py`): export date, exact query parameters, and who ran it.

### County-level heterogeneity data (later, smaller scope)

The heterogeneity stage (`docs/research_protocol.md` §10) needs **diabetes and drug overdose only**, at **county level**, for a pre-period and post-period — 2 more exports, same one-cause-per-query rule, grouped by **County** + **Year**. Expect heavier suppression than the national pulls; that's expected, not a sign something's wrong. Do this after the 15 national exports above are working end to end.

### Cross-check (scriptable, no manual step)

`src/ingestion/cdc_wonder.py` also pulls the **national-level** annual series via the WONDER XML API (which *is* usable at the national level) as an independent check that the manually-exported data matches — a validation step, not a data-acquisition shortcut.

## (Other sources)

Census/ACS, EPA AQS, USDA Food Environment Atlas, and HRSA AHRF are all programmatically downloadable (API or direct bulk file) — see `DATA_SOURCES.md` for each. No manual step is required for those; their ingestion modules download directly.

CHR&R has no public API; its annual files are direct, stable CSV/Excel downloads (not an interactive-query restriction like WONDER), so `src/ingestion/county_health_rankings.py` downloads them directly by URL per year rather than requiring a manual export.
