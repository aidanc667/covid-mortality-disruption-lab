"""The PDF report's text helpers and overall structure. Needs reportlab
(requirements-report.txt) and, for the structure test, the precomputed
outputs; skips cleanly without them."""
from pathlib import Path

import pandas as pd
import pytest

pytest.importorskip("reportlab")
from reportlab.graphics.shapes import Drawing
from reportlab.platypus import KeepTogether, PageBreak, Paragraph, Table

from scripts import generate_report as gr

ROOT = Path(__file__).resolve().parent.parent


def test_number_ranges_get_en_dashes_but_codes_and_exponents_do_not():
    assert gr._dashes("2020-21 and 1999-2019, 83-94% rural") == "2020–21 and 1999–2019, 83–94% rural"
    assert gr._dashes("ICD-10 codes X40-X44, COVID-19, 4.5e-4") == "ICD-10 codes X40-X44, COVID-19, 4.5e-4"


def test_p_values_read_as_prose_and_as_table_cells():
    assert gr._p(0.18) == "= 0.18"
    assert gr._p(0.0040293) == "= 0.004"
    assert gr._p(0.00045) == "< 0.001"
    assert gr._p_cell(0.82) == "0.82"
    cell = gr._p_cell(2.07e-7)
    assert isinstance(cell, Paragraph) and "2.1×10<super>−7</super>" in cell.text


def _het(rows):
    return pd.DataFrame(rows, columns=["cause", "variable", "slope", "fdr_significant"])


def test_county_summary_groups_measures_by_direction_and_count():
    causes = gr.COUNTY_CAUSES
    rows = []
    for i, c in enumerate(causes):
        rows += [
            (c, "pct_smokers", 1.0, True),                 # larger for all five
            (c, "pct_uninsured_chr", 1.0, True),           # larger for all five
            (c, "median_income_chr", -1.0, i < 4),         # smaller for four
            (c, "pct_obese", 1.0, i < 3),                  # larger for three
            (c, "pct_rural", 1.0 if i < 3 else -1.0, i < 4),  # larger for three, smaller for one
        ]
    assert gr._county_summary(_het(rows)) == (
        "Higher smoking and uninsured rates went with larger increases for all five causes; "
        "higher household income went with smaller increases for four of the five causes; "
        "higher obesity rates went with larger increases for three of the five causes. "
        "The link with rurality was mixed: larger for three causes, smaller for one"
    )


@pytest.mark.skipif(not (ROOT / "outputs" / "models" / "disruption_summary.parquet").exists(),
                    reason="precomputed outputs/models/ not present")
def test_report_is_a_continuous_paper_with_all_figures_and_tables():
    story = gr.build(gr.load_data())

    def flat(items):
        for item in items:
            if isinstance(item, KeepTogether):
                yield from flat(item._content)
            else:
                yield item

    flowables = list(flat(story))
    # No forced page breaks: those left pages two-thirds empty in the earlier layout.
    assert not any(isinstance(f, PageBreak) for f in flowables)
    headings = [f.text for f in flowables if isinstance(f, Paragraph) and f.style.name == "H1"]
    assert headings == ["1. Introduction", "2. Data and methods", "3. Results", "4. Discussion",
                        "5. Limitations", "6. Data availability", "References"]
    assert sum(isinstance(f, Drawing) for f in flowables) == 4
    assert sum(isinstance(f, Table) for f in flowables) == 5
    captions = " ".join(f.text for f in flowables if isinstance(f, Paragraph) and f.style.name in ("Caption", "TableCaption"))
    for label in ["Figure 1.", "Figure 2.", "Figure 3.", "Figure 4.",
                  "Table 1.", "Table 2.", "Table 3.", "Table 4.", "Table 5."]:
        assert label in captions
