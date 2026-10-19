import pandas as pd
import streamlit as st

from app.components.charts import then_vs_now_chart
from app.components.county_text import (
    county_pattern_sentences,
    rurality_change,
    rurality_change_is_notable,
    rurality_split_reading,
)
from app.components.data_loading import (
    CAUSE_COLORS,
    CONTEXT_VAR_LABELS,
    EXPLORATORY_COUNTY_CAUSES,
    HETEROGENEITY_CAUSES,
    NEGATIVE_CONTROL,
    TEST_CAUSES,
    YEARLY_COMPARISON_CAUSES,
    data_available,
    display_cause,
    load_county_disruption,
    load_county_disruption_yearly,
    load_disruption_deviations,
    load_disruption_summary,
    load_heterogeneity_rurality_robustness,
    load_heterogeneity_selection_bias,
    load_heterogeneity_summary,
    load_heterogeneity_summary_yearly,
    load_negative_control,
    load_sensitivity_check,
    scale_context_slope_for_display,
    sensitivity_check_available,
    synthetic_banner,
)
from app.components.findings_text import findings_takeaway
from app.components.ui import takeaway_html
from src.ingestion.county_health_rankings import load_year as load_chr_year
from src.utils.config import OUTPUTS_REPORTS


def _names_with(items: list[str]) -> str:
    return " and ".join(items) if len(items) <= 2 else ", ".join(items[:-1]) + ", and " + items[-1]


def _names(causes) -> str:
    names = [display_cause(c) for c in causes]
    return " and ".join(names) if len(names) <= 2 else ", ".join(names[:-1]) + ", and " + names[-1]


st.title("Findings")
synthetic_banner()

if not data_available():
    st.warning("No precomputed data available yet.", icon=":material/warning:")
    st.stop()

summary = load_disruption_summary()
neg_control = load_negative_control().iloc[0]
het = load_heterogeneity_summary()
deviations = load_disruption_deviations()

latest_year = int(deviations["year"].max())
latest = deviations[deviations["year"] == latest_year].set_index("cause")
disrupted = summary.loc[summary["persistence_class"] != "No significant disruption", "cause"].tolist()
n_disrupted = len(disrupted)
n_fdr = int(summary["fdr_significant"].sum())
faded = [c for c in disrupted if not latest.loc[c, "significant"]]
below_now = [c for c in faded if latest.loc[c, "deviation"] < 0]
# Disrupted upward in 2020-21 but significantly BELOW trend in the latest year
# (still "Persisted": the significant 2022-24 years lean upward on average).
crossed = [
    c for c in disrupted
    if latest.loc[c, "significant"] and (latest.loc[c, "deviation"] > 0) != (summary.set_index("cause").loc[c, "acute_pct_deviation"] > 0)
]

CAUSE_LABELS = {c: display_cause(c) for c in TEST_CAUSES}


def _band_pct(cause: str) -> float:
    """Half-width of a cause's latest-year 95% prediction interval, as % of expected."""
    r = latest.loc[cause]
    return (r["pi_high"] - r["expected"]) / r["expected"] * 100


st.html(takeaway_html(findings_takeaway(summary, deviations, CAUSE_LABELS)))

chart_col, side_col = st.columns([2.2, 1], gap="large", vertical_alignment="center")
with chart_col, st.container(border=True):
    st.markdown("**Peak disruption vs. where each cause stands now**")
    st.altair_chart(
        then_vs_now_chart(summary, deviations, CAUSE_COLORS, CAUSE_LABELS),
        width="stretch",
    )
with side_col:
    st.caption(
        f"Hollow dot: the 2020–21 average gap from each cause's own pre-pandemic trend. Filled dot: "
        f"{latest_year}. **Gray band: that cause's normal year-to-year range in {latest_year}.** A filled "
        f"dot outside its band is significant (solid); inside it, the gap is within normal noise (faded). "
        "Distance from 0% alone doesn't decide it: cancer's band is about "
        f"±{_band_pct('Malignant neoplasms'):.0f}%, stroke's about ±{_band_pct('Cerebrovascular disease'):.0f}%."
    )
    st.caption(
        "**What \"disrupted\" means here:** statistically distinguishable from that cause's normal "
        "year-to-year variation before 2020, not simply far from zero. \"Within normal range\" doesn't mean "
        "no effect: a gap inside the band can still be thousands of deaths, it just can't be told apart "
        "from ordinary year-to-year swings with this method."
    )
    report_path = OUTPUTS_REPORTS / "covid_mortality_disruption_report.pdf"
    if report_path.exists():
        st.download_button(
            "Download the PDF report",
            data=report_path.read_bytes(),
            file_name="covid_mortality_disruption_report.pdf",
            mime="application/pdf",
            icon=":material/description:",
            width="stretch",
        )

