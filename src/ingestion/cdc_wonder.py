"""CDC WONDER ingestion: national/state/county-level mortality, multi-cause.

County-level data cannot be pulled through WONDER's API (see
docs/manual_data_acquisition.md and DATA_SOURCES.md #1-2 for the confirmed
restriction and citations) — this module therefore has two halves:

1. `load_manual_export()` : loads, validates, and standardizes the
   CSV/TSV file(s) a human exports by hand from wonder.cdc.gov, following
   the exact steps in docs/manual_data_acquisition.md. This is the real
   data source, at whichever geography level (national, state, or county)
   the export was grouped by.
2. `fetch_national_series()` : a genuinely scriptable call to the WONDER XML
   API for the *national* annual series only, used purely as a cross-check
   that the manually-exported data matches.

Column names in WONDER's exported files are asserted, not guessed: if the
real export doesn't match REQUIRED_COLUMNS, `load_manual_export` raises
with the actual columns found, rather than silently mis-mapping data. This
project has already had two incorrect assumptions about WONDER caught
before they reached downstream code (see DATA_SOURCES.md #1, and the
national-vs-county-only-hardcoded bug fixed 2026-09-01 after the first
national-level export failed validation) — the goal is to keep making the
next mismatch loud instead of silent.
"""
from __future__ import annotations

import io
from dataclasses import dataclass
from pathlib import Path

import pandas as pd
import requests

from src.utils.config import DATA_RAW, DIABETES_ICD10_CODES

CDC_WONDER_RAW_DIR = DATA_RAW / "cdc_wonder"

# Present in every export regardless of geography level.
REQUIRED_COLUMNS = {
    "year": "Year",
    "deaths": "Deaths",
    "population": "Population",
    "crude_rate": "Crude Rate",
}

# Present in most exports, but confirmed absent (2026-09-01) from real
# D158 (2018-2024, Single Race) exports grouped by County -- WONDER simply
# does not offer age-adjustment at that geography level for that database,
# likely because single-race population estimates lack the age-stratified
# denominators needed to standardize at fine geography. This is a whole-file
# capability gap, not per-cell suppression, so it's handled separately from
# REQUIRED_COLUMNS rather than raising.
OPTIONAL_COLUMNS = {
    "age_adjusted_rate": "Age Adjusted Rate",
}

# Present only when the export was grouped by that geography level.
# National exports (Group Results By: Year only) have NEITHER of these --
# confirmed against a real export 2026-09-01 (the drowning pull, national,
# 1999-2019: header was Notes/Year/Year Code/Deaths/Population/Crude
# Rate/.../Age Adjusted Rate/..., no location column at all).
GEOGRAPHY_COLUMNS = {
    "county": {"county": "County", "county_code": "County Code"},
    "state": {"state": "State", "state_code": "State Code"},
}

SUPPRESSED_TOKENS = {"Suppressed"}
UNRELIABLE_TOKENS = {"Unreliable", "Not Applicable"}

WONDER_API_ENDPOINT = "https://wonder.cdc.gov/controller/datarequest/{database_code}"


@dataclass
class WonderLoadResult:
    df: pd.DataFrame
    source_files: list[Path]
    n_rows: int
    n_suppressed: int
    n_unreliable: int
    geography: str  # "national", "state", or "county"
    age_adjusted_rate_available: bool = True


def _read_wonder_export(path: Path) -> pd.DataFrame:
    """Read one WONDER export (CSV or TSV — confirmed both occur depending
    on the Export Type the user picks in the web form; delimiter is
    detected from the header line rather than assumed), stripping the
    trailing Messages/Footnotes/Caveats block WONDER appends after the data
    rows. Confirmed against a real export: that block is separated by a
    line whose entire (quoted) content is `"---"` — not a bare `---` — so
    the check strips quotes before comparing, and the file layout has an
    empty leading "Notes" column, which is harmless since columns are
    selected by name, not position."""
    raw = path.read_text(encoding="utf-8-sig")
    lines = raw.splitlines()
    sep = "\t" if lines and "\t" in lines[0] else ","

    data_lines = []
    for line in lines:
        if line.strip().strip('"') == "---":
            break
        data_lines.append(line)
    return pd.read_csv(io.StringIO("\n".join(data_lines)), sep=sep)


def _detect_geography(df: pd.DataFrame, source: Path) -> str:
    """Determine which geography level an export was grouped by, from
    which location columns are present -- never assumed from context
    (e.g. which URL was used), since a human could group by County, State,
    or neither regardless of database."""
    has_county = all(c in df.columns for c in GEOGRAPHY_COLUMNS["county"].values())
    has_state = all(c in df.columns for c in GEOGRAPHY_COLUMNS["state"].values())
    if has_county and has_state:
        raise ValueError(
            f"{source}: export has both County and State columns -- this loader expects "
            "exactly one geography level per file (per docs/manual_data_acquisition.md, "
            "queries should be grouped by a single geography, not both at once)."
        )
    if has_county:
        return "county"
    if has_state:
        return "state"
    return "national"


def _validate_columns(df: pd.DataFrame, source: Path) -> None:
    missing = [c for c in REQUIRED_COLUMNS.values() if c not in df.columns]
    if missing:
        raise ValueError(
            f"{source}: WONDER export is missing expected column(s) {missing}. "
            f"Actual columns found: {list(df.columns)}. "
            "CDC may have renamed a field, or this file wasn't exported with the "
            "layout in docs/manual_data_acquisition.md — update REQUIRED_COLUMNS "
            "in src/ingestion/cdc_wonder.py to match, then re-run."
        )


