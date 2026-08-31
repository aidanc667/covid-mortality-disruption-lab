"""Tests for the WONDER manual-export loader, using synthetic fixture files
shaped like a real "Export Results" download (see EXPECTED_COLUMNS in
src/ingestion/cdc_wonder.py). Real WONDER files are not available until the
manual export step in docs/manual_data_acquisition.md is performed; these
tests verify the parsing/suppression/validation logic independent of that.
"""
import pytest

from src.ingestion.cdc_wonder import load_manual_export, _read_wonder_export, _validate_columns

FIXTURE_HEADER = "County\tCounty Code\tYear\tDeaths\tPopulation\tCrude Rate\tAge Adjusted Rate"


def _write_fixture(tmp_path, name, rows):
    lines = [FIXTURE_HEADER] + rows + ["---", '"Total"\t""\t""\t"0"\t"0"\t"0"\t"0"']
    path = tmp_path / name
    path.write_text("\n".join(lines))
    return path


def test_load_manual_export_parses_basic_rows(tmp_path):
    f = _write_fixture(tmp_path, "export1.txt", [
        "Autauga County, AL\t01001\t2010\t12\t54000\t22.2\t21.5",
        "Baldwin County, AL\t01003\t2010\t45\t183000\t24.6\t23.1",
    ])
    result = load_manual_export(subdir_files=[f])
    assert result.n_rows == 2
    assert result.n_suppressed == 0
    assert set(result.df["county_fips"]) == {"01001", "01003"}


def test_load_manual_export_preserves_suppressed_flags_no_zero_coercion(tmp_path):
    f = _write_fixture(tmp_path, "export1.txt", [
        "Loving County, TX\t48301\t2010\tSuppressed\t82\tSuppressed\tSuppressed",
    ])
    result = load_manual_export(subdir_files=[f])
    row = result.df.iloc[0]
    assert row["deaths_suppressed"] is True or bool(row["deaths_suppressed"]) is True
    assert pd.isna(row["deaths"])  # never coerced to 0
    assert result.n_suppressed == 1


def test_load_manual_export_preserves_unreliable_flags(tmp_path):
    f = _write_fixture(tmp_path, "export1.txt", [
        "Some County, AL\t01005\t2010\t15\t9000\t166.7\tUnreliable",
    ])
    result = load_manual_export(subdir_files=[f])
    row = result.df.iloc[0]
    assert row["age_adjusted_rate_unreliable"]
    assert pd.isna(row["age_adjusted_rate"])


def test_load_manual_export_raises_on_duplicate_county_year(tmp_path):
    f1 = _write_fixture(tmp_path, "export1.txt", [
        "Autauga County, AL\t01001\t2010\t12\t54000\t22.2\t21.5",
    ])
    f2 = _write_fixture(tmp_path, "export2.txt", [
        "Autauga County, AL\t01001\t2010\t12\t54000\t22.2\t21.5",
    ])
    with pytest.raises(ValueError, match="Duplicate"):
        load_manual_export(subdir_files=[f1, f2])


def test_load_manual_export_raises_clearly_on_missing_expected_column(tmp_path):
    path = tmp_path / "bad_export.txt"
    path.write_text("County\tCounty Code\tYear\tDeaths\n" "Autauga County, AL\t01001\t2010\t12\n---\n")
    with pytest.raises(ValueError, match="missing expected column"):
        load_manual_export(subdir_files=[path])


def test_load_manual_export_missing_directory_raises_filenotfound(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_manual_export(subdir_files=[])


def test_load_manual_export_parses_real_csv_export_format(tmp_path):
    # Shaped exactly like a real WONDER CSV export (confirmed 2026-08-31):
    # comma-delimited, a leading empty "Notes" column, and a trailing
    # Messages/Footnotes/Caveats block starting with a quoted `"---"` line
    # (not a bare `---`) — both quirks caused real parsing bugs on first
    # contact with actual data.
    content = (
        '"Notes","County","County Code","Year","Year Code",Deaths,Population,Crude Rate,Age Adjusted Rate\n'
        ',"Autauga County, AL","01001","2020","2020",27,56145,48.1,41.8\n'
        ',"Barbour County, AL","01005","2020","2020",Suppressed,24589,Suppressed,Suppressed\n'
        ',"Blount County, AL","01009","2020","2020",12,57879,Unreliable,Unreliable\n'
        '"---"\n'
        'Messages:\n'
        '"1. Totals are not available for these results due to suppression constraints."\n'
        '"---"\n'
        'Footnotes:\n'
        '"1. Data are not available for this area for all of the requested years."\n'
    )
    path = tmp_path / "real_export.csv"
    path.write_text(content)

    result = load_manual_export(subdir_files=[path])
    assert result.n_rows == 3
    assert set(result.df["county_fips"]) == {"01001", "01005", "01009"}
    assert result.n_suppressed == 1
    assert result.n_unreliable == 1
    autauga = result.df[result.df["county_fips"] == "01001"].iloc[0]
    assert autauga["deaths"] == 27
    assert autauga["age_adjusted_rate"] == 41.8


import pandas as pd  # noqa: E402  (kept at bottom to mirror fixture usage above)
