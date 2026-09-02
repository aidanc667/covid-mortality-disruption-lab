"""Generates a formal, standalone PDF research report from the same
precomputed outputs the Streamlit app reads (outputs/models/*.parquet) --
never recomputes analysis, only formats existing results (same discipline
as the app, research_protocol.md's brief section 46 origin). This is a
distinct deliverable from the interactive app: something a reader can
save, print, or attach without running anything.

Requires reportlab, which is NOT in the main requirements.txt (the
deployed Streamlit app doesn't need it) -- see requirements-report.txt.
"""
from datetime import date

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, HRFlowable,
)
from reportlab.graphics.shapes import Drawing, String
from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.graphics.charts.lineplots import LinePlot
from reportlab.graphics.charts.legends import Legend

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

# median_income_chr's slope is fit against raw dollars, so it's a tiny
# number (~-0.00005) next to the other four variables' 0-1-proportion
# slopes (~1-40) -- found rounding to "0.000" in this report's own table
# and rendering as an invisible flat bar next to the others on
# make_heterogeneity_chart's shared axis, even though it's highly
# significant. Scales ONLY the value shown in this report, never the
# underlying regression.
CONTEXT_VAR_DISPLAY_SCALE = {
    "median_income_chr": 10_000,
}


def _scaled_slope(variable: str, slope: float) -> float:
    return slope * CONTEXT_VAR_DISPLAY_SCALE.get(variable, 1)

OUTPUT_PATH = OUTPUTS_REPORTS / "covid_mortality_disruption_report.pdf"

styles = getSampleStyleSheet()
styles.add(ParagraphStyle("ReportTitle", parent=styles["Title"], fontSize=22, spaceAfter=6))
styles.add(ParagraphStyle("ReportSubtitle", parent=styles["Normal"], fontSize=13, textColor=colors.HexColor("#444444"), spaceAfter=4))
styles.add(ParagraphStyle("Byline", parent=styles["Normal"], fontSize=10, textColor=colors.HexColor("#666666"), spaceAfter=24))
styles.add(ParagraphStyle("H1", parent=styles["Heading1"], fontSize=15, spaceBefore=18, spaceAfter=8, textColor=colors.HexColor("#1a1a1a")))
styles.add(ParagraphStyle("H2", parent=styles["Heading2"], fontSize=12, spaceBefore=12, spaceAfter=6, textColor=colors.HexColor("#333333")))
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
        "bridging": pd.read_parquet(OUTPUTS_MODELS / "bridging_summary.parquet"),
        "sensitivity": pd.read_parquet(OUTPUTS_MODELS / "sensitivity_check.parquet"),
        "national_series": pd.read_parquet(OUTPUTS_MODELS / "national_mortality_series.parquet"),
        "deviations": pd.read_parquet(OUTPUTS_MODELS / "disruption_deviations.parquet"),
        "baseline_fitted": pd.read_parquet(OUTPUTS_MODELS / "baseline_fitted_trend.parquet"),
        "county_disruption": {
            cause: pd.read_parquet(OUTPUTS_MODELS / f"county_disruption_{cause.lower().replace(' ', '_')}.parquet")
            for cause in ["Diabetes mellitus", "Drug overdose"]
        },
    }


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

    legend = Legend()
    legend.x = 60
    legend.y = 15
    legend.fontSize = 7.5
    legend.dxTextSpace = 6
    legend.columnMaximum = 1
    legend.colorNamePairs = [
        (observed_color, "Observed"),
        (expected_color, "Expected trend"),
        (interval_color, "95% prediction interval"),
    ]
    drawing.add(legend)

    return drawing


# Short display names for the small-multiples grid, where a full cause
# name would collide with its neighbor at this width.
_SHORT_CAUSE_NAMES = {
    "Diseases of heart": "Diseases of heart",
    "Diabetes mellitus": "Diabetes mellitus",
    "Alzheimer's disease": "Alzheimer's disease",
    "Cerebrovascular disease": "Cerebrovascular disease",
    "Drug overdose": "Drug overdose",
    "Malignant neoplasms": "Malignant neoplasms (cancer)",
}


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

        title = f"{_SHORT_CAUSE_NAMES.get(cause, cause)}  (p={r['p_value']:.2g})"
        drawing.add(String(x0, y0 + cell_h - 4, title, fontSize=7.5, fillColor=colors.HexColor("#1a1a1a")))

    legend = Legend()
    legend.x = cols * cell_w / 2 - 90
    legend.y = 16
    legend.fontSize = 7.5
    legend.dxTextSpace = 6
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
    chart.categoryAxis.categoryNames = [c.replace(" mellitus", "").replace("Malignant neoplasms", "Cancer").replace("Diseases of ", "").replace("Cerebrovascular disease", "Cerebrovasc.") for c in ordered["cause"]]
    chart.categoryAxis.labels.fontSize = 7
    chart.categoryAxis.labels.angle = 20
    chart.categoryAxis.labels.dy = -12
    chart.valueAxis.valueMin = min(0, ordered["acute_pct_deviation"].min() - 5)
    chart.valueAxis.valueMax = ordered["acute_pct_deviation"].max() + 5
    chart.valueAxis.labels.fontSize = 7
    chart.bars[0].fillColor = colors.HexColor("#2b3a55")
    drawing.add(chart)
    return drawing


