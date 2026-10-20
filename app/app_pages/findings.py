import streamlit as st

from app.components.charts import then_vs_now_chart
from app.components.county_text import (
    county_pattern_sentences,
    rurality_change,
    rurality_change_is_notable,
)
from app.components.data_loading import (
    CAUSE_COLORS,
    CONTEXT_VAR_LABELS,
    EXPLORATORY_COUNTY_CAUSES,
    HETEROGENEITY_CAUSES,
    TEST_CAUSES,
    YEARLY_COMPARISON_CAUSES,
    data_available,
    display_cause,
    load_county_disruption,
    load_county_disruption_yearly,
    load_disruption_deviations,
    load_disruption_summary,
    load_heterogeneity_selection_bias,
    load_heterogeneity_summary,
    load_heterogeneity_summary_yearly,
    load_latest_year_window_check,
    load_national_series,
    load_negative_control,
    load_sensitivity_check,
    scale_context_slope_for_display,
    sensitivity_check_available,
    synthetic_banner,
)
from app.components.findings_text import findings_takeaway, trend_vs_reference_note
from app.components.ui import takeaway_html
from src.utils.config import OUTPUTS_REPORTS

_WORDS = {1: "one", 2: "two", 3: "three", 4: "four", 5: "five", 6: "six"}


def _names_with(items: list[str]) -> str:
    return " and ".join(items) if len(items) <= 2 else ", ".join(items[:-1]) + ", and " + items[-1]


def _in_sentence(name: str) -> str:
    return name if name.startswith("Alzheimer") else name[0].lower() + name[1:]


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

CAUSE_LABELS = {c: display_cause(c) for c in TEST_CAUSES}


window_check = load_latest_year_window_check()
st.html(takeaway_html(findings_takeaway(
    summary, deviations, CAUSE_LABELS,
    baseline_sensitive=window_check.loc[window_check["baseline_sensitive"], "cause"].tolist(),
)))

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
        f"dot outside its band is significant (solid); inside it, the gap is within normal noise (faded)."
    )
    st.caption(
        "**What \"disrupted\" means here:** statistically distinguishable from that cause of death's "
        "normal year-to-year variation before 2020. Not looking at the distance from 0% line, but instead "
        "looking at if it falls outside its projected range (gray band)."
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

trend_note = trend_vs_reference_note(load_national_series(), deviations, CAUSE_LABELS)
if trend_note:
    st.caption(trend_note)

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
        lower = [_in_sentence(display_cause(c)) for c in faded]
        definition += (
            f" By {latest_year}, {_names_with(lower)} {'was' if len(faded) == 1 else 'were'} back within "
            f"{'its' if len(faded) == 1 else 'their'} normal range"
        )
        if below_now:
            gaps = ", ".join(
                f"{_in_sentence(display_cause(c))} " + f"{latest.loc[c, 'deviation'] / latest.loc[c, 'expected'] * 100:+.1f}%".replace("-", "−")
                for c in below_now
            )
            definition += f" ({gaps}, slightly below trend but not significant)"
        definition += "."
    st.caption(definition)
    display = summary.sort_values("p_value").copy()
    if sensitivity_check_available():
        trend_shape = load_sensitivity_check()
        trend_shape = trend_shape[trend_shape["check"].isin([
            "baseline_trend_shape (linear vs quadratic)", "trend_scale (linear vs log-linear)",
        ])].groupby("cause", as_index=False)["agrees"].all()
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
                help="Unchecked means this cause's result changes (currently: loses significance) if the pre-pandemic trend is fit "
                     "as a curve or as a steady percentage change instead of a straight line. See Data quality.",
            ),
        },
        hide_index=True,
        width="stretch",
    )
    st.caption(
        "\"Deviation\" is the effect size, as a percent of the expected rate. Significant and large are "
        "different things: cancer is significant at under 2%. \"Robust to trend shape\" is unchecked for "
        "stroke (not significant with a curved trend) and cancer (not significant with a steady-percentage "
        "trend)."
    )

