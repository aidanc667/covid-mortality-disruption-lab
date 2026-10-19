"""Generates a formal, standalone PDF research report from the same
precomputed outputs the Streamlit app reads (outputs/models/*.parquet) --
never recomputes analysis, only formats existing results (same discipline
as the app, research_protocol.md's brief section 46 origin). This is a
distinct deliverable from the interactive app: something a reader can
save, print, or attach without running anything.

Requires reportlab, which is NOT in the main requirements.txt (the
deployed Streamlit app doesn't need it) -- see requirements-report.txt.
"""

import pandas as pd
from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.graphics.charts.legends import Legend
from reportlab.graphics.charts.lineplots import LinePlot
from reportlab.graphics.shapes import Circle, Drawing, String
from reportlab.lib import colors
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    HRFlowable,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.components.county_text import (
    county_pattern_sentences,
    rurality_change,
    rurality_change_is_notable,
    rurality_split_reading,
)
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
styles.add(ParagraphStyle("ReportTitle", parent=styles["Title"], fontSize=22, spaceAfter=6))
styles.add(ParagraphStyle("ReportSubtitle", parent=styles["Normal"], fontSize=13, leading=18, textColor=colors.HexColor("#444444"), spaceAfter=4))
styles.add(ParagraphStyle("Byline", parent=styles["Normal"], fontSize=10, textColor=colors.HexColor("#666666"), spaceAfter=24))
styles.add(ParagraphStyle("H1", parent=styles["Heading1"], keepWithNext=1, fontSize=15, spaceBefore=18, spaceAfter=8, textColor=colors.HexColor("#1a1a1a")))
styles.add(ParagraphStyle("H2", parent=styles["Heading2"], keepWithNext=1, fontSize=12, spaceBefore=12, spaceAfter=6, textColor=colors.HexColor("#333333")))
styles.add(ParagraphStyle("Body", parent=styles["Normal"], fontSize=10, leading=14, spaceAfter=8))
styles.add(ParagraphStyle("Caption", parent=styles["Normal"], fontSize=8.5, leading=11, textColor=colors.HexColor("#666666"), spaceAfter=10))
styles.add(ParagraphStyle("Callout", parent=styles["Normal"], fontSize=10, leading=14, spaceAfter=8, borderColor=colors.HexColor("#cccccc"), borderWidth=0.5, borderPadding=8, backColor=colors.HexColor("#f7f7f7")))

TABLE_HEADER_STYLE = TableStyle([
    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2b3a55")),
    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
    ("FONTSIZE", (0, 0), (-1, -1), 8.5),
    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f2f2f2")]),
    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cccccc")),
    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ("TOPPADDING", (0, 0), (-1, -1), 4),
    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
])


