import io
import zipfile

import pandas as pd
import pytest

from src.ingestion.usda_food_atlas import load_atlas, VARIABLE_CODES


def _make_fixture_zip(rows: list[tuple]) -> bytes:
    csv_content = "FIPS,State,County,Variable_Code,Value\n"
    for fips, state, county, code, value in rows:
        csv_content += f"{fips},{state},{county},{code},{value}\n"
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("StateAndCountyData.csv", csv_content)
    return buf.getvalue()


def test_load_atlas_pivots_to_wide_format(monkeypatch):
    rows = []
    for fips in ("01001", "01003"):
        for name, code in VARIABLE_CODES.items():
            rows.append((fips, "AL", "Some County", code, 1.5))
    fixture_bytes = _make_fixture_zip(rows)
    monkeypatch.setattr("src.ingestion.usda_food_atlas.download_atlas", lambda: fixture_bytes)

    df = load_atlas()
    assert set(df["county_fips"]) == {"01001", "01003"}
    for name in VARIABLE_CODES:
        assert name in df.columns
        assert (df[name] == 1.5).all()


def test_load_atlas_raises_clearly_on_missing_variable_code(monkeypatch):
    rows = [("01001", "AL", "Some County", "SOME_OTHER_CODE", 1.5)]
    fixture_bytes = _make_fixture_zip(rows)
    monkeypatch.setattr("src.ingestion.usda_food_atlas.download_atlas", lambda: fixture_bytes)

    with pytest.raises(ValueError, match="missing expected variable code"):
        load_atlas()


def test_load_atlas_state_broadcast_limitation_is_real_in_fixture(monkeypatch):
    # Reproduces the documented quirk: FOODINSEC is identical across all
    # counties in a state, unlike the genuinely county-varying measures.
    rows = [
        ("01001", "AL", "A", "PCT_LACCESS_POP19", 10.0),
        ("01001", "AL", "A", "PCT_LACCESS_LOWI19", 5.0),
        ("01001", "AL", "A", "GROCPTH20", 0.2),
        ("01001", "AL", "A", "FFRPTH20", 0.5),
        ("01001", "AL", "A", "FOODINSEC_21_23", 14.0),
        ("01003", "AL", "B", "PCT_LACCESS_POP19", 20.0),
        ("01003", "AL", "B", "PCT_LACCESS_LOWI19", 8.0),
        ("01003", "AL", "B", "GROCPTH20", 0.3),
        ("01003", "AL", "B", "FFRPTH20", 0.6),
        ("01003", "AL", "B", "FOODINSEC_21_23", 14.0),
    ]
    fixture_bytes = _make_fixture_zip(rows)
    monkeypatch.setattr("src.ingestion.usda_food_atlas.download_atlas", lambda: fixture_bytes)

    df = load_atlas()
    assert df["food_insecurity_rate_state_level"].nunique() == 1
    assert df["pct_low_access_pop"].nunique() == 2