results_tab, surprises_tab, robustness_tab, counties_tab, limits_tab = st.tabs(
    ["Results", "Surprises", "Robustness", "Counties", "Limits"]
)

with results_tab:
    passed = bool(neg_control["passed"])
    reversed_causes = summary.loc[summary["persistence_class"] == "Reversed", "cause"].map(display_cause)
    with st.container(horizontal=True):
        with st.container(border=True):
            st.metric(
                "Disrupted", f"{n_disrupted} of {len(summary)}",
                help="Causes whose 2020–21 death rate moved outside what a straight-line projection "
                     "of the pre-pandemic trend predicts: a real statistical deviation, not year-to-year noise.",
            )
        with st.container(border=True):
            st.metric(
                "Survive FDR correction", f"{n_fdr} of {len(summary)}",
                help="Testing 6 causes at once means some 'significant' results could appear by chance. "
                     "FDR correction is a stricter bar that accounts for this.",
            )
        with st.container(border=True):
            st.metric(
                "Reversed", ", ".join(reversed_causes) if len(reversed_causes) else "None",
                help="'Reversed' means the years after 2021 that were significantly off trend went the "
                     "opposite way from 2020–21.",
            )
        with st.container(border=True):
            st.metric(
                "Negative control", "Passed" if passed else "FAILED",
                help="The identical method run on a cause with no direct COVID mechanism (congenital "
                     "malformations), to confirm it doesn't find 'disruption' everywhere. See Robustness.",
            )
    if not passed:
        st.error(
            "The negative control did not pass. Per research_protocol.md §7 method 4, this is a hard "
            "gate. Results on the other 6 causes should not be trusted until this is resolved.",
            icon=":material/error:",
        )
    # Built from the data so it can't contradict chart B above: a cause can
    # be "Persisted" (2022 or 2023 still significantly off trend) while its
    # latest year is back inside the prediction interval, or even below trend.
    definition = (
        f"**What \"Persisted\" means:** at least one year from 2022 to {latest_year} stayed "
        "significantly off trend in the same direction as 2020–21. It does not mean every year did."
    )
    if faded:
        definition += (
            f" By {latest_year}, {_names(faded)} {'was' if len(faded) == 1 else 'were'} no longer "
            "significantly off trend"
        )
        if below_now:
            gaps = ", ".join(
                f"{display_cause(c)} {latest.loc[c, 'deviation'] / latest.loc[c, 'expected'] * 100:+.1f}%"
                for c in below_now
            )
            definition += f", and {_names(below_now)} had dipped below it ({gaps}, not significant)"
        definition += "."
    if crossed:
        gaps = ", ".join(
            f"{latest.loc[c, 'deviation'] / latest.loc[c, 'expected'] * 100:+.1f}%" for c in crossed
        )
        definition += (
            f" {_names(crossed)} {'is' if len(crossed) == 1 else 'are'} still classed Persisted because "
            f"its 2022–23 years ran significantly above trend, but by {latest_year} {'it' if len(crossed) == 1 else 'they'} "
            f"had fallen significantly below it ({gaps})."
        )
    st.caption(definition)
    display = summary.sort_values("p_value").copy()
    if sensitivity_check_available():
        trend_shape = load_sensitivity_check()
        trend_shape = trend_shape[trend_shape["check"] == "baseline_trend_shape (linear vs quadratic)"][["cause", "agrees"]]
        display = display.merge(trend_shape, on="cause", how="left")
        display["agrees"] = display["agrees"].fillna(True)
    else:
        display["agrees"] = True
    display["cause"] = display["cause"].map(display_cause)
    st.dataframe(
        display[["cause", "persistence_class", "p_value", "fdr_significant", "acute_pct_deviation", "latest_pct_deviation", "agrees"]],
        column_config={
            "cause": st.column_config.TextColumn("Cause", width="medium"),
            "persistence_class": st.column_config.TextColumn("Result", width="medium"),
            "p_value": st.column_config.NumberColumn("p-value", format="%.3g"),
            "fdr_significant": st.column_config.CheckboxColumn("Survives FDR"),
            "acute_pct_deviation": st.column_config.NumberColumn("2020–21 deviation", format="%+.1f%%"),
            "latest_pct_deviation": st.column_config.NumberColumn("2024 deviation", format="%+.1f%%"),
            "agrees": st.column_config.CheckboxColumn(
                "Robust to trend shape",
                help="False means this result loses significance if the pre-pandemic baseline is fit "
                     "as a curve instead of a straight line. See Causes of death or Data Quality.",
            ),
        },
        hide_index=True,
        width="stretch",
    )
    st.caption(
        "\"Deviation\" is the effect size: how far the observed rate is from the expected trend, as a "
        "percent. Significance and magnitude are different claims (a result can be statistically "
        "significant while still small, or vice versa). \"Robust to trend shape\" flags whether the "
        "result survives a curved baseline fit instead of a straight line; only stroke fails it. Heart "
        "disease had the same issue but is now fully robust after a baseline correction (see Causes of "
        "death, and research_protocol.md's 2026-09-01 addendum)."
    )

