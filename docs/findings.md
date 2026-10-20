# Findings

CDC WONDER age-adjusted death rates, 1999–2024. The method and the predictions made beforehand are in [research_protocol.md](research_protocol.md); the full write-up is the [PDF report](../outputs/reports/covid_mortality_disruption_report.pdf).

## Summary

Five of the six causes rose significantly above their pre-pandemic trend in 2020–21, and all five survive correction for testing six causes at once. By 2024, diabetes (+15.0%) and cancer (+4.6%) were still above trend and Alzheimer's disease (−19.1%) had fallen below it. Heart disease, stroke and drug overdose were back within their normal ranges.

| Cause | Classification | 2020–21 gap | p-value | 2024 gap |
|---|---|---|---|---|
| Drug overdose | Persisted | +40.9% | 2.1 × 10⁻⁷ | −4.3% |
| Diabetes | Persisted | +26.9% | 2.5 × 10⁻⁶ | +15.0% |
| Heart disease | Persisted | +7.8% | 1.1 × 10⁻⁴ | +3.0% |
| Cancer | Persisted | +1.7% | 4.5 × 10⁻⁴ | +4.6% |
| Stroke | Persisted | +8.8% | 0.004 | +6.1% |
| Alzheimer's disease | No significant disruption | +1.0% | 0.82 | −19.1% |

A gap counts as significant when it falls outside the range the cause's own pre-2020 variation would explain. That range is about ±1% for cancer in 2024 but about ±13% for drug overdose, so cancer's +4.6% is significant and overdose's −4.3% is not. "Persisted" means at least one year from 2022 to 2024 stayed significantly off trend in the same direction as 2020–21; it does not require 2024 itself to be off trend.

## Trend is not the same as 2019

The gaps compare each year with where the pre-2020 trend pointed, not with 2019. In 2024, diabetes was back at its 2019 rate (21.7 vs. 21.6) and reads +15% only because its trend line was still falling. Cancer kept falling (146.2 to 139.4), just more slowly than its trend. Drug overdose (23.1) and stroke (38.6) are back within their normal ranges but still about 7% and 4% above their 2019 rates. These rates match CDC's published figures (NCHS Data Briefs 521, 548 and 549).

## Two results that went against the predictions

**Cancer.** No disruption was expected this soon. Cancer instead rose 1.7% above trend in 2020–21 (p < 0.001) and was 4.6% above it in 2024. The result is fragile: with a trend that falls by a steady percentage each year, the 2020–21 gap is not significant (p = 0.43). Outside evidence is mixed. Modeling of England's actual 2020–22 deaths found breast and lung cancer deaths close to their pre-pandemic trends, while a review of earlier studies links each four-week delay in starting treatment with higher mortality.

**Alzheimer's disease.** A large increase was expected. The 2020–21 test found none (p = 0.82): 2020 ran 4.2% above trend, but 2021 fell below it. This project counts Alzheimer's only as the underlying cause of death, and when a person with dementia died of COVID-19, COVID-19 was usually recorded as the underlying cause. Studies that also count dementia as a contributing cause found about 94,700 excess deaths in the first pandemic year (Chen et al., JAMA Neurology 2023). Pooling all five post-2020 years does find a significant later decline (p = 0.016), consistent with mortality displacement, though these data cannot confirm that.

## Robustness

- **Negative control.** Congenital malformations, which have no direct link to COVID-19, show no disruption (p = 0.71 on death counts). The first choice, accidental drowning, was dropped because pandemic pool and beach closures did change drowning deaths.
- **Baseline correction.** Using only pre-2020 data, a straight line over 1999–2019 already sat 17.7 and 5.8 points below the actual 2019 rates for heart disease and stroke, which fell steeply and then leveled off. Both now use a 2010–2019 baseline; both stay significant, with 2020–21 gaps of 8–9% rather than 26–37%.
- **Sensitivity analyses.** Each cause's classification was recomputed with the other baseline window, a stricter significance level (α = 0.01), a curved trend and a steady-percentage trend. Drug overdose, diabetes and heart disease hold under all four. Stroke loses significance with a curved trend (p = 0.18), and at α = 0.01 its 2020–21 result stays significant (p = 0.004) but its later years do not, so it would be classed Resolved. Cancer loses significance with a steady-percentage trend. Stroke and cancer are the two least certain results.
- **Autocorrelation.** Four causes have correlated baseline years. A Newey-West version of the 2020–21 test raises the p-values most for diabetes (about 25 times) and drug overdose (about 120 times); all five significant causes stay significant.
- **Baseline window in 2024.** The 2020–21 results hold under either window, but the 2024 status of four causes does not. Against a 2010–2019 trend, diabetes would be within its normal range (+0.2%) and drug overdose significantly below trend (−18.0%). For heart disease and stroke, the other window is the 1999–2019 line already shown to misfit them.
- **p-value correction.** On 2026-10-19 the 2020–21 p-values were corrected; the original formula made them roughly 2–4 times too small. No classification changed.

## Counties

Each county's change in crude death rate from 2015–19 to 2020–24 was regressed separately on five County Health Rankings measures, with correction for multiple tests within each cause. Counties are included when CDC reports a reliable rate in both periods: 3,066 for heart disease, 3,062 for cancer, 2,651 for stroke, 2,342 for diabetes and 1,564 for drug overdose.

- Higher smoking and uninsured rates went with larger increases for all five causes.
- Higher household income went with smaller increases for four causes (not stroke).
- Higher obesity went with larger increases for heart disease, diabetes and drug overdose.
- Rurality was mixed: larger increases for heart disease, drug overdose and cancer, smaller for stroke, and no link for diabetes.

An earlier method kept only 926 counties for diabetes and 641 for drug overdose, mostly larger and less rural ones, and pointed to smaller increases in rural counties. With five-year totals that pattern disappears for diabetes and reverses for overdose. Counties still left out are mostly rural (83–94% rural against 45–63% for included counties), and county rates are not age-adjusted, so a rural association can partly reflect older populations. Alzheimer's disease, run the same way as an exploratory comparison across 2,426 counties, showed no significant association with any measure.

## What the data cannot show

Mortality data cannot separate direct infection, delayed or interrupted care, strained hospitals and economic or isolation stress, since all of them change death rates the same way. Every result here is an association between rates and time, or between county averages, not a causal claim.

## Data

All results use real CDC WONDER exports: 15 national files and 18 county files. Download steps are in [manual_data_acquisition.md](manual_data_acquisition.md).
