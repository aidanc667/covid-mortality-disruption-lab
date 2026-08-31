# Manual Data Acquisition Steps

Per brief §43: "Where APIs/downloads are unavailable or require manual access, clearly document the required manual step." This file is the single place those steps live. Everything downstream of the files produced here is scripted and reproducible; the steps themselves are not automatable because the source restricts them to its interactive web interface (see `DATA_SOURCES.md` #1–2 for why).

## CDC WONDER county-level mortality exports

CDC WONDER's public API cannot group or limit National Vital Statistics System mortality queries by County (or State/Region/Urbanization) — confirmed against CDC's own API documentation and a CDC-authored *Preventing Chronic Disease* article on county-level WONDER estimation. County-level data is only obtainable through the interactive web query tool.

### Export 1 — primary window (1999–2020, bridged-race)

1. Go to https://wonder.cdc.gov/ucd-icd10.html ("Underlying Cause of Death, 1999-2020").
2. Accept the data-use terms (public-use; no account needed).
3. **Organize table layout:** Group results by **County**, then **Year**.
4. **Select demographics:** leave Age Groups / Gender / Race at "All" for the primary panel (age/sex/race-stratified pulls, if ever needed, are separate, additional exports — not required for the primary outcome).
5. **Select year range:** 1999–2020, all years.
6. **Select cause of death:** UCD - ICD-10 Codes → enter/select **E10–E14** (Diabetes mellitus).
7. **Other options:** check "Age-Adjusted Rates," and set "Rate Options" to per 100,000, 2000 U.S. standard population (WONDER's default). Confirm Crude Rate is also included.
8. Send the query; on the results page use **Export Results** to download the full table as a tab-delimited text file.
9. If the query is rejected for exceeding WONDER's row-count export limit, split by roughly equal year ranges (e.g., 1999–2009 and 2010–2020) and export each separately — the ingestion loader concatenates and de-duplicates by `(county_fips, year)`.
10. Save the file(s) to `data/raw/cdc_wonder/ucd_1999_2020_raw_<range>.txt`, and record in a sibling `.meta.json` (see `src/utils/caching.py`): the export date, the exact query parameters used (steps 3–7 above), and who ran it.

### Export 2 — extension window (2018–2024, single-race)

Repeat the same steps at https://wonder.cdc.gov/ucd-icd10-expanded.html ("Underlying Cause of Death, 2018-2024, Single Race"), years 2018–2024, saved to `data/raw/cdc_wonder/ucd_2018_2024_raw.txt`.

### Cross-check (scriptable, no manual step)

`src/ingestion/cdc_wonder.py` also pulls the **national-level** annual diabetes mortality series via the WONDER XML API (which *is* usable at the national level) as an independent check that the manually-exported county data sums to the same national totals — a validation step, not a data-acquisition shortcut.

## (Other sources)

Census/ACS, EPA AQS, USDA Food Environment Atlas, and HRSA AHRF are all programmatically downloadable (API or direct bulk file) — see `DATA_SOURCES.md` for each. No manual step is required for those; their ingestion modules download directly.

CHR&R has no public API; its annual files are direct, stable CSV/Excel downloads (not an interactive-query restriction like WONDER), so `src/ingestion/county_health_rankings.py` downloads them directly by URL per year rather than requiring a manual export.
