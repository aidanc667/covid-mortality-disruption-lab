"""Generates a formal, standalone PDF research report from the same
precomputed outputs the Streamlit app reads (outputs/models/*.parquet) --
never recomputes analysis, only formats existing results (same discipline
as the app, research_protocol.md's brief section 46 origin). This is a
distinct deliverable from the interactive app: something a reader can
save, print, or attach without running anything.

Requires reportlab, which is NOT in the main requirements.txt (the
deployed Streamlit app doesn't need it) -- see requirements-report.txt.
"""

import re

import pandas as pd
from reportlab.graphics.charts.legends import Legend
from reportlab.graphics.charts.lineplots import LinePlot
from reportlab.graphics.shapes import Circle, Drawing, Line, Rect, String
from reportlab.lib import colors
from reportlab.lib.enums import TA_JUSTIFY
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.pdfbase.pdfmetrics import registerFontFamily
from reportlab.platypus import (
    HRFlowable,
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.components.county_text import rurality_change
from app.components.findings_text import trend_vs_reference_note
from src.utils.config import OUTPUTS_MODELS, OUTPUTS_REPORTS

# Duplicated from app/components/data_loading.py's CONTEXT_VAR_LABELS/
# CONTEXT_VAR_DISPLAY_SCALE rather than imported, to keep this standalone
# script fully decoupled from the Streamlit app runtime. Human-readable
# labels for the raw CHR&R context-variable column names -- found
# rendering illegibly as raw column names (e.g. "median_income_chr") in
# an earlier version.
CONTEXT_VAR_LABELS = {
    "pct_uninsured_chr": "% uninsured",
    "pct_smokers": "% adult smokers",
    "pct_obese": "% adult obesity",
    "median_income_chr": "Median household income (per $10k)",
    "pct_rural": "% rural",
}

# Duplicated from app/components/data_loading.py's CAUSE_DISPLAY_NAMES for
# the same standalone-script reason as CONTEXT_VAR_LABELS above. The
# underlying dataframes still key on the official CDC WONDER cause name
# (needed to join against the pipeline's own output) -- this is only the
# reader-facing form. Two of the six (Alzheimer's disease, drug overdose)
# are already plain English, so they're unchanged here.
CAUSE_DISPLAY_NAMES = {
    "Diseases of heart": "Heart disease",
    "Diabetes mellitus": "Diabetes",
    "Alzheimer's disease": "Alzheimer's disease",
    "Cerebrovascular disease": "Stroke",
    "Drug overdose": "Drug overdose",
    "Malignant neoplasms": "Cancer",
}


def display_cause(cause: str) -> str:
    return CAUSE_DISPLAY_NAMES.get(cause, cause)

# median_income_chr's slope is fit against raw dollars, so it's a tiny
# number (~-0.00005) next to the other four variables' 0-1-proportion
# slopes (~1-40) -- found rounding to "0.000" in this report's own table
# and rendering as an invisible flat bar next to the others on
# a shared chart axis, even though it's highly
# significant. Scales ONLY the value shown in this report, never the
# underlying regression.
CONTEXT_VAR_DISPLAY_SCALE = {
    "median_income_chr": 10_000,
}


def _scaled_slope(variable: str, slope: float) -> float:
    return slope * CONTEXT_VAR_DISPLAY_SCALE.get(variable, 1)

OUTPUT_PATH = OUTPUTS_REPORTS / "covid_mortality_disruption_report.pdf"

# Same list as app/components/data_loading.py's HETEROGENEITY_CAUSES (every
# test cause with a significant 2020-21 disruption), duplicated for the same
# standalone-script reason as the labels above.
COUNTY_CAUSES = [
    "Diseases of heart", "Diabetes mellitus", "Cerebrovascular disease", "Drug overdose", "Malignant neoplasms",
]

styles = getSampleStyleSheet()
_SERIF, _SERIF_BOLD = "Times-Roman", "Times-Bold"
registerFontFamily("Times-Roman", normal="Times-Roman", bold="Times-Bold", italic="Times-Italic",
                   boldItalic="Times-BoldItalic")
_TEXT = colors.HexColor("#1F2933")
styles.add(ParagraphStyle("ReportTitle", fontName="Helvetica-Bold", fontSize=20, leading=24, textColor=_TEXT, spaceAfter=6))
styles.add(ParagraphStyle("ReportSubtitle", fontName=_SERIF, fontSize=12.5, leading=17, textColor=colors.HexColor("#3E4C59"), spaceAfter=6))
styles.add(ParagraphStyle("Byline", fontName="Helvetica", fontSize=9, leading=12, textColor=colors.HexColor("#5A6875"), spaceAfter=8))
styles.add(ParagraphStyle("AbstractHead", fontName="Helvetica-Bold", fontSize=9.5, leading=12, textColor=_TEXT, spaceAfter=4))
styles.add(ParagraphStyle("Abstract", fontName=_SERIF, fontSize=10, leading=13.5, alignment=TA_JUSTIFY, textColor=_TEXT,
                          spaceAfter=4, backColor=colors.HexColor("#F3F5F7"), borderPadding=(4, 8, 4, 8), leftIndent=8, rightIndent=8))
styles.add(ParagraphStyle("H1", fontName="Helvetica-Bold", fontSize=12.5, leading=16, keepWithNext=1, spaceBefore=12, spaceAfter=5, textColor=_TEXT))
styles.add(ParagraphStyle("H2", fontName="Helvetica-Bold", fontSize=10, leading=13, keepWithNext=1, spaceBefore=8, spaceAfter=3, textColor=colors.HexColor("#3E4C59")))
styles.add(ParagraphStyle("Body", fontName=_SERIF, fontSize=10.5, leading=14.2, alignment=TA_JUSTIFY, textColor=_TEXT, spaceAfter=6))
styles.add(ParagraphStyle("ListItem", parent=styles["Body"], leftIndent=12, bulletIndent=2, spaceAfter=3))
styles.add(ParagraphStyle("Caption", fontName="Helvetica", fontSize=8, leading=10.5, textColor=colors.HexColor("#5A6875"), spaceBefore=2, spaceAfter=10))
styles.add(ParagraphStyle("TableCaption", fontName="Helvetica-Bold", fontSize=8.5, leading=11, textColor=_TEXT, spaceBefore=4, spaceAfter=4, keepWithNext=1))
styles.add(ParagraphStyle("TableNote", parent=styles["Caption"], spaceBefore=3, spaceAfter=10))
styles.add(ParagraphStyle("Cell", fontName="Helvetica", fontSize=8, leading=10, textColor=_TEXT))
styles.add(ParagraphStyle("Reference", fontName=_SERIF, fontSize=9, leading=12, leftIndent=18, bulletIndent=0, spaceAfter=3, textColor=_TEXT))

TABLE_STYLE = TableStyle([
    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
    ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
    ("FONTSIZE", (0, 0), (-1, -1), 8),
    ("LEADING", (0, 0), (-1, -1), 10),
    ("TEXTCOLOR", (0, 0), (-1, -1), _TEXT),
    ("LINEABOVE", (0, 0), (-1, 0), 0.9, _TEXT),
    ("LINEBELOW", (0, 0), (-1, 0), 0.5, _TEXT),
    ("LINEBELOW", (0, -1), (-1, -1), 0.9, _TEXT),
    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ("TOPPADDING", (0, 0), (-1, -1), 3),
    ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ("LEFTPADDING", (0, 0), (-1, -1), 4),
])


def load_data() -> dict:
    return {
        "summary": pd.read_parquet(OUTPUTS_MODELS / "disruption_summary.parquet"),
        "window_check": pd.read_parquet(OUTPUTS_MODELS / "latest_year_window_check.parquet"),
        "negative_control": pd.read_parquet(OUTPUTS_MODELS / "negative_control.parquet").iloc[0],
        "heterogeneity": pd.read_parquet(OUTPUTS_MODELS / "heterogeneity_summary.parquet"),
        "selection_bias": pd.read_parquet(OUTPUTS_MODELS / "heterogeneity_selection_bias.parquet"),
        "rurality_robustness": pd.read_parquet(OUTPUTS_MODELS / "heterogeneity_rurality_robustness.parquet"),
        "heterogeneity_yearly": pd.read_parquet(OUTPUTS_MODELS / "heterogeneity_summary_yearly.parquet"),
        "county_disruption_yearly": {
            cause: pd.read_parquet(OUTPUTS_MODELS / f"county_disruption_yearly_{cause.lower().replace(' ', '_')}.parquet")
            for cause in ["Diabetes mellitus", "Drug overdose"]
        },
        "bridging": pd.read_parquet(OUTPUTS_MODELS / "bridging_summary.parquet"),
        "sensitivity": pd.read_parquet(OUTPUTS_MODELS / "sensitivity_check.parquet"),
        "national_series": pd.read_parquet(OUTPUTS_MODELS / "national_mortality_series.parquet"),
        "deviations": pd.read_parquet(OUTPUTS_MODELS / "disruption_deviations.parquet"),
        "baseline_fitted": pd.read_parquet(OUTPUTS_MODELS / "baseline_fitted_trend.parquet"),
        "county_disruption": {
            cause: pd.read_parquet(OUTPUTS_MODELS / f"county_disruption_{cause.lower().replace(' ', '_')}.parquet")
            for cause in COUNTY_CAUSES
        },
    }


def _plot_xy(plot, x, y):
    """Maps a data coordinate to Drawing-space pixels for a LinePlot with
    linear axes and explicit valueMin/valueMax -- reportlab doesn't expose
    this mapping as a public method, so it's re-derived here from the same
    x/y/width/height and axis range already set on the plot."""
    x_frac = (x - plot.xValueAxis.valueMin) / (plot.xValueAxis.valueMax - plot.xValueAxis.valueMin)
    y_frac = (y - plot.yValueAxis.valueMin) / (plot.yValueAxis.valueMax - plot.yValueAxis.valueMin)
    return plot.x + x_frac * plot.width, plot.y + y_frac * plot.height


def _add_significance_markers(drawing, plot, obs, dev, color, halo_r=7.0, point_r=3.2):
    """Draws a halo + solid point at each year that landed outside its 95%
    prediction interval -- the static-PDF equivalent of the app's Altair
    significance markers (app/app_pages/causes.py). A PDF reader has no
    hover tooltip to fall back on, so without this the same "small but
    real gap" cases (cancer) that needed a highlight in the app need it
    here too, not just a raw line comparison."""
    sig_years = set(dev.loc[dev["significant"], "year"])
    if not sig_years:
        return
    obs_by_year = dict(zip(obs["year"], obs["age_adjusted_rate"]))
    for year in sig_years:
        if year not in obs_by_year:
            continue
        cx, cy = _plot_xy(plot, float(year), obs_by_year[year])
        drawing.add(Circle(cx, cy, halo_r, fillColor=color, fillOpacity=0.25, strokeColor=None))
        drawing.add(Circle(cx, cy, point_r, fillColor=color, strokeColor=colors.white, strokeWidth=1))


def make_trajectory_chart(
    cause: str, national_series: pd.DataFrame, deviations: pd.DataFrame, baseline_fitted: pd.DataFrame,
) -> Drawing:
    """The one chart missing from earlier report versions: a plain
    observed-vs-expected trajectory, which is what actually makes the
    "excess mortality" method click for a reader who isn't fluent in
    p-values. national_series carries the full 1999-2024 observed line;
    deviations carries the 2020-2024 expected trend and its prediction
    interval (compute_deviations only ever projects forward into the
    post period, so there's nothing to plot for the interval before
    2020); baseline_fitted carries the same model's own fit across
    1999-2019, the years used to build it, with no interval since they
    weren't tested against it. The expected line is drawn across the
    full 1999-2024 span (baseline_fitted + deviations concatenated) so a
    reader can judge for themselves how well the straight-line
    assumption tracks the real pre-pandemic trend, rather than only
    seeing the projection appear at the 2020 breakpoint with no way to
    check it against history -- exactly the gap a reader question
    surfaced for heart disease and cerebrovascular disease (section 4).
    Drawn as three thin reference lines (expected, plus the interval's
    low and high edges) rather than a filled band, since a hand-computed
    polygon would have to reimplement this chart's own axis scaling to
    place its corners correctly, and getting that wrong silently would
    be far more misleading than a plain line."""
    obs = national_series[national_series["cause"] == cause].sort_values("year")
    dev = deviations[deviations["cause"] == cause].sort_values("year")
    fitted = baseline_fitted[baseline_fitted["cause"] == cause].sort_values("year")

    observed_pts = list(zip(obs["year"].astype(float), obs["age_adjusted_rate"]))
    expected_pts = list(zip(fitted["year"].astype(float), fitted["fitted"])) + list(
        zip(dev["year"].astype(float), dev["expected"])
    )
    pi_low_pts = list(zip(dev["year"].astype(float), dev["pi_low"]))
    pi_high_pts = list(zip(dev["year"].astype(float), dev["pi_high"]))

    drawing = Drawing(460, 245)
    plot = LinePlot()
    plot.x, plot.y = 50, 55
    plot.width, plot.height = 380, 160
    plot.data = [observed_pts, expected_pts, pi_low_pts, pi_high_pts]

    plot.xValueAxis.valueMin = float(obs["year"].min())
    plot.xValueAxis.valueMax = float(obs["year"].max())
    plot.xValueAxis.labelTextFormat = "%d"
    plot.xValueAxis.labels.fontSize = 7

    all_values = pd.concat([obs["age_adjusted_rate"], dev["pi_low"], dev["pi_high"], fitted["fitted"]])
    plot.yValueAxis.valueMin = float(all_values.min()) * 0.85
    plot.yValueAxis.valueMax = float(all_values.max()) * 1.1
    plot.yValueAxis.labels.fontSize = 7

    observed_color = colors.HexColor("#2b3a55")
    expected_color = colors.HexColor("#888888")
    interval_color = colors.HexColor("#c9a0a5")
    line_styles = [
        (observed_color, 2.0, None),
        (expected_color, 1.2, (4, 3)),
        (interval_color, 0.8, (2, 2)),
        (interval_color, 0.8, (2, 2)),
    ]
    for i, (color, width, dash) in enumerate(line_styles):
        plot.lines[i].strokeColor = color
        plot.lines[i].strokeWidth = width
        plot.lines[i].symbol = None
        if dash:
            plot.lines[i].strokeDashArray = dash

    drawing.add(plot)
    _add_significance_markers(drawing, plot, obs, dev, observed_color)

    legend = Legend()
    legend.x = 60
    legend.y = 15
    legend.fontSize = 7.5
    legend.dxTextSpace = 6
    legend.alignment = "right"  # swatch first, then its label
    legend.fontName = "Helvetica"
    legend.columnMaximum = 1
    legend.colorNamePairs = [
        (observed_color, "Observed"),
        (expected_color, "Expected trend"),
        (interval_color, "95% prediction interval"),
    ]
    drawing.add(legend)

    return drawing




def make_trajectory_grid(
    causes: list[str], summary: pd.DataFrame, national_series: pd.DataFrame,
    deviations: pd.DataFrame, baseline_fitted: pd.DataFrame,
) -> Drawing:
    """A small-multiples overview of all 6 test causes' trajectories side
    by side, the single figure that answers "what does the full picture
    look like" without paging through six separate full-size charts.
    Deliberately stripped down from make_trajectory_chart's single
    detailed example: no prediction-interval lines (that concept is
    already taught by Figure 1), just observed vs. expected, since the
    point of a small-multiples grid is comparability at a glance, not
    depth in any one panel. Each panel's own title reports its p-value
    directly, so the results table's numbers have a visual anchor."""
    cols, rows = 3, 2
    cell_w, cell_h = 158, 104
    margin_x, margin_y = 15, 16
    title_h = 22
    legend_h = 26
    drawing = Drawing(cols * cell_w, legend_h + rows * (cell_h + title_h))

    observed_color = colors.HexColor("#2b3a55")
    expected_color = colors.HexColor("#c0392b")

    for i, cause in enumerate(causes):
        col, row = i % cols, i // cols
        x0 = col * cell_w + margin_x
        y0 = legend_h + (rows - 1 - row) * (cell_h + title_h) + margin_y

        obs = national_series[national_series["cause"] == cause].sort_values("year")
        dev = deviations[deviations["cause"] == cause].sort_values("year")
        fitted = baseline_fitted[baseline_fitted["cause"] == cause].sort_values("year")
        r = summary[summary["cause"] == cause].iloc[0]

        observed_pts = list(zip(obs["year"].astype(float), obs["age_adjusted_rate"]))
        expected_pts = list(zip(fitted["year"].astype(float), fitted["fitted"])) + list(
            zip(dev["year"].astype(float), dev["expected"])
        )

        plot = LinePlot()
        plot.x, plot.y = x0, y0
        plot.width, plot.height = cell_w - margin_x - 8, cell_h - 12
        plot.data = [observed_pts, expected_pts]
        plot.xValueAxis.valueMin = float(obs["year"].min())
        plot.xValueAxis.valueMax = float(obs["year"].max())
        plot.xValueAxis.labelTextFormat = "%d"
        plot.xValueAxis.labels.fontSize = 5.5
        plot.xValueAxis.visibleTicks = 0
        all_values = pd.concat([obs["age_adjusted_rate"], fitted["fitted"], dev["expected"]])
        plot.yValueAxis.valueMin = float(all_values.min()) * 0.9
        plot.yValueAxis.valueMax = float(all_values.max()) * 1.05
        plot.yValueAxis.labels.fontSize = 5.5
        plot.lines[0].strokeColor = observed_color
        plot.lines[0].strokeWidth = 1.4
        plot.lines[0].symbol = None
        plot.lines[1].strokeColor = expected_color
        plot.lines[1].strokeWidth = 1.0
        plot.lines[1].strokeDashArray = (3, 2)
        plot.lines[1].symbol = None
        drawing.add(plot)
        _add_significance_markers(drawing, plot, obs, dev, observed_color, halo_r=4.0, point_r=1.8)

        title = f"{display_cause(cause)}  (p {_p(r['p_value'])})"
        drawing.add(String(x0, y0 + cell_h - 4, title, fontSize=7.5, fillColor=colors.HexColor("#1a1a1a")))

    legend = Legend()
    legend.x = cols * cell_w / 2 - 90
    legend.y = 16
    legend.fontSize = 7.5
    legend.dxTextSpace = 6
    legend.alignment = "right"  # swatch first, then its label
    legend.fontName = "Helvetica"
    legend.columnMaximum = 1
    legend.colorNamePairs = [(observed_color, "Observed"), (expected_color, "Expected trend")]
    drawing.add(legend)

    return drawing


CAUSE_COLORS = {
    "Drug overdose": "#2C5D86", "Diabetes mellitus": "#B3261E", "Cerebrovascular disease": "#7A5C99",
    "Malignant neoplasms": "#2F6F4E", "Diseases of heart": "#C26A2E", "Alzheimer's disease": "#8A6D3B",
}
INK = colors.HexColor("#1F2933")
MUTED = colors.HexColor("#5A6875")
BAND = colors.HexColor("#E3E7EB")


def _x_scale(lo: float, hi: float, x0: float, width: float):
    return lambda v: x0 + (v - lo) / (hi - lo) * width


def _x_axis(drawing, to_x, y, ticks, fmt="{:+d}%", zero_dash=True, top=None):
    """Tick labels along y, plus a dashed zero line up to `top`."""
    for t in ticks:
        drawing.add(String(to_x(t), y - 10, (fmt.format(t) if t else "0%").replace("-", "\u2212"), fontSize=7, fillColor=MUTED,
                           textAnchor="middle", fontName="Helvetica"))
        drawing.add(Line(to_x(t), y, to_x(t), y + 3, strokeColor=MUTED, strokeWidth=0.5))
    drawing.add(Line(to_x(ticks[0]), y, to_x(ticks[-1]), y, strokeColor=MUTED, strokeWidth=0.5))
    if zero_dash and top is not None:
        drawing.add(Line(to_x(0), y, to_x(0), top, strokeColor=MUTED, strokeWidth=0.6, strokeDashArray=(2, 2)))


def make_peak_vs_now_chart(summary: pd.DataFrame, deviations: pd.DataFrame, latest_year: int) -> Drawing:
    """Each cause's 2020-21 average gap (hollow dot) and latest-year gap (filled
    dot) against its pre-pandemic trend, over a gray band showing the
    latest year's 95% prediction interval: the same reading as the app's
    Findings chart. A filled dot outside its band is significant; inside it,
    faded."""
    order = summary.sort_values("acute_pct_deviation", ascending=False)["cause"].tolist()
    latest = deviations[deviations["year"] == latest_year].set_index("cause")
    row_h, top_pad, label_w, plot_w = 21, 6, 92, 345
    height = top_pad + row_h * len(order) + 38
    drawing = Drawing(460, height)
    lo, hi = -25, 45
    to_x = _x_scale(lo, hi, label_w, plot_w)
    axis_y = 34
    for i, cause in enumerate(order):
        y = height - top_pad - row_h * (i + 0.5)
        row = latest.loc[cause]
        band = (row["pi_high"] - row["expected"]) / row["expected"] * 100
        now = row["deviation"] / row["expected"] * 100
        peak = float(summary.set_index("cause").loc[cause, "acute_pct_deviation"])
        color = colors.HexColor(CAUSE_COLORS[cause])
        drawing.add(String(label_w - 8, y - 3, display_cause(cause), fontSize=8, fontName="Helvetica",
                           fillColor=INK, textAnchor="end"))
        drawing.add(Rect(to_x(max(-band, lo)), y - 5, to_x(min(band, hi)) - to_x(max(-band, lo)), 10,
                         fillColor=BAND, strokeColor=None))
        drawing.add(Line(to_x(peak), y, to_x(now), y, strokeColor=color, strokeWidth=1, strokeOpacity=0.6))
        drawing.add(Circle(to_x(peak), y, 3.6, fillColor=colors.white, strokeColor=color, strokeWidth=1.3))
        significant = bool(row["significant"])
        drawing.add(Circle(to_x(now), y, 3.8, fillColor=color, strokeColor=color,
                           fillOpacity=1 if significant else 0.35, strokeOpacity=1 if significant else 0.35))
    _x_axis(drawing, to_x, axis_y, list(range(-20, 41, 10)), top=height - top_pad)
    drawing.add(String(label_w + plot_w / 2, axis_y - 22, "Gap from pre-pandemic trend",
                       fontSize=7.5, fontName="Helvetica", fillColor=MUTED, textAnchor="middle"))
    legend_y = 2
    drawing.add(Circle(label_w + 4, legend_y + 3, 3.4, fillColor=colors.white, strokeColor=INK, strokeWidth=1.2))
    drawing.add(String(label_w + 12, legend_y, "2020-21 average", fontSize=7.5, fontName="Helvetica", fillColor=INK))
    drawing.add(Circle(label_w + 92, legend_y + 3, 3.6, fillColor=INK, strokeColor=INK))
    drawing.add(String(label_w + 100, legend_y, f"{latest_year} (faded: within normal range)", fontSize=7.5,
                       fontName="Helvetica", fillColor=INK))
    drawing.add(Rect(label_w + 238, legend_y - 1, 14, 8, fillColor=BAND, strokeColor=None))
    drawing.add(String(label_w + 256, legend_y, f"{latest_year} normal range", fontSize=7.5, fontName="Helvetica",
                       fillColor=INK))
    return drawing


def make_change_since_reference_chart(
    national_series: pd.DataFrame, deviations: pd.DataFrame, causes: list[str], latest_year: int,
    reference_year: int = 2019,
) -> Drawing:
    """For each cause, the actual change in its rate from the reference year to
    the latest year next to the change its pre-2020 trend projected. Shows why
    "above trend" and "above 2019" are different statements."""
    rates = national_series.pivot_table(index="cause", columns="year", values="age_adjusted_rate")
    expected = deviations[deviations["year"] == latest_year].set_index("cause")["expected"]
    rows = []
    for cause in causes:
        then = rates.loc[cause, reference_year]
        rows.append((cause, (rates.loc[cause, latest_year] / then - 1) * 100, (expected[cause] / then - 1) * 100))
    group_h, top_pad, label_w, plot_w = 26, 8, 92, 345
    height = top_pad + group_h * len(rows) + 38
    drawing = Drawing(460, height)
    lo, hi = -15, 15
    to_x = _x_scale(lo, hi, label_w, plot_w)
    axis_y = 34
    for i, (cause, actual, projected) in enumerate(rows):
        y = height - top_pad - group_h * (i + 0.5)
        color = colors.HexColor(CAUSE_COLORS[cause])
        drawing.add(String(label_w - 8, y - 3, display_cause(cause), fontSize=8, fontName="Helvetica",
                           fillColor=INK, textAnchor="end"))
        for value, dy, filled in [(projected, 3, False), (actual, -6, True)]:
            x_a, x_b = sorted([to_x(0), to_x(value)])
            drawing.add(Rect(x_a, y + dy - 1, max(x_b - x_a, 0.6), 7,
                             fillColor=color if filled else colors.white, strokeColor=color, strokeWidth=0.8))
            anchor = "start" if value >= 0 else "end"
            drawing.add(String(x_b + 3 if value >= 0 else x_a - 3, y + dy, _pct(value), fontSize=6.5,
                               fontName="Helvetica", fillColor=MUTED, textAnchor=anchor))
    _x_axis(drawing, to_x, axis_y, list(range(-15, 16, 5)), top=height - top_pad)
    drawing.add(String(label_w + plot_w / 2, axis_y - 22, f"Change in age-adjusted death rate since {reference_year}",
                       fontSize=7.5, fontName="Helvetica", fillColor=MUTED, textAnchor="middle"))
    legend_y = 2
    drawing.add(Rect(label_w, legend_y - 1, 12, 7, fillColor=INK, strokeColor=INK))
    drawing.add(String(label_w + 16, legend_y, f"Actual, {reference_year} to {latest_year}", fontSize=7.5,
                       fontName="Helvetica", fillColor=INK))
    drawing.add(Rect(label_w + 130, legend_y - 1, 12, 7, fillColor=colors.white, strokeColor=INK, strokeWidth=0.8))
    drawing.add(String(label_w + 146, legend_y, f"Where the pre-2020 trend pointed for {latest_year}", fontSize=7.5,
                       fontName="Helvetica", fillColor=INK))
    return drawing


def _number_word(n: int) -> str:
    words = ["zero", "one", "two", "three", "four", "five", "six"]
    return words[n] if 0 <= n < len(words) else str(n)


def _join_text(items: list[str]) -> str:
    if len(items) <= 2:
        return " and ".join(items)
    return ", ".join(items[:-1]) + ", and " + items[-1]


def _lower(cause: str) -> str:
    name = display_cause(cause)
    return name if name.startswith("Alzheimer") else name.lower()


_RANGE = re.compile(r"(?<![\w.])(\d+)-(\d+)(?![\w.]*\d-)")


def _dashes(text: str) -> str:
    """Number ranges (2020-21, 1999-2019, 83-94%) get a typographic en dash."""
    return _RANGE.sub("\\1\u2013\\2", text)


def _para(text: str, style, **kwargs) -> Paragraph:
    return Paragraph(_dashes(text), style, **kwargs)


def _figure(drawing, caption: str):
    return KeepTogether([Spacer(1, 4), drawing, _para(caption, styles["Caption"])])


def _table(caption: str, rows: list, col_widths: list, extra_style: list | None = None, note: str | None = None):
    rows = [[_dashes(c) if isinstance(c, str) else c for c in r] for r in rows]
    table = Table(rows, colWidths=col_widths, repeatRows=1)
    table.setStyle(TABLE_STYLE)
    if extra_style:
        table.setStyle(TableStyle(extra_style))
    parts = [_para(caption, styles["TableCaption"]), table]
    if note:
        parts.append(_para(note, styles["TableNote"]))
    else:
        parts.append(Spacer(1, 8))
    return KeepTogether(parts)


def _pct(v: float) -> str:
    return f"{v:+.1f}%".replace("-", "−")


def _p(v: float) -> str:
    """For prose: exact to two significant figures down to 0.001, then "< 0.001"."""
    return f"= {v:.2g}" if v >= 0.001 else "< 0.001"


def _p_cell(v: float):
    """For tables: two significant figures, in x10 notation below 0.001."""
    if v >= 0.001:
        return f"{v:.2g}"
    mantissa, exponent = f"{v:.1e}".split("e")
    return _para(f"{mantissa}\u00d710<super>{int(exponent)}</super>".replace("-", "\u2212"), styles["Cell"])


def _sens_row(cause: str, check: str, sens: pd.DataFrame) -> pd.Series:
    return sens[(sens["cause"] == cause) & (sens["check"] == check)].iloc[0]


def _shape_failure(cause: str, check: str, sens: pd.DataFrame, first: bool) -> str:
    """How a cause fails a trend-shape check: losing 2020-21 significance, or
    (if it stays significant) only a change in classification."""
    row = _sens_row(cause, check, sens)
    name = display_cause(cause) if first else _lower(cause)
    shape = "a curved trend" if check.startswith("baseline_trend_shape") else "a steady-percentage trend"
    if row["alt_p_value"] >= 0.05:
        return f"{name} loses significance with {shape} (p {_p(row['alt_p_value'])})"
    return f"{name} changes classification with {shape}"


def _alpha_change(cause: str, sens: pd.DataFrame) -> str:
    """The alpha = 0.01 check compares classifications, which depend on 2022-24
    as well as 2020-21, so say which part changed."""
    row = _sens_row(cause, "significance_threshold (0.05 vs 0.01)", sens)
    if row["primary_p_value"] < 0.01:
        return (f"At \u03b1 = 0.01, {_lower(cause)}'s 2020-21 result stays significant (p {_p(row['primary_p_value'])}), "
                f"but its later years no longer clear the stricter bar, so it is classed "
                f"{row['alt_classification']} rather than {row['primary_classification']}")
    return f"At \u03b1 = 0.01, {_lower(cause)}'s 2020-21 result is no longer significant"


def _county_summary(het: pd.DataFrame) -> str:
    """One sentence naming, for each county measure, how many of the five
    causes it was significantly associated with and in which direction."""
    main = het[het["cause"].isin(COUNTY_CAUSES)]
    rate_measures = {"pct_smokers": "smoking", "pct_uninsured_chr": "uninsured", "pct_obese": "obesity"}
    other_measures = {"median_income_chr": "higher household income", "pct_rural": "greater rurality"}
    groups, mixed = {}, []
    for var in [*rate_measures, *other_measures]:
        sig = main[(main["variable"] == var) & main["fdr_significant"]]
        pos, neg = int((sig["slope"] > 0).sum()), int((sig["slope"] < 0).sum())
        if pos and neg:
            mixed.append((var, pos, neg))
        elif pos or neg:
            groups.setdefault(("larger" if pos else "smaller", pos or neg, var in rate_measures), []).append(var)
    clauses = []
    for (direction, n, is_rate), vars_ in sorted(groups.items(), key=lambda kv: (-kv[0][1], kv[0][0])):
        subject = (f"higher {_join_text([rate_measures[v] for v in vars_])} rates" if is_rate
                   else _join_text([other_measures[v] for v in vars_]))
        scope = "all five causes" if n == 5 else f"{_number_word(n)} of the five causes"
        clauses.append(f"{subject} went with {direction} increases for {scope}")
    text = "; ".join(clauses)
    for var, pos, neg in mixed:
        name = (rate_measures | other_measures)[var].replace("greater ", "").replace("higher ", "")
        text += f". The link with {name} was mixed: larger for {_number_word(pos)} causes, smaller for {_number_word(neg)}"
    return text[0].upper() + text[1:]


def build(data: dict) -> list:
    s = data["summary"].copy()
    nc = data["negative_control"]
    het = data["heterogeneity"]
    selection_bias = data["selection_bias"]
    bridging = data["bridging"]
    sens = data["sensitivity"]
    national_series = data["national_series"]
    deviations = data["deviations"]
    baseline_fitted = data["baseline_fitted"]
    window_check = data["window_check"]

    latest_year = int(deviations["year"].max())
    latest = deviations[deviations["year"] == latest_year].set_index("cause")
    latest_pct = latest["deviation"] / latest["expected"] * 100
    by_cause = s.set_index("cause")
    disrupted = list(s.loc[s["persistence_class"] != "No significant disruption", "cause"])
    n_disrupted, n_fdr = len(disrupted), int(s["fdr_significant"].sum())
    off_now = [c for c in s["cause"] if latest.loc[c, "significant"]]
    back_in_range = [c for c in disrupted if not latest.loc[c, "significant"]]
    sensitive = window_check.loc[window_check["baseline_sensitive"], "cause"].tolist()
    by_acute = s.sort_values("acute_pct_deviation", ascending=False)["cause"].tolist()
    top_two = by_acute[:2]
    shape_checks = ["baseline_trend_shape (linear vs quadratic)", "trend_scale (linear vs log-linear)"]
    shape_fail = sens[sens["check"].isin(shape_checks) & ~sens["agrees"] & sens["cause"].isin(s["cause"])]
    shape_fail_causes = list(dict.fromkeys(shape_fail["cause"]))
    alpha_check = sens[(sens["check"] == "significance_threshold (0.05 vs 0.01)") & sens["cause"].isin(s["cause"])]
    alpha_fail = alpha_check.loc[~alpha_check["agrees"], "cause"].tolist()
    least_certain = list(dict.fromkeys(alpha_fail + shape_fail_causes))
    all_checks = sens[sens["cause"].isin(disrupted)].groupby("cause")["agrees"].all()
    fully_robust = [c for c in by_acute if c in disrupted and bool(all_checks.get(c, False))]
    hac_flip = [c for c in s["cause"] if (by_cause.loc[c, "p_value"] < 0.05) != (by_cause.loc[c, "hac_p_value"] < 0.05)]
    cancer, alz = by_cause.loc["Malignant neoplasms"], by_cause.loc["Alzheimer's disease"]
    alz_2020 = deviations[(deviations["cause"] == "Alzheimer's disease") & (deviations["year"] == 2020)].iloc[0]
    alz_2020_pct = alz_2020["deviation"] / alz_2020["expected"] * 100
    alz_now = latest_pct["Alzheimer's disease"]
    county_disruption = data["county_disruption"]
    county_labels = {c: display_cause(c) for c in COUNTY_CAUSES}

    def gaps(causes):
        return _join_text([f"{_lower(c)} ({_pct(latest_pct[c])})" for c in causes])

    above_now = [c for c in off_now if latest_pct[c] > 0]
    below_now = [c for c in off_now if latest_pct[c] < 0]
    story = []

    # --- Title block and abstract (page 1) ---
    story.append(_para("COVID Mortality Disruption Lab", styles["ReportTitle"]))
    story.append(_para(
        "Did COVID-19 disrupt the trend for six other leading causes of death, has it recovered, and where "
        "did it hit hardest?", styles["ReportSubtitle"]))
    story.append(_para("Aidan Chi &nbsp;&middot;&nbsp; October 2026", styles["Byline"]))
    story.append(HRFlowable(width="100%", thickness=0.6, color=colors.HexColor("#B8C2CC"), spaceAfter=10))

    abstract = [
        ("Background", ("Deaths attributed to COVID-19 understate the pandemic's effect on mortality, because "
         "disrupted care and other indirect effects also change death rates from other causes.")),
        ("Methods", (f"Using CDC WONDER age-adjusted death rates for 1999-{latest_year}, I projected each of six "
         "leading causes' pre-pandemic linear trend with a 95% prediction interval and tested whether 2020-21 "
         "rates departed from it. Predictions were written down before any 2020-2024 data were analyzed. A "
         "negative control, four sensitivity analyses, false discovery rate (FDR) correction and "
         "autocorrelation-robust standard errors test the results. County changes from 2015-19 to 2020-24 were "
         "regressed on five County Health Rankings measures.")),
        ("Results", (f"{_number_word(n_disrupted).capitalize()} of six causes rose significantly above trend in "
         f"2020-21, led by {_lower(top_two[0])} ({_pct(by_cause.loc[top_two[0], 'acute_pct_deviation'])}) and "
         f"{_lower(top_two[1])} ({_pct(by_cause.loc[top_two[1], 'acute_pct_deviation'])}); "
         f"{'all' if n_fdr == n_disrupted else _number_word(n_fdr)} survive FDR correction. By {latest_year}, "
         f"{gaps(above_now)} remained above trend"
         + (f" and {gaps(below_now)} had fallen below it" if below_now else "")
         + f"; {_join_text([_lower(c) for c in back_in_range])} were back within their normal ranges. "
         f"The {latest_year} status of {_number_word(len(sensitive))} causes depends on the baseline window, and "
         f"the 2020-21 results for {_join_text([_lower(c) for c in shape_fail_causes])} depend on the trend's "
         "shape. Across counties, higher smoking and uninsured rates were associated with larger increases for "
         "all five disrupted causes.")),
        ("Conclusions", ("The pandemic's indirect effect on these causes was concentrated in drug overdose and "
         "diabetes and had mostly faded nationally by 2024. Where gaps remain, their size depends heavily on how "
         "the no-pandemic trend is modeled, so they are best read as departures from a projected trend rather "
         "than as changes from 2019 levels.")),
    ]
    story.append(KeepTogether([
        _para("Abstract", styles["AbstractHead"]),
        *[_para(f"<b>{k}.</b> {v}", styles["Abstract"]) for k, v in abstract],
    ]))
    story.append(Spacer(1, 6))

    # --- 1. Introduction ---
    story.append(_para("1. Introduction", styles["H1"]))
    story.append(_para(
        "Counts of deaths attributed to COVID-19 capture only part of the pandemic's effect on mortality. "
        "Delayed or interrupted medical care, strained hospitals, isolation and economic stress can also change "
        "death rates from other causes, and those deaths are recorded under those causes, not under COVID-19. "
        "Excess-mortality analysis, which compares observed deaths with what earlier trends predicted, is the "
        "standard way to measure that wider effect.", styles["Body"]))
    story.append(_para(
        "This study applies that approach to six leading causes of death in the United States: heart disease, "
        "diabetes, Alzheimer's disease, stroke, drug overdose and cancer. It asks whether each cause departed "
        f"from its pre-pandemic trend in 2020-21, whether it had returned to trend by {latest_year}, and where "
        "across U.S. counties the changes were largest. The expected direction and confidence for each cause "
        "were recorded before any 2020-2024 data were analyzed, so the results can be judged against stated "
        "predictions rather than explained after the fact. COVID-19 itself is treated as the shock, not as an "
        "outcome. Mortality data can show what changed, by how much and where, but not why: direct infection, "
        "delayed care and economic stress leave the same mark, so every result is an association.",
        styles["Body"]))

    # --- 2. Data and methods ---
    story.append(_para("2. Data and methods", styles["H1"]))
    story.append(_para("2.1 Data", styles["H2"]))
    story.append(_para(
        "National age-adjusted death rates (2000 U.S. standard population) come from CDC WONDER's Underlying "
        "Cause of Death files: the 1999-2020 database for 1999-2019 and the 2018-2024 single-race database for "
        f"2020-{latest_year}. In 2018-19, the years both databases cover, "
        + ("every cause matched exactly. " if bridging["reliable"].all() and (bridging["median_relative_offset"].abs() < 1e-9).all()
           else "every cause matched within a 10% reliability threshold. ")
        + "Table 1 lists the causes, their ICD-10 codes and the predictions made beforehand. County data are "
        "pooled five-year totals for 2015-19 and 2020-24, which CDC reports only as crude rates, matched to five "
        "measures from the 2024 County Health Rankings &amp; Roadmaps release.", styles["Body"]))
    t1 = [["Cause", "ICD-10", "Baseline", "Prediction made beforehand"],
          ["Drug overdose", "X40-X44, X60-X64, X85, Y10-Y14", "1999-2019", "Largest disruption; may reverse by 2023-24"],
          ["Diabetes", "E10-E14", "1999-2019", "Real disruption; persistence uncertain"],
          ["Heart disease", "I00-I09, I11, I13, I20-I51", "2010-2019", "Real disruption; persistence uncertain"],
          ["Alzheimer's disease", "G30", "1999-2019", "Large, isolation-driven"],
          ["Stroke", "I60-I69", "2010-2019", "Real but harder to detect"],
          ["Cancer", "C00-C97", "1999-2019", "No disruption expected yet"],
          ["Congenital malformations", "Q00-Q99", "1999-2019", "Negative control: no disruption"]]
    story.append(_table("Table 1. Causes analyzed.", [[_para(c, styles["Cell"]) for c in r] for r in t1],
                        [1.35 * inch, 1.75 * inch, 0.75 * inch, 2.45 * inch]))

    story.append(_para("2.2 Expected trend and disruption test", styles["H2"]))
    story.append(_para(
        "For each cause, an ordinary least squares line was fit to its pre-pandemic rates and projected through "
        f"{latest_year} with a 95% prediction interval, which reflects both year-to-year variation and "
        "uncertainty in the fitted line. A year counts as disrupted when its observed rate falls outside that "
        "interval. The primary test compares the average 2020-21 gap with its exact standard error, which counts "
        "the line's uncertainty once and averages only the year-to-year noise. The breakpoint is fixed at 2020 "
        "rather than searched for. Heart disease and stroke use a 2010-2019 baseline: using only pre-2020 data, a "
        "straight line over 1999-2019 already sat well below their flattened 2019 rates (Section 3.4).",
        styles["Body"]))
    story.append(_para(
        "Causes with a significant 2020-21 disruption are classed by what happened in 2022-24: <i>Persisted</i> "
        "if any later year stayed significantly off trend in the same direction, <i>Reversed</i> if in the "
        "opposite direction, and <i>Resolved</i> if none did.", styles["Body"]))

    story.append(_para("2.3 Checks on the method", styles["H2"]))
    checks = [
        ("<b>Negative control.</b> The same pipeline was run on congenital malformations, which have no direct "
        "link to COVID-19, using death counts because the rate is reported to one decimal at about 3 per 100,000."),
        ("<b>Multiple testing.</b> Benjamini-Hochberg FDR correction across the six causes, and separately "
        "across the five county measures within each cause [7]."),
        ("<b>Autocorrelation.</b> The primary test assumes independent baseline years; a Newey-West version "
        "allows for correlation between neighboring years [8, 9]."),
        ("<b>Sensitivity analyses.</b> Each cause's classification was recomputed with the other baseline window, a stricter "
        "significance level (α = 0.01), a curved (quadratic) trend, and a trend that changes by a steady "
        "percentage each year (linear in log rate)."),
        ("<b>Cross-check and full-period test.</b> Three change-point methods search each series for a break "
        "without being told about 2020, and a secondary test pools all five post-2020 years to catch delayed "
        "effects."),
    ]
    for c in checks:
        story.append(_para(c, styles["ListItem"], bulletText="•"))

    story.append(_para("2.4 County analysis", styles["H2"]))
    story.append(_para(
        "For each of the five causes with a 2020-21 disruption, each county's change is its 2020-24 crude rate "
        "minus its 2015-19 rate. A county is included when CDC reports a reliable rate in both periods (about 20 "
        "deaths over five years). The change was regressed separately on the uninsured rate, adult smoking, adult "
        "obesity, median household income and the share of residents living in rural areas. Alzheimer's disease, "
        "which had no 2020-21 disruption, was run the same way as an exploratory comparison.", styles["Body"]))

    # --- 3. Results ---
    story.append(_para("3. Results", styles["H1"]))
    story.append(_para("3.1 Disruption in 2020-21", styles["H2"]))
    story.append(_para(
        f"{_number_word(n_disrupted).capitalize()} of the six causes rose significantly above their pre-pandemic "
        f"trend in 2020-21, and {'all' if n_fdr == n_disrupted else _number_word(n_fdr)} survive FDR correction "
        f"(Table 2). The largest increases were for {_lower(top_two[0])} and {_lower(top_two[1])}. Figure 1 shows "
        "the method on drug overdose: deaths broke above the prediction interval in 2020 and stayed there "
        "through 2023 before falling back. Significance and size are different things. Cancer's 2020-21 gap is "
        f"only {abs(cancer['acute_pct_deviation']):.1f}% but significant because its year-to-year variation before "
        "2020 was so small, while overdose needs a much larger gap to stand out (Figure 2).", styles["Body"]))

    t2 = [["Cause", "Classification", "2020-21 gap", "p-value", "FDR", f"{latest_year} gap", "Trend shape"]]
    for _, r in s.sort_values("p_value").iterrows():
        c = r["cause"]
        t2.append([display_cause(c), r["persistence_class"], _pct(r["acute_pct_deviation"]), _p_cell(r["p_value"]),
                   "Yes" if r["fdr_significant"] else "No", _pct(latest_pct[c]),
                   "Sensitive" if c in shape_fail_causes else "Robust"])
    story.append(_table(
        "Table 2. Departure from the pre-pandemic trend, by cause.", t2,
        [1.25 * inch, 1.5 * inch, 0.75 * inch, 0.7 * inch, 0.45 * inch, 0.75 * inch, 0.8 * inch],
        note="Gaps are observed minus expected, as a percent of expected. p-values are for the 2020-21 average. "
             "Trend shape: whether the result holds with a curved and with a steady-percentage trend (Section 3.4)."))

    story.append(_figure(
        make_trajectory_chart("Drug overdose", national_series, deviations, baseline_fitted),
        "<b>Figure 1.</b> Drug overdose death rate against its 1999-2019 trend. The dashed line is the trend; "
        "the pink lines mark its 95% prediction interval; circled points fall outside it."))
    story.append(_figure(
        make_trajectory_grid(list(s.sort_values("p_value")["cause"]), s, national_series, deviations, baseline_fitted),
        f"<b>Figure 2.</b> All six causes, observed rate against the pre-pandemic trend, 1999-{latest_year}. "
        "Circled points fall outside the 95% prediction interval. Panel titles give the 2020-21 p-value."))

    story.append(_para(f"3.2 Where each cause stood in {latest_year}", styles["H2"]))
    story.append(_para(
        f"Most of the disruption had faded by {latest_year} (Figure 3). {gaps(above_now).capitalize()} were "
        "still significantly above trend"
        + (f", and {gaps(below_now)} had fallen significantly below it" if below_now else "")
        + f". {_join_text([display_cause(back_in_range[0])] + [_lower(c) for c in back_in_range[1:]])} were back "
        f"within their normal ranges. Drug overdose fell from its peak to {_pct(latest_pct['Drug overdose'])}, "
        "slightly below trend but not significantly.", styles["Body"]))
    story.append(_figure(
        make_peak_vs_now_chart(s, deviations, latest_year),
        f"<b>Figure 3.</b> Gap from trend in 2020-21 and {latest_year}. Gray band: {latest_year} 95% prediction "
        "interval; a gap outside it is significant."))
    trend_note = trend_vs_reference_note(national_series, deviations, {c: display_cause(c) for c in s["cause"]})
    story.append(_para(
        "\"Above trend\" is not the same as \"above 2019.\" Figure 4 compares each cause's actual change since "
        "2019 with the change its pre-2020 trend projected. "
        + trend_note.split(". ", 1)[1] if trend_note else
        "Figure 4 compares each cause's actual change since 2019 with the change its pre-2020 trend projected.",
        styles["Body"]))
    story.append(_figure(
        make_change_since_reference_chart(national_series, deviations, by_acute, latest_year),
        f"<b>Figure 4.</b> Change in each cause's age-adjusted death rate from 2019 to {latest_year}: actual "
        "(filled) and as projected by the pre-2020 trend (outlined). The further apart the two bars, the larger "
        f"the {latest_year} gap from trend."))

    story.append(_para("3.3 Results that went against the predictions", styles["H2"]))
    story.append(_para(
        "<b>Cancer.</b> No disruption was expected this soon, since missed screenings were thought to take "
        f"longer to show up as deaths. Instead cancer rose {abs(cancer['acute_pct_deviation']):.1f}% above trend in "
        f"2020-21 (p {_p(cancer['p_value'])}) and was {abs(latest_pct['Malignant neoplasms']):.1f}% above it in "
        f"{latest_year}. The result is fragile: with a steady-percentage trend, the 2020-21 gap is no longer "
        "significant.", styles["Body"]))
    story.append(_para(
        "<b>Alzheimer's disease.</b> A large increase was expected from isolation and disrupted care. The "
        f"2020-21 test found none (p {_p(alz['p_value'])}): 2020 ran {abs(alz_2020_pct):.1f}% above trend, but "
        "2021 fell below it. Pooling all five post-2020 years does find a significant later decline "
        f"(p {_p(alz['full_period_p_value'])}), reaching {_pct(alz_now)} "
        f"by {latest_year}.", styles["Body"]))

    story.append(_para("3.4 Robustness", styles["H2"]))
    story.append(_para(
        "<b>Baseline correction.</b> Heart disease and stroke originally used the 1999-2019 baseline. Using only "
        "pre-2020 data, an F-test showed strong curvature for these two causes (F = 222.7 and 162.6, both "
        "p &lt; 0.00001) and not for the others (F &lt; 9.5): both fell steeply through the 2000s and then "
        "leveled off, so the full-period line sat 17.7 and 5.8 points below their actual 2019 rates. A curved fit "
        "would project rising rates after 2019, so a straight line over 2010-2019 is used instead. Both stay "
        "significant, with 2020-21 gaps of 8-9% rather than 26-37%.", styles["Body"]))
    story.append(_para(
        "<b>Sensitivity analyses.</b> Table 3 shows each check. "
        + f"{_join_text([display_cause(fully_robust[0])] + [_lower(c) for c in fully_robust[1:]])} hold under all of them. "
        + "; ".join(_shape_failure(c, r, sens, first=(k == 0))
                    for k, (c, r) in enumerate(zip(shape_fail["cause"], shape_fail["check"])))
        + "".join(f". {_alpha_change(c, sens)}" for c in alpha_fail)
        + f". {_join_text([display_cause(least_certain[0])] + [_lower(c) for c in least_certain[1:]])} are "
        f"therefore the {_number_word(len(least_certain))} least certain results. "
        + ("Every significant cause stays significant with autocorrelation-robust standard errors. "
           if not hac_flip else "")
        + f"The negative control shows no disruption (p {_p(nc['p_value_counts'])} on death counts).",
        styles["Body"]))

    check_cols = [("baseline_window (1999 vs 2010)", "Other\nwindow"),
                  ("significance_threshold (0.05 vs 0.01)", "α = 0.01"),
                  ("baseline_trend_shape (linear vs quadratic)", "Curved\ntrend"),
                  ("trend_scale (linear vs log-linear)", "Steady-%\ntrend")]
    t3 = [["Cause", "2020-21 result"] + [lbl for _, lbl in check_cols] + ["Robust\np-value"]]
    style3 = []
    hold_bg, change_bg = colors.HexColor("#E3EFE6"), colors.HexColor("#F6DAD7")
    for i, (_, r) in enumerate(s.sort_values("p_value").iterrows(), start=1):
        c = r["cause"]
        row = [display_cause(c), "Significant" if r["p_value"] < 0.05 else "Not significant"]
        for j, (check, _) in enumerate(check_cols, start=2):
            agrees = bool(sens[(sens["cause"] == c) & (sens["check"] == check)]["agrees"].iloc[0])
            row.append("Holds" if agrees else "Changes")
            style3.append(("BACKGROUND", (j, i), (j, i), hold_bg if agrees else change_bg))
        row.append(_p_cell(r["hac_p_value"]))
        t3.append(row)
    story.append(_table(
        "Table 3. Does each cause's classification hold under each alternative?", t3,
        [1.25 * inch, 1.05 * inch, 0.75 * inch, 0.7 * inch, 0.7 * inch, 0.75 * inch, 0.85 * inch], style3,
        note="Holds: same classification (Persisted, Resolved, or no disruption) as the primary analysis. "
             + "".join(f"{_alpha_change(c, sens)}. " for c in alpha_fail)
             + "Robust p-value: Newey-West (autocorrelation-robust) version of the 2020-21 test."))

    story.append(_para(
        f"<b>{latest_year} status and the baseline window.</b> The 2020-21 result holds under either baseline "
        f"window for every cause, but the {latest_year} status is more sensitive (Table 4). Against a 2010-2019 "
        f"trend, diabetes would be back within its normal range and drug overdose significantly below trend. "
        "For heart disease and stroke, the other window is the 1999-2019 line already shown to misfit them.",
        styles["Body"]))
    t4 = [["Cause", "Primary baseline", f"{latest_year} gap", "Other baseline", f"{latest_year} gap"]]
    for _, r in window_check.iterrows():
        t4.append([display_cause(r["cause"]), r["primary_window"], f"{_pct(r['primary_pct'])} ({r['primary_status']})",
                   r["alt_window"], f"{_pct(r['alt_pct'])} ({r['alt_status']})"])
    story.append(_table(f"Table 4. {latest_year} status under each baseline window.", t4,
                        [1.4 * inch, 1.05 * inch, 1.3 * inch, 1.05 * inch, 1.3 * inch]))

    story.append(_para("3.5 Variation across counties", styles["H2"]))
    counts = {c: len(county_disruption[c]) for c in COUNTY_CAUSES}
    story.append(_para(
        f"The county analysis covers {min(counts.values()):,} to {max(counts.values()):,} counties per cause "
        f"({max(counts.values()):,} for {_lower(max(counts, key=counts.get))}, {min(counts.values()):,} for "
        f"{_lower(min(counts, key=counts.get))}). " + _county_summary(het) + " (Table 5).", styles["Body"]))
    t5 = [["County measure"] + [county_labels[c].replace("Heart disease", "Heart").replace("Drug overdose", "Overdose")
                                for c in COUNTY_CAUSES]]
    style5 = []
    larger, smaller = colors.HexColor("#F8DCC8"), colors.HexColor("#D3E3F1")
    for i, (variable, label) in enumerate(CONTEXT_VAR_LABELS.items(), start=1):
        row = [label.replace("Median household income (per $10k)", "Income (per $10k)")]
        for j, cause in enumerate(COUNTY_CAUSES, start=1):
            r = het[(het["cause"] == cause) & (het["variable"] == variable)].iloc[0]
            row.append(f"{_scaled_slope(variable, r['slope']):+.1f}".replace("-", "−"))
            if r["fdr_significant"]:
                style5.append(("BACKGROUND", (j, i), (j, i), larger if r["slope"] > 0 else smaller))
            else:
                style5.append(("TEXTCOLOR", (j, i), (j, i), colors.HexColor("#9AA5B1")))
        t5.append(row)
    story.append(_table(
        "Table 5. Association between county measures and the change in death rate, 2015-19 to 2020-24.", t5,
        [1.7 * inch] + [0.92 * inch] * len(COUNTY_CAUSES), style5,
        note="Slopes: change in deaths per 100,000 for a full 0-1 change in a share, or per $10,000 of income. "
             "Orange: significantly larger increase; blue: significantly smaller; gray: not significant after FDR "
             "correction within each cause."))

    yearly = data["heterogeneity_yearly"].set_index(["cause", "variable"])
    pooled_rows = het.set_index(["cause", "variable"])
    yearly_counts = {c: len(df) for c, df in data["county_disruption_yearly"].items()}
    outcomes = []
    for cause in data["county_disruption_yearly"]:
        before, now = yearly.loc[(cause, "pct_rural")], pooled_rows.loc[(cause, "pct_rural")]
        change = rurality_change(before["slope"], before["fdr_significant"], now["slope"], now["fdr_significant"])
        outcomes.append(f"{change if change != 'no earlier pattern' else 'was never there'} for {_lower(cause)}")
    bias = selection_bias.set_index("cause").loc[COUNTY_CAUSES]
    story.append(_para(
        "<b>Rurality.</b> An earlier version of the county analysis required a reliable rate in individual "
        f"years, which kept only {yearly_counts['Diabetes mellitus']:,} counties for diabetes and "
        f"{yearly_counts['Drug overdose']:,} for drug overdose, mostly larger and less rural ones, and pointed to "
        f"smaller disruption in rural counties. With five-year totals that pattern {_join_text(outcomes)}. "
        "Counties still left out are mostly rural "
        f"({bias['mean_excluded'].min() * 100:.0f}-{bias['mean_excluded'].max() * 100:.0f}% rural, against "
        f"{bias['mean_included'].min() * 100:.0f}-{bias['mean_included'].max() * 100:.0f}% for included counties), "
        "and county rates are not age-adjusted, so a rural association can partly reflect older populations.",
        styles["Body"]))
    exploratory = het[het["exploratory"]] if "exploratory" in het.columns else het.iloc[0:0]
    for cause in dict.fromkeys(exploratory["cause"]):
        n_alz = len(pd.read_parquet(OUTPUTS_MODELS / f"county_disruption_{cause.lower().replace(' ', '_')}.parquet"))
        n_sig = int(exploratory[exploratory["cause"] == cause]["fdr_significant"].sum())
        story.append(_para(
            f"<b>Exploratory: {display_cause(cause)}.</b> Run the same way across {n_alz:,} counties, "
            + ("no county measure was significantly associated with its change."
               if n_sig == 0 else f"{_number_word(n_sig)} of the five measures were significant."),
            styles["Body"]))

    # --- 4. Discussion ---
    story.append(_para("4. Discussion", styles["H1"]))
    story.append(_para(
        "The national pattern agrees with published figures. Overdose deaths rose sharply in 2020-21 and fell "
        "by about a quarter from 2023 to 2024 [2]; by 2024 the heart disease death rate was below its 2019 level and "
        "stroke was within 5% of it [1]; and excess deaths among people with dementia were concentrated in the first "
        "pandemic year [4]. The rates used here match CDC's published 2022-2024 figures exactly [1-3].",
        styles["Body"]))
    story.append(_para(
        "Two results need careful reading. The first is what \"above trend\" means: diabetes in 2024 was back at "
        "its 2019 rate and reads as elevated only because its pre-2020 trend was still falling, which is also why "
        "its status depends on the baseline window. The second is cancer. Its 2020-21 gap is small and depends on "
        "the trend's shape, and outside evidence is mixed: modeling of England's actual 2020-22 deaths found breast "
        "and lung cancer deaths close to their pre-pandemic trends [6], while a review of pre-pandemic studies links "
        "each four-week delay in starting treatment with higher mortality [5]. A small effect is plausible but not "
        "established.", styles["Body"]))
    story.append(_para(
        "The Alzheimer's result reflects the outcome definition as much as the pandemic. This study counts "
        "Alzheimer's only as the underlying cause of death, and when a person with dementia died of COVID-19, "
        "COVID-19 was usually recorded as the underlying cause. Studies that also count dementia as a contributing "
        "cause found about 94,700 excess deaths in the first pandemic year [4]. The later decline found here is "
        "consistent with mortality displacement, but these data cannot confirm it.", styles["Body"]))
    story.append(_para(
        "Across counties, the strongest and most consistent associations were with smoking and the uninsured "
        "rate, which went with larger increases for every disrupted cause. These are ecological associations "
        "between county averages; they describe where increases were larger, not why.", styles["Body"]))

    # --- 5. Limitations ---
    story.append(_para("5. Limitations", styles["H1"]))
    limitations = [
        ("The design is observational and ecological, so it supports no causal claims, and county patterns may "
        "not hold for individuals."),
        ("The projected trend is a model. Results depend on the baseline window and trend shape for four causes' "
        f"{latest_year} status and for two causes' 2020-21 result; Section 3.4 reports each."),
        ("Four causes have autocorrelated baseline years, which makes the classical prediction intervals somewhat "
        "too narrow; the robust p-values address this for the 2020-21 test only."),
        ("Death-certificate coding may have shifted in 2020-21, when some deaths could be recorded as either "
        "COVID-19 or another cause."),
        ("County rates are crude, counties with too few deaths are excluded (mostly rural ones), and the county "
        "measures come from 2024, during rather than before the pandemic. Smoking and obesity are modeled "
        "estimates, and spatial correlation between neighboring counties is not modeled."),
        ("Two changes were made after results were known: the heart disease and stroke baseline, and the switch to "
        "pooled county data. Both are documented, and the earlier versions are reported alongside."),
    ]
    for item in limitations:
        story.append(_para(item, styles["ListItem"], bulletText="•"))

    # --- 6. Data availability ---
    story.append(_para("6. Data availability", styles["H1"]))
    story.append(_para(
        "All results use real CDC WONDER exports: 15 national and 18 county files. The full method, the "
        "predictions made in advance, every later change and the export steps are documented in the project "
        "repository, which also hosts the interactive app: github.com/aidanc667/covid-mortality-disruption-lab. "
        "This project uses public aggregate data for research and education and is not medical advice.",
        styles["Body"]))

    # --- References ---
    story.append(_para("References", styles["H1"]))
    refs = [
        "National Center for Health Statistics. Mortality in the United States, 2024. NCHS Data Brief No. 548. 2026.",
        ("National Center for Health Statistics. Drug overdose deaths in the United States, 2023-2024. NCHS Data "
        "Brief No. 549."),
        "National Center for Health Statistics. Mortality in the United States, 2023. NCHS Data Brief No. 521. 2024.",
        ("Chen R, Charpignon ML, Raquib RV, et al. Excess mortality with Alzheimer disease and related dementias as "
        "an underlying or contributing cause during the COVID-19 pandemic in the US. JAMA Neurol. 2023;80(9):919-928."),
        ("Hanna TP, et al. Mortality due to cancer treatment delay: systematic review and meta-analysis. BMJ. "
        "2020;371:m4087."),
        ("Arik A, Cairns AJG, Streftaris G. Cancer mortality projection: disparities, COVID-19, and late diagnosis "
        "impact. arXiv:2405.05643. 2024."),
        ("Benjamini Y, Hochberg Y. Controlling the false discovery rate: a practical and powerful approach to "
        "multiple testing. J R Stat Soc Series B. 1995;57(1):289-300."),
        ("Newey WK, West KD. A simple, positive semi-definite, heteroskedasticity and autocorrelation consistent "
        "covariance matrix. Econometrica. 1987;55(3):703-708."),
        ("Newey WK, West KD. Automatic lag selection in covariance matrix estimation. Rev Econ Stud. "
        "1994;61(4):631-653."),
    ]
    for i, ref in enumerate(refs, start=1):
        story.append(_para(ref, styles["Reference"], bulletText=f"[{i}]"))

    return story


def _decorate_page(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(MUTED)
    width, height = LETTER
    if doc.page > 1:
        canvas.drawString(doc.leftMargin, height - 0.5 * inch, "COVID Mortality Disruption Lab")
        canvas.drawRightString(width - doc.rightMargin, height - 0.5 * inch, "Aidan Chi")
        canvas.setStrokeColor(colors.HexColor("#D5DCE3"))
        canvas.setLineWidth(0.5)
        canvas.line(doc.leftMargin, height - 0.56 * inch, width - doc.rightMargin, height - 0.56 * inch)
    canvas.drawCentredString(width / 2, 0.45 * inch, str(doc.page))
    canvas.restoreState()


def main():
    OUTPUTS_REPORTS.mkdir(parents=True, exist_ok=True)
    data = load_data()
    doc = SimpleDocTemplate(
        str(OUTPUT_PATH), pagesize=LETTER,
        topMargin=0.8 * inch, bottomMargin=0.75 * inch,
        leftMargin=0.9 * inch, rightMargin=0.9 * inch,
        title="COVID Mortality Disruption Lab", author="Aidan Chi",
    )
    doc.build(build(data), onFirstPage=_decorate_page, onLaterPages=_decorate_page)
    print(f"Wrote {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
