"""Chart builders and the small pure helpers behind them. No Streamlit
calls here, so everything can be unit-tested directly."""
import altair as alt
import pandas as pd

MONO = "IBM Plex Mono"
MUTED = "#5A6875"
GRID = "#E1E6EB"
TREND_LINE = "#8795A3"
# How much non-highlighted causes are washed toward white on chart A.
BACKGROUND_TINT = 0.55
# Minimum vertical spacing between end-of-line labels, in pixels.
LABEL_GAP_PX = 16


def deviation_pct(deviations: pd.DataFrame) -> pd.DataFrame:
    """Copy of `deviations` with `pct`: (observed - expected) as a percent of expected."""
    if (deviations["expected"] == 0).any():
        raise ValueError("expected rate is 0 for at least one row; percent deviation is undefined")
    out = deviations.copy()
    out["pct"] = out["deviation"] / out["expected"] * 100
    return out


def tint(hex_color: str, amount: float) -> str:
    """Mix a #RRGGBB color toward white by `amount` (0 = unchanged, 1 = white)."""
    if not 0 <= amount <= 1:
        raise ValueError(f"amount must be between 0 and 1, got {amount}")
    h = hex_color.removeprefix("#")
    if len(h) != 6:
        raise ValueError(f"expected a #RRGGBB color, got {hex_color!r}")
    channels = [int(h[i:i + 2], 16) for i in (0, 2, 4)]  # int() raises ValueError on non-hex
    return "#" + "".join(f"{round(c + (255 - c) * amount):02X}" for c in channels)


def spread_labels(values: list[float], min_gap: float) -> list[float]:
    """Nudge end-of-line label positions so no two sit closer than `min_gap`
    (data units). Walks from the highest value down, pushing crowded labels
    lower; the top label never moves. Output keeps the input order."""
    out = list(values)
    prev = None
    for i in sorted(range(len(values)), key=lambda i: values[i], reverse=True):
        if prev is not None:
            out[i] = min(values[i], prev - min_gap)
        prev = out[i]
    return out


