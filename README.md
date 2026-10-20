# COVID Mortality Disruption Lab

**Live app:** [covid-mortality-disruption-lab.streamlit.app](https://covid-mortality-disruption-lab.streamlit.app) · **Report:** [PDF](outputs/reports/covid_mortality_disruption_report.pdf) · **Findings:** [docs/findings.md](docs/findings.md)

**Research question:** Did COVID-19 disrupt the trend for six other leading causes of death, has it recovered, and where did it hit hardest?

This project doesn't count COVID-19 deaths. It treats the pandemic as a shock to the health system and asks what happened to deaths from heart disease, diabetes, Alzheimer's disease, stroke, drug overdose, and cancer. It uses CDC mortality data from 1999 to 2024.

## How it works

For each cause, I fit a straight-line trend to the years before 2020 and projected it forward with a 95% prediction interval. A year counts as disrupted when the actual death rate falls outside that range. That makes the bar different for each cause: cancer barely moves from year to year, so a gap of about 1% is significant, while drug overdose swings so much that it needs about 13%.

The expected direction and confidence for every cause were written down before I looked at any 2020–2024 data ([research protocol](docs/research_protocol.md)).

## What I found

- **Five of six causes rose significantly above trend in 2020–21.** Drug overdose (+41%) and diabetes (+27%) had the biggest jumps.
- **Most of it has faded.** By 2024, only diabetes (+15%) and cancer (+5%) were still above trend. Heart disease, stroke, and drug overdose were back in their normal range. "Above trend" means above where the pre-2020 trend pointed, not above 2019: diabetes was back at its 2019 rate, cancer kept falling but more slowly, and overdose is back in range but still about 7% above its 2019 rate.
- **Two results went against my predictions.** I expected cancer to show nothing this soon, but it rose a small amount, though that depends on how the pre-2020 trend is modeled. I expected a large rise for Alzheimer's. It ran 4% above trend in 2020 but below it in 2021, so the two-year test found nothing significant, and it then fell well below trend by 2024 (−19%). Other studies that also count dementia as a contributing cause did find large excess deaths in 2020.
- **Some 2024 results depend on the baseline.** The 2020–21 jumps hold under either baseline window, but the 2024 status of four causes doesn't. For example, diabetes is +15% against a 1999–2019 trend and about 0% against a 2010–2019 one. The app's Robustness tab shows both.
- **Counties with more smokers and more uninsured people were hit harder** for all five disrupted causes. Rurality is mixed: more rural counties saw bigger effects for heart disease, overdose, and cancer, but not for stroke or diabetes.

## Checks

- A negative control: a cause with no direct link to COVID (birth defects) run through the same pipeline. It came back clean.
- Sensitivity checks with a different baseline window, a stricter significance level, a curved trend, and a trend that falls by a steady percentage each year. Stroke and cancer are the two results that don't pass every one.
- Correction for testing six causes at once, and an autocorrelation-robust version of the main test.
- 237 automated tests.

## Data

[CDC WONDER](https://wonder.cdc.gov/) for national and county death rates, and [County Health Rankings](https://www.countyhealthrankings.org/) for county characteristics. The raw CDC files aren't in this repo. County data can only be pulled through CDC WONDER's web interface, and [docs/manual_data_acquisition.md](docs/manual_data_acquisition.md) has the exact steps. More detail on each source is in [DATA_SOURCES.md](DATA_SOURCES.md).

## Running it

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m pytest
streamlit run app/streamlit_app.py
```

The app runs from the precomputed results in `outputs/`. To rebuild them from the raw CDC files, run `python -m scripts.run_covid_disruption_pipeline` and `python -m scripts.run_sensitivity_check`. To rebuild the PDF, install `requirements-report.txt` and run `python -m scripts.generate_report`.

## License

Code is under the [MIT License](LICENSE). CDC WONDER data is public domain; County Health Rankings data has its own [terms of use](https://www.countyhealthrankings.org/about-us/terms-and-conditions). This project uses aggregate public data for research and education and isn't medical advice.
