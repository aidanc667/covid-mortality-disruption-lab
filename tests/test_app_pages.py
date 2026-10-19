"""Run the real multipage app headlessly with Streamlit's AppTest and check
each page renders without an exception. Needs the precomputed parquet
outputs; skips with a reason when they're absent (e.g. a fresh clone)."""
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parent.parent
APP = str(ROOT / "app" / "streamlit_app.py")
PAGES = ["home", "findings", "causes", "geographic_heterogeneity", "county_deep_dive", "data_quality", "methods"]

pytestmark = pytest.mark.skipif(
    not (ROOT / "outputs" / "models" / "disruption_summary.parquet").exists(),
    reason="precomputed outputs/models/ not present; run scripts/run_covid_disruption_pipeline.py first",
)


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
