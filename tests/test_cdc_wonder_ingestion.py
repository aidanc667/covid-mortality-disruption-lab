"""Tests for the WONDER manual-export loader, using synthetic fixture files
shaped like a real "Export Results" download (see EXPECTED_COLUMNS in
src/ingestion/cdc_wonder.py). Real WONDER files are not available until the
manual export step in docs/manual_data_acquisition.md is performed; these
tests verify the parsing/suppression/validation logic independent of that.
"""
import pandas as pd
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
    result = load_manual_export(subdir_files=[f], cause_label="Diabetes mellitus")
    assert result.n_rows == 2
    assert result.n_suppressed == 0
    assert set(result.df["county_fips"]) == {"01001", "01003"}


def test_load_manual_export_preserves_suppressed_flags_no_zero_coercion(tmp_path):
    f = _write_fixture(tmp_path, "export1.txt", [
        "Loving County, TX\t48301\t2010\tSuppressed\t82\tSuppressed\tSuppressed",
    ])
    result = load_manual_export(subdir_files=[f], cause_label="Diabetes mellitus")
    row = result.df.iloc[0]
    assert row["deaths_suppressed"] is True or bool(row["deaths_suppressed"]) is True
    assert pd.isna(row["deaths"])  # never coerced to 0
    assert result.n_suppressed == 1


def test_load_manual_export_preserves_unreliable_flags(tmp_path):
    f = _write_fixture(tmp_path, "export1.txt", [
        "Some County, AL\t01005\t2010\t15\t9000\t166.7\tUnreliable",
    ])
    result = load_manual_export(subdir_files=[f], cause_label="Diabetes mellitus")
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
        load_manual_export(subdir_files=[f1, f2], cause_label="Diabetes mellitus")


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

    result = load_manual_export(subdir_files=[path], cause_label="Diabetes mellitus")
    assert result.n_rows == 3
    assert set(result.df["county_fips"]) == {"01001", "01005", "01009"}
    assert result.n_suppressed == 1
    assert result.n_unreliable == 1
    autauga = result.df[result.df["county_fips"] == "01001"].iloc[0]
    assert autauga["deaths"] == 27
    assert autauga["age_adjusted_rate"] == 41.8


def test_load_manual_export_requires_cause_label_for_single_cause_file(tmp_path):
    f = _write_fixture(tmp_path, "export1.txt", [
        "Autauga County, AL\t01001\t2010\t12\t54000\t22.2\t21.5",
    ])
    with pytest.raises(ValueError, match="no cause_label was passed"):
        load_manual_export(subdir_files=[f])


def test_load_manual_export_applies_cause_label_to_single_cause_file(tmp_path):
    f = _write_fixture(tmp_path, "export1.txt", [
        "Autauga County, AL\t01001\t2010\t12\t54000\t22.2\t21.5",
    ])
    result = load_manual_export(subdir_files=[f], cause_label="Diabetes mellitus")
    assert (result.df["cause"] == "Diabetes mellitus").all()


def test_load_manual_export_reads_cause_column_from_multi_cause_file(tmp_path):
    header = FIXTURE_HEADER + "\tCause of death"
    lines = [header] + [
        "Autauga County, AL\t01001\t2010\t12\t54000\t22.2\t21.5\tDiabetes mellitus (E10-E14)",
        "Autauga County, AL\t01001\t2010\t45\t54000\t83.3\t80.1\tDiseases of heart (I00-I09,I11,I13,I20-I51)",
    ]
    path = tmp_path / "multi_cause.txt"
    path.write_text("\n".join(lines + ["---", '"Total"']))
    result = load_manual_export(subdir_files=[path])
    assert set(result.df["cause"]) == {
        "Diabetes mellitus (E10-E14)",
        "Diseases of heart (I00-I09,I11,I13,I20-I51)",
    }
    assert len(result.df) == 2  # same county+year, different cause -> not deduped away


def test_load_manual_export_rejects_cause_label_when_file_has_own_column(tmp_path):
    header = FIXTURE_HEADER + "\tCause of death"
    lines = [header, "Autauga County, AL\t01001\t2010\t12\t54000\t22.2\t21.5\tDiabetes mellitus (E10-E14)"]
    path = tmp_path / "multi_cause.txt"
    path.write_text("\n".join(lines + ["---", '"Total"']))
    with pytest.raises(ValueError, match="cause_label"):
        load_manual_export(subdir_files=[path], cause_label="Diabetes mellitus")