with surprises_tab:
    st.write(
        "This project pre-registered a confidence level for each cause *before* looking at any "
        "2020–2024 data (Methods → Pre-registered hypotheses). Two results contradict those priors, "
        "which is exactly why they're worth highlighting: a result confirming what you expected is easy "
        "to get by accident; one that surprises you isn't."
    )

    cancer = summary[summary["cause"] == "Malignant neoplasms"].iloc[0]
    alz = summary[summary["cause"] == "Alzheimer's disease"].iloc[0]

    with st.container(border=True):
        st.write("**Cancer was expected to show nothing, and it didn't.**")
        st.write(
            "The pre-registered prior was an explicit null, \"low\" confidence by design: delayed "
            "cancer screening was expected to take years longer than this 2024 data window to show up "
            f"as excess mortality. Instead, cancer shows a real, FDR-significant "
            f"**{cancer['persistence_class'].lower()}** disruption (p = {cancer['p_value']:.3g}), modest "
            f"in size ({cancer['acute_pct_deviation']:+.1f}% in 2020–21, "
            f"{cancer['latest_pct_deviation']:+.1f}% by 2024) next to the larger disruptions below. "
            "Either the deferred-care effect moved faster than expected, or something else is "
            "contributing; this analysis can't tell which, but the result itself is real."
        )

    with st.container(border=True):
        st.write("**Alzheimer's was expected to show a large effect, and it didn't.**")
        st.write(
            "The pre-registered prior was \"high confidence\" of a large effect, on the theory that "
            "pandemic-era isolation and care-facility disruption would show up clearly in dementia "
            f"mortality. It didn't (p = {alz['p_value']:.2g}). That doesn't mean isolation had no "
            "effect, only that it isn't visible in national mortality *rates* over this window using "
            "this method. Pooling all five post-2020 years instead finds a real, later decline "
            f"(p = {alz['full_period_p_value']:.2g}); see Causes of death for the numbers."
        )