with surprises_tab:
    st.write(
        "Each cause's expected result was written down before any 2020–2024 data was analyzed "
        "(Methods → Hypotheses). Two results went the other way."
    )

    cancer = summary[summary["cause"] == "Malignant neoplasms"].iloc[0]
    alz = summary[summary["cause"] == "Alzheimer's disease"].iloc[0]
    alz_2020 = deviations[(deviations["cause"] == "Alzheimer's disease") & (deviations["year"] == 2020)].iloc[0]
    alz_2020 = alz_2020["deviation"] / alz_2020["expected"] * 100

    with st.container(border=True):
        st.write("**Cancer was expected to show nothing, but it did.**")
        st.write(
            "The pre-registered prior was an explicit null, \"low\" confidence by design: delayed "
            "cancer screening was expected to take years longer than this 2024 data window to show up "
            f"as excess mortality. Instead, cancer shows an FDR-significant "
            f"**{cancer['persistence_class'].lower()}** disruption (p = {cancer['p_value']:.3g}), modest "
            f"in size ({cancer['acute_pct_deviation']:+.1f}% in 2020–21, "
            f"{cancer['latest_pct_deviation']:+.1f}% by 2024) next to the larger disruptions below. "
            "The result is fragile, though: with a trend that falls by a steady percentage each "
            "year instead of a straight line, the 2020–21 gap is no longer significant, though cancer "
            "is still above trend in 2024 either way."
        )

    with st.container(border=True):
        st.write("**Alzheimer's was expected to show a large effect, and the annual test didn't find one.**")
        st.write(
            "The pre-registered prior was \"high confidence\" of a large effect, on the theory that "
            "pandemic-era isolation and care-facility disruption would show up clearly in dementia "
            f"mortality. This project's annual test didn't find one (p = {alz['p_value']:.2g}). That "
            f"isn't the same as no effect: in 2020 alone the rate ran {alz_2020:+.0f}% above trend, and "
            "studies that also count dementia as a contributing cause found large excess deaths that "
            "year. Averaged with a below-trend 2021, the 2020–21 gap isn't significant. Pooling all five "
            f"post-2020 years finds a significant later decline (p = {alz['full_period_p_value']:.2g}); "
            "see Causes of death for the numbers."
        )

