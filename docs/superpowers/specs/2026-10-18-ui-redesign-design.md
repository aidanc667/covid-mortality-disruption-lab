# UI redesign: professional, scannable, chart-led

**Date:** 2026-10-18
**Status:** Approved in brainstorming, pending spec review
**Scope:** Visual design system + information architecture for the Streamlit app in `app/`. No change to the analysis pipeline (`src/`, `scripts/`) or to any computed result.

## Goals

1. Look professional and consistent with the author's DataForensics app (same palette and type).
2. Cut reading load: every page leads with one takeaway sentence and one chart; detail lives in tabs.
3. Home page fits on one desktop screen with no scrolling.
4. Every number shown is computed from `outputs/models/*.parquet`, never hand-typed.
5. Keep every caveat that exists today; reorganize it, don't delete it.

## Non-goals

- New analyses, new data, or changed statistical methods.
- Leaving Streamlit, or porting DataForensics' ~250-line `data-testid` CSS override layer.
- Dark mode.

## Acceptance criteria

- At 1440×900 the Home page shows hero, chart, metric strip, and path row with no vertical scroll; at ≤900px wide it stacks to a single column with no horizontal scroll.
- No interior page section is taller than roughly one screen; long content is in `st.tabs`.
- Every page uses the shared fonts/colors; a cause renders in the same color on every chart and chip.
- Home metric values (years, cause count, county counts) come from a tested pure function.
- Every page loads without exceptions under Streamlit `AppTest`.
- Existing `pytest` suite and `ruff` still pass.
- No claim in the copy contradicts a chart shown on the same page (see "Copy corrections").

## 1. Design system

### Tokens (match DataForensics)

| Token | Value | Use |
|---|---|---|
| bg | `#F3F5F7` | page background |
| surface | `#FFFFFF` | cards, chart panels |
| border | `#D5DCE3` | card and table borders |
| text | `#15212B` | body and headings; sidebar background |
| muted | `#5A6875` | captions, axis labels |
| accent | `#2C5D86` | primary button, links, active nav |
| sidebar-active | `#2A3947` | selected nav item |

Fonts (Google Fonts): **Source Serif 4** for titles and section headings, **IBM Plex Sans** for body/UI, **IBM Plex Mono** for numbers (metric values, axis ticks, p-values).

### Cause colors

One muted hue per cause, defined once (in `app/components/data_loading.py`, replacing the current `CAUSE_COLORS`/`chartCategoricalColors` values in matching order) and used for chips, chart lines, and badges:

| Cause | Color |
|---|---|
| Drug overdose | `#2C5D86` |
| Diabetes | `#B3261E` |
| Stroke | `#7A5C99` |
| Cancer | `#2F6F4E` |
| Heart disease | `#C26A2E` |
| Alzheimer's | `#8A6D3B` |
| Congenital malformations (negative control) | `#8795A3` |

When a chart highlights a subset of causes (Home chart A), non-highlighted causes are drawn as a **light tint of their own color** (not flat gray), so chips and lines always agree.

### Implementation approach

- `.streamlit/config.toml` carries the theme: colors, `font`/`headingFont`/`codeFont`, `chartCategoricalColors`, and a dark `[theme.sidebar]`. This does most of the work through supported settings.
- New `app/components/ui.py` with small, explicit helpers. Each emits scoped HTML/CSS via `st.markdown(..., unsafe_allow_html=True)` with class names prefixed `cmd-` so styles don't leak:
  - `inject_base_css()`: called once from `streamlit_app.py`; font import plus the `cmd-` classes only.
  - `hero(eyebrow, title, subtitle, question)`
  - `cause_chips(causes)`
  - `metric_strip(items)`: items are `(value, unit, caption)`.
  - `takeaway(text)`: the one-sentence lede under each page title.
  - `path_row(steps)`: the "Findings → Causes → …" line (uses `st.page_link`).
- Any HTML helper escapes interpolated text (`html.escape`); values come from our own parquet files but escaping is cheap and removes the question.
- Charts stay in Altair, styled through the theme plus a shared `chart_defaults()` (fonts, gridline color, Plex Mono ticks).

### Navigation

Same three groups. Renames: "Geographic heterogeneity" → **Geographic patterns**, "County deep dive" → **County lookup**. Sidebar brand: **COVID Mortality Disruption Lab**; footer: "View source on GitHub" and "By Aidan Chi". File names under `app_pages/` stay the same, so the routes don't change.

## 2. Home page (one screen)

Top to bottom:

1. **Hero, left:** eyebrow `CDC WONDER · MORTALITY RESEARCH · 1999–2024`; title **COVID Mortality Disruption Lab**; subtitle *How the pandemic disrupted non-COVID mortality*; question: *Did COVID-19 bend the trend for six other leading causes of death, has it recovered, and where did it hit hardest?*; six cause chips.
2. **Hero, right: chart A.** "How far each cause ran from its pre-pandemic trend"; % deviation of the age-adjusted rate from expected, 2020–2024, from `disruption_deviations` (`deviation / expected`). Diabetes and drug overdose highlighted, the other four tinted; end-of-line labels with the 2024 value; dashed zero line labeled "pre-pandemic trend"; tooltips on points. A `help` "?" carries the existing plain-language "age-adjusted" explanation.
3. **Metric strip (scope-first):** years of CDC data (from the national series' year range), causes tested (`len(TEST_CAUSES)`, caption "plus a negative control"), counties analyzed (diabetes count, caption with overdose count), and "Pre-registered" (static: it's a property of the protocol, not of the data).
4. **Path row:** Findings → Causes of death → Geographic patterns → Methods, plus a primary **Read the findings** button.

Stays on Home (renders only when triggered): `synthetic_banner()`, `heterogeneity_synthetic_banner()`, missing-data warning, negative-control failure error.

Moves off Home:

| Today's Home content | New home |
|---|---|
| Why this matters; What we did (4 cards) | Methods → Overview |
| COVID-19 reference chart + "age-adjusted" expander | Methods → Overview |
| Headline finding + Disrupted / FDR / Reversed / Negative-control metrics | Findings → Results |
| Start here cards | Replaced by path row |
| Test/protocol/data badges; ethics statement | Methods → Limitations & ethics |

## 3. Interior pages

Pattern: serif title → `takeaway()` → key chart → `st.tabs`.

| Page | Takeaway (data-driven where it cites numbers) | Key chart | Tabs |
|---|---|---|---|
| Findings | "N of 6 causes departed from their pre-pandemic trend; by 2024, X were still significantly above it." | **B**: dumbbell, 2020–21 vs. 2024 deviation per cause | Results · Surprises · Robustness · Counties · Limits |
| Causes of death | One line generated from the summary | Six compact cause cards; selecting one shows **C** (observed vs. "no pandemic" trend with prediction band, 1999–2024) | Trend · Robustness · What could explain it · Sources |
| Geographic patterns | Direction of each context-variable association, from `heterogeneity_summary` | County choropleth with diabetes/overdose toggle | Map · What predicts it · All counties |
| County lookup | (none; it's a tool) | Pre vs. post mini-chart beside the existing metrics | (none; already short) |
| Data quality | "Every check is shown, including the ones that flagged problems." | (none) | Negative control · Multiple testing · Vintage bridging · Sensitivity |
| Methods | (none) | COVID-19 reference chart in Overview | Overview · Hypotheses · Data · Statistics · Counties · Language policy · Limitations & ethics |

All existing expanders and caveats move into the matching tab; none are deleted.

## 4. Copy corrections (found while building the charts)

These sentences currently contradict the data the new charts make visible:

- "none of them has fully returned to normal" / "None of the disrupted causes have resolved back to their expected trend by 2024": in 2024 only diabetes (+15%) and cancer (+5%) are individually significant above trend. Rewrite to say that, computed from `disruption_deviations.significant` for 2024.
- "none reversed direction": drug overdose is −4.3% vs. trend in 2024 (not significant) yet classified "Persisted". The copy must say how that classification is defined, so the claim doesn't conflict with chart A or B. **The classification logic itself is out of scope**; flag it for a separate review.
- Negative control: congenital malformations' age-adjusted rate runs +14% vs. trend by 2024 (significant), while the gate passes on raw counts. Data quality already explains raw counts; Findings → Robustness should say so in one line so a reader comparing to the charts isn't misled. Any change to the gate itself is out of scope and is flagged separately.

## 5. Testing

- `tests/test_ui_metrics.py`: unit tests for the pure function behind the Home metric strip (`home_scope_metrics(national, county_frames)` → years, cause count, county counts), using small hand-built DataFrames with expected values derived by hand. Includes an empty county frame and a single-year series.
- `tests/test_app_pages.py`: Streamlit `AppTest` smoke test per page: runs without exception, and Home shows the computed county count and the title "COVID Mortality Disruption Lab". Skips with a clear reason if `outputs/models/` is absent.
- Helpers in `ui.py`: one test that HTML-special characters in inputs are escaped.
- Manual visual check per rollout step: desktop (1440 wide) and phone (375 wide) screenshots in the browser preview.
- Existing suite (`pytest`) and `ruff check` must still pass.

## 6. Rollout (one page per step, user reviews each)

1. Design system (`config.toml`, `ui.py`, cause colors, nav renames) + Home.
2. Findings (+ copy corrections).
3. Causes of death.
4. Geographic patterns + County lookup.
5. Data quality + Methods (receives content moved off Home).

The README's screenshots and page names get updated in step 5. The PDF report is untouched.

## Risks

- Streamlit theme options (`headingFont`, sidebar theming) depend on the installed Streamlit version; verify against the pinned version in step 1 and fall back to scoped CSS only where an option is missing.
- Content that moves off Home is temporarily absent between step 1 and step 5. Mitigation: step 1 already creates Methods → Overview with that content, ahead of the rest of Methods' redesign.