with robustness_tab:
    passed = bool(neg_control["passed"])
    with st.container(horizontal=True):
        with st.container(border=True):
            st.metric("Negative control", "Passed" if passed else "FAILED")
        with st.container(border=True):
            st.caption("Cause tested")
            st.write(f"**{neg_control['cause'].split(',')[0]}**")
        with st.container(border=True):
            st.metric(
                "p-value", f"{neg_control['p_value_counts']:.3g}",
                help="Computed on raw death counts, the actual gating metric, not age-adjusted rate.",
            )
    st.write(
        "Before trusting any of the above, the pipeline runs the identical method on a cause with no "
        "direct COVID mechanism: congenital malformations, concentrated in infancy and driven by "
        "prenatal/genetic factors. It passed, no significant disruption. That doesn't prove every "
        "positive result above is real, but a failure here would have been strong evidence the method "
        "was just detecting noise, and it didn't fail."
    )
    if NEGATIVE_CONTROL in latest.index:
        nc = latest.loc[NEGATIVE_CONTROL]
        st.caption(
            f"One thing to know when comparing against the charts: the negative control's age-adjusted "
            f"*rate* runs {nc['deviation'] / nc['expected'] * 100:+.0f}% vs. its trend by {latest_year}"
            f"{' (outside its prediction interval)' if nc['significant'] else ''}. The gate deliberately "
            "uses raw death counts instead, because this cause's rate is reported to one decimal at "
            "~3 per 100,000 and the rate-based test is oversensitive to that rounding. Data quality → "
            "Negative control has the full reasoning and both results."
        )
    with st.expander("This wasn't the first choice: a real methodological correction"):
        st.write(
            "Accidental drowning was the original negative control, and it failed: a real, "
            "statistically robust increase in deaths from 2020 on, confirmed on raw counts (not a "
            "rounding artifact) and consistent with published CDC reporting on pandemic-era drowning "
            "increases (pool/beach closures, lifeguard shortages, more unsupervised home-pool time). It "
            "was swapped out because it was never actually COVID-independent, not because the method "
            "failed. Full account: research_protocol.md's 2026-09-01 addenda."
        )
    if sensitivity_check_available():
        sens = load_sensitivity_check()
        test_sens = sens[sens["cause"].isin(TEST_CAUSES)]
        checks = [
            ("baseline_window (1999 vs 2010)", "Baseline window (1999–2019 vs. shorter 2010–2019)"),
            ("significance_threshold (0.05 vs 0.01)", "Significance threshold (α=0.05 vs. stricter α=0.01)"),
            ("baseline_trend_shape (linear vs quadratic)", "Baseline trend shape (linear vs. curved/quadratic)"),
        ]
        all_disagreeing = set()
        for check_name, _ in checks:
            rows = test_sens[test_sens["check"] == check_name]
            all_disagreeing.update(rows.loc[~rows["agrees"], "cause"].map(display_cause))
        hac_disagree = summary[(summary["p_value"] < 0.05) != (summary["hac_p_value"] < 0.05)]["cause"].map(display_cause).tolist()

        if not all_disagreeing and not hac_disagree:
            st.success(
                "Every result holds up under all 3 alternate modeling choices and autocorrelation-robust "
                "standard errors.", icon=":material/check_circle:",
            )
        else:
            st.warning(
                f"Results mostly hold up, with one exception: **{', '.join(sorted(all_disagreeing | set(hac_disagree)))}** "
                "depends partly on some of these modeling choices. Details below.",
                icon=":material/warning:",
            )

        with st.expander("See the full robustness breakdown"):
            for check_name, label in checks:
                check_rows = test_sens[test_sens["check"] == check_name]
                n_disagree = int((~check_rows["agrees"]).sum())
                if n_disagree == 0:
                    st.success(f"**{label}:** all 6 test causes agree.", icon=":material/check_circle:")
                else:
                    disagreeing = check_rows.loc[~check_rows["agrees"], "cause"].map(display_cause).tolist()
                    cause_word, verb = ("cause", "disagrees") if n_disagree == 1 else ("causes", "disagree")
                    st.warning(
                        f"**{label}:** {n_disagree} {cause_word} {verb} ({', '.join(disagreeing)}). "
                        "See Data Quality for the full breakdown.",
                        icon=":material/warning:",
                    )
            st.caption(
                "The trend-shape check originally flagged heart disease and stroke, whose declines had "
                "flattened after 2010; both now use a 2010–2019 baseline, and heart disease is fully "
                "robust while stroke still depends partly on the straight-line assumption "
                "(research_protocol.md, 2026-09-01). Diabetes and drug overdose were later moved to "
                "2010–2019 too, because their 1999–2019 lines ran 5–9% below the actual 2017–19 rates "
                "(post hoc, 2026-10-19). Both, and cancer, hold up across every axis."
            )
            if not hac_disagree:
                st.success(
                    "**Autocorrelation-robust standard errors (Newey-West/HAC):** all 5 significant "
                    "causes stay significant. The classical test assumes independent baseline years, "
                    "which is measurably false for several causes; the HAC version moves p-values by up "
                    "to about an order of magnitude in either direction, but none cross 0.05.",
                    icon=":material/check_circle:",
                )
            else:
                st.warning(
                    f"**Autocorrelation-robust standard errors (Newey-West/HAC):** {len(hac_disagree)} "
                    f"cause(s) disagree with the classical result ({', '.join(hac_disagree)}). See "
                    "Causes of death for each cause's HAC p-value.",
                    icon=":material/warning:",
                )
    else:
        st.info("Run `python -m scripts.run_sensitivity_check` to populate this section.", icon=":material/info:")