def load_manual_export(
    subdir_files: list[Path] | None = None, cause_label: str | None = None
) -> WonderLoadResult:
    """Load one or more manually-exported WONDER files (see
    docs/manual_data_acquisition.md), concatenate, de-duplicate, and
    standardize suppression/unreliability flags. All files in one call
    must share the same geography level (national, state, or county) --
    mixing levels in one call is almost certainly a mistake, not a valid
    combination, so it raises rather than silently picking one.

    `cause_label`: required for single-cause exports that have no
    "Cause of death" column of their own (true for every export in this
    project's design -- see docs/manual_data_acquisition.md's finding that
    multi-cause bundling doesn't work). Must be left as None for the rare
    case of a file that does carry its own "Cause of death" column; passing
    both raises, since only one source of truth for `cause` is allowed.

    Raw suppressed/unreliable cells are NEVER coerced to zero or dropped —
    they are preserved as explicit boolean flag columns alongside a NaN rate,
    per research_protocol.md #6.
    """
    files = sorted(CDC_WONDER_RAW_DIR.glob("*.txt")) if subdir_files is None else subdir_files
    if not files:
        raise FileNotFoundError(
            f"No WONDER export files found in {CDC_WONDER_RAW_DIR}. "
            "Follow docs/manual_data_acquisition.md to produce them first."
        )

    frames = []
    geographies = set()
    for f in files:
        df = _read_wonder_export(f)
        _validate_columns(df, f)
        geography = _detect_geography(df, f)
        geographies.add(geography)

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
                    "cause_label was passed. Single-cause exports must specify "
                    "cause_label explicitly, e.g. load_manual_export(cause_label='Diabetes mellitus')."
                )
            df["cause"] = cause_label
        df["_source_file"] = f.name
        frames.append(df)

    if len(geographies) > 1:
        raise ValueError(
            f"Mixed geography levels across {[f.name for f in files]}: {geographies}. "
            "Load each geography level in a separate call."
        )
    geography = geographies.pop()

    combined = pd.concat(frames, ignore_index=True)
    rename_map = {v: k for k, v in REQUIRED_COLUMNS.items()}
    if geography in GEOGRAPHY_COLUMNS:
        rename_map.update({v: k for k, v in GEOGRAPHY_COLUMNS[geography].items()})
    has_age_adjusted_rate = OPTIONAL_COLUMNS["age_adjusted_rate"] in combined.columns
    if has_age_adjusted_rate:
        rename_map[OPTIONAL_COLUMNS["age_adjusted_rate"]] = "age_adjusted_rate"
    combined = combined.rename(columns=rename_map)

    if geography == "county":
        combined["county_fips"] = combined["county_code"].astype(str).str.zfill(5)
        dedup_keys = ["county_fips", "year", "cause"]
    elif geography == "state":
        # State FIPS codes are conventionally 2-digit zero-padded (e.g. "01"
        # for Alabama) -- without this, pandas infers the column as integer
        # and silently drops the leading zero, same class of bug already
        # fixed for county_fips.
        combined["state_code"] = combined["state_code"].astype(str).str.zfill(2)
        dedup_keys = ["state_code", "year", "cause"]
    else:
        dedup_keys = ["year", "cause"]

    rate_cols = ["deaths", "crude_rate"] + (["age_adjusted_rate"] if has_age_adjusted_rate else [])
    for col in rate_cols:
        raw_col = combined[col].astype(str)
        combined[f"{col}_suppressed"] = raw_col.isin(SUPPRESSED_TOKENS)
        combined[f"{col}_unreliable"] = raw_col.isin(UNRELIABLE_TOKENS)
        combined[col] = pd.to_numeric(combined[col], errors="coerce")

    if not has_age_adjusted_rate:
        # Whole-file capability gap, not per-cell suppression -- NaN with
        # both flags False, never True, so downstream code can't mistake
        # "database doesn't offer this" for "value was privacy-suppressed".
        combined["age_adjusted_rate"] = float("nan")
        combined["age_adjusted_rate_suppressed"] = False
        combined["age_adjusted_rate_unreliable"] = False

    before = len(combined)
    combined = combined.drop_duplicates(subset=dedup_keys, keep="first")
    if len(combined) != before:
        raise ValueError(
            f"Duplicate {tuple(dedup_keys)} rows found across {[f.name for f in files]} "
            "after concatenation — check for overlapping year ranges between exports."
        )

    return WonderLoadResult(
        df=combined,
        source_files=files,
        n_rows=len(combined),
        n_suppressed=int(combined["deaths_suppressed"].sum()),
        n_unreliable=int(combined["age_adjusted_rate_unreliable"].sum()),
        geography=geography,
        age_adjusted_rate_available=has_age_adjusted_rate,
    )


def fetch_national_series(database_code: str, icd10_codes: list[str] | None = None) -> pd.DataFrame:
    """Pull the NATIONAL annual diabetes mortality series via WONDER's XML API.

    This is a cross-check only (research_protocol.md, DATA_SOURCES.md #1) —
    the API is confirmed usable at the national level, unlike county level.

    `database_code` must be the WONDER database identifier for the vintage in
    question (e.g. the code shown when generating an "Export Request XML"
    from an actual national-level query at wonder.cdc.gov for that database —
    not hardcoded here, since CDC has changed these codes across vintages and
    guessing one would risk silently querying the wrong database).
    """
    raise NotImplementedError(
        "fetch_national_series requires a WONDER database_code confirmed from "
        "an actual 'Export Request XML' generated at wonder.cdc.gov for the "
        "database being queried (see the API doc's guidance to read parameter "
        "names off the web form / a real export). Populate database_code and "
        "the request XML template here once that value has been obtained and "
        "verified, rather than assuming one."
    )
