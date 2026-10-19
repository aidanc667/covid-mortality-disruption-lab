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


def test_methods_overview_holds_content_moved_off_home():
    at = _app_on("methods")
    assert [t.label for t in at.tabs] == ["Overview", "Details"]
    overview = at.tabs[0]
    assert [s.value for s in overview.subheader] == ["Why this matters", "What we did", "The breaking point"]
    card_text = " ".join(m.value for m in overview.markdown)
    for card in ("Real data", "Locked before looking", "Tested, not assumed", "Mapped and explained"):
        assert card in card_text
    assert len(overview.get("vega_lite_chart")) == 1  # the COVID-19 reference chart
    details_expanders = _expander_labels(at.tabs[1])
    assert "Research question" in details_expanders
    assert "Ethics and project checks" in details_expanders


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
    assert f"{len(disrupted)} of 6 causes departed" in html
    # Expected names written out by hand from the 2024 deviations table.
    assert set(still_above) == {"Diabetes mellitus", "Malignant neoplasms"}
    assert "only Diabetes and Cancer were still significantly above it" in html


def test_findings_copy_no_longer_contradicts_the_2024_data():
    text = _page_text(_app_on("findings"))
    for phrase in ("still-unresolved", "none have reversed", "None of the disrupted causes have resolved"):
        assert phrase not in text
    # The overdose dip below trend in 2024 is stated, not hidden behind "Persisted".
    assert "Drug overdose -4.3%" in text
