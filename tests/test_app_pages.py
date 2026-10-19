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
    overview_headings = [s.value for s in at.tabs[0].subheader]
    assert overview_headings == ["Why this matters", "What we did", "The breaking point"]
    details_expanders = _expander_labels(at.tabs[1])
    assert "Research question" in details_expanders
    assert "Ethics and project checks" in details_expanders


def test_home_shows_title_and_county_count_from_the_data():
    at = _app_on("home")
    assert at.title[0].value == "COVID Mortality Disruption Lab"
    html = " ".join(e.proto.body for e in at.get("html"))
    # Expected value read straight from the parquet, independently of home_scope_metrics.
    n = pd.read_parquet(ROOT / "outputs/models/county_disruption_diabetes_mellitus.parquet")["county_fips"].nunique()
    assert f"{n:,}" in html
    assert "counties analyzed" in html
    assert "How the pandemic disrupted non-COVID mortality" in html


def test_home_is_short():
    at = _app_on("home")
    # The long-form sections moved to Methods/Findings; Home has no section headings or expanders.
    assert [s.value for s in at.subheader] == []
    assert _expander_labels(at) == []
    assert [b.label for b in at.button] == ["Read the findings"]
