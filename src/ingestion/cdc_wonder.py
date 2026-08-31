"""CDC WONDER ingestion: county-level diabetes mortality.

County-level data cannot be pulled through WONDER's API (see
docs/manual_data_acquisition.md and DATA_SOURCES.md #1-2 for the confirmed
restriction and citations) — this module therefore has two halves:

1. `load_manual_export()` : loads, validates, and standardizes the
   tab-delimited file(s) a human exports by hand from wonder.cdc.gov,
   following the exact steps in docs/manual_data_acquisition.md. This is the
   real county-level data source.
2. `fetch_national_series()` : a genuinely scriptable call to the WONDER XML
   API for the *national* annual series only, used purely as a cross-check
   that the manually-exported county data sums to the same national totals.

Column names in WONDER's exported files are asserted, not guessed: if the
real export doesn't match `EXPECTED_COLUMNS`, `load_manual_export` raises
with the actual columns found, rather than silently mis-mapping data. This
project has already had one incorrect assumption about WONDER caught before
it reached code (see the correction note in DATA_SOURCES.md #1); the goal
here is to make the next mismatch loud instead of silent.
"""
from __future__ import annotations

import io
from dataclasses import dataclass
from pathlib import Path

import pandas as pd
import requests

from src.utils.config import DATA_RAW, DIABETES_ICD10_CODES

CDC_WONDER_RAW_DIR = DATA_RAW / "cdc_wonder"

# Column names as documented by CDC WONDER's standard "Export Results" output
# for a County x Year grouped query. VERIFY against the actual exported file
# the first time a real export is produced (docs/manual_data_acquisition.md)
# — load_manual_export() will raise a clear error listing the real columns
# if these don't match, rather than mis-parsing silently.
EXPECTED_COLUMNS = {
    "county": "County",
    "county_code": "County Code",
    "year": "Year",
    "deaths": "Deaths",
    "population": "Population",
    "crude_rate": "Crude Rate",
    "age_adjusted_rate": "Age Adjusted Rate",
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


def _validate_columns(df: pd.DataFrame, source: Path) -> None:
    missing = [c for c in EXPECTED_COLUMNS.values() if c not in df.columns]
    if missing:
        raise ValueError(
            f"{source}: WONDER export is missing expected column(s) {missing}. "
            f"Actual columns found: {list(df.columns)}. "
            "CDC may have renamed a field, or this file wasn't exported with the "
            "layout in docs/manual_data_acquisition.md — update EXPECTED_COLUMNS "
            "in src/ingestion/cdc_wonder.py to match, then re-run."
        )


def load_manual_export(subdir_files: list[Path] | None = None) -> WonderLoadResult:
    """Load one or more manually-exported WONDER files (see
    docs/manual_data_acquisition.md), concatenate, de-duplicate on
    (county_code, year), and standardize suppression/unreliability flags.

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
    combined = combined.drop_duplicates(subset=["county_fips", "year"], keep="first")
    if len(combined) != before:
        raise ValueError(
            f"Duplicate (county_fips, year) rows found across {[f.name for f in files]} "
            "after concatenation — check for overlapping year ranges between exports."
        )

    return WonderLoadResult(
        df=combined,
        source_files=files,
        n_rows=len(combined),
        n_suppressed=int(combined["deaths_suppressed"].sum()),
        n_unreliable=int(combined["age_adjusted_rate_unreliable"].sum()),
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