with counties_tab:
    county_labels = {c: display_cause(c) for c in HETEROGENEITY_CAUSES}
    county_counts = {c: len(load_county_disruption(c)) for c in HETEROGENEITY_CAUSES}
    st.write(
        "For each of the five causes with a 2020–21 disruption, each county's change in death rate "
        "from 2015–19 to 2020–24 was compared against five county measures. Counties included: "
        + "; ".join(f"{county_labels[c].lower()} {n:,}" for c, n in county_counts.items())
        + ". Only FDR-significant associations count below."
    )
    for sentence in county_pattern_sentences(het, county_labels):
        st.markdown(f"- {sentence}")
    alz_het = het[het["cause"].isin(EXPLORATORY_COUNTY_CAUSES)]
    for cause in EXPLORATORY_COUNTY_CAUSES:
        rows = alz_het[alz_het["cause"] == cause]
        sig = rows[rows["fdr_significant"]]
        st.caption(
            f"**Exploratory:** {display_cause(cause)}, which had no 2020–21 disruption, was run the same way "
            f"({len(load_county_disruption(cause)):,} counties) and kept out of the summary above. "
            + ("None of the five measures survives FDR correction for it."
               if sig.empty else f"{len(sig)} of the five measures survive FDR correction; see Geographic patterns.")
        )
    st.caption(
        "These are associations, not causes. County rates are crude, not age-adjusted (CDC doesn't offer "
        "age adjustment at county level for 2018–2024), so part of any change could reflect a county's "
        "population getting older. That matters most for rurality, since rural counties tend to be older."
    )

    yearly_het = load_heterogeneity_summary_yearly()
    changes = {}
    for cause in YEARLY_COMPARISON_CAUSES:
        now = het[(het["cause"] == cause) & (het["variable"] == "pct_rural")].iloc[0]
        before = yearly_het[(yearly_het["cause"] == cause) & (yearly_het["variable"] == "pct_rural")].iloc[0]
        change = rurality_change(before["slope"], before["fdr_significant"], now["slope"], now["fdr_significant"])
        if rurality_change_is_notable(change, before["fdr_significant"]):
            changes[cause] = change
    if changes:
        outcomes = _names_with([f"{'disappears' if ch == 'disappears' else 'reverses'} for {display_cause(c).lower()}"
                                for c, ch in changes.items()])
        st.info(
            f"**This changed the rurality result.** The earlier year-by-year method kept only "
            f"{len(load_county_disruption_yearly('Diabetes mellitus')):,} counties for diabetes and "
            f"{len(load_county_disruption_yearly('Drug overdose')):,} for drug overdose, mostly larger and "
            "less rural ones, and pointed to smaller disruption in more rural counties. With the rural "
            f"counties included, that pattern {outcomes}. It was largely a product of which counties were "
            "left out. Geographic patterns → What predicts it shows both versions side by side.",
            icon=":material/sync_alt:",
        )

    with st.expander("Full regression results, by cause"):
        for cause in HETEROGENEITY_CAUSES:
            cause_het = het[het["cause"] == cause].sort_values("p_value").copy()
            cause_het["slope"] = cause_het.apply(
                lambda r: scale_context_slope_for_display(r["variable"], r["slope"]), axis=1
            )
            cause_het["variable"] = cause_het["variable"].map(CONTEXT_VAR_LABELS).fillna(cause_het["variable"])
            st.write(
                f"**{display_cause(cause)}** ({county_counts[cause]:,} counties): "
                f"{int(cause_het['fdr_significant'].sum())} of {len(cause_het)} measures survive FDR correction"
            )
            st.dataframe(
                cause_het[["variable", "slope", "p_value", "fdr_significant"]],
                column_config={
                    "variable": st.column_config.TextColumn("County measure", width="large"),
                    "slope": st.column_config.NumberColumn("Direction/magnitude", format="%.2f", width="small"),
                    "p_value": st.column_config.NumberColumn("p-value", format="%.3g", width="small"),
                    "fdr_significant": st.column_config.CheckboxColumn("FDR-significant", width="small"),
                },
                hide_index=True,
                width="stretch",
            )

    # One real example county per cause per extreme, so the regression isn't
    # just an abstract slope -- picked live from the same parquet the map and
    # regression use, not hardcoded, so it can't drift out of sync.
    st.markdown("**The most and least changed counties**")
    county_examples = {}
    example_cols = st.columns(len(HETEROGENEITY_CAUSES))
    for i, cause in enumerate(HETEROGENEITY_CAUSES):
        cd = load_county_disruption(cause)
        most = cd.loc[cd["disruption"].idxmax()]
        least = cd.loc[cd["disruption"].abs().idxmin()]
        county_examples[cause] = (most, least)
        with example_cols[i], st.container(border=True):
            st.write(f"**{display_cause(cause)}**")
            st.caption(
                f"Largest rise: **{most['county_name']}** "
                f"({most['crude_rate_pre']:.1f} → {most['crude_rate_post']:.1f} per 100,000)"
            )
            st.caption(f"Least change: **{least['county_name']}** ({least['disruption']:+.1f})")

    with st.expander("Why might these specific counties differ? Read this before assuming a cause"):
        st.write(
            "This project has no data on mask mandates, local ordinances, or age/race demographics "
            "anywhere in its pipeline; the regression uses only the five County Health Rankings measures. "
            "Assigning a specific policy or demographic story to any county would be invented, not "
            "measured, exactly what Methods → Language policy exists to rule out."
        )
        st.write(
            "A single county's average is also noisy: in a small county a handful of extra deaths can move "
            "it a lot, which is often a better explanation for an extreme value than any story. What can be "
            "checked is whether each example lines up with the same five measures:"
        )
        chr_df = load_chr_year(2024)
        for cause, (most, least) in county_examples.items():
            cd = load_county_disruption(cause)
            sample_means = chr_df[chr_df["county_fips"].isin(cd["county_fips"])][list(CONTEXT_VAR_LABELS)].mean()
            for label, row in [("largest rise", most), ("least change", least)]:
                crow = chr_df[chr_df["county_fips"] == row["county_fips"]]
                if not len(crow):
                    continue
                crow = crow.iloc[0]
                comparisons = [
                    f"{disp.lower()} {'above' if crow[var] > sample_means[var] else 'below'} the sample average"
                    for var, disp in CONTEXT_VAR_LABELS.items()
                    if pd.notna(crow.get(var)) and pd.notna(sample_means.get(var))
                ]
                st.caption(f"**{row['county_name']}** ({display_cause(cause)}, {label}): " + "; ".join(comparisons) + ".")
        st.write(
            "Some examples line up with the overall pattern and others don't. That's expected: an "
            "association across thousands of counties doesn't reliably predict any single one, the same "
            "ecological-fallacy caveat in Methods → Limitations & ethics."
        )

    bias = load_heterogeneity_selection_bias().set_index("cause")
    robustness = load_heterogeneity_rurality_robustness()
    with st.expander("The rurality result: caveats", icon=":material/warning:"):
        st.write(
            "Counties left out (too few deaths for a reliable rate) are much more rural than those included, "
            "so the most rural places are still under-represented, though far less than under the earlier "
            "year-by-year method:"
        )
        for cause in HETEROGENEITY_CAUSES:
            row = bias.loc[cause]
            r = robustness[robustness["cause"] == cause].set_index("half")
            upper, lower = r.loc["upper_half"], r.loc["lower_half"]
            full_sig = bool(het[(het["cause"] == cause) & (het["variable"] == "pct_rural")].iloc[0]["fdr_significant"])
            reading = rurality_split_reading(upper["slope"], upper["p_value"], lower["slope"], lower["p_value"],
                                             full_significant=full_sig)
            st.write(
                f"**{display_cause(cause)}**: excluded counties average {row['mean_excluded']*100:.0f}% rural vs. "
                f"{row['mean_included']*100:.0f}% included. Split at the median rurality: {reading}"
            )
        st.caption("Rural counties also tend to be older, and county rates aren't age-adjusted, so a rural link "
                   "can partly reflect aging rather than the pandemic.")

with limits_tab:
    st.write(
        "Mortality data alone cannot separate several very different mechanisms that would all produce "
        "the same statistical signature: direct viral harm, deferred or interrupted medical care, "
        "healthcare-system strain, and economic/isolation stress. A \"Persisted\" classification for heart "
        "disease could be any of these, in any combination, which is why every result here is described as "
        "\"associated with\" or \"consistent with,\" never \"caused by\" (see Methods → Language policy)."
    )

    st.caption(
        "All national-level results use 15 real CDC WONDER exports. County results use 10 pooled exports "
        "(five causes, 2015–2019 and 2020–2024), 2 for the exploratory Alzheimer's county run, plus 4 year-by-year exports kept for the diabetes and "
        "overdose comparison and 2 heart disease 2018–2019 exports used to check the two databases match "
        "county by county. Nothing in this project is synthetic. Full provenance: "
        "`docs/manual_data_acquisition.md`."
    )