def then_vs_now_chart(
    summary: pd.DataFrame, deviations: pd.DataFrame, colors: dict[str, str], labels: dict[str, str],
    height: int = 270,
) -> alt.LayerChart:
    """Findings chart B: per cause, the 2020-21 deviation (hollow dot) and the
    latest-year deviation (filled dot), sorted by the 2020-21 deviation.

    Distance from 0% alone doesn't say whether a gap is real: cancer's
    year-to-year noise is ~1% while drug overdose's is ~13%. So each row also
    shows the latest year's 95% prediction interval as a gray "normal range"
    band around 0%, and the latest dot is solid only when it falls outside
    that band (significant), faded when it's inside.

    `summary` needs cause and acute_pct_deviation; `deviations` needs cause,
    year, deviation, expected, pi_high and significant. `labels` fixes which
    causes are drawn."""
    rows = summary[summary["cause"].isin(labels)][["cause", "acute_pct_deviation"]].copy()
    missing = set(labels) - set(rows["cause"])
    if missing:
        raise ValueError(f"summary is missing labelled causes: {sorted(missing)}")
    latest_year = int(deviations["year"].max())
    latest = deviations[(deviations["year"] == latest_year) & deviations["cause"].isin(labels)].copy()
    missing = set(labels) - set(latest["cause"])
    if missing:
        raise ValueError(f"deviations has no {latest_year} row for: {sorted(missing)}")
    latest["latest_pct"] = latest["deviation"] / latest["expected"] * 100
    # Half-width of the prediction interval, as a percent of the expected rate.
    latest["band_pct"] = (latest["pi_high"] - latest["expected"]) / latest["expected"] * 100
    rows = rows.merge(latest[["cause", "latest_pct", "band_pct", "significant"]], on="cause")
    rows["label"] = rows["cause"].map(labels)
    rows["band_low"], rows["band_high"] = -rows["band_pct"], rows["band_pct"]
    rows["status"] = rows["significant"].map({True: "Outside normal range", False: "Within normal range"})
    order = rows.sort_values("acute_pct_deviation", ascending=False)["label"].tolist()

    color = alt.Color(
        "cause:N", scale=alt.Scale(domain=list(labels), range=[colors[c] for c in labels]), legend=None,
    )
    y = alt.Y("label:N", sort=order, title=None, axis=alt.Axis(
        ticks=False, domain=False, labelFontSize=12, labelLimit=0))
    # Kept short: under Streamlit's container-width fit a long axis title
    # squeezes the plot to nothing at phone width. The page caption explains
    # the dots and the band.
    x = alt.X("pct:Q", title="% vs. pre-pandemic trend", axis=alt.Axis(
        labelFont=MONO, labelColor=MUTED, gridColor=GRID, ticks=False, domain=False, titleColor=MUTED,
        titleFontWeight=400, labelExpr="(datum.value > 0 ? '+' : '') + datum.value + '%'"))

    band = alt.Chart(rows).mark_bar(height=14, color="#D5DCE3", opacity=0.75, cornerRadius=2).encode(
        x=alt.X("band_low:Q"), x2="band_high:Q", y=y,
        tooltip=[alt.Tooltip("label:N", title="Cause"),
                 alt.Tooltip("band_pct:Q", title=f"{latest_year} normal range (±%)", format=".1f")])
    zero = alt.Chart(pd.DataFrame({"pct": [0.0]})).mark_rule(color=TREND_LINE, strokeDash=[4, 3]).encode(x="pct:Q")
    connector = alt.Chart(rows).mark_rule(strokeWidth=2.5, opacity=0.3).encode(
        x=alt.X("acute_pct_deviation:Q"), x2="latest_pct:Q", y=y, color=color)
    acute = alt.Chart(rows.assign(pct=rows["acute_pct_deviation"])).mark_point(
        size=110, filled=False, strokeWidth=2.2).encode(
        x=x, y=y, color=color,
        tooltip=[alt.Tooltip("label:N", title="Cause"), alt.Tooltip("pct:Q", title="2020–21 vs. trend", format="+.1f")])
    now = alt.Chart(rows.assign(pct=rows["latest_pct"])).mark_circle(size=130).encode(
        x=x, y=y, color=color,
        opacity=alt.condition("datum.significant", alt.value(1.0), alt.value(0.3)),
        tooltip=[alt.Tooltip("label:N", title="Cause"),
                 alt.Tooltip("pct:Q", title=f"{latest_year} vs. trend", format="+.1f"),
                 alt.Tooltip("status:N", title=f"{latest_year}")])
    # Left padding: Vega-Lite's auto margin falls a few px short of the
    # longest label and the canvas edge clips its first letter.
    return (
        alt.layer(band, zero, connector, acute, now)
        .properties(height=height, padding={"left": 24, "top": 4, "right": 8, "bottom": 4})
        .configure_view(stroke=None)
    )


