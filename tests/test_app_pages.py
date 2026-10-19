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
    n_diabetes = pd.read_parquet(models / "county_disruption_diabetes_mellitus.parquet")["county_fips"].nunique()
    n_overdose = pd.read_parquet(models / "county_disruption_drug_overdose.parquet")["county_fips"].nunique()
    years = pd.read_parquet(models / "national_mortality_series.parquet")["year"]
    n_years = int(years.max()) - int(years.min()) + 1
    assert f'>{n_diabetes:,}<span class="cmd-kpi-unit">counties analyzed<' in html
    assert f"Diabetes; {n_overdose:,} for drug overdose" in html
    assert f'>{n_years}<span class="cmd-kpi-unit">years of CDC data<' in html
    assert "How the pandemic disrupted non-COVID mortality" in html


def test_home_is_short():
    at = _app_on("home")
    # The long-form sections moved to Methods/Findings; Home has no section headings or expanders.
    assert [s.value for s in at.subheader] == []
    assert _expander_labels(at) == []
    assert [b.label for b in at.button] == ["Read the findings"]


def _page_text(at) -> str:
    parts = [e.proto.body for e in at.get("html")]
    for kind in ("markdown", "caption", "subheader", "title"):
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
    assert "5 of 6 causes departed" in html
    # Expected names written out by hand from the 2024 deviations table.
    assert set(still_above) == {"Diabetes mellitus", "Malignant neoplasms"}
    assert "only Diabetes and Cancer were still significantly above it" in html


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
        "Why might these specific counties differ? Read this before assuming a cause",
        "The rurality finding needs a real caveat: click to see why",
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
    html = " ".join(e.proto.body for e in at.get("html"))
    # heterogeneity_summary, diabetes: all five FDR-significant; uninsured/smoking/obesity
    # slopes positive, income and rurality negative.
    assert ("Diabetes disruption was larger where obesity, smoking and the uninsured rate were higher, "
            "and smaller where household income and rurality were higher.") in html
    assert "The rurality result has a selection-bias caveat" in html


def test_geographic_takeaway_leaves_out_associations_that_fail_fdr():
    at = _app_on("geographic_heterogeneity")
    at.button_group[0].set_value("Drug overdose").run()
    (takeaway,) = [e.proto.body for e in at.get("html") if 'class="cmd-takeaway"' in e.proto.body]
    # heterogeneity_summary, overdose: rurality p=0.069, not FDR-significant; the other four are.
    assert ("Drug overdose disruption was larger where smoking, the uninsured rate and obesity were higher, "
            "and smaller where household income was higher.") in takeaway
    assert "rurality" not in takeaway


def test_county_lookup_shows_pre_post_chart():
    at = _app_on("county_deep_dive")
    assert len(at.get("vega_lite_chart")) == 1



def test_data_quality_tabs():
    at = _app_on("data_quality")
    assert [t.label for t in at.tabs] == ["Negative control", "Multiple testing", "Vintage bridging", "Sensitivity"]