def test_load_manual_export_dedup_key_includes_cause(tmp_path):
    header = FIXTURE_HEADER + "\tCause of death"
    lines = [header] + [
        "Autauga County, AL\t01001\t2010\t12\t54000\t22.2\t21.5\tDiabetes mellitus (E10-E14)",
        "Autauga County, AL\t01001\t2010\t12\t54000\t22.2\t21.5\tDiabetes mellitus (E10-E14)",
    ]
    path = tmp_path / "dup.txt"
    path.write_text("\n".join(lines + ["---", '"Total"']))
    with pytest.raises(ValueError, match="Duplicate"):
        load_manual_export(subdir_files=[path])


NATIONAL_HEADER = "Year\tDeaths\tPopulation\tCrude Rate\tAge Adjusted Rate"
STATE_HEADER = "State\tState Code\tYear\tDeaths\tPopulation\tCrude Rate\tAge Adjusted Rate"


def test_load_manual_export_national_level_has_no_location_columns(tmp_path):
    # Shaped exactly like the real national-level drowning export
    # (verified 2026-09-01): no County or State columns at all.
    lines = [NATIONAL_HEADER, "1999\t3529\t279040168\t1.3\t1.3", "2000\t3482\t281421906\t1.2\t1.2"]
    path = tmp_path / "national.txt"
    path.write_text("\n".join(lines + ["---", '"Total"']))

    result = load_manual_export(subdir_files=[path], cause_label="Accidental drowning")
    assert result.geography == "national"
    assert "county_fips" not in result.df.columns
    assert "state_code" not in result.df.columns
    assert result.n_rows == 2
    assert result.df.iloc[0]["deaths"] == 3529


def test_load_manual_export_state_level_detected(tmp_path):
    lines = [STATE_HEADER, "Alabama\t01\t2020\t45\t5000000\t0.9\t0.9"]
    path = tmp_path / "state.txt"
    path.write_text("\n".join(lines + ["---", '"Total"']))

    result = load_manual_export(subdir_files=[path], cause_label="Drug overdose")
    assert result.geography == "state"
    assert "county_fips" not in result.df.columns
    assert result.df.iloc[0]["state_code"] == "01"


def test_load_manual_export_raises_on_mixed_geography_across_files(tmp_path):
    national = tmp_path / "national.txt"
    national.write_text("\n".join([NATIONAL_HEADER, "1999\t100\t1000000\t1.0\t1.0", "---", '"Total"']))
    state = tmp_path / "state.txt"
    state.write_text("\n".join([STATE_HEADER, "Alabama\t01\t1999\t10\t500000\t2.0\t2.0", "---", '"Total"']))

    with pytest.raises(ValueError, match="Mixed geography"):
        load_manual_export(subdir_files=[national, state], cause_label="Diabetes mellitus")


def test_load_manual_export_county_level_still_works_backward_compatible(tmp_path):
    f = _write_fixture(tmp_path, "county.txt", [
        "Autauga County, AL\t01001\t2010\t12\t54000\t22.2\t21.5",
    ])
    result = load_manual_export(subdir_files=[f], cause_label="Diabetes mellitus")
    assert result.geography == "county"
    assert result.df.iloc[0]["county_fips"] == "01001"


def test_load_manual_export_handles_missing_age_adjusted_rate_column(tmp_path):
    # Confirmed real WONDER behavior (2026-09-01): the D158 (2018-2024
    # Single Race) database does not offer Age-Adjusted Rate at all when
    # grouped by County -- the export has no such column, not suppressed
    # cells within one. Must not raise; age_adjusted_rate should come back
    # as NaN with no false suppressed/unreliable flag, since this is a
    # database capability gap, not per-cell suppression.
    header = "County\tCounty Code\tYear\tDeaths\tPopulation\tCrude Rate"
    lines = [header, "Autauga County, AL\t01001\t2020\t27\t56145\t48.1"]
    path = tmp_path / "county_no_aa_rate.txt"
    path.write_text("\n".join(lines + ["---", '"Total"']))

    result = load_manual_export(subdir_files=[path], cause_label="Diabetes mellitus")
    assert result.geography == "county"
    row = result.df.iloc[0]
    assert pd.isna(row["age_adjusted_rate"])
    assert not row["age_adjusted_rate_suppressed"]
    assert not row["age_adjusted_rate_unreliable"]
    assert row["crude_rate"] == 48.1
