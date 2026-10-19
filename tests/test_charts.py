import pandas as pd
import pytest

from app.components.charts import (
    deviation_pct,
    gap_from_trend_chart,
    spread_labels,
    then_vs_now_chart,
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
        "significant": [True, True, True, False],
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
    dev = pd.DataFrame({"cause": ["Other"], "year": [2020], "pct": [1.0], "significant": [False]})
    with pytest.raises(ValueError, match="labelled causes"):
        gap_from_trend_chart(dev, colors={}, labels={"Diabetes mellitus": "Diabetes"}, highlight=set())


def _datasets_and_scales(spec):
    """All dataset rows and every (field, scale-domain) pair in a Vega-Lite dict."""
    rows = [r for values in spec.get("datasets", {}).values() for r in values]
    scales = []

    def walk(node):
        if isinstance(node, dict):
            for key in ("y",):
                enc = node.get("encoding", {}).get(key) if isinstance(node.get("encoding"), dict) else None
                if enc and "scale" in enc and "domain" in enc["scale"]:
                    scales.append((enc["field"], enc["scale"]["domain"]))
            for v in node.values():
                walk(v)
        elif isinstance(node, list):
            for v in node:
                walk(v)

    walk(spec)
    return rows, scales


def test_gap_chart_keeps_crowded_low_labels_inside_the_y_domain():
    # Three causes ending within 1 point of the series minimum: spreading
    # pushes two labels below the lowest data value. They must stay on-chart.
    causes = ["A", "B", "C"]
    dev = pd.DataFrame({
        "cause": [c for c in causes for _ in (2020, 2021)],
        "year": [2020, 2021] * 3,
        "pct": [30.0, -19.1, 20.0, -19.5, 10.0, -20.0],
        "significant": [True, False] * 3,
    })
    spec = gap_from_trend_chart(
        dev, colors=dict.fromkeys(causes, "#B3261E"), labels={c: c for c in causes}, highlight=set(),
    ).to_dict()
    rows, scales = _datasets_and_scales(spec)
    label_ys = [r["label_y"] for r in rows if "label_y" in r]
    (domain,) = {tuple(d) for field, d in scales if field == "label_y"}
    assert len(label_ys) == 3
    assert min(label_ys) < -20.0  # spreading really did push one below the data
    assert all(domain[0] <= y <= domain[1] for y in label_ys)


def _summary():
    return pd.DataFrame({
        "cause": ["Diabetes mellitus", "Drug overdose", "Diseases of heart"],
        "acute_pct_deviation": [26.9, 40.9, 7.8],
    })


def _deviations():
    # 2024 rows. pct = deviation/expected; band = (pi_high - expected)/expected.
    # Diabetes: +15% with a ±12% band -> significant. Overdose: -4% with ±13% -> not.
    # Heart: +3% with ±4% -> not.
    return pd.DataFrame({
        "cause": ["Diabetes mellitus", "Drug overdose", "Diseases of heart", "Diabetes mellitus"],
        "year": [2024, 2024, 2024, 2023],
        "expected": [20.0, 25.0, 100.0, 20.0],
        "deviation": [3.0, -1.0, 3.0, 3.4],
        "pi_high": [22.4, 28.25, 104.0, 22.3],
        "significant": [True, False, False, True],
    })


LABELS = {"Diseases of heart": "Heart disease", "Diabetes mellitus": "Diabetes", "Drug overdose": "Drug overdose"}
COLORS = {"Diseases of heart": "#C26A2E", "Diabetes mellitus": "#B3261E", "Drug overdose": "#2C5D86"}


def _chart_rows():
    spec = then_vs_now_chart(_summary(), _deviations(), COLORS, LABELS).to_dict()
    rows = [r for values in spec["datasets"].values() for r in values]
    return spec, {r["label"]: r for r in rows if "band_pct" in r}


def test_then_vs_now_rows_are_sorted_by_2020_21_deviation():
    spec, _ = _chart_rows()
    sorts = []

    def walk(node):
        if isinstance(node, dict):
            y = node.get("encoding", {}).get("y") if isinstance(node.get("encoding"), dict) else None
            if isinstance(y, dict) and isinstance(y.get("sort"), list):
                sorts.append(y["sort"])
            for v in node.values():
                walk(v)
        elif isinstance(node, list):
            for v in node:
                walk(v)

    walk(spec)
    # Overdose +40.9 > Diabetes +26.9 > Heart +7.8
    assert sorts and all(s == ["Drug overdose", "Diabetes", "Heart disease"] for s in sorts)


def test_then_vs_now_uses_the_latest_year_and_its_normal_range():
    _, rows = _chart_rows()
    # Hand-computed from _deviations()' 2024 rows (the 2023 row must be ignored).
    assert rows["Diabetes"]["latest_pct"] == pytest.approx(15.0)
    assert rows["Diabetes"]["band_pct"] == pytest.approx(12.0)
    assert rows["Drug overdose"]["latest_pct"] == pytest.approx(-4.0)
    assert rows["Drug overdose"]["band_pct"] == pytest.approx(13.0)
    assert rows["Heart disease"]["band_low"] == pytest.approx(-4.0)
    assert rows["Heart disease"]["band_high"] == pytest.approx(4.0)


def test_then_vs_now_marks_which_latest_dots_are_significant():
    _, rows = _chart_rows()
    assert rows["Diabetes"]["status"] == "Outside normal range"
    assert rows["Drug overdose"]["status"] == "Within normal range"
    assert rows["Heart disease"]["status"] == "Within normal range"


def test_then_vs_now_rejects_summary_missing_a_labelled_cause():
    with pytest.raises(ValueError, match="summary is missing"):
        then_vs_now_chart(_summary().iloc[:2], _deviations(), COLORS, LABELS)


def test_then_vs_now_rejects_deviations_missing_the_latest_year_for_a_cause():
    devs = _deviations()
    with pytest.raises(ValueError, match="no 2024 row"):
        then_vs_now_chart(_summary(), devs[devs["cause"] != "Drug overdose"], COLORS, LABELS)


def _end_layers(spec):
    """(mark type, filled, causes) for each layer drawn at the latest year."""
    out = []
    for layer in spec["layer"]:
        rows = spec["datasets"].get(layer.get("data", {}).get("name"), [])
        if rows and "status" in rows[0] and layer["mark"]["type"] in ("circle", "point"):
            out.append((layer["mark"]["type"], layer["mark"].get("filled", True), sorted(r["cause"] for r in rows)))
    return out


def test_gap_chart_end_point_is_solid_only_when_latest_year_is_significant():
    # Cancer-like case: small gap but significant; heart-like case: similar gap, not significant.
    dev = pd.DataFrame({
        "cause": ["Malignant neoplasms", "Malignant neoplasms", "Diseases of heart", "Diseases of heart"],
        "year": [2023, 2024, 2023, 2024],
        "pct": [4.2, 4.6, 4.8, 3.0],
        "significant": [True, True, True, False],
    })
    spec = gap_from_trend_chart(
        dev, colors={"Malignant neoplasms": "#2F6F4E", "Diseases of heart": "#C26A2E"},
        labels={"Malignant neoplasms": "Cancer", "Diseases of heart": "Heart disease"}, highlight=set(),
    ).to_dict()
    assert sorted(_end_layers(spec)) == [
        ("circle", True, ["Malignant neoplasms"]),
        ("point", False, ["Diseases of heart"]),
    ]


def test_gap_chart_requires_significance_column():
    dev = pd.DataFrame({"cause": ["Diabetes mellitus"], "year": [2024], "pct": [15.0]})
    with pytest.raises(ValueError, match="significant"):
        gap_from_trend_chart(dev, colors={"Diabetes mellitus": "#B3261E"}, labels={"Diabetes mellitus": "Diabetes"},
                             highlight=set())


def test_gap_chart_end_points_keep_full_color_for_tinted_lines():
    # Regression: layered charts share one color scale unless resolved
    # independently, so a non-highlighted (tinted) cause's significant end
    # point rendered in the pale tint instead of its full color.
    dev = pd.DataFrame({
        "cause": ["Malignant neoplasms", "Malignant neoplasms"], "year": [2023, 2024],
        "pct": [4.2, 4.6], "significant": [True, True],
    })
    spec = gap_from_trend_chart(dev, colors={"Malignant neoplasms": "#2F6F4E"},
                                labels={"Malignant neoplasms": "Cancer"}, highlight=set()).to_dict()
    assert spec["resolve"]["scale"]["color"] == "independent"