with robustness_tab:
    st.markdown(f"**Does the {latest_year} status depend on the baseline window?**")
    wc = window_check.copy()
    wc["cause"] = wc["cause"].map(display_cause)
    st.dataframe(
        wc[["cause", "primary_window", "primary_pct", "primary_status", "alt_window", "alt_pct", "alt_status", "baseline_sensitive"]],
        column_config={
            "cause": "Cause", "primary_window": "Primary baseline",
            "primary_pct": st.column_config.NumberColumn(f"{latest_year} gap", format="%+.1f%%"),
            "primary_status": "Status", "alt_window": "Other window",
            "alt_pct": st.column_config.NumberColumn(f"{latest_year} gap (other)", format="%+.1f%%"),
            "alt_status": "Status (other)", "baseline_sensitive": st.column_config.CheckboxColumn("Depends on window"),
        },
        hide_index=True, width="stretch",
    )
    st.caption(
        "The 2020–21 test holds under either window for every cause. The latest-year status is more "
        "sensitive. For heart disease and stroke the other window is the 1999–2019 line already shown to "
        "misfit them; for diabetes and drug overdose it's a 2010–2019 line that tracks their flattened or "
        "accelerating pre-2020 rates more closely. Primary results stay on the pre-registered windows "
        "(research_protocol.md, 2026-10-19 reversal addendum)."
    )
    st.markdown("**Other checks**")
    lines = [(
        f"**Negative control:** {'passed' if neg_control['passed'] else 'FAILED'}. Congenital malformations, "
        f"a cause with no direct COVID link, shows no disruption (p = {neg_control['p_value_counts']:.2f} on "
        "death counts). The first choice, accidental drowning, was dropped because pandemic pool and beach "
        "closures really did change drowning deaths."
    )]
    if sensitivity_check_available():
        sens = load_sensitivity_check()
        test_sens = sens[sens["cause"].isin(TEST_CAUSES)]
        for check_name, label in [
            ("baseline_window (1999 vs 2010)", "Other baseline window"),
            ("significance_threshold (0.05 vs 0.01)", "Stricter significance level (α = 0.01)"),
            ("baseline_trend_shape (linear vs quadratic)", "Curved instead of straight trend"),
            ("trend_scale (linear vs log-linear)", "Steady-percentage instead of straight trend"),
        ]:
            rows = test_sens[test_sens["check"] == check_name]
            off_rows = rows[~rows["agrees"]]
            if off_rows.empty:
                lines.append(f"**{label}:** all six causes give the same result.")
                continue
            parts = []
            for _, r in off_rows.iterrows():
                name = display_cause(r["cause"])
                if r["alt_p_value"] >= (0.01 if check_name.startswith("significance") else 0.05):
                    parts.append(f"{name}'s 2020–21 result is no longer significant (p = {r['alt_p_value']:.2g})")
                else:
                    # Still significant in 2020-21: only the later years' classification changed.
                    parts.append(f"{name}'s 2020–21 result stays significant (p = {r['primary_p_value']:.2g}), but "
                                 f"its later years no longer clear the bar, so it is classed "
                                 f"{r['alt_classification']} rather than {r['primary_classification']}")
            lines.append(f"**{label}:** " + "; ".join(parts) + ". The rest hold.")
        hac_disagree = summary[(summary["p_value"] < 0.05) != (summary["hac_p_value"] < 0.05)]["cause"].map(display_cause).tolist()
        lines.append(
            "**Autocorrelation-robust p-values:** "
            + (f"all {_WORDS.get(n_disrupted, n_disrupted)} significant causes stay significant." if not hac_disagree
               else f"{_names_with(hac_disagree)} {'changes' if len(hac_disagree) == 1 else 'change'}.")
        )
    for line in lines:
        st.markdown(f"- {line}")
    st.caption("Data quality has the full tables for each check.")

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

    st.markdown("**Largest rise in each cause**")
    example_cols = st.columns(len(HETEROGENEITY_CAUSES))
    for i, cause in enumerate(HETEROGENEITY_CAUSES):
        cd = load_county_disruption(cause)
        most = cd.loc[cd["disruption"].idxmax()]
        with example_cols[i], st.container(border=True):
            st.write(f"**{display_cause(cause)}**")
            st.caption(
                f"**{most['county_name']}** "
                f"({most['crude_rate_pre']:.1f} → {most['crude_rate_post']:.1f} per 100,000)"
            )
    st.caption(
        "Single counties are noisy: in a small county a handful of extra deaths can move the rate a lot, "
        "so an extreme county says little on its own."
    )

    bias = load_heterogeneity_selection_bias().set_index("cause").loc[HETEROGENEITY_CAUSES]
    with st.expander("The rurality result: caveats", icon=":material/warning:"):
        st.write(
            f"Counties left out for having too few deaths are much more rural "
            f"({bias['mean_excluded'].min()*100:.0f}–{bias['mean_excluded'].max()*100:.0f}% rural) than those "
            f"included ({bias['mean_included'].min()*100:.0f}–{bias['mean_included'].max()*100:.0f}%), so the "
            "most rural places are still under-represented. Rural counties also tend to be older, and county "
            "rates aren't age-adjusted, so a rural link can partly reflect aging. Geographic patterns → What "
            "predicts it shows how each cause's result splits between more and less rural counties."
        )

with limits_tab:
    st.write(
        "Mortality data alone cannot separate several very different mechanisms that would all produce "
        "the same statistical signature: direct viral harm, deferred or interrupted medical care, "
        "healthcare-system strain, and economic/isolation stress. A \"Persisted\" classification for heart "
        "disease could be any of these, in any combination, which is why every result here is described as "
        "\"associated with\" or \"consistent with,\" never \"caused by\" (see Methods → Language policy)."
    )

    st.caption(
        "Every result uses real CDC WONDER exports: 15 national and 18 county. Nothing is synthetic. "
        "Full list: `docs/manual_data_acquisition.md`."
    )
