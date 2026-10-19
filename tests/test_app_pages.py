"""Run the real multipage app headlessly with Streamlit's AppTest and check
each page renders without an exception. Needs the precomputed parquet
outputs; skips with a reason when they're absent (e.g. a fresh clone)."""
from pathlib import Path

import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parent.parent
APP = str(ROOT / "app" / "streamlit_app.py")
PAGES = ["home", "findings", "causes", "geographic_heterogeneity", "county_deep_dive", "data_quality", "methods"]

pytestmark = pytest.mark.skipif(
    not (ROOT / "outputs" / "models" / "disruption_summary.parquet").exists(),
    reason="precomputed outputs/models/ not present; run scripts/run_covid_disruption_pipeline.py first",
)


def _expander_labels(block) -> list[str]:
    """AppTest reports an expander given an `icon=` as a Status element, not
    an Expander, so collect both to see every collapsible section."""
    return [e.label for e in block.expander] + [s.label for s in block.status]


def _app_on(page: str) -> AppTest:
    at = AppTest.from_file(APP, default_timeout=60).run()
    if page != "home":
        at.switch_page(f"app_pages/{page}.py").run()
    return at


@pytest.mark.parametrize("page", PAGES)
def test_page_runs_without_exception(page):
    at = _app_on(page)
    assert not at.exception, [e.value for e in at.exception]


def test_renamed_pages_use_new_titles():
    assert _app_on("geographic_heterogeneity").title[0].value == "Geographic patterns"
    assert _app_on("county_deep_dive").title[0].value == "County lookup"


def test_methods_tabs_hold_all_content_including_what_moved_off_home():
    at = _app_on("methods")
    assert [t.label for t in at.tabs] == [
        "Overview", "Hypotheses", "Data", "Statistics", "Counties", "Language policy", "Limitations & ethics",
    ]
    overview = at.tabs[0]
    assert [s.value for s in overview.subheader] == ["Why this matters", "What we did", "The breaking point"]
    card_text = " ".join(m.value for m in overview.markdown)
    for card in ("Real data", "Locked before looking", "Tested, not assumed", "Mapped and explained"):
        assert card in card_text
    assert len(overview.get("vega_lite_chart")) == 1  # the COVID-19 reference chart
    assert [s.value for s in at.tabs[1].subheader] == ["Research question", "Pre-registered hypotheses"]
    assert [s.value for s in at.tabs[6].subheader] == ["Known limitations", "Ethics and project checks"]
    # Nothing left collapsed: every section is a tab now.
    assert _expander_labels(at) == []


def test_home_shows_title_and_county_count_from_the_data():
    at = _app_on("home")
    assert at.title[0].value == "COVID Mortality Disruption Lab"
    html = " ".join(e.proto.body for e in at.get("html"))
    # Expected value read straight from the parquet, independently of home_scope_metrics.
    models = ROOT / "outputs" / "models"
    # Widest coverage is heart disease, narrowest drug overdose (pooled county files).
    n_heart = pd.read_parquet(models / "county_disruption_diseases_of_heart.parquet")["county_fips"].nunique()
    n_overdose = pd.read_parquet(models / "county_disruption_drug_overdose.parquet")["county_fips"].nunique()
    years = pd.read_parquet(models / "national_mortality_series.parquet")["year"]
    n_years = int(years.max()) - int(years.min()) + 1
    assert f'>{n_heart:,}<span class="cmd-kpi-unit">counties<' in html
    assert f"Analyzed across 5 causes ({n_overdose:,} for drug overdose)" in html
    assert f'>{n_years}<span class="cmd-kpi-unit">years of CDC data<' in html
    assert "How the pandemic impacted non-COVID mortality" in html
    assert ("<b>Research Question:</b> Did COVID-19 disrupt the trend for six other leading causes of death, "
            "has it recovered, and where did it hit hardest?") in html


def test_home_is_short():
    at = _app_on("home")
    # The long-form sections moved to Methods/Findings; Home has no section headings or expanders.
    assert [s.value for s in at.subheader] == []
    assert _expander_labels(at) == []
    assert [b.label for b in at.button] == ["Read the findings"]


def _page_text(at) -> str:
    parts = [e.proto.body for e in at.get("html")]
    for kind in ("markdown", "caption", "subheader", "title", "info", "warning", "success", "error"):
        parts += [str(e.value) for e in getattr(at, kind)]
    return " ".join(parts)


def test_findings_tabs_and_data_driven_takeaway():
    at = _app_on("findings")
    assert [t.label for t in at.tabs] == ["Results", "Surprises", "Robustness", "Counties", "Limits"]
    models = ROOT / "outputs" / "models"
    dev = pd.read_parquet(models / "disruption_deviations.parquet")
    summary = pd.read_parquet(models / "disruption_summary.parquet")
    latest = dev[dev["year"] == dev["year"].max()].set_index("cause")
    disrupted = summary.loc[summary["persistence_class"] != "No significant disruption", "cause"]
    still_above = [c for c in disrupted if latest.loc[c, "significant"] and latest.loc[c, "deviation"] > 0]
    html = " ".join(e.proto.body for e in at.get("html"))
    # 5 = every test cause except Alzheimer's (the only "No significant disruption"), pinned by hand.
    assert len(disrupted) == 5
    # Expected names and gaps written out by hand from the 2024 deviations table:
    # diabetes +15.0% and cancer +4.6% above, Alzheimer's -19.1% below; heart disease,
    # stroke, and overdose not significant.
    assert set(still_above) == {"Diabetes mellitus", "Malignant neoplasms"}
    assert (
        "Five of six causes rose significantly above their pre-pandemic trend in 2020–21. "
        "By 2024, three were significantly off trend: diabetes (+15%) and cancer (+5%) above it, "
        "and Alzheimer&#x27;s disease (−19%) below it. "
        "Heart disease, stroke, and drug overdose were back within their normal range."
    ) in html


