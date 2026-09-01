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
from reportlab.graphics.shapes import Drawing
from reportlab.graphics.charts.barcharts import VerticalBarChart

from src.utils.config import OUTPUTS_MODELS, OUTPUTS_REPORTS

# Duplicated from app/components/data_loading.py's CONTEXT_VAR_LABELS
# rather than imported, to keep this standalone script fully decoupled
# from the Streamlit app runtime. Human-readable labels for the raw CHR&R
# context-variable column names -- found rendering illegibly as raw
# column names (e.g. "median_income_chr") in an earlier version.
CONTEXT_VAR_LABELS = {
    "pct_uninsured_chr": "% uninsured",
    "pct_smokers": "% adult smokers",
    "pct_obese": "% adult obesity",
    "median_income_chr": "Median household income",
    "pct_rural": "% rural",
}

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
    }


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
    drawing = Drawing(460, 180)
    chart = VerticalBarChart()
    chart.x, chart.y = 50, 30
    chart.width, chart.height = 380, 130
    chart.data = [list(ordered["slope"])]
    chart.categoryAxis.categoryNames = [CONTEXT_VAR_LABELS.get(v, v) for v in ordered["variable"]]
    chart.categoryAxis.labels.fontSize = 7
    chart.categoryAxis.labels.angle = 20
    chart.categoryAxis.labels.dy = -12
    vmin, vmax = ordered["slope"].min(), ordered["slope"].max()
    pad = max(abs(vmin), abs(vmax)) * 0.15 + 0.01
    chart.valueAxis.valueMin = vmin - pad
    chart.valueAxis.valueMax = vmax + pad
    chart.valueAxis.labels.fontSize = 7
    chart.bars[0].fillColor = colors.HexColor("#7a2d3d")
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
        "This design treats COVID-19 as a system-wide shock to the healthcare/public-health system, "
        "not as the disease under study, and asks what changed, how much, and where "
        "&mdash; not why, since mortality data alone cannot cleanly separate direct viral effects "
        "from deferred care, isolation, or economic-stress mechanisms. All results below are "
        "reported as associational, never causal, per the project's causal-language policy.",
        styles["Body"]
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
        "An expected trend is fit on 1999-2019 age-adjusted mortality rates, projected forward "
        "through 2020-2024 with a 95% prediction interval, and a year is flagged as significantly "
        "disrupted if the observed value falls outside that interval. The breakpoint (2020) is "
        "fixed by the shock's known date, not searched for.", styles["Body"]))
    story.append(Paragraph("<b>Three-way persistence classification.</b> For causes with a significant "
        "2020-2021 disruption: Persisted (still significant, same direction, through 2024), "
        "Resolved (shrank back within the interval), or Reversed (flipped sign).", styles["Body"]))
    story.append(Paragraph("<b>Independent cross-check.</b> Three change-point methods (PELT, binary "
        "segmentation, segmented regression) run on each series to verify a breakpoint near 2020 "
        "without being told to. Disagreement here is not itself evidence against a result: the "
        "primary method tests one specific pre-registered date, while the cross-check methods "
        "search the whole series for whichever single breakpoint fits best.", styles["Body"]))
    story.append(Paragraph("<b>Negative control.</b> The identical pipeline run on a cause with no "
        "direct COVID mechanism. A significant result there would indicate the method is "
        "detecting an artifact, not a real signal &mdash; a hard gate, not a footnote.", styles["Body"]))
    story.append(Paragraph("<b>Multiple-testing correction.</b> Benjamini-Hochberg FDR correction "
        "applied across the 6 test causes as one family, separately from the heterogeneity-stage "
        "correction applied per cause across its context variables.", styles["Body"]))
    story.append(Paragraph("<b>Data.</b> CDC WONDER Underlying Cause of Death, two database vintages "
        "bridged at the 2018-2019 overlap: \"1999-2020\" (database D76) for the 1999-2019 baseline, "
        "\"2018-2024, Single Race\" (database D158) for the 2020-2024 post-shock period. County-level "
        "heterogeneity data (diabetes, drug overdose) covers pre-period 2015-2019 vs. post-period "
        "2020-2024, regressed against real County Health Rankings &amp; Roadmaps context variables.",
        styles["Body"]))

    # --- 3. Results ---
    story.append(Paragraph("3. Results", styles["H1"]))
    story.append(Paragraph(
        f"<b>{n_disrupted} of 6</b> test causes show a significant disruption; "
        f"<b>{int(s['fdr_significant'].sum())} of 6</b> survive FDR correction.", styles["Body"]
    ))

    table_data = [["Cause", "Result", "p-value", "FDR-sig.", "2020-21 dev.", "2024 dev."]]
    for _, r in s.sort_values("p_value").iterrows():
        table_data.append([
            r["cause"], r["persistence_class"], f"{r['p_value']:.3g}",
            "Yes" if r["fdr_significant"] else "No",
            f"{r['acute_pct_deviation']:+.1f}%", f"{r['latest_pct_deviation']:+.1f}%",
        ])
    result_table = Table(table_data, colWidths=[1.5 * inch, 1.5 * inch, 0.75 * inch, 0.65 * inch, 0.85 * inch, 0.75 * inch])
    result_table.setStyle(TABLE_HEADER_STYLE)
    story.append(result_table)
    story.append(Paragraph(
        "\"Deviation\" is the effect size: how far the observed rate is from the expected "
        "pre-pandemic trend, as a percent. Significance and magnitude are different claims.",
        styles["Caption"]
    ))
    story.append(Spacer(1, 6))
    story.append(make_deviation_chart(s))
    story.append(Paragraph("Figure 1. Mean 2020-2021 deviation from expected trend, by cause.", styles["Caption"]))

    story.append(Paragraph("The two results that weren't supposed to happen this way", styles["H2"]))
    cancer = s[s["cause"] == "Malignant neoplasms"].iloc[0]
    alz = s[s["cause"] == "Alzheimer's disease"].iloc[0]
    story.append(Paragraph(
        f"<b>Cancer was expected to show nothing, and it didn't.</b> The pre-registered prior was "
        f"an explicit null result, with low confidence by design &mdash; delayed cancer screening "
        f"and treatment during the pandemic was expected to take years longer than the 2024 data "
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
        f"<b>Alzheimer's was expected to show a large effect, and it didn't.</b> The pre-registered "
        f"prior was high confidence of a large disruption, on the theory that pandemic-era isolation "
        f"and care-facility disruption would show up clearly in dementia mortality. It didn't "
        f"(p = {alz['p_value']:.2g}). This doesn't mean isolation had no effect; it means that effect, "
        f"if real, isn't visible in national mortality rates over this window using this method.",
        styles["Body"]
    ))

    story.append(Paragraph("Negative control", styles["H2"]))
    passed = bool(nc["passed"])
    story.append(Paragraph(
        f"{nc['cause']} &mdash; a cause concentrated in infancy with no direct COVID mechanism "
        f"&mdash; {'shows no significant disruption, as expected' if passed else 'FAILED the gate'} "
        f"(p = {nc['p_value_counts']:.3g} on raw death counts, the gating metric; WONDER's 1-decimal "
        f"age-adjusted-rate rounding made the rate-based test unreliable at this cause's low "
        f"magnitude). This does not prove every positive result above is real, but a failure here "
        f"would have been strong evidence the method was detecting an artifact.", styles["Body"]
    ))
    story.append(Paragraph(
        "Accidental drowning was the original negative control and failed &mdash; a real, "
        "statistically robust increase in deaths from 2020 onward, confirmed on raw counts, "
        "consistent with published CDC reporting on pandemic-era drowning increases (pool/beach "
        "closures, lifeguard shortages). It was swapped out because it was never actually "
        "COVID-independent, not because the method failed. Even the replacement isn't hermetically "
        "sealed from the pandemic: prenatal and obstetric care was also disrupted during "
        "2020-2021, a real if smaller and more indirect pathway than the ones behind the 6 test "
        "causes.", styles["Caption"]
    ))

    # --- 4. Robustness ---
    story.append(Paragraph("4. Robustness", styles["H1"]))
    story.append(Paragraph(
        "Three independent sensitivity checks re-fit the primary method one modeling choice at a "
        "time.", styles["Body"]
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
        verdict = "All 6 test causes agree." if n_disagree == 0 else f"{n_disagree} cause(s) disagree: {', '.join(rows.loc[~rows['agrees'], 'cause'])}."
        story.append(Paragraph(f"<b>{label}.</b> {verdict}", styles["Body"]))
    story.append(Paragraph(
        "The trend-shape check is the one that matters: heart disease and cerebrovascular disease "
        "lose significance when the pre-pandemic baseline is allowed to curve instead of being "
        "forced into a straight line &mdash; part of what the linear method reads as a 2020 "
        "disruption for these two causes could instead be the natural curvature of their "
        "pre-existing trend. Diabetes, drug overdose, and cancer hold up across every axis tested "
        "and are the most robust of the 5 disrupted causes.", styles["Callout"]
    ))
    story.append(Paragraph(
        "Separately, measured lag-1 autocorrelation of each cause's own pre-pandemic residuals is "
        "large for 5 of 6 causes (0.65-0.93; only cancer is low, at 0.19). The prediction-interval "
        "math assumes independent year-to-year residuals, which this data doesn't really satisfy "
        "&mdash; reported p-values throughout this report are likely more confident than a model "
        "accounting for this would produce. This does not overturn the results (deviations found "
        "are large, and the negative control still passed), but it is a real limitation, not a "
        "footnote.", styles["Body"]
    ))

    n_bridge_unreliable = int((~bridging["reliable"]).sum())
    story.append(Paragraph(
        f"Vintage-bridging reliability (D76 vs. D158 database overlap, 2018-2019): "
        f"{'all causes within the 10% reliability threshold' if n_bridge_unreliable == 0 else f'{n_bridge_unreliable} cause(s) exceed the threshold'} "
        f"&mdash; median relative offset is 0% for every cause tested.", styles["Body"]
    ))

    # --- 5. Heterogeneity ---
    story.append(Paragraph("5. Which counties were hit hardest", styles["H1"]))
    story.append(Paragraph(
        "For the two causes with real county-level data &mdash; diabetes and drug overdose, "
        "~3,000 counties each, pre-period 2015-2019 vs. post-period 2020-2024 &mdash; disruption "
        "magnitude is regressed against real County Health Rankings &amp; Roadmaps context "
        "variables. This stage uses crude rate, not age-adjusted rate, for both periods: CDC "
        "WONDER does not offer age-adjustment at county granularity for its 2018-2024 database, "
        "so part of any county's measured disruption could reflect its own population-aging "
        "trajectory rather than a COVID-era shift.", styles["Body"]
    ))
    for cause in ["Diabetes mellitus", "Drug overdose"]:
        cause_het = het[het["cause"] == cause].sort_values("p_value")
        n_fdr_het = int(cause_het["fdr_significant"].sum())
        story.append(Paragraph(f"{cause} &mdash; {n_fdr_het} of {len(cause_het)} context variables survive FDR correction", styles["H2"]))
        het_table_data = [["Context variable", "Slope", "p-value", "FDR-sig."]]
        for _, r in cause_het.iterrows():
            var_label = CONTEXT_VAR_LABELS.get(r["variable"], r["variable"])
            het_table_data.append([var_label, f"{r['slope']:.3f}", f"{r['p_value']:.3g}", "Yes" if r["fdr_significant"] else "No"])
        het_table = Table(het_table_data, colWidths=[2.2 * inch, 1.1 * inch, 1.0 * inch, 0.9 * inch])
        het_table.setStyle(TABLE_HEADER_STYLE)
        story.append(het_table)
        story.append(Spacer(1, 6))
        story.append(make_heterogeneity_chart(cause_het))
        story.append(Spacer(1, 6))
    story.append(Paragraph(
        "Higher uninsured rate, smoking rate, and obesity rate all predict larger disruption for "
        "both causes. Higher median household income predicts smaller disruption for both. Higher "
        "rurality predicts smaller disruption for both &mdash; the one genuinely counterintuitive "
        "result, running against a common assumption that rural areas were hit hardest. These are "
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
            verdict = f"is driven almost entirely by the less-rural half (p={lower['p_value']:.3g}) and is not significant among the more-rural half (p={upper['p_value']:.3g}) &mdash; read with real skepticism."
        story.append(Paragraph(f"<b>{cause}:</b> the relationship {verdict}", styles["Body"]))
    story.append(PageBreak())

    # --- 6. Limitations ---
    story.append(Paragraph("6. Limitations", styles["H1"]))
    limitations = [
        "Observational, ecological design &mdash; no individual-level causal inference. The "
        "county-level heterogeneity stage carries ecological fallacy risk by name: a county-average "
        "relationship does not necessarily hold at the individual level.",
        "Selection bias in the county-level heterogeneity sample: counties excluded by the "
        "suppression filter are disproportionately rural, and the rurality finding is more "
        "trustworthy for diabetes (holds up among more-rural included counties) than for drug "
        "overdose (driven by less-rural counties, not significant among more-rural ones) &mdash; "
        "see section 5.",
        "Mortality-vintage discontinuity between the two CDC WONDER databases (mitigated by "
        "bridging-overlap validation, not eliminated).",
        "ICD-10 coding practices may have shifted during 2020-2021 due to strain on "
        "death-certification systems, independent of true mortality changes.",
        "Cancer's pre-registered prior was an expected null result; the real result contradicts "
        "that &mdash; cancer shows a significant, still-persisting disruption, not the null "
        "originally expected.",
        "Temporal autocorrelation of baseline residuals is not modeled and is empirically large "
        "(0.65-0.93 for 5 of 6 test causes) &mdash; reported p-values are likely optimistic.",
        "“Significant” and “large” are different claims: cancer's disruption is "
        "real but small (+1.7% acute) next to heart disease, diabetes, cerebrovascular disease, "
        "or overdose (+26% to +41%).",
        "Heart disease and cerebrovascular disease's significance is not robust to the choice of "
        "linear vs. curved baseline trend shape.",
        "County-level heterogeneity uses crude rate, not age-adjusted rate (WONDER does not offer "
        "age-adjustment at county granularity for the 2018-2024 database), so measured disruption "
        "magnitude may partly reflect each county's own population-aging trajectory.",
        "Small-county suppression and instability at the county-level heterogeneity stage.",
        "PLACES model-based behavioral estimates (CHR&amp;R smoking/obesity/inactivity).",
        "Context-variable vintage is post-period, not pre-period: all five heterogeneity-stage "
        "context variables come from CHR&amp;R's 2024 release, measured during or after the "
        "2020-2024 disruption window, not a pre-pandemic baseline &mdash; income and the uninsured "
        "rate plausibly moved during the pandemic itself.",
        "Multiple testing across both the 6-cause family and, separately, the context-variable "
        "family per cause.",
        "Spatial non-independence of counties (spatial autocorrelation not modeled).",
        "All findings remain associational &mdash; the mechanism behind any confirmed disruption "
        "(direct viral effect vs. deferred care vs. isolation vs. economic stress) cannot be "
        "separated by mortality data alone.",
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
