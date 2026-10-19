# UI Redesign, Step 1: Design System + Home Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give the Streamlit app the DataForensics look (slate palette, Source Serif 4 / IBM Plex) and replace the long Home page with a one-screen, chart-led page, without losing any content.

**Architecture:** Theme colors and fonts go in `.streamlit/config.toml` (supported settings, no internal-selector CSS). Three new small modules: `app/components/home_metrics.py` (pure numbers for the Home strip), `app/components/charts.py` (pure helpers + the Altair "gap from trend" chart), and `app/components/ui.py` (pure, escaped HTML snippets + one scoped stylesheet). Content leaving Home moves into a new **Overview** tab on Methods *before* Home is rewritten, so nothing is ever missing.

**Tech Stack:** Python 3.12, Streamlit 1.62.0, Altair 6.2.2, pandas 3.0.5, pytest (with `streamlit.testing.v1.AppTest`), ruff 0.16.5.

**Spec:** `docs/superpowers/specs/2026-10-18-ui-redesign-design.md` (rollout step 1 of 5).

## Global Constraints

- Colors (exact): bg `#F3F5F7`, surface `#FFFFFF`, border `#D5DCE3`, text `#15212B`, muted `#5A6875`, accent `#2C5D86`, sidebar-active `#2A3947`.
- Fonts: Source Serif 4 (headings), IBM Plex Sans (body), IBM Plex Mono (numbers).
- Cause colors (exact): Drug overdose `#2C5D86`, Diabetes `#B3261E`, Stroke `#7A5C99`, Cancer `#2F6F4E`, Heart disease `#C26A2E`, Alzheimer's `#8A6D3B`, negative control `#8795A3`.
- Home title is exactly **COVID Mortality Disruption Lab**; subtitle *How the pandemic disrupted non-COVID mortality*; question *Did COVID-19 bend the trend for six other leading causes of death, has it recovered, and where did it hit hardest?*
- Nav renames: "Geographic heterogeneity" → **Geographic patterns**, "County deep dive" → **County lookup**. Files under `app_pages/` keep their names.
- Every number on Home is computed from `outputs/models/*.parquet`, except "Pre-registered" (a protocol fact).
- Every HTML helper escapes interpolated text; colors are validated as `#RRGGBB`.
- No change to `src/`, `scripts/`, or any parquet output.
- Run everything with the project venv from the repo root: `.venv/bin/python -m pytest …`, `.venv/bin/ruff …`.
- Baseline before this plan: `106 passed`. `ruff check .` already reports 67 pre-existing errors; this plan must add **zero new** ruff errors (new files must be clean; touched files must not gain errors).

### Deliberate deviations from the spec (decided while planning)

- **Sidebar brand:** Streamlit's `st.navigation` always renders nav first and `st.logo` only takes images, so the app name goes in the sidebar *footer* (with "By Aidan Chi" and the GitHub link) rather than above the nav.
- **`takeaway()` helper:** not built here; no step-1 page uses it. It's built in step 2 (Findings), its first consumer.
- **`path_row()` helper:** inlined in `home.py` (its only user) as `st.page_link`s.
- **Test file name:** spec said `tests/test_ui_metrics.py`; this plan uses `tests/test_home_metrics.py`, `tests/test_charts.py`, `tests/test_ui.py`, `tests/test_app_pages.py` (one file per module).
- **Ethics + project-check badges:** go into Methods → Details (a new expander) in this step; step 5 moves them to the "Limitations & ethics" tab.
- **Findings page:** the Disrupted / FDR / Reversed metrics that leave Home are not re-added until step 2; Findings already states the disrupted and FDR counts in its headline and table.

## File structure

| File | Status | Responsibility |
|---|---|---|
| `app/components/home_metrics.py` | create | `ScopeMetrics`, `home_scope_metrics()`: year range and county counts (pure) |
| `app/components/charts.py` | create | `deviation_pct()`, `tint()`, `spread_labels()`, `gap_from_trend_chart()` |
| `app/components/ui.py` | create | `BASE_CSS`, `inject_base_css()`, `eyebrow_html()`, `hero_text_html()`, `cause_chips_html()`, `metric_strip_html()` |
| `.streamlit/config.toml` | modify | theme tokens, fonts, cause palette, dark sidebar |
| `app/components/data_loading.py` | modify | new `CAUSE_COLORS` values; delete now-unused `CAUSE_HOME_LABELS` |
| `app/streamlit_app.py` | modify | nav renames, inject CSS, sidebar footer |
| `app/app_pages/geographic_heterogeneity.py`, `app/app_pages/county_deep_dive.py` | modify | page titles / cross-references use new names |
| `app/app_pages/methods.py` | modify | `Overview` / `Details` tabs; Overview receives Home's long-form content |
| `app/app_pages/home.py` | rewrite | one-screen Home |
| `tests/test_home_metrics.py`, `tests/test_charts.py`, `tests/test_ui.py`, `tests/test_app_pages.py` | create | tests |

---

### Task 1: Home scope metrics (pure)

**Files:**
- Create: `app/components/home_metrics.py`
- Test: `tests/test_home_metrics.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `ScopeMetrics(first_year: int, last_year: int, n_years: int, county_counts: dict[str, int])` and `home_scope_metrics(national: pd.DataFrame, county_frames: dict[str, pd.DataFrame]) -> ScopeMetrics`. `national` needs a `year` column; each county frame needs `county_fips`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_home_metrics.py
import pandas as pd
import pytest

from app.components.home_metrics import ScopeMetrics, home_scope_metrics


def _national(years):
    return pd.DataFrame({"cause": ["Diabetes mellitus"] * len(years), "year": years})


def test_year_range_is_inclusive():
    # 1999..2024 inclusive is 26 calendar years.
    m = home_scope_metrics(_national(list(range(1999, 2025))), {})
    assert m == ScopeMetrics(first_year=1999, last_year=2024, n_years=26, county_counts={})


def test_single_year_series_counts_as_one_year():
    m = home_scope_metrics(_national([2020]), {})
    assert (m.first_year, m.last_year, m.n_years) == (2020, 2020, 1)


def test_county_counts_are_distinct_fips_per_cause():
    frames = {
        "Diabetes mellitus": pd.DataFrame({"county_fips": ["01001", "01003", "01003"]}),
        "Drug overdose": pd.DataFrame({"county_fips": pd.Series([], dtype="str")}),
    }
    m = home_scope_metrics(_national([2019, 2020]), frames)
    assert m.county_counts == {"Diabetes mellitus": 2, "Drug overdose": 0}


def test_empty_national_series_is_an_error():
    with pytest.raises(ValueError, match="empty"):
        home_scope_metrics(_national([]), {})
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_home_metrics.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.components.home_metrics'`

