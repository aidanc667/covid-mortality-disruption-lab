# COVID Mortality Disruption Lab

**Live app:** [covid-mortality-disruption-lab.streamlit.app](https://covid-mortality-disruption-lab.streamlit.app) &nbsp;·&nbsp; **Full report:** [`outputs/reports/covid_mortality_disruption_report.pdf`](outputs/reports/covid_mortality_disruption_report.pdf) &nbsp;·&nbsp; **Findings:** [`docs/findings.md`](docs/findings.md)

**Which causes of death were most disrupted by the COVID-19 pandemic, how long did the disruption last, and which parts of the country got hit hardest?**

COVID-19 isn't the subject of this analysis; it's the shock. Rather than counting deaths attributed to the virus itself, this project treats the pandemic as a system-wide disruption and asks what it did to mortality from six other major causes — heart disease, stroke, diabetes, Alzheimer's disease, drug overdose, and cancer — using 26 years of real CDC mortality data, not synthetic or simulated numbers.

## What it found

Five of the six causes tested show a statistically significant deviation from their pre-pandemic trend that is still unresolved four years later; none have fully returned to normal, and none have reversed direction. Drug overdose shows the largest acute swing (+40.9% in 2020-21), easing back toward its pre-pandemic trend by 2024 (-4.3%) but not fully reversing. Diabetes (+26.9% acute, still +15.0% in 2024) and heart disease (+7.8% acute, after a baseline correction described below) have eased somewhat but remain significantly elevated rather than resolving.

The two most interesting results are the two that weren't supposed to happen. Cancer was pre-registered as an expected null — the theory was that delayed screening wouldn't show up as excess deaths for years past this project's 2024 data window — and it showed a real, if modest, disruption anyway (+1.7%, still significant after correcting for testing six causes at once). Alzheimer's disease was pre-registered as a high-confidence, large effect, on the theory that pandemic isolation would show up clearly in dementia mortality, and it showed none in the acute 2020-21 window. Pooling all five post-2020 years instead of just the acute window turns up something else entirely: a real, later decline that only became significant in 2023-2024, consistent with mortality displacement rather than the originally hypothesized mechanism.

Both of these were decided in writing, with a stated confidence level, before any 2020-2024 data was pulled — otherwise a result that happens to confirm what you expected proves very little.

## Why this exists

Excess-mortality analysis is the real technique public health agencies use to estimate a pandemic's true toll beyond its officially attributed death count, and to catch the damage that never shows up in a case count at all — deferred cancer screening, interrupted addiction treatment, delayed cardiac care. Running it across six causes at once, with a shared statistical pipeline and a hypothesis locked in advance for each one, turns a single case study into something closer to a small research program. That's also what makes it a useful project to read closely: it isn't just a dashboard of pandemic statistics, it's a demonstration of what happens when you follow a rigorous method all the way through, including the parts where the data disagrees with you.

## Rigor, shown rather than claimed

- **Pre-registered hypotheses.** Every cause's predicted direction and confidence level was written down before the 2020-2024 data was ever pulled ([`docs/research_protocol.md`](docs/research_protocol.md)).
- **A negative control.** The identical pipeline is run on a cause with no direct COVID mechanism; a significant result there would mean the method is just detecting noise. It passed — and the project documents, rather than hides, that the *first* negative control it tried (accidental drowning) genuinely failed, and explains why that's not a contradiction.
- **Independent cross-check.** Three unrelated change-point detection methods (PELT, binary segmentation, segmented regression) are run on each series to see whether they land on a 2020 breakpoint without being told to.
- **A three-axis sensitivity analysis.** The primary method is re-fit with a different baseline window, a stricter significance threshold, and a curved instead of linear trend, to see whether any result depends on a modeling choice rather than the data.
- **An autocorrelation-robust check.** The classical significance test assumes each year's deviation from trend is independent noise, which is measurably false for several causes. A Newey-West (HAC) version of the same test is reported alongside the classical one — it widens the uncertainty for the affected causes but doesn't overturn any result.
- **106 automated tests**, run on every change, including tests that encode real findings (like the Alzheimer's delayed-decline result) as regression checks rather than just asserting they hold.

All of this is visible directly in the app's Data Quality page, not summarized away.

## Inside the app

- **Findings** — the plain-language summary of every result, including the two that contradicted the project's own priors.
- **Causes of death** — a deep dive per cause: the trajectory chart, the effect size, three different significance checks side by side, and what the published research literature plausibly suggests as a mechanism (clearly separated from what this project's own data can prove).
- **Geographic heterogeneity** — an interactive U.S. county choropleth for the two causes with usable county-level data, showing where disruption was largest and what socioeconomic or healthcare-access variables predict it.
- **County deep dive** — look up any individual county's pre/post rates and real local context.
- **Data quality** — the negative control, the sensitivity analysis, vintage-bridging reliability, and every methodological correction, shown directly.
- **Methods** — the full statistical design in one place.

## Approach

A known-date interrupted time series ("excess mortality") design: fit each cause's own pre-pandemic trend, project it forward with a 95% prediction interval, and flag a year as disrupted when the observed rate steps outside that interval. The breakpoint (March 2020) is fixed by the pandemic's known onset, never searched for after the fact. County-level heterogeneity regresses per-county disruption magnitude against real socioeconomic and healthcare-access variables from County Health Rankings & Roadmaps.

Two causes (diseases of heart and cerebrovascular disease) needed a mid-project correction: their original 1999-2019 baseline was found, through evidence that never touched any 2020+ data, to already be diverging from their real pre-pandemic trajectory. The fix, why it was needed, and why a couple of tempting alternatives were rejected, is documented in full rather than quietly applied — see the addenda in [`docs/research_protocol.md`](docs/research_protocol.md).

## Data sources

CDC WONDER (Underlying Cause of Death, national and county level) and County Health Rankings & Roadmaps are the two sources actually used in the published analysis. U.S. Census/ACS, USDA's Food Environment Atlas, HRSA's Area Health Resources File, and the EPA's Air Quality System were investigated during an early feasibility pass and are documented for transparency, but play no part in the final pipeline or any reported result. Full provenance and known limitations for each source: [`DATA_SOURCES.md`](DATA_SOURCES.md). CDC WONDER's API can't group mortality data below the national level, so every export behind this analysis was pulled manually — exact steps: [`docs/manual_data_acquisition.md`](docs/manual_data_acquisition.md).

## Running it locally

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pytest
```

The 19 CDC WONDER exports underlying this analysis aren't checked into the repo (see `docs/manual_data_acquisition.md` for why, and the exact steps to re-pull them). With them in place:

```bash
python -m scripts.run_covid_disruption_pipeline   # national + county disruption/persistence/heterogeneity analysis
python -m scripts.run_sensitivity_check           # 3-axis robustness check (window, threshold, trend shape)
streamlit run app/streamlit_app.py
```

The PDF report needs one extra dependency the deployed app doesn't (kept out of `requirements.txt` to keep the app's build lean):

```bash
pip install -r requirements-report.txt
python -m scripts.generate_report
```

## Ethics statement

This project uses publicly available aggregate data and is intended for research and educational purposes. It does not provide medical advice or individual-level risk predictions.

## License

Code and documentation are released under the [MIT License](LICENSE). CDC WONDER mortality data is U.S. government public domain (not subject to copyright, per 17 U.S.C. §105); County Health Rankings & Roadmaps data carries its own [terms of use](https://www.countyhealthrankings.org/about-us/terms-and-conditions) — neither is relicensed by this repository.