def load_data() -> dict:
    return {
        "summary": pd.read_parquet(OUTPUTS_MODELS / "disruption_summary.parquet"),
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
    cols, rows = 2, 3
    cell_w, cell_h = 210, 118
    margin_x, margin_y = 15, 16
    title_h = 14
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

        title = f"{display_cause(cause)}  (p={r['p_value']:.2g})"
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


def make_deviation_chart(summary: pd.DataFrame) -> Drawing:
    ordered = summary.sort_values("acute_pct_deviation", ascending=False)
    drawing = Drawing(460, 220)
    chart = VerticalBarChart()
    chart.x, chart.y = 50, 30
    chart.width, chart.height = 380, 170
    chart.data = [list(ordered["acute_pct_deviation"])]
    chart.categoryAxis.categoryNames = [display_cause(c) for c in ordered["cause"]]
    chart.categoryAxis.labels.fontSize = 7
    chart.categoryAxis.labels.angle = 20
    chart.categoryAxis.labels.dy = -12
    chart.valueAxis.valueMin = min(0, ordered["acute_pct_deviation"].min() - 5)
    chart.valueAxis.valueMax = ordered["acute_pct_deviation"].max() + 5
    chart.valueAxis.labels.fontSize = 7
    chart.bars[0].fillColor = colors.HexColor("#2b3a55")
    drawing.add(chart)
    return drawing


def _number_word(n: int) -> str:
    words = ["zero", "one", "two", "three", "four", "five", "six"]
    return words[n] if 0 <= n < len(words) else str(n)


def _join_text(items: list[str]) -> str:
    if len(items) <= 2:
        return " and ".join(items)
    return ", ".join(items[:-1]) + ", and " + items[-1]


def _join_names(causes) -> str:
    names = [display_cause(c) for c in causes]
    if len(names) <= 2:
        return " and ".join(names)
    return ", ".join(names[:-1]) + ", and " + names[-1]




def build(data: dict) -> list:
    s = data["summary"]
    nc = data["negative_control"]
    het = data["heterogeneity"]
    selection_bias = data["selection_bias"]
    rurality_robustness = data["rurality_robustness"]
    bridging = data["bridging"]
    sens = data["sensitivity"]
    national_series = data["national_series"]
    deviations = data["deviations"]
    baseline_fitted = data["baseline_fitted"]
    trend_shape_robust = sens[sens["check"] == "baseline_trend_shape (linear vs quadratic)"].set_index("cause")["agrees"].to_dict()

    # Where each disrupted cause stood in the latest year, so the summary
    # can't claim more persistence than the data shows (a cause can be
    # "Persisted" while its latest year is back inside the interval).
    latest_year = int(deviations["year"].max())
    latest = deviations[deviations["year"] == latest_year].set_index("cause")
    latest_pct = latest["deviation"] / latest["expected"] * 100
    disrupted = list(s.loc[s["persistence_class"] != "No significant disruption", "cause"])
    n_disrupted = len(disrupted)
    n_fdr = int(s["fdr_significant"].sum())
    # Off trend in the latest year in either direction, across all six test
    # causes: a cause significantly *below* trend (Alzheimer's) is a finding too.
    off_now = [c for c in s["cause"] if latest.loc[c, "significant"]]
    back_in_range = [c for c in disrupted if not latest.loc[c, "significant"]]

    def _gaps(causes):
        return [f"{display_cause(c) if c.startswith('Alzheimer') else display_cause(c).lower()} "
                f"({latest_pct[c]:+.1f}%)" for c in causes]

    above_text = _join_text(_gaps([c for c in off_now if latest_pct[c] > 0]))
    below_text = _join_text(_gaps([c for c in off_now if latest_pct[c] < 0]))
    off_parts = [t for t in (f"{above_text} above it" if above_text else "",
                             f"{below_text} below it" if below_text else "") if t]
    band = (latest["pi_high"] - latest["expected"]) / latest["expected"] * 100

    story = []

    # --- Title page ---
    story.append(Spacer(1, 1.2 * inch))
    story.append(Paragraph("COVID Mortality Disruption Lab", styles["ReportTitle"]))
    story.append(Spacer(1, 0.25 * inch))
    story.append(Paragraph(
        "<b>Research Question:</b> Did COVID-19 disrupt the trend for six other leading causes of death, has it recovered, and "
        "where did it hit hardest?", styles["ReportSubtitle"]
    ))
    story.append(Spacer(1, 0.2 * inch))
    story.append(Paragraph("By: Aidan Chi", styles["Byline"]))
    story.append(HRFlowable(width="100%", color=colors.HexColor("#cccccc")))
    story.append(Spacer(1, 0.3 * inch))

    story.append(Paragraph("Summary", styles["H1"]))
    story.append(Paragraph(
        f"I tested six causes of death against their own pre-pandemic trends using CDC WONDER "
        f"mortality data from 1999 to {latest_year}. <b>{_number_word(n_disrupted).capitalize()} of them "
        f"moved significantly off trend in 2020-21</b>, and {_number_word(n_fdr)} of those results hold up "
        f"after correcting for testing six "
        f"causes at once. Much of that has since faded. By {latest_year}, {_number_word(len(off_now))} "
        f"causes were significantly off trend: {', and '.join(off_parts)}. "
        f"{_join_names(back_in_range).capitalize()} were back within their normal range.", styles["Body"]
    ))
    story.append(Paragraph(
        "\"Disrupted\" here means statistically distinguishable from a cause's normal year-to-year "
        "variation before 2020, not simply far from zero: the gap falls outside the range that variation "
        "would explain. That range is narrow for steady causes and "
        f"wide for volatile ones: about ±{band['Malignant neoplasms']:.0f}% for cancer in {latest_year}, but "
        f"about ±{band['Drug overdose']:.0f}% for drug overdose. So cancer's {latest_pct['Malignant neoplasms']:+.1f}% "
        f"counts, while drug overdose's {latest_pct['Drug overdose']:+.1f}% doesn't. Being within the normal "
        "range doesn't mean no effect, only that the gap can't be told apart from ordinary year-to-year "
        "swings with this method.", styles["Body"]
    ))
    story.append(Paragraph(
        "Two results went against what I predicted before looking at the data. Cancer was expected "
        "to show nothing in this time window and showed a small but real increase. Alzheimer's "
        "disease was expected to show a large increase and showed none in 2020-21, though a "
        "decline appears in later years. A negative control, three sensitivity checks, and a "
        "multiple-testing correction were all run before any result was reported.", styles["Body"]
    ))
    story.append(Paragraph(
        "COVID-19 itself is not what's being studied here. It's treated as a shock to the health "
        "system, and the question is what happened to deaths from other causes afterward. Mortality "
        "data can show what changed, by how much, and where. It can't show why, because direct "
        "infection, delayed care, isolation, and economic stress all leave the same mark in the "
        "numbers. Every result below is an association, not a causal claim.", styles["Body"]
    ))
    story.append(Paragraph(
        "This kind of excess-mortality analysis is how public health agencies estimate a pandemic's "
        "toll beyond deaths officially attributed to the virus: missed cancer screenings, interrupted "
        "addiction treatment, delayed heart care. Each cause got a written prediction and confidence "
        "level before any 2020-2024 data was pulled, so the results can be checked against what was "
        "expected rather than explained after the fact.", styles["Body"]
    ))
    story.append(PageBreak())

    # --- 1. Research question ---
    story.append(Paragraph("1. Research question", styles["H1"]))
    story.append(Paragraph(
        "Which causes of death were most disrupted during the COVID-19 pandemic (2020-2024), how "
        "long did those disruptions last, and how did their size vary across U.S. counties by income, "
        "health insurance coverage, and rurality?",
        styles["Callout"]
    ))
    story.append(Paragraph(
        "The six causes tested are heart disease, diabetes, Alzheimer's disease, stroke, drug "
        "overdose, and cancer. Two more series fill out the design: congenital malformations as a "
        "negative control (a cause with no direct link to COVID), and COVID-19 deaths as a reference "
        "that isn't itself tested.", styles["Body"]
    ))

    # --- 2. Methods ---
    story.append(Paragraph("2. Methods", styles["H1"]))
    story.append(Paragraph("<b>Excess mortality with a fixed breakpoint.</b> For each cause, I fit a "
        "straight-line trend to its pre-pandemic age-adjusted death rate and projected it forward "
        "through 2020-2024 with a 95% prediction interval. A year counts as disrupted when the observed "
        "rate falls outside that interval. Most causes use a 1999-2019 baseline; heart disease and "
        "stroke use 2010-2019 for reasons covered in section 4. The breakpoint is 2020 because that's "
        "when the pandemic started, not because a search found it.",
        styles["Body"]))
    story.append(Paragraph("<b>How long it lasted.</b> Causes with a significant 2020-21 disruption "
        "are sorted into three groups based on the years 2022-2024. <i>Persisted</i> means the later "
        "years that were still significantly off trend leaned the same way as 2020-21. It doesn't "
        "require the most recent year to be off trend. <i>Resolved</i> means no later year was "
        "significantly off trend, and <i>Reversed</i> means the later significant years leaned the "
        "opposite way.", styles["Body"]))
    story.append(Paragraph("<b>Cross-check.</b> Three change-point methods (PELT, binary segmentation, "
        "and segmented regression) were run on each series to see whether they find a break near 2020 "
        "on their own. They search the whole series for the single best breakpoint, so landing "
        "somewhere else doesn't count against a result at the fixed 2020 date.", styles["Body"]))
    story.append(Paragraph("<b>Negative control.</b> The same pipeline was run on a cause with no direct "
        "COVID link. If it had shown a significant disruption, the method would be picking up an "
        "artifact, and no other result could be trusted.", styles["Body"]))
    story.append(Paragraph("<b>Multiple testing.</b> Testing six causes at once makes a chance "
        "\"significant\" result more likely, so the six p-values are adjusted together with the "
        "Benjamini-Hochberg false discovery rate (FDR) method. The county analysis gets its own "
        "correction for each cause.", styles["Body"]))
    story.append(Paragraph("<b>Full-period check.</b> Each cause also gets a second p-value that pools "
        "all five post-2020 years instead of just 2020-21. It doesn't replace the main test, since "
        "averaging more years can hide a reversal as easily as it can reveal a slow effect, but it "
        "catches disruptions that showed up after 2021 (see Alzheimer's in section 3).", styles["Body"]))
    story.append(Paragraph("<b>Autocorrelation check.</b> The main test assumes each baseline year's "
        "deviation from trend is independent of the last. For several causes it isn't, so the same "
        "test is also run with Newey-West (HAC) standard errors, which allow for that (section 4).",
        styles["Body"]))
    story.append(Paragraph("<b>Data.</b> CDC WONDER Underlying Cause of Death, from two databases joined "
        "at their 2018-2019 overlap: D76 (1999-2020) for the baseline and D158 (2018-2024, Single Race) "
        "for 2020-2024. County data for the five disrupted causes compares pooled 2015-2019 with pooled "
        "2020-2024 rates and is matched to County Health Rankings &amp; Roadmaps measures.",
        styles["Body"]))

    # --- 3. Results ---
    story.append(Paragraph("3. Results", styles["H1"]))
    story.append(Paragraph(
        "Figure 1 shows the method on drug overdose, the cause with the largest jump. The solid line "
        "is the observed death rate. The dashed gray line is where the 1999-2019 trend says the rate "
        "should have gone, and the two thin pink lines mark its 95% prediction interval. Overdose "
        f"deaths broke above that interval in 2020 and stayed there through 2023, then fell back in "
        f"{latest_year}.",
        styles["Body"]
    ))
    story.append(make_trajectory_chart("Drug overdose", national_series, deviations, baseline_fitted))
    story.append(Paragraph(
        f"Figure 1. Drug overdose: observed death rate against its pre-pandemic trend, 1999-{latest_year}.",
        styles["Caption"]
    ))
    story.append(Paragraph(
        f"<b>{n_disrupted} of 6</b> causes show a significant 2020-21 disruption, and "
        f"<b>{n_fdr} of 6</b> hold up after FDR correction.", styles["Body"]
    ))

    table_data = [["Cause", "Result", "p-value", "FDR-sig.", "2020-21 dev.", f"{latest_year} dev.", "Robust?"]]
    for _, r in s.sort_values("p_value").iterrows():
        robust = trend_shape_robust.get(r["cause"], True)
        table_data.append([
            display_cause(r["cause"]), r["persistence_class"], f"{r['p_value']:.3g}",
            "Yes" if r["fdr_significant"] else "No",
            f"{r['acute_pct_deviation']:+.1f}%", f"{r['latest_pct_deviation']:+.1f}%",
            "Yes" if robust else "No",
        ])
    result_table = Table(
        table_data,
        colWidths=[1.5 * inch, 1.5 * inch, 0.75 * inch, 0.6 * inch, 0.8 * inch, 0.6 * inch, 0.65 * inch],
    )
    result_table.setStyle(TABLE_HEADER_STYLE)
    story.append(result_table)
    story.append(Paragraph(
        "\"Dev.\" is the effect size: how far the observed rate sits from the expected trend, in "
        "percent. A result can be significant and still small. \"Robust?\" shows whether the result "
        "survives a curved baseline in place of a straight one; only stroke doesn't (section 4).",
        styles["Caption"]
    ))
    story.append(Spacer(1, 6))
    story.append(make_deviation_chart(s))
    story.append(Paragraph("Figure 2. Average 2020-21 deviation from the expected trend, by cause.", styles["Caption"]))

    story.append(Paragraph(
        "Figure 3 repeats Figure 1 for all six causes, with each cause's p-value in its panel title. "
        "It's worth noticing how poorly the size of a gap predicts significance. Cancer's gap is barely "
        "visible but significant, because its year-to-year noise before 2020 was so small. The next "
        "two sections explain why some results hold up and others need caution.", styles["Body"]
    ))
    story.append(make_trajectory_grid(
        list(s.sort_values("p_value")["cause"]), s, national_series, deviations, baseline_fitted,
    ))
    story.append(Paragraph(
        f"Figure 3. All six causes, observed vs. expected trend, 1999-{latest_year}.", styles["Caption"]
    ))

    story.append(Paragraph("Two results that went against the predictions", styles["H2"]))
    cancer = s[s["cause"] == "Malignant neoplasms"].iloc[0]
    alz = s[s["cause"] == "Alzheimer's disease"].iloc[0]
    story.append(Paragraph(
        f"<b>Cancer was expected to show nothing.</b> The prediction was a null result, since missed "
        f"screenings were thought to take longer than this data window to show up as deaths. Instead "
        f"cancer shows a significant disruption (p = {cancer['p_value']:.3g}, survives FDR correction), "
        f"though a small one: {cancer['acute_pct_deviation']:+.1f}% in 2020-21 and "
        f"{cancer['latest_pct_deviation']:+.1f}% in {latest_year}. Other research doesn't settle "
        f"this either. Early models predicted large increases in cancer deaths from delayed "
        f"screening, while later work using English data found lung and breast cancer deaths came in "
        f"below pre-pandemic trends.",
        styles["Body"]
    ))
    story.append(Paragraph(
        f"<b>Alzheimer's was expected to show a large effect.</b> The reasoning was that isolation and "
        f"disruption in care facilities would show up clearly in dementia deaths. It didn't "
        f"(p = {alz['p_value']:.2g} for 2020-21). That doesn't rule out an effect, only one visible in "
        f"national death rates with this method. Pooling all five post-2020 years does find a later "
        f"decline (p = {alz['full_period_p_value']:.2g}, averaging {alz['full_period_pct_deviation']:+.1f}% "
        f"vs. trend). One likely explanation is mortality displacement: people who would have died in "
        f"2023-2024 may have died earlier in the pandemic. The main classification still uses the "
        f"pre-registered 2020-21 window, so this is reported as an additional finding.",
        styles["Body"]
    ))

    story.append(Paragraph("Negative control", styles["H2"]))
    passed = bool(nc["passed"])
    nc_rate_note = ""
    if nc["cause"] in latest.index:
        nc_rate_note = (
            f" Its age-adjusted <i>rate</i> does drift {latest_pct[nc['cause']]:+.0f}% above trend by "
            f"{latest_year}, which is why the gate uses raw death counts: WONDER reports this rate to "
            f"one decimal place at about 3 per 100,000, and the rate-based test is too sensitive to "
            f"that rounding."
        )
    story.append(Paragraph(
        f"Congenital malformations, a cause concentrated in infancy with no direct COVID link, "
        f"{'shows no significant disruption, as expected' if passed else 'failed the gate'} "
        f"(p = {nc['p_value_counts']:.3g} on raw death counts).{nc_rate_note} Passing doesn't prove "
        f"every other result is real, but failing would have been strong evidence of a problem.",
        styles["Body"]
    ))
    story.append(Paragraph(
        "The first negative control, accidental drowning, failed. Drowning deaths really did rise from "
        "2020 on, in line with CDC reports tied to pool and beach closures and lifeguard shortages. It "
        "was replaced because it turned out to be affected by the pandemic, not because the method "
        "broke. The replacement isn't perfectly insulated either, since prenatal and obstetric care "
        "were also disrupted in 2020-21, but that path is smaller and less direct than for the six "
        "test causes.",
        styles["Caption"]
    ))

    # --- 4. Robustness ---
    story.append(Paragraph("4. Robustness", styles["H1"]))
    story.append(Paragraph(
        "<b>A baseline correction for heart disease and stroke.</b> Both originally used the same "
        "1999-2019 baseline as the other causes, and both failed the trend-shape check below. Using "
        "only 1999-2019 data, an F-test comparing straight-line and curved fits showed strong curvature "
        "for these two causes (F=222.7 and F=162.6, both p&lt;0.00001) and not for the others "
        "(F&lt;9.5). Both fell steeply through the 2000s and then leveled off, so a straight line "
        "across the whole period already sat 17.7 and 5.8 points below the real 2019 rate before the "
        "pandemic. A curved fit matches history well but predicts <i>rising</i> rates after 2019, a "
        "common problem when extending a polynomial past its data, so it wasn't used. A straight line "
        "over 2010-2019 has neither problem and is now the baseline for these two causes. Both stay "
        "significant, but their estimated 2020-21 deviation drops from 26-37% to 8-9%. Details are in "
        "research_protocol.md (2026-09-01 addendum).",
        styles["Body"]
    ))
    story.append(Paragraph(
        "With that correction in place, three sensitivity checks re-run the main test with one "
        "modeling choice changed at a time.", styles["Body"]
    ))
    axis_labels = {
        "baseline_window (1999 vs 2010)": "Baseline window (1999-2019 vs. 2010-2019)",
        "significance_threshold (0.05 vs 0.01)": "Significance threshold (α=0.05 vs. α=0.01)",
        "baseline_trend_shape (linear vs quadratic)": "Baseline shape (straight vs. curved)",
    }
    test_causes = list(s["cause"])
    for check_key, label in axis_labels.items():
        rows = sens[(sens["check"] == check_key) & (sens["cause"].isin(test_causes))]
        n_disagree = int((~rows["agrees"]).sum())
        cause_word, verb = ("cause", "changes") if n_disagree == 1 else ("causes", "change")
        verdict = (
            "No result changes."
            if n_disagree == 0
            else f"{_number_word(n_disagree).capitalize()} {cause_word} {verb}: {', '.join(display_cause(c) for c in rows.loc[~rows['agrees'], 'cause'])}."
        )
        story.append(Paragraph(f"<b>{label}.</b> {verdict}", styles["Body"]))
    story.append(Paragraph(
        "The baseline-shape check matters most. Heart disease now passes it and stays significant "
        "under either a straight or curved baseline. Stroke improves but doesn't fully pass: its "
        "p-value under a curved baseline went from 0.37 with the old baseline to 0.096 with the "
        "corrected one, still above 0.05. That makes stroke the least certain \"Persisted\" result in "
        "this report. Diabetes, drug overdose, and cancer pass every check.", styles["Callout"]
    ))
    story.append(Paragraph(
        "Lag-1 autocorrelation measures whether a year that runs above trend tends to be followed by "
        "another one. In the pre-pandemic baselines it is high for diabetes, overdose, and Alzheimer's "
        "(0.65-0.82), moderate for stroke (0.50), and low for heart disease and cancer (0.12-0.19). "
        "Heart disease and stroke had much higher values (0.92 and 0.93) on the old 1999-2019 "
        "baseline, which is another sign that a straight line was the wrong fit there. Because the "
        "standard test assumes no autocorrelation, the same test was rerun with Newey-West (HAC) "
        "standard errors. That raises the p-values for diabetes, overdose, and stroke by one to two "
        f"orders of magnitude, but all {n_disrupted} significant causes stay significant.",
        styles["Body"]
    ))
    hac_table_data = [["Cause", "Autocorrelation", "Classical p-value", "HAC p-value"]]
    for _, r in s.sort_values("hac_p_value").iterrows():
        hac_table_data.append([
            display_cause(r["cause"]), f"{r['residual_autocorrelation']:.2f}",
            f"{r['p_value']:.3g}", f"{r['hac_p_value']:.3g}",
        ])
    hac_table = Table(hac_table_data, colWidths=[1.7 * inch, 1.2 * inch, 1.3 * inch, 1.1 * inch])
    hac_table.setStyle(TABLE_HEADER_STYLE)
    story.append(hac_table)
    story.append(Spacer(1, 10))

    n_bridge_unreliable = int((~bridging["reliable"]).sum())
    bridge_cause_word, bridge_verb = ("cause", "exceeds") if n_bridge_unreliable == 1 else ("causes", "exceed")
    story.append(Paragraph(
        "<b>Joining the two databases.</b> In the 2018-2019 years both databases cover, "
        f"{'every cause matched within the 10% reliability threshold' if n_bridge_unreliable == 0 else f'{n_bridge_unreliable} {bridge_cause_word} {bridge_verb} the 10% threshold'}, "
        "and the median difference was 0% for every cause.", styles["Body"]
    ))

    # --- 5. Heterogeneity ---
    story.append(Paragraph("5. Which counties were hit hardest", styles["H1"]))
    county_disruption = data["county_disruption"]
    county_labels = {c: display_cause(c) for c in COUNTY_CAUSES}
    story.append(Paragraph(
        "Each of the five causes with a 2020-21 disruption has county data. For each county, disruption "
        "is the change in death rate from 2015-2019 to 2020-2024, using one five-year total per period, "
        "and it's compared against five County Health Rankings &amp; Roadmaps measures. A county is "
        "included when CDC reports a reliable rate in both periods, which takes roughly 20 deaths over "
        "five years. County rates are crude rather than age-adjusted, because WONDER doesn't offer age "
        "adjustment at the county level for its 2018-2024 database, so some of a county's change could "
        "come from its population getting older.", styles["Body"]
    ))
    coverage = [["Cause", "Counties included", "Median change (per 100,000)"]]
    for cause in COUNTY_CAUSES:
        cd = county_disruption[cause]
        coverage.append([county_labels[cause], f"{len(cd):,}", f"{cd['disruption'].median():+.1f}"])
    coverage_table = Table(coverage, colWidths=[1.8 * inch, 1.5 * inch, 2.0 * inch])
    coverage_table.setStyle(TABLE_HEADER_STYLE)
    story.append(coverage_table)
    story.append(Spacer(1, 8))

    story.append(Paragraph("What went with larger or smaller disruption (FDR-significant only):", styles["Body"]))
    for sentence in county_pattern_sentences(het, county_labels):
        story.append(Paragraph(f"&bull; {sentence}", styles["Body"]))

    short = {"Diseases of heart": "Heart", "Diabetes mellitus": "Diabetes", "Cerebrovascular disease": "Stroke",
             "Drug overdose": "Overdose", "Malignant neoplasms": "Cancer"}
    grid = [["County measure"] + [short[c] for c in COUNTY_CAUSES]]
    for variable, label in CONTEXT_VAR_LABELS.items():
        row = [label.replace("Median household income (per $10k)", "Income (per $10k)")]
        for cause in COUNTY_CAUSES:
            r = het[(het["cause"] == cause) & (het["variable"] == variable)].iloc[0]
            row.append(f"{_scaled_slope(variable, r['slope']):+.1f}{'*' if r['fdr_significant'] else ''}")
        grid.append(row)
    grid_table = Table(grid, colWidths=[1.8 * inch] + [0.85 * inch] * len(COUNTY_CAUSES))
    grid_table.setStyle(TABLE_HEADER_STYLE)
    story.append(grid_table)
    story.append(Paragraph(
        "Regression slopes: change in death rate per 100,000 for each unit of the measure (a full 0-1 "
        "share for the percentage measures; $10,000 for income). * = significant after FDR correction "
        "within that cause.", styles["Caption"]
    ))

    yearly = data["heterogeneity_yearly"]
    yearly_counts = {c: len(df) for c, df in data["county_disruption_yearly"].items()}
    heading_index = len(story)  # heading inserted below once we know whether the result changed
    yearly_rows = yearly.set_index(["cause", "variable"])
    pooled_rows = het.set_index(["cause", "variable"])
    earlier_bits, outcome_bits, notable = [], [], []
    for cause in data["county_disruption_yearly"]:
        before, now = yearly_rows.loc[(cause, "pct_rural")], pooled_rows.loc[(cause, "pct_rural")]
        earlier_bits.append(
            f"{before['slope']:+.1f}, {'significant' if before['fdr_significant'] else f'p = {before.p_value:.2f}'}, "
            f"for {county_labels[cause].lower()}"
        )
        change = rurality_change(before["slope"], before["fdr_significant"], now["slope"], now["fdr_significant"])
        outcome_bits.append(f"{change if change != 'no earlier pattern' else 'was never there'} for {county_labels[cause].lower()}")
        notable.append(rurality_change_is_notable(change, before["fdr_significant"]))
    story.append(Paragraph(
        f"An earlier version of this analysis needed a reliable rate in at least two individual years of "
        f"each period. That kept only {yearly_counts['Diabetes mellitus']:,} counties for diabetes and "
        f"{yearly_counts['Drug overdose']:,} for drug overdose, mostly larger and less rural ones, and it "
        f"pointed to smaller disruption in more rural counties (slope {'; '.join(earlier_bits)}). With "
        f"five-year totals, which keep most rural counties, that pattern {' and '.join(outcome_bits)}. "
        f"The switch was made after the earlier results were known, so it's logged in "
        f"research_protocol.md (2026-10-19 addendum) and both versions are shown in the app.",
        styles["Body"]
    ))
    story.insert(heading_index, Paragraph(
        "The rurality result changed" if any(notable) else "Comparison with the earlier county method", styles["H2"]
    ))
    bias = selection_bias.set_index("cause").loc[COUNTY_CAUSES]  # five main causes only
    story.append(Paragraph(
        "Two caveats still apply. Counties left out are still mostly rural ("
        f"{bias['mean_excluded'].min()*100:.0f}-{bias['mean_excluded'].max()*100:.0f}% rural, vs. "
        f"{bias['mean_included'].min()*100:.0f}-{bias['mean_included'].max()*100:.0f}% for included "
        "counties), though far fewer are left out than before. And rural counties tend to be older and "
        "aging faster, which crude rates don't adjust for. Splitting the included counties at their "
        "median rurality:", styles["Body"]
    ))
    for cause in COUNTY_CAUSES:
        r = rurality_robustness[rurality_robustness["cause"] == cause].set_index("half")
        upper, lower = r.loc["upper_half"], r.loc["lower_half"]
        reading = rurality_split_reading(upper["slope"], upper["p_value"], lower["slope"], lower["p_value"],
                                         full_significant=bool(pooled_rows.loc[(cause, "pct_rural"), "fdr_significant"]))
        story.append(Paragraph(
            f"&bull; <b>{county_labels[cause]}:</b> more rural half {upper['slope']:+.1f} (p={upper['p_value']:.2g}), "
            f"less rural half {lower['slope']:+.1f} (p={lower['p_value']:.2g}). {reading}", styles["Body"]
        ))
    exploratory = het[het["exploratory"]] if "exploratory" in het.columns else het.iloc[0:0]
    for cause in dict.fromkeys(exploratory["cause"]):
        alz_rows = exploratory[exploratory["cause"] == cause]
        n_alz = len(pd.read_parquet(OUTPUTS_MODELS / f"county_disruption_{cause.lower().replace(' ', '_')}.parquet"))
        n_sig = int(alz_rows["fdr_significant"].sum())
        story.append(Paragraph(
            f"<b>Exploratory: {display_cause(cause)}.</b> It had no 2020-21 disruption, so it isn't part of the "
            f"county analysis above, but it was run the same way for comparison ({n_alz:,} counties). "
            + ("None of the five county measures survives FDR correction for it. "
               if n_sig == 0 else f"{n_sig} of the five county measures survive FDR correction. ")
            + "Its national decline came in 2023-24, and averaging all of 2020-24 mixes that with earlier "
            "years, so this is a blunt measure of it.", styles["Body"]
        ))
    story.append(Paragraph(
        "This analysis has no data on local policies or on age and race, so it doesn't try to explain "
        "any single county, and these are associations, not causes.", styles["Body"]
    ))
    story.append(PageBreak())

    # --- 6. Limitations ---
    story.append(Paragraph("6. Limitations", styles["H1"]))
    limitations = [
        ("This is an observational study of population averages, so it can't support causal claims "
        "about individuals. At the county level there's also a risk of ecological fallacy: a pattern "
        "across counties may not hold for the people living in them."),
        ("Counties with too few deaths for a reliable rate are left out, and they're mostly rural. Pooling "
        "five years keeps far more of them than the earlier method did, but the most rural places are "
        "still under-represented, and the rurality result differs by cause (section 5)."),
        ("The two CDC WONDER databases may not line up perfectly. The 2018-2019 overlap check reduces "
        "this risk but can't remove it."),
        ("Death certificate coding may have shifted in 2020-21 while reporting systems were strained, "
        "separate from any real change in deaths."),
        ("Cancer was predicted to show no disruption and showed a small one. The cause isn't clear, "
        f"and its {cancer['latest_pct_deviation']:+.1f}% deviation in {latest_year} is modest."),
        ("The standard test assumes baseline years are independent, which isn't true for several causes "
        "(autocorrelation 0.65-0.82 for diabetes, overdose, and Alzheimer's; 0.50 for stroke; "
        "0.12-0.19 for heart disease and cancer). The HAC version of the test accounts for this, "
        f"and all {n_disrupted} significant causes stay significant under it (section 4)."),
        ("Significant doesn't mean large. Drug overdose and diabetes had the biggest 2020-21 jumps "
        "(roughly 27-41%), while cancer, heart disease, and stroke were real but much smaller (about 2-9%)."),
        ("Heart disease and stroke use a 2010-2019 baseline instead of 1999-2019 because the longer "
        "window didn't fit their pre-pandemic trend (section 4). Heart disease now holds up under "
        "either baseline shape. Stroke remains the least certain result."),
        ("County rates are crude, not age-adjusted, so some measured disruption may reflect each "
        "county's population getting older."),
        "Small counties are suppressed or unstable in the county data.",
        "Smoking and obesity rates come from modeled small-area estimates (PLACES), not direct counts.",
        ("The county measures come from the 2024 County Health Rankings release, so they describe "
        "counties during or after the pandemic, not before it. Income and insurance rates may have "
        "changed during the pandemic itself."),
        ("Many tests were run: across the six causes, and across the county measures for each cause. "
        "Both sets are corrected separately."),
        ("Neighboring counties aren't independent of each other, and this analysis doesn't model "
        "that spatial correlation."),
        ("Mortality data alone can't separate direct infection, delayed care, isolation, and economic "
        "stress. Every finding here is an association."),
    ]
    for item in limitations:
        story.append(Paragraph(f"&bull; {item}", styles["Body"]))

    # --- 7. Data provenance ---
    story.append(Paragraph("7. Data and reproducibility", styles["H1"]))
    story.append(Paragraph(
        "National results use 15 CDC WONDER exports (7 from the 1999-2020 database, 8 from the "
        "2018-2024 database). County results use 10 pooled exports (five causes, before and after 2020) "
        "and 2 more for the exploratory Alzheimer's county run, "
        "plus 4 year-by-year exports kept for the diabetes and overdose comparison and 2 heart disease "
        "2018-2019 exports showing the two databases match exactly county by county. No synthetic data is used anywhere. The full method, the predictions made before "
        "seeing the data, and every change made along the way are in research_protocol.md. Export "
        "steps are in manual_data_acquisition.md. The interactive app and source code are at "
        "github.com/aidanc667/covid-mortality-disruption-lab.", styles["Body"]
    ))
    story.append(Paragraph(
        "This project uses public aggregate data for research and education. It isn't medical advice "
        "and doesn't predict risk for any individual.", styles["Caption"]
    ))

    return story


def main():
    OUTPUTS_REPORTS.mkdir(parents=True, exist_ok=True)
    data = load_data()
    doc = SimpleDocTemplate(
        str(OUTPUT_PATH), pagesize=LETTER,
        topMargin=0.75 * inch, bottomMargin=0.75 * inch,
        leftMargin=0.85 * inch, rightMargin=0.85 * inch,
        title="COVID Mortality Disruption Lab", author="Aidan Chi",
    )
    doc.build(build(data))
    print(f"Wrote {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