- [ ] **Step 3: Write the implementation**

```python
# app/components/home_metrics.py
"""Numbers for the Home page's scope strip, derived from the pipeline
outputs rather than typed in, so they can't drift out of sync with the data."""
from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class ScopeMetrics:
    first_year: int
    last_year: int
    n_years: int
    county_counts: dict[str, int]


def home_scope_metrics(national: pd.DataFrame, county_frames: dict[str, pd.DataFrame]) -> ScopeMetrics:
    if national.empty:
        raise ValueError("national mortality series is empty; cannot compute the year range")
    first, last = int(national["year"].min()), int(national["year"].max())
    counts = {cause: int(df["county_fips"].nunique()) for cause, df in county_frames.items()}
    return ScopeMetrics(first_year=first, last_year=last, n_years=last - first + 1, county_counts=counts)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_home_metrics.py -v`
Expected: `4 passed`

- [ ] **Step 5: Lint and commit**

Run: `.venv/bin/ruff check app/components/home_metrics.py tests/test_home_metrics.py`
Expected: `All checks passed!`

```bash
git add app/components/home_metrics.py tests/test_home_metrics.py
git commit -m "Add home_scope_metrics for the Home page scope strip"
```

---

### Task 2: Chart helpers + gap-from-trend chart

**Files:**
- Create: `app/components/charts.py`
- Test: `tests/test_charts.py`

**Interfaces:**
- Consumes: nothing.
- Produces:
  - `deviation_pct(deviations: pd.DataFrame) -> pd.DataFrame` (adds `pct`; needs `deviation`, `expected`)
  - `tint(hex_color: str, amount: float) -> str` (returns uppercase `#RRGGBB`)
  - `spread_labels(values: list[float], min_gap: float) -> list[float]`
  - `gap_from_trend_chart(dev: pd.DataFrame, colors: dict[str, str], labels: dict[str, str], highlight: set[str], height: int = 300) -> alt.LayerChart` (`dev` needs `cause`, `year`, `pct`; `labels` maps cause → display name and fixes which causes are drawn and in what order)

- [ ] **Step 1: Write the failing tests**

Expected values are worked by hand, not by calling the code under test:
- `tint("#B3261E", 0.6)`: R 179+(76×0.6)=224.6→225=`E1`; G 38+(217×0.6)=168.2→168=`A8`; B 30+(225×0.6)=165=`A5` → `#E1A8A5`.
- `tint("#C26A2E", 0.55)`: R 194+61×0.55=227.55→228=`E4`; G 106+149×0.55=187.95→188=`BC`; B 46+209×0.55=160.95→161=`A1` → `#E4BCA1`.
- `spread_labels([15, 6.1, 4.6, 3.0, -4.3, -19.1], 4)`: walk from the top. 15 stays; 6.1 is 8.9 below, stays; 4.6 must be ≤ 6.1−4 = 2.1; 3.0 ≤ 2.1−4 = −1.9; −4.3 ≤ −1.9−4 = −5.9; −19.1 stays.

```python
# tests/test_charts.py
import pandas as pd
import pytest

from app.components.charts import deviation_pct, gap_from_trend_chart, spread_labels, tint


def test_deviation_pct_is_percent_of_expected():
    df = pd.DataFrame({"deviation": [5.0, -2.0], "expected": [20.0, 40.0]})
    out = deviation_pct(df)
    assert out["pct"].tolist() == pytest.approx([25.0, -5.0])
    assert "pct" not in df.columns  # input is not mutated


def test_deviation_pct_rejects_zero_expected():
    with pytest.raises(ValueError, match="expected"):
        deviation_pct(pd.DataFrame({"deviation": [1.0], "expected": [0.0]}))


def test_tint_mixes_toward_white():
    assert tint("#B3261E", 0.6) == "#E1A8A5"
    assert tint("#B3261E", 0) == "#B3261E"
    assert tint("#b3261e", 1) == "#FFFFFF"


@pytest.mark.parametrize("bad", ["B3261", "#GG0000", "red"])
def test_tint_rejects_non_hex(bad):
    with pytest.raises(ValueError):
        tint(bad, 0.5)


def test_tint_rejects_amount_out_of_range():
    with pytest.raises(ValueError, match="amount"):
        tint("#B3261E", 1.5)


def test_spread_labels_pushes_crowded_labels_down():
    out = spread_labels([15.0, 6.1, 4.6, 3.0, -4.3, -19.1], 4)
    assert out == pytest.approx([15.0, 6.1, 2.1, -1.9, -5.9, -19.1])


def test_spread_labels_keeps_input_order_and_leaves_spaced_labels_alone():
    assert spread_labels([3.0, 15.0], 4) == [3.0, 15.0]
    assert spread_labels([0.0, 1.0], 4) == pytest.approx([-3.0, 1.0])


def test_spread_labels_empty():
    assert spread_labels([], 4) == []


def _color_scale(spec):
    """Find the first color scale (the one with an explicit domain) in a Vega-Lite dict."""
    if isinstance(spec, dict):
        enc = spec.get("encoding", {})
        scale = enc.get("color", {}).get("scale") if isinstance(enc, dict) else None
        if scale and "domain" in scale:
            return scale
        for v in spec.values():
            found = _color_scale(v)
            if found:
                return found
    elif isinstance(spec, list):
        for v in spec:
            found = _color_scale(v)
            if found:
                return found
    return None


def test_gap_chart_full_color_for_highlight_tint_for_rest():
    dev = pd.DataFrame({
        "cause": ["Diabetes mellitus", "Diabetes mellitus", "Diseases of heart", "Diseases of heart"],
        "year": [2020, 2021, 2020, 2021],
        "pct": [24.6, 29.3, 5.5, 10.1],
    })
    chart = gap_from_trend_chart(
        dev,
        colors={"Diabetes mellitus": "#B3261E", "Diseases of heart": "#C26A2E"},
        labels={"Diabetes mellitus": "Diabetes", "Diseases of heart": "Heart disease"},
        highlight={"Diabetes mellitus"},
    )
    scale = _color_scale(chart.to_dict())
    assert scale["domain"] == ["Diabetes mellitus", "Diseases of heart"]
    assert scale["range"] == ["#B3261E", "#E4BCA1"]


def test_gap_chart_rejects_data_with_none_of_the_labelled_causes():
    dev = pd.DataFrame({"cause": ["Other"], "year": [2020], "pct": [1.0]})
    with pytest.raises(ValueError, match="labelled causes"):
        gap_from_trend_chart(dev, colors={}, labels={"Diabetes mellitus": "Diabetes"}, highlight=set())
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_charts.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.components.charts'`

