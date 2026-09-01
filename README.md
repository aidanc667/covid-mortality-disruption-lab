# COVID Mortality Disruption Lab

**Which causes of death were most disrupted by the COVID-19 pandemic, how persistent were those disruptions through the most recent available data, and how did they vary across U.S. counties by socioeconomic status, healthcare access, and rurality?**

## Status: complete, running on real data

Rather than treating COVID-19 as the disease under study, this project treats the pandemic as a system-wide shock and asks what it did to mortality from other major causes — cardiovascular disease, stroke, diabetes, Alzheimer's disease, drug overdose, and cancer. All national-level results (15 real CDC WONDER exports) and county-level heterogeneity results (4 real CDC WONDER exports) are real data — nothing synthetic remains in this project. **See [`docs/findings.md`](docs/findings.md) for what the analysis found**, including two results that contradicted the project's own pre-registered priors — or read the same findings inside the live app (Findings page), which also offers a formal PDF report ([`outputs/reports/covid_mortality_disruption_report.pdf`](outputs/reports/covid_mortality_disruption_report.pdf)) as a download.

96 automated tests, a pre-registered protocol locked before results were inspected, a negative control, a three-axis sensitivity analysis, effect-size reporting, and full vintage-bridging/suppression handling — all shown directly in the app's Data Quality page, not hidden.

The app includes an interactive U.S. county choropleth map (Geographic heterogeneity page) and a per-cause deep-dive (Causes of death page) with the trajectory, effect size, and plausible research-literature reasoning for each of the 6 test causes.

## Approach

A known-date interrupted time series ("excess mortality") design against a 1999–2019 baseline trend, cross-validated with independent change-point detection, a negative control (a cause with no direct COVID mechanism), and Benjamini-Hochberg FDR correction across the 6 tested causes. County-level heterogeneity regresses per-county disruption magnitude against real socioeconomic/healthcare-access context variables (County Health Rankings & Roadmaps).

Full methodology, pre-registered hypotheses, statistical methods, and every deviation logged as it happened: [`docs/research_protocol.md`](docs/research_protocol.md).

## Data sources

CDC WONDER (Underlying Cause of Death, national and county level) and County Health Rankings & Roadmaps are the two sources actually used in the published analysis. U.S. Census/ACS, USDA Food Environment Atlas, HRSA Area Health Resources File, and EPA Air Quality System were investigated during an early feasibility pass and are documented for transparency, but are not part of the final pipeline or any reported result. Full provenance, access method, and known limitations for each: [`DATA_SOURCES.md`](DATA_SOURCES.md). Exact manual-export steps for the CDC WONDER data (its API can't group mortality data below the national level): [`docs/manual_data_acquisition.md`](docs/manual_data_acquisition.md).

## Reproducibility

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pytest
```

The 19 CDC WONDER exports underlying this analysis are not checked into the repo (see `docs/manual_data_acquisition.md` for why, and the exact steps to re-pull them). With them in place:

```bash
python -m scripts.run_covid_disruption_pipeline   # national + county disruption/persistence/heterogeneity analysis
python -m scripts.run_sensitivity_check           # 3-axis robustness check (window, threshold, trend shape)
streamlit run app/streamlit_app.py
```

The formal PDF report (`outputs/reports/covid_mortality_disruption_report.pdf`) needs one extra dependency not in the app's own `requirements.txt` (kept lean for deployment):

```bash
pip install -r requirements-report.txt
python -m scripts.generate_report
```

## Ethics statement

This project uses publicly available aggregate data and is intended for research and educational purposes. It does not provide medical advice or individual-level risk predictions.

## License

Code and documentation are released under the [MIT License](LICENSE). CDC WONDER mortality data is U.S. government public domain (not subject to copyright, per 17 U.S.C. §105); County Health Rankings & Roadmaps data carries its own [terms of use](https://www.countyhealthrankings.org/about-us/terms-and-conditions) — neither is relicensed by this repository.
