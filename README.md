# COVID Mortality Disruption Lab

**Which causes of death were most disrupted by the COVID-19 pandemic, how persistent were those disruptions through the most recent available data, and how did they vary across U.S. counties by socioeconomic status, healthcare access, and rurality?**

## Status: complete, running on real data

Rather than treating COVID-19 as the disease under study, this project treats the pandemic as a system-wide shock and asks what it did to mortality from other major causes — cardiovascular disease, stroke, diabetes, Alzheimer's disease, drug overdose, and cancer. All national-level results (15 real CDC WONDER exports) and county-level heterogeneity results (4 real CDC WONDER exports) are real data — nothing synthetic remains in this project. **See [`docs/findings.md`](docs/findings.md) for what the analysis found**, including two results that contradicted the project's own pre-registered priors.

90 automated tests, a pre-registered protocol locked before results were inspected, a negative control, a sensitivity analysis, and full vintage-bridging/suppression handling — all shown directly in the app's Data Quality page, not hidden.

## Approach

A known-date interrupted time series ("excess mortality") design against a 1999–2019 baseline trend, cross-validated with independent change-point detection, a negative control (a cause with no plausible COVID mechanism), and Benjamini-Hochberg FDR correction across the 6 tested causes. County-level heterogeneity regresses per-county disruption magnitude against real socioeconomic/healthcare-access context variables (County Health Rankings & Roadmaps).

Full methodology, pre-registered hypotheses, statistical methods, and every deviation logged as it happened: [`docs/research_protocol.md`](docs/research_protocol.md).

## Data sources

CDC WONDER (Underlying Cause of Death, national and county level), County Health Rankings & Roadmaps, U.S. Census/ACS, USDA Food Environment Atlas, HRSA Area Health Resources File, EPA Air Quality System. Full provenance, access method, and known limitations for each: [`DATA_SOURCES.md`](DATA_SOURCES.md). Exact manual-export steps for the CDC WONDER data (its API can't group mortality data below the national level): [`docs/manual_data_acquisition.md`](docs/manual_data_acquisition.md).

## Reproducibility

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pytest
```

The 19 CDC WONDER exports underlying this analysis are not checked into the repo (see `docs/manual_data_acquisition.md` for why, and the exact steps to re-pull them). With them in place:

```bash
python -m scripts.run_covid_disruption_pipeline   # national + county disruption/persistence/heterogeneity analysis
python -m scripts.run_sensitivity_check           # alternate-baseline robustness check
streamlit run app/streamlit_app.py
```

## Ethics statement

This project uses publicly available aggregate data and is intended for research and educational purposes. It does not provide medical advice or individual-level risk predictions.