- [ ] **Step 3: Write the implementation**

```python
# app/components/charts.py
"""Chart builders and the small pure helpers behind them. No Streamlit
calls here, so everything can be unit-tested directly."""
import altair as alt
import pandas as pd

MONO = "IBM Plex Mono"
MUTED = "#5A6875"
GRID = "#E1E6EB"
TREND_LINE = "#8795A3"
# How much non-highlighted causes are washed toward white on chart A.
BACKGROUND_TINT = 0.55
# Minimum vertical spacing between end-of-line labels, in pixels.
LABEL_GAP_PX = 13


def deviation_pct(deviations: pd.DataFrame) -> pd.DataFrame:
    """Copy of `deviations` with `pct`: (observed - expected) as a percent of expected."""
    if (deviations["expected"] == 0).any():
        raise ValueError("expected rate is 0 for at least one row; percent deviation is undefined")
    out = deviations.copy()
    out["pct"] = out["deviation"] / out["expected"] * 100
    return out


def tint(hex_color: str, amount: float) -> str:
    """Mix a #RRGGBB color toward white by `amount` (0 = unchanged, 1 = white)."""
    if not 0 <= amount <= 1:
        raise ValueError(f"amount must be between 0 and 1, got {amount}")
    h = hex_color.removeprefix("#")
    if len(h) != 6:
        raise ValueError(f"expected a #RRGGBB color, got {hex_color!r}")
    channels = [int(h[i:i + 2], 16) for i in (0, 2, 4)]  # int() raises ValueError on non-hex
    return "#" + "".join(f"{round(c + (255 - c) * amount):02X}" for c in channels)


def spread_labels(values: list[float], min_gap: float) -> list[float]:
    """Nudge end-of-line label positions so no two sit closer than `min_gap`
    (data units). Walks from the highest value down, pushing crowded labels
    lower; the top label never moves. Output keeps the input order."""
    out = list(values)
    prev = None
    for i in sorted(range(len(values)), key=lambda i: values[i], reverse=True):
        if prev is not None:
            out[i] = min(values[i], prev - min_gap)
        prev = out[i]
    return out


def gap_from_trend_chart(
    dev: pd.DataFrame,
    colors: dict[str, str],
    labels: dict[str, str],
    highlight: set[str],
    height: int = 300,
) -> alt.LayerChart:
    """Home chart A: each cause's percent gap from its projected pre-pandemic
    trend, one line per cause. Highlighted causes are drawn in full color; the
    rest in a light tint of their own color, so the Home cause chips (full
    color) still match their lines."""
    present = set(dev["cause"])
    causes = [c for c in labels if c in present]
    if not causes:
        raise ValueError("none of the labelled causes appear in the deviation data")

    data = dev[dev["cause"].isin(causes)].copy()
    data["label"] = data["cause"].map(labels)
    data["highlighted"] = data["cause"].isin(highlight)
    color = alt.Color(
        "cause:N",
        scale=alt.Scale(
            domain=causes,
            range=[colors[c] if c in highlight else tint(colors[c], BACKGROUND_TINT) for c in causes],
        ),
        legend=None,
    )

    years = sorted(int(y) for y in data["year"].unique())
    y_lo, y_hi = float(min(data["pct"].min(), 0)), float(max(data["pct"].max(), 0))
    pad = (y_hi - y_lo) * 0.08 or 1.0
    y_domain = [y_lo - pad, y_hi + pad]
    y_scale = alt.Scale(domain=y_domain, nice=False)
    # Extend the x domain to the right so the end-of-line labels have room
    # inside the plot instead of being clipped at its edge.
    x_scale = alt.Scale(domain=[years[0] - 0.2, years[-1] + 1.7], nice=False)
    x = alt.X("year:Q", scale=x_scale, title=None, axis=alt.Axis(
        values=years, format="d", labelFont=MONO, labelColor=MUTED, grid=False, ticks=False, domain=False))
    y = alt.Y("pct:Q", scale=y_scale, title=None, axis=alt.Axis(
        labelFont=MONO, labelColor=MUTED, gridColor=GRID, ticks=False, domain=False, tickCount=5,
        labelExpr="datum.value == 0 ? '0%' : (datum.value > 0 ? '+' : '') + datum.value + '%'"))

    # Two line layers so highlighted causes are always drawn on top.
    lines_bg = alt.Chart(data[~data["highlighted"]]).mark_line(strokeWidth=1.5, strokeJoin="round").encode(
        x=x, y=y, color=color)
    lines_fg = alt.Chart(data[data["highlighted"]]).mark_line(strokeWidth=2.6, strokeJoin="round").encode(
        x=x, y=y, color=color)
    points = alt.Chart(data).mark_circle(size=34).encode(
        x=x, y=y, color=color,
        opacity=alt.condition("datum.highlighted", alt.value(1.0), alt.value(0.0)),
        tooltip=[
            alt.Tooltip("label:N", title="Cause"),
            alt.Tooltip("year:Q", title="Year", format="d"),
            alt.Tooltip("pct:Q", title="vs. pre-pandemic trend", format="+.1f"),
        ],
    )

    zero = pd.DataFrame({"year": [years[0] - 0.2], "pct": [0.0], "text": ["pre-pandemic trend"]})
    trend_rule = alt.Chart(zero).mark_rule(color=TREND_LINE, strokeDash=[4, 3]).encode(y=alt.Y("pct:Q", scale=y_scale))
    trend_label = alt.Chart(zero).mark_text(
        align="left", dx=4, dy=11, fontStyle="italic", fontSize=11, color=MUTED,
    ).encode(x=x, y=y, text="text:N")

    ends = data[data["year"] == years[-1]].copy()
    min_gap = (y_domain[1] - y_domain[0]) * LABEL_GAP_PX / height
    ends["label_y"] = spread_labels(ends["pct"].tolist(), min_gap)
    ends["end_text"] = ends.apply(lambda r: f"{r['label']} {r['pct']:+.0f}%", axis=1)
    end_y = alt.Y("label_y:Q", scale=y_scale)
    end_labels = [
        alt.Chart(ends[ends["highlighted"]]).mark_text(align="left", dx=8, fontSize=11.5, fontWeight=600)
        .encode(x=x, y=end_y, text="end_text:N", color=color),
        alt.Chart(ends[~ends["highlighted"]]).mark_text(align="left", dx=8, fontSize=11, color=MUTED)
        .encode(x=x, y=end_y, text="end_text:N"),
    ]

    return (
        alt.layer(trend_rule, trend_label, lines_bg, lines_fg, points, *end_labels)
        .properties(height=height)
        .configure_view(stroke=None)
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_charts.py -v`
Expected: `12 passed` (the `tint` non-hex case is parametrized ×3).