@pytest.mark.parametrize("page", PAGES)
def test_no_page_claims_effects_persisted_through_2024(page):
    # In 2024 only diabetes and cancer are significantly above trend, so copy
    # implying every disrupted cause was still off trend in 2024 is false.
    text = _page_text(_app_on(page))
    for phrase in ("still-unresolved", "none have reversed", "None of the disrupted causes have resolved",
                   "still significant, same direction, through", "none of them has fully returned"):
        assert phrase not in text, phrase


def test_findings_overdose_dip_is_stated():
    text = _page_text(_app_on("findings"))
    # The overdose dip below trend in 2024 is stated, not hidden behind "Persisted".
    assert "Drug overdose -4.3%" in text


def test_findings_keeps_every_caveat_section():
    labels = _expander_labels(_app_on("findings"))
    for caveat in (
        "This wasn't the first choice: a real methodological correction",
        "See the full robustness breakdown",
        "Full regression results, by cause",
        "Why might these specific counties differ? Read this before assuming a cause",
        "The rurality result: caveats",
    ):
        assert caveat in labels


def test_causes_page_tabs_and_takeaway():
    at = _app_on("causes")
    assert [t.label for t in at.tabs] == ["Trend", "Robustness", "What could explain it", "Sources"]
    html = " ".join(e.proto.body for e in at.get("html"))
    # From disruption_summary: overdose +40.9% and diabetes +26.9% are the two largest; Alzheimer's is not disrupted.
    assert "drug overdose (+41%) and diabetes (+27%)" in html
    assert "Alzheimer&#x27;s disease showed no significant 2020–21 disruption" in html


def test_geographic_patterns_tabs_and_takeaway():
    at = _app_on("geographic_heterogeneity")
    assert [t.label for t in at.tabs] == ["Map", "What predicts it", "All counties"]
    (takeaway,) = [e.proto.body for e in at.get("html") if 'class="cmd-takeaway"' in e.proto.body]
    # heterogeneity_summary, heart disease (the default cause): all five FDR-significant;
    # smoking, obesity, uninsured, rurality positive, income negative; listed by p-value.
    assert ("Heart disease disruption was larger where smoking, obesity, the uninsured rate and rurality "
            "were higher, and smaller where household income was higher.") in takeaway
    assert "The rurality result has caveats" in takeaway


def test_geographic_takeaway_leaves_out_associations_that_fail_fdr():
    at = _app_on("geographic_heterogeneity")
    at.button_group[0].set_value("Diabetes mellitus").run()
    (takeaway,) = [e.proto.body for e in at.get("html") if 'class="cmd-takeaway"' in e.proto.body]
    # heterogeneity_summary, diabetes (pooled): rurality p=0.22, not FDR-significant; the other four are.
    assert ("Diabetes disruption was larger where smoking, obesity and the uninsured rate were higher, "
            "and smaller where household income was higher.") in takeaway
    assert "rurality" not in takeaway


def test_geographic_shows_year_by_year_comparison_for_diabetes_only():
    at = _app_on("geographic_heterogeneity")
    assert not any("year-by-year" in label for label in _expander_labels(at))  # heart disease: no earlier run
    at.button_group[0].set_value("Diabetes mellitus").run()
    assert "Compare: the earlier year-by-year method (926 counties)" in _expander_labels(at)


def test_county_lookup_shows_pre_post_chart():
    at = _app_on("county_deep_dive")
    assert len(at.get("vega_lite_chart")) == 1



def test_data_quality_tabs():
    at = _app_on("data_quality")
    assert [t.label for t in at.tabs] == ["Negative control", "Multiple testing", "Vintage bridging", "Sensitivity"]


def test_findings_states_that_the_rurality_result_changed():
    text = _page_text(_app_on("findings"))
    # Year-by-year: rural slope negative for diabetes (FDR) and overdose (p=0.069).
    # Pooled: diabetes not significant, overdose significantly positive.
    assert "This changed the rurality result." in text
    assert "that pattern disappears for diabetes and reverses for drug overdose" in text
    # Export counts in the Limits caption: 10 pooled + 4 year-by-year + 2 bridging.
    assert "County results use 10 pooled exports" in text
    assert "For all five causes, higher smoking rates went with larger disruption." in text


def test_geographic_alzheimers_is_labeled_exploratory():
    at = _app_on("geographic_heterogeneity")
    at.button_group[0].set_value("Alzheimer's disease").run()
    assert not at.exception
    assert any("Exploratory." in i.value for i in at.info)
    (takeaway,) = [e.proto.body for e in at.get("html") if 'class="cmd-takeaway"' in e.proto.body]
    # heterogeneity_summary, Alzheimer's (exploratory): no measure survives FDR.
    assert "No context variable survives FDR correction for Alzheimer" in takeaway


def test_findings_mentions_alzheimers_county_run_as_exploratory():
    text = _page_text(_app_on("findings"))
    assert "Exploratory:" in text and "None of the five measures survives FDR correction for it." in text
    # Still only five causes in the cross-cause summary.
    assert "For all five causes, higher smoking rates went with larger disruption." in text


def test_findings_defines_disrupted_as_statistically_distinguishable():
    text = _page_text(_app_on("findings"))
    assert "statistically distinguishable from that cause's normal year-to-year variation" in text
    assert "doesn't mean no effect" in text
