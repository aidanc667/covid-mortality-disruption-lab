# Manual Data Acquisition Steps

Per brief §43: "Where APIs/downloads are unavailable or require manual access, clearly document the required manual step." This file is the single place those steps live. Everything downstream of the files produced here is scripted and reproducible; the steps themselves are not automatable because the source restricts them to its interactive web interface (see `DATA_SOURCES.md` #1–2 for why).

## CDC WONDER mortality exports (multi-cause COVID disruption design)

CDC WONDER's public API cannot group or limit National Vital Statistics System mortality queries by County, State, Region, or Urbanization — confirmed against CDC's own API documentation and a CDC-authored *Preventing Chronic Disease* article on county-level WONDER estimation. National/state/county-level data is only obtainable through the interactive web query tool.

### What needs to be pulled

Per `docs/research_protocol.md` §3–4: **two databases** (1999–2019 baseline, 2020–2024 post-shock), **two geography levels** (national, state — age-adjusted rates cannot be derived by summing across states, so national and state must each be pulled directly, not aggregated after the fact), and **8 cause-of-death series**. Two of the causes (COVID-19, and drug overdose's exact multi-intent definition) don't cleanly combine with the other six in one query, so the full pull is **8 exports**:

| # | Database | Years | Geography | Causes | Est. size |
|---|---|---|---|---|---|
| 1 | D76 (1999-2020) | 1999–2019 | National | 6: heart, cerebrovascular, diabetes, Alzheimer's, cancer, drowning | small |
| 2 | D76 | 1999–2019 | State | same 6 | medium |
| 3 | D76 | 1999–2019 | National | Drug overdose (separate — see note below) | small |
| 4 | D76 | 1999–2019 | State | Drug overdose | medium |
| 5 | D158 (2018-2024) | 2020–2024 | National | same 6 + **COVID-19** (7 causes) | small |
| 6 | D158 | 2020–2024 | State | same 7 | medium |
| 7 | D158 | 2020–2024 | National | Drug overdose | small |
| 8 | D158 | 2020–2024 | State | Drug overdose | medium |

**Why overdose is separate:** the standard CDC definition (X40-X44, X60-X64, X85, Y10-Y14) spans four different "intent" categories that live under WONDER's separate **Drug/Alcohol Induced Causes** finder tool, not the main ICD-10 Codes tree the other six causes use. Whether WONDER lets you combine selections from two different finder tools in one query is unconfirmed — rather than guess, pull it separately.

### Shared steps for every export

1. Go to https://wonder.cdc.gov/ucd-icd10.html for exports 1–4 (database D76, "Underlying Cause of Death, 1999-2020"), or https://wonder.cdc.gov/ucd-icd10-expanded.html for exports 5–8 (database D158, "Underlying Cause of Death, 2018-2024, Single Race").
2. Accept the data-use terms (public-use; no account needed — re-appears each fresh page load).
3. **Organize table layout:** Group Results By **Year**; for the state-level exports (2, 4, 6, 8) also select **And By → State**.
4. **Select year range:** 1999–2019 for exports 1–4; 2020–2024 for exports 5–8 (leave *All Years* only if you then filter with the year finder to just that range — don't submit the full 1999–2020 or 2018–2024 span, it's more than needed and more likely to time out).
5. **Select cause of death** — see the two cases below.
6. **Other options:** check **Age-Adjusted Rate** and its 95% CI, keep **Crude Rate** checked (WONDER's default), check **Show Zero Values** and **Show Suppressed Values** (critical — otherwise suppressed rows silently vanish instead of being flagged), uncheck **Show Totals**.
7. Check **Export Results**, set Export Type to **TSV** (not CSV or XLS — matches what `src/ingestion/cdc_wonder.py` parses; the loader also auto-detects CSV if TSV isn't available, but TSV is the primary target).
8. Click **Send**.

**Case A — the 6-cause group (exports 1, 2, 5, 6):** ICD-10 Codes finder → Ctrl+click to multi-select: **E10-E14** (Diabetes mellitus, under Endocrine/E00-E88), **I00-I09,I11,I13,I20-I51** (Diseases of heart, under Circulatory/I00-I99), **I60-I69** (Cerebrovascular diseases), **G30** (Alzheimer disease, under Nervous system/G00-G98), **C00-C97** (Malignant neoplasms, under Neoplasms/C00-D48), **W65-W74** (Accidental drowning and submersion, under External causes/V01-Y89 → Accidents → Nontransport). For exports 5 and 6 only, also select **U07.1** (COVID-19, under Codes for special purposes/U00-U99) — it doesn't exist before 2020 so isn't in exports 1/2.

**Case B — drug overdose (exports 3, 4, 7, 8):** use the **Drug/Alcohol Induced Causes** finder tool instead of ICD-10 Codes. Expand **Drug-induced causes** and Ctrl+click all four: **Drug poisonings (overdose) Unintentional (X40-X44)**, **Drug poisonings (overdose) Suicide (X60-X64)**, **Drug poisonings (overdose) Homicide (X85)**, **Drug poisonings (overdose) Undetermined (Y10-Y14)** — not the broader parent "Drug-induced causes" node, which includes non-overdose deaths outside the pre-registered definition.

### If a query times out or errors

Split by year range first (e.g. 1999–2009 and 2010–2019), then by a handful of states at a time if it still fails — this happened even for single-cause, single-year-range pulls during this project's earlier testing, so don't be surprised if the state-level exports (2, 4, 6, 8) need splitting. The ingestion loader concatenates multiple files automatically and de-duplicates on `(county_fips or state, year, cause)` — save each piece as its own file rather than trying to force one giant export.

### File naming and provenance

Save to `data/raw/cdc_wonder/`, named by database + geography + cause-group, e.g. `d76_national_6causes_1999_2019.txt`, `d76_state_overdose_1999_2019.txt`, `d158_national_7causes_2020_2024.txt`. Record in a sibling `.meta.json` (see `src/utils/caching.py`): export date, exact query parameters (steps 3–8 above), and who ran it.

### County-level heterogeneity data (optional, smaller scope)

The heterogeneity stage (`docs/research_protocol.md` §10) currently only needs **diabetes and drug overdose**, at **county level**, for a **pre-period** (e.g. 2015–2019) and **post-period** (2020–2024) — 2 more exports (one per database), grouped by **County** + **Year**, Case A/B causes restricted to just those two. Expect heavier suppression than the national/state pulls; that's expected and handled by the existing suppression-flag logic, not a sign something's wrong.

### Cross-check (scriptable, no manual step)

`src/ingestion/cdc_wonder.py` also pulls the **national-level** annual series via the WONDER XML API (which *is* usable at the national level) as an independent check that the manually-exported data matches — a validation step, not a data-acquisition shortcut.

## (Other sources)

Census/ACS, EPA AQS, USDA Food Environment Atlas, and HRSA AHRF are all programmatically downloadable (API or direct bulk file) — see `DATA_SOURCES.md` for each. No manual step is required for those; their ingestion modules download directly.

CHR&R has no public API; its annual files are direct, stable CSV/Excel downloads (not an interactive-query restriction like WONDER), so `src/ingestion/county_health_rankings.py` downloads them directly by URL per year rather than requiring a manual export.
