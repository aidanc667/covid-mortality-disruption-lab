import io
import zipfile

import pandas as pd
import pytest

from src.ingestion.hrsa import load_primary_care_physicians, AHRF_HP_MEMBER, VARIABLE_COLUMNS


def _make_fixture_zip(columns: list[str], rows: list[list]) -> bytes:
    df = pd.DataFrame(rows, columns=columns)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr(AHRF_HP_MEMBER, df.to_csv(index=False))
    return buf.getvalue()


def test_load_primary_care_physicians_parses_real_shaped_fixture(monkeypatch):
    cols = ["fips_st_cnty", "cnty_name_st_abbrev", "phys_nf_prim_care_pc_exc_rsdt_23"]
    rows = [[1001, "Autauga, AL", 22], [1003, "Baldwin, AL", 172]]
    fixture_bytes = _make_fixture_zip(cols, rows)
    monkeypatch.setattr("src.ingestion.hrsa.download_ahrf", lambda: fixture_bytes)

    df = load_primary_care_physicians()
    assert set(df["county_fips"]) == {"01001", "01003"}
    assert df.loc[df["county_fips"] == "01001", "primary_care_physicians_count"].iloc[0] == 22


def test_load_primary_care_physicians_raises_on_missing_column(monkeypatch):
    cols = ["fips_st_cnty", "some_other_column"]
    rows = [[1001, 5]]
    fixture_bytes = _make_fixture_zip(cols, rows)
    monkeypatch.setattr("src.ingestion.hrsa.download_ahrf", lambda: fixture_bytes)

    with pytest.raises(ValueError, match="missing expected column"):
        load_primary_care_physicians()


def test_load_primary_care_physicians_raises_on_missing_zip_member(monkeypatch):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("some_other_file.csv", "a,b\n1,2\n")
    monkeypatch.setattr("src.ingestion.hrsa.download_ahrf", lambda: buf.getvalue())

    with pytest.raises(ValueError, match="not found in the AHRF zip"):
        load_primary_care_physicians()
