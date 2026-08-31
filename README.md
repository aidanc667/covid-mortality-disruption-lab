# COVID Mortality Disruption Lab

**Which causes of death were most disrupted by the COVID-19 pandemic, how persistent were those disruptions through the most recent available data, and how did they vary across U.S. counties by socioeconomic status, healthcare access, and rurality?**

## Status: active development, pre-results

This project is mid-build. The data-ingestion pipeline (CDC WONDER, Census/ACS, County Health Rankings, USDA Food Environment Atlas, HRSA, EPA PM2.5) is built and verified against live official sources. The core analysis — the actual disruption/persistence findings — has not been run on real data yet. **Nothing in this repo currently represents a research finding.** See `docs/superpowers/specs/2026-08-31-covid-mortality-disruption-design.md` for the full design and `docs/research_protocol.md` for the pre-registered methodology.

## Approach

Rather than treating COVID-19 as the disease under study, this project treats the pandemic as a system-wide shock and asks what it did to mortality from other major causes — cardiovascular disease, stroke, diabetes, Alzheimer's disease, drug overdose, and cancer — using a known-date interrupted time series ("excess mortality") design against a 1999–2019 baseline trend, cross-validated with independent change-point detection methods, a deliberately-included negative control (a cause with no plausible COVID mechanism), and FDR correction across the tested causes.

Full methodology, pre-registered hypotheses, and limitations: `docs/research_protocol.md`.

## Data sources

CDC WONDER (Underlying Cause of Death), U.S. Census/ACS, County Health Rankings & Roadmaps, USDA Food Environment Atlas, HRSA Area Health Resources File, EPA Air Quality System. Full provenance, access method, and known limitations for each: `DATA_SOURCES.md`.

## Reproducibility

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pytest
```

CDC WONDER county-level data requires a manual export step (its API cannot group mortality data below the national level — confirmed against CDC's own documentation, see `DATA_SOURCES.md`); exact click-by-click steps are in `docs/manual_data_acquisition.md`.

## Ethics statement

This project uses publicly available aggregate data and is intended for research and educational purposes. It does not provide medical advice or individual-level risk predictions.