- [ ] **Step 5: Lint and commit**

Run: `.venv/bin/ruff check app/components/charts.py tests/test_charts.py`
Expected: `All checks passed!`

```bash
git add app/components/charts.py tests/test_charts.py
git commit -m "Add gap-from-trend chart and its pure helpers"
```

---

### Task 3: Escaped HTML building blocks + scoped stylesheet

**Files:**
- Create: `app/components/ui.py`
- Test: `tests/test_ui.py`

**Interfaces:**
- Consumes: nothing.
- Produces:
  - `BASE_CSS: str` and `inject_base_css() -> None` (calls `st.html(BASE_CSS)`)
  - `eyebrow_html(tag: str, text: str) -> str`
  - `hero_text_html(subtitle: str, question: str) -> str`
  - `cause_chips_html(chips: list[tuple[str, str]]) -> str`: `(label, "#RRGGBB")` pairs
  - `metric_strip_html(items: list[tuple[str, str, str]]) -> str`: `(value, unit, caption)` triples

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_ui.py
import pytest

from app.components.ui import BASE_CSS, cause_chips_html, eyebrow_html, hero_text_html, metric_strip_html


def test_every_helper_escapes_its_text():
    hostile = '<script>alert("x")</script>'
    outputs = [
        eyebrow_html(hostile, hostile),
        hero_text_html(hostile, hostile),
        cause_chips_html([(hostile, "#B3261E")]),
        metric_strip_html([(hostile, hostile, hostile)]),
    ]
    for out in outputs:
        assert "<script>" not in out
        assert "&lt;script&gt;" in out


def test_cause_chips_rejects_non_hex_color():
    # A color goes into a style attribute; anything but #RRGGBB could inject CSS.
    with pytest.raises(ValueError, match="RRGGBB"):
        cause_chips_html([("Diabetes", "red; background:url(x)")])


def test_cause_chips_renders_one_chip_per_cause_in_order():
    out = cause_chips_html([("Diabetes", "#B3261E"), ("Stroke", "#7A5C99")])
    assert out.count('class="cmd-chip"') == 2
    assert out.index("Diabetes") < out.index("Stroke")
    assert "#B3261E" in out


def test_metric_strip_renders_value_unit_caption():
    out = metric_strip_html([("926", "counties analyzed", "Diabetes; 641 for drug overdose")])
    assert out.count('class="cmd-kpi"') == 1
    for text in ("926", "counties analyzed", "Diabetes; 641 for drug overdose"):
        assert text in out


def test_base_css_only_styles_its_own_classes():
    # Guard against regressing into DataForensics-style overrides of
    # Streamlit internals, which break across Streamlit releases.
    assert "data-testid" not in BASE_CSS
    assert BASE_CSS.lstrip().startswith("<style>")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_ui.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.components.ui'`

- [ ] **Step 3: Write the implementation**

```python
# app/components/ui.py
"""Small HTML building blocks for the redesigned pages. Each *_html function
is pure (returns a string and escapes every interpolated value) so it can be
unit-tested; pages hand the result to st.html. All classes are prefixed
`cmd-` and BASE_CSS styles only those classes, never Streamlit's own
internal elements, so a Streamlit upgrade can't silently break the look."""
import re
from html import escape

import streamlit as st

_HEX = re.compile(r"#[0-9A-Fa-f]{6}")

BASE_CSS = """<style>
:root {
  --cmd-text: #15212B; --cmd-muted: #5A6875; --cmd-border: #D5DCE3; --cmd-surface: #FFFFFF;
  --cmd-serif: "Source Serif 4", Georgia, serif;
  --cmd-mono: "IBM Plex Mono", ui-monospace, SFMono-Regular, monospace;
}
.cmd-eyebrow { font-family: var(--cmd-mono); font-size: 0.74rem; letter-spacing: 0.04em;
  text-transform: uppercase; color: var(--cmd-muted); }
.cmd-eyebrow b { background: var(--cmd-text); color: #fff; font-weight: 500; padding: 2px 7px;
  border-radius: 2px; margin-right: 8px; }
.cmd-subtitle { font-family: var(--cmd-serif); font-size: 1.35rem; line-height: 1.3;
  color: var(--cmd-muted); margin: 0 0 1rem; }
.cmd-question { font-size: 1.05rem; line-height: 1.6; color: var(--cmd-text); max-width: 34rem; margin: 0; }
.cmd-chips { display: flex; flex-wrap: wrap; gap: 6px; }
.cmd-chip { display: inline-flex; align-items: center; gap: 6px; font-size: 0.8rem; font-weight: 500;
  padding: 3px 10px; background: var(--cmd-surface); border: 1px solid var(--cmd-border);
  border-radius: 3px; color: var(--cmd-text); }
.cmd-chip i { width: 7px; height: 7px; border-radius: 50%; display: inline-block; }
.cmd-strip { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 14px; }
.cmd-kpi { background: var(--cmd-surface); border: 1px solid var(--cmd-border); border-radius: 4px;
  padding: 16px 18px; }
.cmd-kpi-value { font-family: var(--cmd-mono); font-size: 1.85rem; font-weight: 500; line-height: 1.1;
  color: var(--cmd-text); font-variant-numeric: tabular-nums; overflow-wrap: anywhere; }
.cmd-kpi-unit { font-size: 0.9rem; font-weight: 500; margin-left: 8px; color: var(--cmd-text); }
.cmd-kpi-caption { font-size: 0.8rem; color: var(--cmd-muted); margin-top: 8px; line-height: 1.45; }
@media (max-width: 900px) { .cmd-strip { grid-template-columns: repeat(2, minmax(0, 1fr)); } }
</style>"""


def inject_base_css() -> None:
    st.html(BASE_CSS)


def eyebrow_html(tag: str, text: str) -> str:
    return f'<div class="cmd-eyebrow"><b>{escape(tag)}</b>{escape(text)}</div>'


def hero_text_html(subtitle: str, question: str) -> str:
    return f'<p class="cmd-subtitle">{escape(subtitle)}</p><p class="cmd-question">{escape(question)}</p>'


def cause_chips_html(chips: list[tuple[str, str]]) -> str:
    parts = []
    for label, color in chips:
        if not _HEX.fullmatch(color):
            raise ValueError(f"chip color must be #RRGGBB, got {color!r}")
        parts.append(f'<span class="cmd-chip"><i style="background:{color}"></i>{escape(label)}</span>')
    return f'<div class="cmd-chips">{"".join(parts)}</div>'


def metric_strip_html(items: list[tuple[str, str, str]]) -> str:
    cards = "".join(
        f'<div class="cmd-kpi"><div class="cmd-kpi-value">{escape(value)}'
        f'<span class="cmd-kpi-unit">{escape(unit)}</span></div>'
        f'<div class="cmd-kpi-caption">{escape(caption)}</div></div>'
        for value, unit, caption in items
    )
    return f'<div class="cmd-strip">{cards}</div>'
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_ui.py -v`
Expected: `5 passed`

