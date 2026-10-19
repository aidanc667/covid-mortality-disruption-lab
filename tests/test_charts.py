import pandas as pd
import pytest

from app.components.charts import (
    deviation_pct,
    gap_from_trend_chart,
    spread_labels,
    tint,
)


def test_deviation_pct_is_percent_of_expected():
    df = pd.DataFrame({"deviation": [5.0, -2.0], "expected": [20.0, 40.0]})
    out = deviation_pct(df)
    assert out["pct"].tolist() == pytest.approx([25.0, -5.0])
    assert "pct" not in df.columns  # input is not mutated


def test_deviation_pct_rejects_zero_expected():
    with pytest.raises(ValueError, match="expected"):
        deviation_pct(pd.DataFrame({"deviation": [1.0], "expected": [0.0]}))


def test_tint_mixes_toward_white():
    assert tint("#B3261E", 0.6) == "#E1A8A5"
    assert tint("#B3261E", 0) == "#B3261E"
    assert tint("#b3261e", 1) == "#FFFFFF"


@pytest.mark.parametrize("bad", ["B3261", "#GG0000", "red"])
def test_tint_rejects_non_hex(bad):
    with pytest.raises(ValueError):
        tint(bad, 0.5)


def test_tint_rejects_amount_out_of_range():
    with pytest.raises(ValueError, match="amount"):
        tint("#B3261E", 1.5)


def test_spread_labels_pushes_crowded_labels_down():
    out = spread_labels([15.0, 6.1, 4.6, 3.0, -4.3, -19.1], 4)
    assert out == pytest.approx([15.0, 6.1, 2.1, -1.9, -5.9, -19.1])


def test_spread_labels_keeps_input_order_and_leaves_spaced_labels_alone():
    assert spread_labels([3.0, 15.0], 4) == [3.0, 15.0]
    assert spread_labels([0.0, 1.0], 4) == pytest.approx([-3.0, 1.0])


def test_spread_labels_empty():
    assert spread_labels([], 4) == []


def _color_scale(spec):
    """Find the first color scale (the one with an explicit domain) in a Vega-Lite dict."""
    if isinstance(spec, dict):
        enc = spec.get("encoding", {})
        scale = enc.get("color", {}).get("scale") if isinstance(enc, dict) else None
        if scale and "domain" in scale:
            return scale
        for v in spec.values():
            found = _color_scale(v)
            if found:
                return found
    elif isinstance(spec, list):
        for v in spec:
            found = _color_scale(v)
            if found:
                return found
    return None


def test_gap_chart_full_color_for_highlight_tint_for_rest():
    dev = pd.DataFrame({
        "cause": ["Diabetes mellitus", "Diabetes mellitus", "Diseases of heart", "Diseases of heart"],
        "year": [2020, 2021, 2020, 2021],
        "pct": [24.6, 29.3, 5.5, 10.1],
    })
    chart = gap_from_trend_chart(
        dev,
        colors={"Diabetes mellitus": "#B3261E", "Diseases of heart": "#C26A2E"},
        labels={"Diabetes mellitus": "Diabetes", "Diseases of heart": "Heart disease"},
        highlight={"Diabetes mellitus"},
    )
    scale = _color_scale(chart.to_dict())
    assert scale["domain"] == ["Diabetes mellitus", "Diseases of heart"]
    assert scale["range"] == ["#B3261E", "#E4BCA1"]


def test_gap_chart_rejects_data_with_none_of_the_labelled_causes():
    dev = pd.DataFrame({"cause": ["Other"], "year": [2020], "pct": [1.0]})
    with pytest.raises(ValueError, match="labelled causes"):
        gap_from_trend_chart(dev, colors={}, labels={"Diabetes mellitus": "Diabetes"}, highlight=set())