def make_heterogeneity_chart(het_cause_df: pd.DataFrame) -> Drawing:
    ordered = het_cause_df.sort_values("p_value")
    display_slopes = [_scaled_slope(v, s) for v, s in zip(ordered["variable"], ordered["slope"])]
    drawing = Drawing(460, 180)
    chart = VerticalBarChart()
    chart.x, chart.y = 50, 30
    chart.width, chart.height = 380, 130
    chart.data = [display_slopes]
    chart.categoryAxis.categoryNames = [CONTEXT_VAR_LABELS.get(v, v) for v in ordered["variable"]]
    chart.categoryAxis.labels.fontSize = 7
    chart.categoryAxis.labels.angle = 20
    chart.categoryAxis.labels.dy = -12
    vmin, vmax = min(display_slopes), max(display_slopes)
    pad = max(abs(vmin), abs(vmax)) * 0.15 + 0.01
    chart.valueAxis.valueMin = vmin - pad
    chart.valueAxis.valueMax = vmax + pad
    chart.valueAxis.labels.fontSize = 7
    chart.bars[0].fillColor = colors.HexColor("#7a2d3d")
    drawing.add(chart)
    return drawing


def make_county_distribution_chart(county_df: pd.DataFrame, n_bins: int = 14) -> Drawing:
    """How disruption was actually distributed across the included
    counties, not just its average -- the two context-variable charts
    above show what predicts disruption, but not whether most counties
    clustered near zero with a long tail, or split into two real groups.
    Same binning approach as the app's own county-level histogram
    (app/app_pages/geographic_heterogeneity.py)."""
    values = county_df["disruption"].dropna()
    binned = pd.cut(values, bins=n_bins)
    counts = binned.value_counts(sort=False)
    edges = binned.cat.categories

    drawing = Drawing(460, 170)
    chart = VerticalBarChart()
    chart.x, chart.y = 45, 30
    chart.width, chart.height = 390, 115
    chart.data = [list(counts.values)]
    chart.categoryAxis.categoryNames = [
        f"{iv.left:.0f}" if i % 2 == 0 else "" for i, iv in enumerate(edges)
    ]
    chart.categoryAxis.labels.fontSize = 6
    chart.valueAxis.labels.fontSize = 7
    chart.bars[0].fillColor = colors.HexColor("#4a6fa5")
    drawing.add(chart)
    return drawing


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

    story = []

    # --- Title page ---
    story.append(Spacer(1, 1.2 * inch))
    story.append(Paragraph("COVID Mortality Disruption Lab", styles["ReportTitle"]))
    story.append(Paragraph(
        "Which causes of death were most disrupted by the COVID-19 pandemic, how persistent were "
        "those disruptions, and how did they vary across U.S. counties?", styles["ReportSubtitle"]
    ))
    story.append(Paragraph(f"Aidan Chi &nbsp;&bull;&nbsp; {date.today().strftime('%B %Y')}", styles["Byline"]))
    story.append(HRFlowable(width="100%", color=colors.HexColor("#cccccc")))
    story.append(Spacer(1, 0.3 * inch))

    n_disrupted = int((s["persistence_class"] != "No significant disruption").sum())
    story.append(Paragraph("Executive summary", styles["H1"]))
    story.append(Paragraph(
        f"Of 6 major causes of death tested against real CDC WONDER mortality data (1999-2024), "
        f"<b>{n_disrupted} show a statistically significant, still-unresolved deviation</b> from "
        f"their pre-pandemic trend, four years after the pandemic began. Two results directly "
        f"contradicted this project's own pre-registered priors: cancer, expected to show no "
        f"disruption within this data window, showed a real (if modest) one; Alzheimer's disease, "
        f"expected to show a large disruption, showed none. A negative-control validation, a "
        f"three-axis sensitivity analysis, and full FDR correction across the test family were run "
        f"before any result was reported, and every methodological deviation encountered along the "
        f"way is logged rather than silently absorbed.", styles["Body"]
    ))
    story.append(Paragraph(
        "This design treats COVID-19 as a system-wide shock to the healthcare and public-health "
        "system rather than as the disease under study. It asks what changed, how much, and where, "
        "not why, because mortality data alone cannot cleanly separate direct viral effects from "
        "deferred care, isolation, and economic stress. All results below are reported as "
        "associational, never causal, following the project's causal-language policy.",
        styles["Body"]
    ))
    story.append(Paragraph(
        "Excess-mortality analysis is the same basic technique public health agencies use to "
        "estimate a pandemic's true toll beyond its officially attributed death count, and to "
        "catch the downstream damage that never shows up in a case count at all: deferred cancer "
        "screening, disrupted addiction treatment, delayed cardiac care. Running it here across "
        "six causes at once, rather than one, turns a single case study into something closer to "
        "a small research program: a stated hypothesis and confidence level per cause, one shared "
        "statistical pipeline applied identically to all six, and every result reported honestly "
        "whether or not it matched the prediction. Deciding what would count as evidence before "
        "seeing the outcome is what separates that kind of finding from a plausible story fitted "
        "to results already known.", styles["Body"]
    ))
    story.append(PageBreak())

    # --- 1. Research question ---
    story.append(Paragraph("1. Research question", styles["H1"]))
    story.append(Paragraph(
        "Which causes of death experienced the greatest and most statistically significant "
        "disruption during the COVID-19 pandemic (2020-2024), how persistent were those "
        "disruptions through the most recent available data, and how did disruption severity "
        "vary across U.S. counties by socioeconomic status, healthcare access, and rurality?",
        styles["Callout"]
    ))
    story.append(Paragraph(
        "Six substantive causes were tested: diseases of heart, diabetes mellitus, Alzheimer's "
        "disease, cerebrovascular disease, drug overdose, and malignant neoplasms (cancer). A "
        "negative control (congenital malformations, a cause with no direct COVID mechanism) "
        "and a COVID-19 reference series (not a hypothesis test) round out the 8-series design. "
        "Every cause's confidence level was stated before any 2020-2024 data was pulled or "
        "analyzed, so results can be checked against stated priors rather than narrated after "
        "the fact.", styles["Body"]
    ))

    # --- 2. Methods ---
    story.append(Paragraph("2. Methods", styles["H1"]))
    story.append(Paragraph("<b>Primary method: known-date interrupted time series (\"excess mortality\").</b> "
        "An expected trend is fit on pre-pandemic age-adjusted mortality rates (1999-2019 for 4 "
        "of the 6 test causes; 2010-2019 for Diseases of heart and Cerebrovascular disease, "
        "corrected after the full-range fit was found to misdescribe their real trajectory -- "
        "section 4), projected forward through 2020-2024 with a 95% prediction interval, and a "
        "year is flagged as significantly disrupted if the observed value falls outside that "
        "interval. The breakpoint (2020) is fixed by the shock's known date, not searched for.",
        styles["Body"]))
    story.append(Paragraph("<b>Three-way persistence classification.</b> For causes with a significant "
        "2020-2021 disruption: Persisted (still significant, same direction, through 2024), "
        "Resolved (shrank back within the interval), or Reversed (flipped sign).", styles["Body"]))
    story.append(Paragraph("<b>Independent cross-check.</b> Three independent statistical techniques "
        "for detecting a shift in a trend (PELT, binary segmentation, and segmented regression) are "
        "run on each series to see whether they land on a breakpoint near 2020 without being told "
        "to. Disagreement here is not itself evidence against a result: the primary method tests "
        "one specific pre-registered date, while the cross-check methods search the whole series "
        "for whichever single breakpoint fits best.", styles["Body"]))
    story.append(Paragraph("<b>Negative control.</b> The identical pipeline is run on a cause with "
        "no direct COVID mechanism. A significant result there would mean the method is detecting "
        "an artifact rather than a real signal. This is treated as a hard gate, not a minor caveat.",
        styles["Body"]))
    story.append(Paragraph("<b>Multiple-testing correction.</b> Testing 6 causes at once raises the "
        "odds that one \"significant\" result appears by chance alone, so Benjamini-Hochberg FDR "
        "correction, a standard statistical adjustment for exactly this problem, is applied across "
        "the 6 test causes as one family. The heterogeneity stage gets its own separate correction, "
        "applied per cause across its context variables.", styles["Body"]))
    story.append(Paragraph("<b>Full-period secondary check.</b> Alongside the pre-registered acute "
        "(2020-2021) test, each cause also gets a p-value pooling all five post-2020 years, using "
        "the identical t-test over a wider window. This never replaces the acute test or gates the "
        "classification above -- averaging more years can hide a real reversal as easily as it can "
        "reveal a delayed effect -- but it catches disruptions the acute window is too narrow to "
        "see (section 3).", styles["Body"]))
    story.append(Paragraph("<b>Autocorrelation-robust check (Newey-West/HAC).</b> The acute test's "
        "prediction-interval math assumes each baseline year is independent noise. Several causes' "
        "residuals are measurably autocorrelated, so a second version of the same test, with "
        "Newey-West standard errors instead of the classical formula, is also reported (section 4).",
        styles["Body"]))
    story.append(Paragraph("<b>Data.</b> CDC WONDER Underlying Cause of Death, two database vintages "
        "bridged at the 2018-2019 overlap: \"1999-2020\" (database D76) for the 1999-2019 baseline, "
        "\"2018-2024, Single Race\" (database D158) for the 2020-2024 post-shock period. County-level "
        "heterogeneity data (diabetes, drug overdose) covers pre-period 2015-2019 vs. post-period "
        "2020-2024, regressed against real County Health Rankings &amp; Roadmaps context variables.",
        styles["Body"]))

    # --- 3. Results ---
    story.append(Paragraph("3. Results", styles["H1"]))
    story.append(Paragraph(
        "Before the summary table, here is what the primary method actually measures, shown for "
        "drug overdose: the cause with the largest acute disruption and the clearest before-and-"
        "after pattern. The solid line is the real observed rate. The dashed gray line is what "
        "the 1999-2019 trend would have predicted for 2020-2024 had nothing changed, with its 95% "
        "prediction interval shown as the two thin pink lines around it. A year counts as "
        "significantly disrupted when the solid line steps outside that interval, which is "
        "exactly what happens starting in 2020 and what pulls back toward it by 2024.",
        styles["Body"]
    ))
    story.append(make_trajectory_chart("Drug overdose", national_series, deviations, baseline_fitted))
    story.append(Paragraph(
        "Figure 1. Drug overdose: observed mortality rate against its pre-pandemic trend, "
        "1999-2024.", styles["Caption"]
    ))
    story.append(Paragraph(
        f"<b>{n_disrupted} of 6</b> test causes show a significant disruption; "
        f"<b>{int(s['fdr_significant'].sum())} of 6</b> survive FDR correction.", styles["Body"]
    ))

    table_data = [["Cause", "Result", "p-value", "FDR-sig.", "2020-21 dev.", "2024 dev.", "Robust?"]]
    for _, r in s.sort_values("p_value").iterrows():
        robust = trend_shape_robust.get(r["cause"], True)
        table_data.append([
            r["cause"], r["persistence_class"], f"{r['p_value']:.3g}",
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
        "\"Deviation\" is the effect size: how far the observed rate is from the expected "
        "pre-pandemic trend, as a percent. Significance and magnitude are different claims. "
        "\"Robust?\" marks whether the result survives an alternate, curved baseline fit "
        "instead of the primary straight line; cerebrovascular disease does not, though less "
        "severely than before its baseline was corrected (see section 4 for why).",
        styles["Caption"]
    ))
    story.append(Spacer(1, 6))
    story.append(make_deviation_chart(s))
    story.append(Paragraph("Figure 2. Mean 2020-2021 deviation from expected trend, by cause.", styles["Caption"]))

    story.append(Paragraph(
        "Figure 1 walked through one cause in detail; here is the same comparison for all six, "
        "side by side. Each panel plots the real observed rate against what its own pre-pandemic "
        "trend would have predicted, with that cause's primary p-value in the title. The point "
        "isn't to read each panel closely (the table above already has the numbers) -- it's to see at a "
        "glance which gaps look large, which look small, and how little that visual impression "
        "lines up with which ones are actually significant, exactly the puzzle the next two "
        "sections work through.", styles["Body"]
    ))
    story.append(make_trajectory_grid(
        list(s.sort_values("p_value")["cause"]), s, national_series, deviations, baseline_fitted,
    ))
    story.append(Paragraph(
        "Figure 3. All six test causes, observed vs. expected trend, 1999-2024.", styles["Caption"]
    ))

    story.append(Paragraph("The two results that weren't supposed to happen this way", styles["H2"]))
    cancer = s[s["cause"] == "Malignant neoplasms"].iloc[0]
    alz = s[s["cause"] == "Alzheimer's disease"].iloc[0]
    story.append(Paragraph(
        f"<b>Cancer was expected to show nothing, and it didn't.</b> The pre-registered prior was "
        f"an explicit null result, with low confidence by design. Delayed cancer screening and "
        f"treatment during the pandemic was expected to take years longer than the 2024 data "
        f"window to appear as excess mortality. Instead, cancer shows a {cancer['persistence_class'].lower()} "
        f"disruption (p = {cancer['p_value']:.3g}, survives FDR correction), though its magnitude "
        f"({cancer['acute_pct_deviation']:+.1f}% in 2020-21) is modest next to the larger disruptions "
        f"above. The wider literature on this question is unsettled: early 2020 models projected "
        f"large future increases in cancer deaths from delayed screening, but more recent modeling "
        f"using actual pandemic-era England data found lung and breast cancer deaths came in lower "
        f"than pre-pandemic trends predicted, not higher. This project's small, real, persisting "
        f"effect should be read against that uncertainty.",
        styles["Body"]
    ))
    story.append(Paragraph(
        f"<b>Alzheimer's was expected to show a large effect. It showed none.</b> The pre-registered "
        f"prior was high confidence of a large disruption, on the theory that pandemic-era isolation "
        f"and care-facility disruption would show up clearly in dementia mortality. It didn't "
        f"(p = {alz['p_value']:.2g}). That doesn't mean isolation had no effect on people with "
        f"Alzheimer's. If there is a real effect, it simply isn't visible in national mortality "
        f"rates over this window, using this method. Pooling all five post-2020 years instead of "
        f"just the acute window does turn up a real, later decline (p = {alz['full_period_p_value']:.2g}, "
        f"averaging {alz['full_period_pct_deviation']:+.1f}% vs. trend), consistent with mortality "
        f"displacement: patients who would otherwise have died in 2023-2024 may already have died "
        f"earlier in the pandemic. This project's own primary classification stays scoped to the "
        f"pre-registered acute window rather than switching after the fact, so the headline result "
        f"above is correct as reported; this is an additional finding, not a contradiction.",
        styles["Body"]
    ))

    story.append(Paragraph("Negative control", styles["H2"]))
    passed = bool(nc["passed"])
    story.append(Paragraph(
        f"{nc['cause']}, a cause concentrated in infancy with no direct COVID mechanism, "
        f"{'shows no significant disruption, as expected' if passed else 'FAILED the gate'} "
        f"(p = {nc['p_value_counts']:.3g} on raw death counts, the gating metric. WONDER's 1-decimal "
        f"age-adjusted-rate rounding made the rate-based test unreliable at this cause's low "
        f"magnitude). This does not prove every positive result above is real, but a failure here "
        f"would have been strong evidence the method was detecting an artifact.", styles["Body"]
    ))
    story.append(Paragraph(
        "Accidental drowning was the original negative control, and it failed: deaths rose in a "
        "real, statistically robust way starting in 2020, confirmed on raw counts and consistent "
        "with published CDC reporting on pandemic-era drowning increases (pool and beach closures, "
        "lifeguard shortages). It was swapped out because it was never actually independent of the "
        "pandemic, not because the method itself failed. Even the replacement isn't fully "
        "insulated: prenatal and obstetric care were also disrupted during 2020-2021, a real, if "
        "smaller and more indirect, pathway compared with the ones behind the 6 test causes.",
        styles["Caption"]
    ))

    # --- 4. Robustness ---
    story.append(Paragraph("4. Robustness", styles["H1"]))
    story.append(Paragraph(
        "<b>A baseline correction, found through this exact process.</b> Diseases of heart and "
        "Cerebrovascular disease originally used the same 1999-2019 baseline as the other four "
        "test causes. The trend-shape check below found their significance didn't survive a "
        "curved baseline; investigating why, using only 1999-2019 data with no reference to "
        "2020+, found an F-test comparing linear vs. quadratic fits showed overwhelming curvature "
        "for exactly these two causes (F=222.7 and F=162.6, both p&lt;0.00001, vs. F&lt;9.5 for "
        "every other test cause) -- both declined steeply through the 2000s, then flattened, and "
        "a straight line across the full period was already 17.7 and 5.8 points below the real "
        "2019 value before the pandemic. A quadratic fit tracks history almost perfectly but was "
        "rejected as the fix: extrapolated to 2020-2024 it predicts <i>rising</i> rates for both "
        "causes, the standard failure mode of polynomial extrapolation. A shorter, more recent "
        "linear window (2010-2019) has neither defect, and is now this project's baseline for "
        "these two causes only. Both remain significant -- heart disease more confidently than "
        "before -- but the reported deviation drops from an overstated 26-37% to a defensible "
        "8-9%, and both causes now drift slightly toward their expected trend by 2024 rather than "
        "away from it. Full investigation: research_protocol.md's 2026-09-01 addendum.",
        styles["Body"]
    ))
    story.append(Paragraph(
        "With that correction in place, three independent sensitivity checks re-fit the primary "
        "method one modeling choice at a time.", styles["Body"]
    ))
    axis_labels = {
        "baseline_window (1999 vs 2010)": "Baseline window (1999-2019 vs. shorter 2010-2019)",
        "significance_threshold (0.05 vs 0.01)": "Significance threshold (α=0.05 vs. stricter α=0.01)",
        "baseline_trend_shape (linear vs quadratic)": "Baseline trend shape (linear vs. curved/quadratic)",
    }
    test_causes = list(s["cause"])
    for check_key, label in axis_labels.items():
        rows = sens[(sens["check"] == check_key) & (sens["cause"].isin(test_causes))]
        n_disagree = int((~rows["agrees"]).sum())
        cause_word, verb = ("cause", "disagrees") if n_disagree == 1 else ("causes", "disagree")
        verdict = (
            "All 6 test causes agree."
            if n_disagree == 0
            else f"{n_disagree} {cause_word} {verb}: {', '.join(rows.loc[~rows['agrees'], 'cause'])}."
        )
        story.append(Paragraph(f"<b>{label}.</b> {verdict}", styles["Body"]))
    story.append(Paragraph(
        "The trend-shape check, now run against each cause's corrected baseline, is the one that "
        "matters most. Heart disease is now fully robust: it stays significant whether the "
        "baseline is a straight line or a curve. Cerebrovascular disease is substantially "
        "improved but not fully resolved -- its quadratic p-value moves from 0.37 under the old, "
        "uncorrected full-range comparison to a much closer 0.096 under the corrected window, "
        "better, but still on the wrong side of 0.05. It remains this project's single most "
        "uncertain \"Persisted\" classification. Diabetes, drug overdose, and cancer were never "
        "affected by any of this and hold up across every axis tested.", styles["Callout"]
    ))
    story.append(Paragraph(
        "Separately, lag-1 autocorrelation, a measure of whether one year's unexpected result "
        "tends to be followed by another, was calculated for each cause's own pre-pandemic "
        "residuals. It is large for diabetes, overdose, and Alzheimer's (0.65-0.82); moderate for "
        "cerebrovascular disease (0.50); and low for heart disease and cancer (0.12-0.19) -- heart "
        "disease's and cerebrovascular disease's dropped sharply after their baseline correction "
        "(from 0.92 and 0.93 on the old full-range baseline), since a shorter window's residuals "
        "are far less serially smooth than a 21-year decline. The classical prediction-interval math "
        "assumes independent year-to-year residuals, which the high-autocorrelation causes' "
        "baselines don't satisfy, so a Newey-West (HAC) autocorrelation-robust version of the same "
        "acute-window test was built and is reported alongside the classical p-value: it raises "
        "diabetes, drug overdose, and cerebrovascular disease's p-values by roughly 1-2 orders of "
        "magnitude, but all 5 causes previously found significant remain significant under it. This "
        "is a genuine correction, not just a disclosed caveat, and it is a reassuring result rather "
        "than a damaging one.", styles["Body"]
    ))
    hac_table_data = [["Cause", "Autocorrelation", "Classical p-value", "HAC p-value"]]
    for _, r in s.sort_values("hac_p_value").iterrows():
        hac_table_data.append([
            r["cause"], f"{r['residual_autocorrelation']:.2f}",
            f"{r['p_value']:.3g}", f"{r['hac_p_value']:.3g}",
        ])
    hac_table = Table(hac_table_data, colWidths=[1.7 * inch, 1.2 * inch, 1.3 * inch, 1.1 * inch])
    hac_table.setStyle(TABLE_HEADER_STYLE)
    story.append(hac_table)
    story.append(Spacer(1, 10))

    n_bridge_unreliable = int((~bridging["reliable"]).sum())
    bridge_cause_word, bridge_verb = ("cause", "exceeds") if n_bridge_unreliable == 1 else ("causes", "exceed")
    story.append(Paragraph(
        f"Vintage-bridging reliability (D76 vs. D158 database overlap, 2018-2019): "
        f"{'all causes fall within the 10% reliability threshold' if n_bridge_unreliable == 0 else f'{n_bridge_unreliable} {bridge_cause_word} {bridge_verb} the threshold'}. "
        f"The median relative offset was 0% for every cause tested.", styles["Body"]
    ))

    # --- 5. Heterogeneity ---
    story.append(Paragraph("5. Which counties were hit hardest", styles["H1"]))
    county_disruption = data["county_disruption"]
    n_diabetes_counties = len(county_disruption["Diabetes mellitus"])
    n_overdose_counties = len(county_disruption["Drug overdose"])
    story.append(Paragraph(
        f"For the two causes with real county-level data, disruption magnitude is regressed "
        f"against real County Health Rankings &amp; Roadmaps context variables. Of roughly 3,143 "
        f"U.S. counties, only {n_diabetes_counties} qualify for diabetes and {n_overdose_counties} "
        f"for drug overdose, pre-period 2015-2019 versus post-period 2020-2024 -- CDC WONDER "
        f"suppresses any county-year cell with too few deaths to protect privacy, and a county "
        f"needs at least 2 non-suppressed years in each period to be included at all. This stage "
        "also uses crude rate, not age-adjusted rate, for both periods, because WONDER does not "
        "offer age-adjustment at county granularity for its 2018-2024 database. That means part "
        "of any county's measured disruption could reflect its own population-aging trajectory "
        "rather than a COVID-era shift.", styles["Body"]
    ))
    for cause in ["Diabetes mellitus", "Drug overdose"]:
        cause_het = het[het["cause"] == cause].sort_values("p_value")
        n_fdr_het = int(cause_het["fdr_significant"].sum())
        story.append(Paragraph(f"{cause}: {n_fdr_het} of {len(cause_het)} context variables survive FDR correction", styles["H2"]))
        het_table_data = [["Context variable", "Slope", "p-value", "FDR-sig."]]
        for _, r in cause_het.iterrows():
            var_label = CONTEXT_VAR_LABELS.get(r["variable"], r["variable"])
            display_slope = _scaled_slope(r["variable"], r["slope"])
            het_table_data.append([var_label, f"{display_slope:.3f}", f"{r['p_value']:.3g}", "Yes" if r["fdr_significant"] else "No"])
        het_table = Table(het_table_data, colWidths=[2.2 * inch, 1.1 * inch, 1.0 * inch, 0.9 * inch])
        het_table.setStyle(TABLE_HEADER_STYLE)
        story.append(het_table)
        story.append(Spacer(1, 6))
        story.append(make_heterogeneity_chart(cause_het))
        story.append(Spacer(1, 2))
        story.append(make_county_distribution_chart(county_disruption[cause]))
        story.append(Paragraph(
            f"Figure: {cause} -- context-variable associations (top), and how disruption was "
            f"actually distributed across the {len(county_disruption[cause])} included counties "
            "(bottom; x-axis is the disruption value, y-axis is county count).",
            styles["Caption"]
        ))
        story.append(Spacer(1, 6))
    story.append(Paragraph(
        "Higher uninsured rate, smoking rate, and obesity rate all predict larger disruption for "
        "both causes. Higher median household income predicts smaller disruption for both. Higher "
        "rurality predicts smaller disruption for both, the one genuinely counterintuitive result "
        "here, running against the common assumption that rural areas were hit hardest. These are "
        "associations, not causal claims.", styles["Body"]
    ))
    story.append(Paragraph("Rurality finding: a real caveat, found on self-audit", styles["H2"]))
    bias_text = "; ".join(
        f"{r['cause']}: excluded counties average {r['mean_excluded']*100:.0f}% rural vs. "
        f"{r['mean_included']*100:.0f}% rural for counties included"
        for _, r in selection_bias.iterrows()
    )
    story.append(Paragraph(
        f"Counties excluded from this regression (too few non-suppressed years) are far more rural, "
        f"on average, than the counties included: {bias_text}. Splitting the included counties at "
        f"their own median rurality shows the two causes are not equally trustworthy here.",
        styles["Body"]
    ))
    for cause in ["Diabetes mellitus", "Drug overdose"]:
        r = rurality_robustness[rurality_robustness["cause"] == cause].set_index("half")
        upper, lower = r.loc["upper_half"], r.loc["lower_half"]
        if upper["p_value"] < 0.05:
            verdict = f"holds up and even strengthens among the more-rural half (p={upper['p_value']:.3g}) vs. the less-rural half (p={lower['p_value']:.3g})."
        else:
            verdict = f"is driven almost entirely by the less-rural half (p={lower['p_value']:.3g}) and is not significant among the more-rural half (p={upper['p_value']:.3g}). This result should be read with real skepticism."
        story.append(Paragraph(f"<b>{cause}:</b> the relationship {verdict}", styles["Body"]))
    story.append(PageBreak())

    # --- 6. Limitations ---
    story.append(Paragraph("6. Limitations", styles["H1"]))
    limitations = [
        "Observational, ecological design: no individual-level causal inference. The county-level "
        "heterogeneity stage carries ecological fallacy risk by name, meaning a county-average "
        "relationship does not necessarily hold at the individual level.",
        "Selection bias in the county-level heterogeneity sample: counties excluded by the "
        "suppression filter are disproportionately rural, and the rurality finding is more "
        "trustworthy for diabetes (holds up among more-rural included counties) than for drug "
        "overdose (driven by less-rural counties, not significant among more-rural ones). See "
        "section 5.",
        "Mortality-vintage discontinuity between the two CDC WONDER databases, mitigated by "
        "bridging-overlap validation but not eliminated.",
        "ICD-10 coding practices may have shifted during 2020-2021 due to strain on "
        "death-certification systems, independent of true mortality changes.",
        "Cancer's pre-registered prior was an expected null result, and the real result "
        "contradicts that: cancer shows a significant, still-persisting disruption rather than "
        "the null originally expected.",
        "The classical p-value assumes independent baseline residuals, which is empirically false "
        "for several causes (autocorrelation 0.65-0.82 for diabetes, overdose, and Alzheimer's; "
        "0.50 for cerebrovascular disease; 0.12-0.19, roughly independent, for heart disease and "
        "cancer). A Newey-West (HAC) autocorrelation-robust version of the test is now also "
        "reported (section 4): p-values rise for the high-autocorrelation causes, but all 5 "
        "previously-significant causes remain significant.",
        "“Significant” and “large” are different claims: drug overdose and diabetes show the "
        "largest disruptions (15-41%), while cancer, heart disease, and cerebrovascular disease "
        "are all real and FDR-significant but modest by comparison (3-9%).",
        "Diseases of heart and Cerebrovascular disease use a corrected 2010-2019 baseline, not "
        "1999-2019 like the other four test causes, after finding the longer window was already "
        "diverging from their real trajectory before 2020 (section 4). Heart disease is now fully "
        "robust to the choice of linear vs. curved baseline trend shape; cerebrovascular disease "
        "is substantially improved but remains this project's single most uncertain result.",
        "County-level heterogeneity uses crude rate, not age-adjusted rate, because WONDER does "
        "not offer age-adjustment at county granularity for the 2018-2024 database. Measured "
        "disruption magnitude may partly reflect each county's own population-aging trajectory.",
        "Small-county suppression and instability at the county-level heterogeneity stage.",
        "PLACES model-based behavioral estimates (CHR&amp;R smoking/obesity/inactivity).",
        "Context-variable vintage is post-period, not pre-period. All five heterogeneity-stage "
        "context variables come from CHR&amp;R's 2024 release, measured during or after the "
        "2020-2024 disruption window rather than from a pre-pandemic baseline. Income and the "
        "uninsured rate plausibly moved during the pandemic itself.",
        "Multiple testing across both the 6-cause family and, separately, the context-variable "
        "family per cause.",
        "Spatial non-independence of counties (spatial autocorrelation not modeled).",
        "All findings remain associational. The mechanism behind any confirmed disruption, "
        "whether direct viral effect, deferred care, isolation, or economic stress, cannot be "
        "separated out by mortality data alone.",
    ]
    for item in limitations:
        story.append(Paragraph(f"&bull; {item}", styles["Body"]))

    # --- 7. Data provenance ---
    story.append(Paragraph("7. Data provenance and reproducibility", styles["H1"]))
    story.append(Paragraph(
        "All national-level results use 15 real CDC WONDER exports (7 from the 1999-2019 "
        "database, 8 from the 2018-2024 database). All county-level heterogeneity results use "
        "4 real CDC WONDER exports (diabetes and drug overdose, pre/post period, county-grouped). "
        "Nothing in this project is synthetic. Full methodology, pre-registered hypotheses, and "
        "every deviation logged as it happened: research_protocol.md. Exact manual data-export "
        "steps: manual_data_acquisition.md. Interactive app and full source: "
        "github.com/aidanc667/covid-mortality-disruption-lab.", styles["Body"]
    ))
    story.append(Paragraph(
        "This project uses publicly available aggregate data and is intended for research and "
        "educational purposes. It does not provide medical advice or individual-level risk "
        "predictions.", styles["Caption"]
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