def gap_from_trend_chart(
    dev: pd.DataFrame,
    colors: dict[str, str],
    labels: dict[str, str],
    highlight: set[str],
    height: int = 270,
) -> alt.LayerChart:
    """Home chart A: each cause's percent gap from its projected pre-pandemic
    trend, one line per cause. Highlighted causes are drawn in full color; the
    rest in a light tint of their own color, so the Home cause chips (full
    color) still match their lines."""
    present = set(dev["cause"])
    causes = [c for c in labels if c in present]
    if not causes:
        raise ValueError("none of the labelled causes appear in the deviation data")

    data = dev[dev["cause"].isin(causes)].copy()
    data["label"] = data["cause"].map(labels)
    data["highlighted"] = data["cause"].isin(highlight)
    color = alt.Color(
        "cause:N",
        scale=alt.Scale(
            domain=causes,
            range=[colors[c] if c in highlight else tint(colors[c], BACKGROUND_TINT) for c in causes],
        ),
        legend=None,
    )

    years = sorted(int(y) for y in data["year"].unique())
    y_lo, y_hi = float(min(data["pct"].min(), 0)), float(max(data["pct"].max(), 0))
    pad = (y_hi - y_lo) * 0.08 or 1.0
    y_domain = [y_lo - pad, y_hi + pad]

    # End-of-line labels, spread apart. spread_labels only pushes labels
    # down, so lower the domain floor if needed to keep the lowest one on the
    # chart instead of drawing over the year axis.
    ends = data[data["year"] == years[-1]].copy()
    min_gap = (y_domain[1] - y_domain[0]) * LABEL_GAP_PX / height
    ends["label_y"] = spread_labels(ends["pct"].tolist(), min_gap)
    ends["end_text"] = ends.apply(lambda r: f"{r['label']} {r['pct']:+.0f}%", axis=1)
    y_domain[0] = min(y_domain[0], float(ends["label_y"].min()) - min_gap / 2)
    y_scale = alt.Scale(domain=y_domain, nice=False)
    # Extend the x domain past the last year so the end-of-line labels have
    # room inside the plot. (Chart padding can't do this: Streamlit's
    # container-width fit shrinks the plot by the padding instead.)
    x_scale = alt.Scale(domain=[years[0] - 0.2, years[-1] + 2.8], nice=False)
    x = alt.X("year:Q", scale=x_scale, title=None, axis=alt.Axis(
        values=years, format="d", labelFont=MONO, labelColor=MUTED, grid=False, ticks=False, domain=False))
    y = alt.Y("pct:Q", scale=y_scale, title=None, axis=alt.Axis(
        labelFont=MONO, labelColor=MUTED, gridColor=GRID, ticks=False, domain=False, tickCount=5,
        labelExpr="datum.value == 0 ? '0%' : (datum.value > 0 ? '+' : '') + datum.value + '%'"))

    # Two line layers so highlighted causes are always drawn on top.
    lines_bg = alt.Chart(data[~data["highlighted"]]).mark_line(strokeWidth=1.5, strokeJoin="round").encode(
        x=x, y=y, color=color)
    lines_fg = alt.Chart(data[data["highlighted"]]).mark_line(strokeWidth=2.6, strokeJoin="round").encode(
        x=x, y=y, color=color)
    points = alt.Chart(data).mark_circle(size=34).encode(
        x=x, y=y, color=color,
        opacity=alt.condition("datum.highlighted", alt.value(1.0), alt.value(0.0)),
        tooltip=[
            alt.Tooltip("label:N", title="Cause"),
            alt.Tooltip("year:Q", title="Year", format="d"),
            alt.Tooltip("pct:Q", title="vs. pre-pandemic trend", format="+.1f"),
        ],
    )

    zero = pd.DataFrame({"year": [years[0] - 0.2], "pct": [0.0], "text": ["pre-pandemic trend"]})
    trend_rule = alt.Chart(zero).mark_rule(color=TREND_LINE, strokeDash=[4, 3]).encode(y=alt.Y("pct:Q", scale=y_scale))
    trend_label = alt.Chart(zero).mark_text(
        align="left", dx=4, dy=11, fontStyle="italic", fontSize=11, color=MUTED,
    ).encode(x=x, y=y, text="text:N")

    end_y = alt.Y("label_y:Q", scale=y_scale)
    end_labels = [
        alt.Chart(ends[ends["highlighted"]]).mark_text(align="left", dx=8, fontSize=11.5, fontWeight=600)
        .encode(x=x, y=end_y, text="end_text:N", color=color),
        alt.Chart(ends[~ends["highlighted"]]).mark_text(align="left", dx=8, fontSize=11, color=MUTED)
        .encode(x=x, y=end_y, text="end_text:N"),
    ]

    return (
        alt.layer(trend_rule, trend_label, lines_bg, lines_fg, points, *end_labels)
        .properties(height=height)
        .configure_view(stroke=None)
    )
