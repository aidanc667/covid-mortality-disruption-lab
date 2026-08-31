import pandas as pd
import pytest

from src.cleaning.bridging import estimate_vintage_offset, is_bridging_reliable


def _panel(rows):
    return pd.DataFrame(rows, columns=["county_fips", "year", "age_adjusted_rate"])


def test_estimate_vintage_offset_computes_difference_per_overlap_year():
    old_df = _panel([
        ("01001", 2018, 20.0),
        ("01001", 2019, 21.0),
        ("01001", 2020, 22.0),
    ])
    new_df = _panel([
        ("01001", 2018, 21.0),
        ("01001", 2019, 22.5),
        ("01001", 2020, 23.0),
    ])
    result = estimate_vintage_offset(old_df, new_df, overlap_years=[2018, 2019, 2020], group_cols=["county_fips"])
    assert len(result) == 3
    row_2019 = result[result["year"] == 2019].iloc[0]
    assert row_2019["offset"] == pytest.approx(1.5)


def test_estimate_vintage_offset_only_includes_overlap_years():
    old_df = _panel([("01001", 2017, 19.0), ("01001", 2018, 20.0)])
    new_df = _panel([("01001", 2018, 20.5), ("01001", 2021, 25.0)])
    result = estimate_vintage_offset(old_df, new_df, overlap_years=[2018], group_cols=["county_fips"])
    assert list(result["year"]) == [2018]


def test_is_bridging_reliable_true_for_small_offset():
    offset_df = pd.DataFrame({
        "county_fips": ["01001", "01001"],
        "year": [2018, 2019],
        "age_adjusted_rate_old": [20.0, 21.0],
        "age_adjusted_rate_new": [20.5, 21.4],
        "offset": [0.5, 0.4],
    })
    assert is_bridging_reliable(offset_df) is True


def test_is_bridging_reliable_false_for_large_offset():
    offset_df = pd.DataFrame({
        "county_fips": ["01001", "01001"],
        "year": [2018, 2019],
        "age_adjusted_rate_old": [20.0, 21.0],
        "age_adjusted_rate_new": [26.0, 27.0],
        "offset": [6.0, 6.0],
    })
    assert is_bridging_reliable(offset_df) is False