- [ ] **Step 5: Lint and commit**

Run: `.venv/bin/ruff check app/components/ui.py tests/test_ui.py`
Expected: `All checks passed!`

```bash
git add app/components/ui.py tests/test_ui.py
git commit -m "Add escaped HTML building blocks and scoped stylesheet"
```

---

### Task 4: Theme, cause palette, navigation renames, page smoke tests

**Files:**
- Modify: `.streamlit/config.toml` (whole file)
- Modify: `app/components/data_loading.py:36-71` (delete `CAUSE_HOME_LABELS`, new `CAUSE_COLORS`)
- Modify: `app/streamlit_app.py` (whole file)
- Modify: `app/app_pages/geographic_heterogeneity.py:13`, `app/app_pages/county_deep_dive.py:10-17`, `app/app_pages/methods.py:148`
- Create: `tests/test_app_pages.py`

**Interfaces:**
- Consumes: `inject_base_css()` from Task 3.
- Produces: new `CAUSE_COLORS` values (keys unchanged); `tests/test_app_pages.py` with `_app_on(page: str) -> AppTest` reused by Tasks 5 and 6.

- [ ] **Step 1: Write the smoke test (passes now; it's the safety net for this task)**

```python
# tests/test_app_pages.py
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
```

- [ ] **Step 2: Run it: page smoke tests pass, rename test fails**

Run: `.venv/bin/python -m pytest tests/test_app_pages.py -v`
Expected: 7 `test_page_runs_without_exception` PASS; `test_renamed_pages_use_new_titles` FAIL (`'Geographic heterogeneity' == 'Geographic patterns'`).

- [ ] **Step 3: Replace `.streamlit/config.toml`**

```toml
[theme]
base = "light"
primaryColor = "#2C5D86"
backgroundColor = "#F3F5F7"
secondaryBackgroundColor = "#EEF2F6"
textColor = "#15212B"
borderColor = "#D5DCE3"
linkColor = "#2C5D86"

redColor = "#B3261E"
orangeColor = "#C26A2E"
yellowColor = "#8A5D06"
greenColor = "#2F6F4E"
blueColor = "#2C5D86"
violetColor = "#7A5C99"
grayColor = "#5A6875"

font = "'IBM Plex Sans':https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600&display=swap"
headingFont = "'Source Serif 4':https://fonts.googleapis.com/css2?family=Source+Serif+4:opsz,wght@8..60,400;8..60,600&display=swap"
codeFont = "'IBM Plex Mono':https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&display=swap"

baseFontSize = 15
baseFontWeight = 400
headingFontSizes = ["40px", "26px", "20px", "16px", "14px", "13px"]
headingFontWeights = [600, 600, 600, 600, 600, 600]
linkUnderline = false

baseRadius = "4px"
buttonRadius = "3px"
showWidgetBorder = true
showSidebarBorder = false

# Per-cause colors, in TEST_CAUSES + NEGATIVE_CONTROL order (heart, diabetes,
# Alzheimer's, stroke, overdose, cancer, congenital) so a cause renders the
# same hue everywhere. Must match CAUSE_COLORS in app/components/data_loading.py.
chartCategoricalColors = [
    "#C26A2E",
    "#B3261E",
    "#8A6D3B",
    "#7A5C99",
    "#2C5D86",
    "#2F6F4E",
    "#8795A3",
]
chartSequentialColors = [
    "#FFF7ED",
    "#FFEDD5",
    "#FED7AA",
    "#FDBA74",
    "#FB923C",
    "#F97316",
    "#EA580C",
    "#C2410C",
    "#9A3412",
    "#7C2D12",
]

dataframeBorderColor = "#D5DCE3"
dataframeHeaderBackgroundColor = "#EEF2F6"

[theme.sidebar]
backgroundColor = "#15212B"
secondaryBackgroundColor = "#2A3947"
textColor = "#E6EBF0"
borderColor = "#2A3947"
primaryColor = "#8FB3D9"
linkColor = "#AAB6C2"
```

- [ ] **Step 4: Update `CAUSE_COLORS` and delete `CAUSE_HOME_LABELS` in `app/components/data_loading.py`**

Delete the whole `CAUSE_HOME_LABELS` block and its comment (lines 36-50); its only user is the old `home.py`, rewritten in Task 6. Replace the `CAUSE_COLORS` block (and its comment) with:

```python
# Matches .streamlit/config.toml's chartCategoricalColors, in the same
# TEST_CAUSES + NEGATIVE_CONTROL order, so a cause renders the same color
# everywhere: chart marks, Home's cause chips, and the dumbbell/trend charts.
CAUSE_COLORS = {
    "Diseases of heart": "#C26A2E",
    "Diabetes mellitus": "#B3261E",
    "Alzheimer's disease": "#8A6D3B",
    "Cerebrovascular disease": "#7A5C99",
    "Drug overdose": "#2C5D86",
    "Malignant neoplasms": "#2F6F4E",
    NEGATIVE_CONTROL: "#8795A3",
}
```

(Leave `CAUSE_BADGE_STYLE` as is; Causes of death still uses it, and step 3 restyles that page.)

`home.py` still imports `CAUSE_HOME_LABELS` until Task 6, so **in this same step** make the old Home use display names instead. In `app/app_pages/home.py`, delete `CAUSE_HOME_LABELS,` from the import list and change line 92 from `st.badge(CAUSE_HOME_LABELS[cause], …)` to:

```python
            st.badge(display_cause(cause), icon=icon, color=badge_color)
```

- [ ] **Step 5: Replace `app/streamlit_app.py`**

```python
import sys
from pathlib import Path

# Ensure the project root (parent of app/) is importable as `src.*` and
# `app.*` regardless of the working directory `streamlit run` is invoked from.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st

from app.components.ui import inject_base_css

st.set_page_config(
    page_title="COVID Mortality Disruption Lab",
    page_icon=":material/monitor_heart:",
    layout="wide",
)
inject_base_css()

page = st.navigation(
    {
        "": [
            st.Page("app_pages/home.py", title="Home", icon=":material/home:"),
            st.Page("app_pages/findings.py", title="Findings", icon=":material/insights:"),
        ],
        "Explore": [
            st.Page("app_pages/causes.py", title="Causes of death", icon=":material/monitor_heart:"),
            st.Page("app_pages/geographic_heterogeneity.py", title="Geographic patterns", icon=":material/map:"),
            st.Page("app_pages/county_deep_dive.py", title="County lookup", icon=":material/location_on:"),
        ],
        "Rigor": [
            st.Page("app_pages/data_quality.py", title="Data quality", icon=":material/fact_check:"),
            st.Page("app_pages/methods.py", title="Methods", icon=":material/school:"),
        ],
    },
    position="sidebar",
)

with st.sidebar:
    st.divider()
    st.markdown("**COVID Mortality Disruption Lab**")
    st.caption("By Aidan Chi")
    st.link_button(
        "View source on GitHub",
        "https://github.com/aidanc667/covid-mortality-disruption-lab",
        icon=":material/code:",
        width="stretch",
    )

page.run()
```

- [ ] **Step 6: Rename page titles and cross-references**

`app/app_pages/geographic_heterogeneity.py:13`:
```python
st.title("Geographic patterns")
```

`app/app_pages/county_deep_dive.py:10-17`:
```python
st.title("County lookup")
heterogeneity_synthetic_banner()
st.caption(
    "County-level heterogeneity data exists only as pre/post period aggregates for the "
    "causes analyzed on the Geographic patterns page, not full annual trajectories "
    "like the original diabetes-only pilot. See research_protocol.md §4 for why county-level "
    "analysis uses coarser aggregation than the national/state series."
)
```

`app/app_pages/methods.py:148`: change `"Geographic Heterogeneity for the full check\n"` to `"Geographic patterns for the full check\n"`.

- [ ] **Step 7: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_app_pages.py -v`
Expected: `8 passed`

Run: `grep -rn "CAUSE_HOME_LABELS\|Geographic Heterogeneity\|County deep dive" app`
Expected: no output.

- [ ] **Step 8: Visual check**

Start the preview (`preview_start` with name `streamlit`; if port 8501 is taken by another project, ask the user before stopping it, or set `"autoPort": true` in `.claude/launch.json` and drop the `--server.port` args). Screenshot Home and Causes of death at desktop width. Confirm: slate background, dark sidebar with the three groups and the new names, serif page titles, cause colors in the Causes trend chart match the table in Global Constraints.

- [ ] **Step 9: Lint and commit**

Run: `.venv/bin/ruff check tests/test_app_pages.py app/streamlit_app.py && .venv/bin/ruff check . --statistics | tail -1`
Expected: first command `All checks passed!`; second `Found 67 errors.` or fewer (the pre-plan baseline).

```bash
git add .streamlit/config.toml app/components/data_loading.py app/streamlit_app.py \
  app/app_pages/geographic_heterogeneity.py app/app_pages/county_deep_dive.py \
  app/app_pages/methods.py app/app_pages/home.py tests/test_app_pages.py
git commit -m "Apply the DataForensics theme and rename two pages"
```

---

### Task 5: Methods gets an Overview tab holding Home's long-form content

Done **before** the Home rewrite so this content is never missing from the app.

**Files:**
- Modify: `app/app_pages/methods.py` (whole file restructured)
- Modify: `tests/test_app_pages.py` (append one test)

**Interfaces:**
- Consumes: `_app_on()` from Task 4; `load_covid_reference_series`, `data_available` from `data_loading`.
- Produces: Methods tabs labelled exactly `["Overview", "Details"]`.

- [ ] **Step 1: Write the failing test** (append to `tests/test_app_pages.py`)

```python
def test_methods_overview_holds_content_moved_off_home():
    at = _app_on("methods")
    assert [t.label for t in at.tabs] == ["Overview", "Details"]
    overview_headings = [s.value for s in at.tabs[0].subheader]
    assert overview_headings == ["Why this matters", "What we did", "The breaking point"]
    details_expanders = [e.label for e in at.tabs[1].expander]
    assert "Research question" in details_expanders
    assert "Ethics and project checks" in details_expanders
```

- [ ] **Step 2: Run it to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_app_pages.py::test_methods_overview_holds_content_moved_off_home -v`
Expected: FAIL (`[] == ['Overview', 'Details']`)

- [ ] **Step 3: Restructure `app/app_pages/methods.py`**

Replace the top of the file (imports through the `st.caption(...)` on line 7) with the code below, then **indent every existing `with st.expander(...)` block (lines 9-183) by four spaces so it sits under `with details:`**, and add the ethics expander at the end of `details`. The trailing `st.caption("See docs/research_protocol.md …")` stays outside both tabs. Expander bodies are unchanged except the line-148 rename from Task 4.

```python
import altair as alt
import streamlit as st

from app.components.data_loading import data_available, load_covid_reference_series, synthetic_banner

AGE_ADJUSTED_EXPLAINER = (
    "It reweights each year's rate as if the U.S. had the exact same age mix every time, "
    "so a real change in risk isn't confused with the population simply getting older "
    "(older populations have higher death rates for almost any cause). Every national-level "
    "rate in this app is age-adjusted, not the raw \"crude\" rate, so different years can be "
    "compared fairly; the county-level maps use crude rate instead, since CDC WONDER "
    "doesn't offer age-adjustment at that granularity (see Data Quality)."
)

st.title("Methods")
synthetic_banner()
st.caption("Every statistical choice below is fixed in docs/research_protocol.md before results are inspected.")

overview, details = st.tabs(["Overview", "Details"])

with overview:
    st.subheader("Why this matters")
    st.write(
        "The impact of a pandemic can't be understood from deaths attributed to the virus alone: "
        "disruption to healthcare, behavior, and daily life can also alter mortality from causes that "
        "have nothing to do with the infection itself. This project asks whether that happened, and "
        "left a measurable footprint in the mortality record."
    )
    st.write(
        "Using 26 years of CDC mortality data, we establish each cause's pre-pandemic trajectory, "
        "estimate what 2020–2024 mortality would have looked like without a pandemic, and test whether "
        "observed mortality significantly departed from that baseline, then whether any disruption was "
        "temporary or persisted through 2024, both nationally and, for two causes, across U.S. counties "
        "by socioeconomic status, healthcare access, and rurality."
    )

    st.subheader("What we did")
    with st.container(horizontal=True):
        for icon, title, body in [
            (":material/database:", "Real data",
             "19 CDC WONDER mortality exports (national + county), plus real County Health Rankings socioeconomic data."),
            (":material/edit_note:", "Locked before looking",
             "Hypotheses and confidence levels for each cause were written down before any 2020–2024 data was analyzed."),
            (":material/verified:", "Tested, not assumed",
             "A negative control, 3 independent sensitivity checks, and FDR correction: a passing grade wasn't assumed."),
            (":material/travel_explore:", "Mapped and explained",
             "Results broken down by cause and by county, with research-grounded reasoning for what could explain each one."),
        ]:
            with st.container(border=True, width="stretch"):
                st.markdown(f"{icon} **{title}**")
                st.caption(body)

    st.subheader("The breaking point")
    st.caption(
        "COVID-19 itself is not one of the causes tested. It's the fixed, known-date shock the whole "
        "analysis is built around. Every cause is compared against the trend it was already on before "
        "this date, not searched for after the fact."
    )
    if data_available():
        covid_series = load_covid_reference_series()
        with st.container(border=True):
            st.markdown("**COVID-19 deaths: March 2020 is the fixed breakpoint**", help=AGE_ADJUSTED_EXPLAINER)
            covid_chart = (
                alt.Chart(covid_series)
                .mark_bar(color="#2C5D86")
                .encode(
                    x=alt.X("year:O", title=None, axis=alt.Axis(labelAngle=0)),
                    # Short title: the full "Age-adjusted rate (per 100,000)"
                    # rotated 90 degrees needs more height than this chart has
                    # and clips; units are in the tooltip and caption.
                    y=alt.Y("age_adjusted_rate:Q", title="Age-adjusted rate"),
                    tooltip=[
                        alt.Tooltip("year:O", title="Year"),
                        alt.Tooltip("age_adjusted_rate:Q", title="Rate per 100,000", format=".1f"),
                    ],
                )
                .properties(height=180, padding={"left": 5, "top": 5, "right": 5, "bottom": 5})
            )
            st.altair_chart(covid_chart, width="stretch")
            peak = covid_series.loc[covid_series["age_adjusted_rate"].idxmax()]
            st.caption(
                f"COVID-19's own age-adjusted mortality rate peaked at {peak['age_adjusted_rate']:.1f} per "
                f"100,000 in {int(peak['year'])}, then declined sharply through 2024. It has no "
                "pre-pandemic baseline to test against (the cause didn't exist before 2020), so it's shown "
                "only as the event this analysis is built around, not one of the 6 causes tested."
            )

with details:
    # ... the existing seven `with st.expander(...)` blocks, unchanged, indented one level ...

    with st.expander("Ethics and project checks", icon=":material/balance:"):
        st.write(
            "This project uses publicly available aggregate data and is intended for research and "
            "educational purposes. It does not provide medical advice or individual-level risk predictions."
        )
        # Static, not computed live (running pytest inside the deployed app
        # would be slow and fragile). Update by hand when tests/ changes;
        # verify with `.venv/bin/python -m pytest --collect-only -q | tail -1`.
        st.caption(
            ":green-badge[106 automated tests] :blue-badge[Pre-registered protocol] "
            ":violet-badge[Real CDC WONDER data] :orange-badge[3-axis sensitivity analysis]"
        )
```

(The `# ...` line is only for this plan: in the file, it's the seven real expander blocks, moved in, with their bodies untouched.)

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_app_pages.py -v`
Expected: `9 passed`

- [ ] **Step 5: Visual check**

Open Methods in the preview. Overview: two paragraphs, four "What we did" cards in a row, the COVID-19 bar chart with a working "?" tooltip. Details: all eight expanders open and read as before.

- [ ] **Step 6: Lint and commit**

Run: `.venv/bin/ruff check app/app_pages/methods.py tests/test_app_pages.py`
Then: `.venv/bin/ruff check . --statistics | tail -1`
Expected: `tests/test_app_pages.py` clean; repo total `Found 67 errors.` or fewer (the pre-plan baseline).

```bash
git add app/app_pages/methods.py tests/test_app_pages.py
git commit -m "Give Methods an Overview tab holding Home's long-form content"
```

---

### Task 6: One-screen Home page

**Files:**
- Rewrite: `app/app_pages/home.py` (whole file)
- Modify: `tests/test_app_pages.py` (append two tests)

**Interfaces:**
- Consumes: `home_scope_metrics` (Task 1); `deviation_pct`, `gap_from_trend_chart` (Task 2); `eyebrow_html`, `hero_text_html`, `cause_chips_html`, `metric_strip_html` (Task 3); `CAUSE_COLORS` (Task 4); `_app_on` (Task 4).
- Produces: nothing new for later tasks.

- [ ] **Step 1: Write the failing tests** (append to `tests/test_app_pages.py`)

```python
import pandas as pd  # add to the imports at the top of the file


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
    assert len(at.expander) == 0
    assert [b.label for b in at.button] == ["Read the findings"]
```

- [ ] **Step 2: Run them to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_app_pages.py -k home_ -v`
Expected: both FAIL (old Home has subheaders and no `counties analyzed` HTML).

- [ ] **Step 3: Replace `app/app_pages/home.py`**

```python
import streamlit as st

from app.components.charts import deviation_pct, gap_from_trend_chart
from app.components.data_loading import (
    CAUSE_COLORS, HETEROGENEITY_CAUSES, TEST_CAUSES, data_available, display_cause,
    heterogeneity_synthetic_banner, load_county_disruption, load_disruption_deviations,
    load_national_series, load_negative_control, synthetic_banner,
)
from app.components.home_metrics import home_scope_metrics
from app.components.ui import cause_chips_html, eyebrow_html, hero_text_html, metric_strip_html

TITLE = "COVID Mortality Disruption Lab"
SUBTITLE = "How the pandemic disrupted non-COVID mortality"
QUESTION = (
    "Did COVID-19 bend the trend for six other leading causes of death, "
    "has it recovered, and where did it hit hardest?"
)
# The two largest 2020-21 disruptions, and the two causes with county data.
HIGHLIGHT = set(HETEROGENEITY_CAUSES)
AGE_ADJUSTED_HELP = (
    "Age-adjusted: each year's rate is reweighted as if the U.S. had the same age mix every "
    "year, so a real change in risk isn't confused with the population getting older. "
    "0% is where the cause's own pre-pandemic trend, projected forward, says it should be."
)

synthetic_banner()
heterogeneity_synthetic_banner()

if not data_available():
    st.title(TITLE)
    st.warning(
        "No precomputed results found yet. Run `python -m scripts.run_covid_disruption_pipeline` "
        "to populate outputs/models/.",
        icon=":material/warning:",
    )
    st.stop()

if not bool(load_negative_control().iloc[0]["passed"]):
    st.error(
        "The negative control did not pass. Per research_protocol.md §7 method 4, this is a hard "
        "gate. Results on the other 6 causes should not be trusted until this is resolved.",
        icon=":material/error:",
    )

scope = home_scope_metrics(load_national_series(), {c: load_county_disruption(c) for c in HETEROGENEITY_CAUSES})
dev = deviation_pct(load_disruption_deviations())

left, right = st.columns([1, 1.05], gap="large", vertical_alignment="center")
with left:
    st.html(eyebrow_html("CDC WONDER", f"Mortality research · {scope.first_year}–{scope.last_year}"))
    st.title(TITLE)
    st.html(hero_text_html(SUBTITLE, QUESTION))
    st.html(cause_chips_html([(display_cause(c), CAUSE_COLORS[c]) for c in TEST_CAUSES]))
with right:
    with st.container(border=True):
        st.markdown("**How far each cause ran from its pre-pandemic trend**", help=AGE_ADJUSTED_HELP)
        st.caption(f"Age-adjusted death rate vs. expected, {int(dev['year'].min())}–{int(dev['year'].max())}")
        st.altair_chart(
            gap_from_trend_chart(dev, CAUSE_COLORS, {c: display_cause(c) for c in TEST_CAUSES}, HIGHLIGHT),
            width="stretch",
        )

diabetes_n = scope.county_counts["Diabetes mellitus"]
overdose_n = scope.county_counts["Drug overdose"]
st.html(metric_strip_html([
    (str(scope.n_years), "years of CDC data", f"{scope.first_year}–{scope.last_year}, CDC WONDER"),
    (str(len(TEST_CAUSES)), "causes tested", "Plus a negative control"),
    (f"{diabetes_n:,}", "counties analyzed", f"Diabetes; {overdose_n:,} for drug overdose"),
    ("Pre-registered", "", "Hypotheses locked before any 2020+ data"),
]))

st.divider()
path, cta = st.columns([3, 1], vertical_alignment="center")
with path, st.container(horizontal=True):
    st.page_link("app_pages/findings.py", label="Findings", icon=":material/insights:")
    st.page_link("app_pages/causes.py", label="Causes of death", icon=":material/monitor_heart:")
    st.page_link("app_pages/geographic_heterogeneity.py", label="Geographic patterns", icon=":material/map:")
    st.page_link("app_pages/methods.py", label="Methods", icon=":material/school:")
with cta:
    if st.button("Read the findings", type="primary", icon=":material/arrow_forward:",
                 icon_position="right", width="stretch"):
        st.switch_page("app_pages/findings.py")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_app_pages.py -v`
Expected: `11 passed`

- [ ] **Step 5: Visual check (acceptance criteria)**

In the preview:
1. Desktop (`resize_window` 1440×900): hero, chart, metric strip, path row all visible with **no vertical scroll** (`document.scrollingElement.scrollHeight <= innerHeight + 4` via `javascript_tool`). End-of-line labels don't overlap or clip; "pre-pandemic trend" label sits under the dashed line; hovering a diabetes point shows a tooltip; the "?" shows the age-adjusted help.
2. Phone (`resize_window` preset `mobile`, reload): single column, metric strip 2×2, `document.scrollingElement.scrollWidth <= innerWidth` (no horizontal scroll).
3. Chip colors match line colors (diabetes red, overdose blue; others' lines are lighter tints of their chip color).
4. "Read the findings" goes to Findings.
Reset with `resize_window` preset `desktop`. Fix anything off and re-run Step 4 before committing.

- [ ] **Step 6: Lint and commit**

Run: `.venv/bin/ruff check app/app_pages/home.py tests/test_app_pages.py`
Expected: `All checks passed!`

```bash
git add app/app_pages/home.py tests/test_app_pages.py
git commit -m "Rebuild Home as a one-screen, chart-led page"
```

---

### Task 7: Full verification and test-count badge

**Files:**
- Modify: `app/app_pages/methods.py` (the `106 automated tests` badge number)

- [ ] **Step 1: Run the whole suite**

Run: `.venv/bin/python -m pytest -q`
Expected: all pass. Note the total (planned: 106 + 4 + 12 + 5 + 11 = **138 passed**).

- [ ] **Step 2: Update the badge**

Run: `.venv/bin/python -m pytest --collect-only -q | tail -1`
Set the number in Methods' `:green-badge[N automated tests]` to that count (planned: 138).

- [ ] **Step 3: Ruff: no new errors**

Run: `.venv/bin/ruff check . --statistics | tail -1`
Expected: `Found 67 errors.` or fewer (the pre-existing baseline). Any increase must be fixed.

- [ ] **Step 4: Commit**

```bash
git add app/app_pages/methods.py
git commit -m "Update automated-test count badge"
```

- [ ] **Step 5: Independent review**

Dispatch the `engineering-reviewer` subagent with: the spec path, this plan path, `git diff <commit before Task 1>..HEAD`, the test matrix (files above), and the actual pytest/ruff output. Address blocker/major findings, re-run Steps 1-3, and stop at two review rounds.

- [ ] **Step 6: Hand off to the user**

Send desktop and phone screenshots of Home and the Methods Overview tab, list what changed, and ask for approval before starting step 2 (Findings). Do not push.
