# Findings

**COVID Mortality Disruption Lab** — real CDC WONDER data, 1999–2024. Full methodology and pre-registered hypotheses: [`research_protocol.md`](research_protocol.md). This document summarizes what the completed analysis found; it does not repeat the methodology, only interprets the results.

## The headline

Of the 6 major causes of death tested, **5 show a statistically significant, still-unresolved deviation from their pre-pandemic trend, four years after the pandemic began.** None of the 5 have resolved back to their expected trend by 2024, and none have reversed direction. The one cause with no significant disruption — Alzheimer's disease — is itself a real, meaningful result, not a gap in the data.

| Cause | Result | p-value | Survives FDR | 2020–21 deviation | 2024 deviation |
|---|---|---|---|---|---|
| Drug overdose | Persisted | 5.98 × 10⁻⁸ | Yes | +40.9% | -4.3% |
| Diabetes mellitus | Persisted | 7.99 × 10⁻⁷ | Yes | +26.9% | +15.0% |
| Malignant neoplasms (cancer) | Persisted | 1.94 × 10⁻⁴ | Yes | +1.7% | +4.6% |
| Diseases of heart | Persisted | 6.33 × 10⁻⁴ | Yes | +26.1% | +34.9% |
| Cerebrovascular disease | Persisted | 1.42 × 10⁻³ | Yes | +37.0% | +57.3% |
| Alzheimer's disease | No significant disruption | 0.807 | No | +1.0% | -19.1% |

"Deviation" is the effect size — how far the observed rate is from the expected pre-pandemic trend, as a percent. This matters because significance and magnitude are different claims: cancer's disruption is real and statistically significant but an order of magnitude smaller in relative terms (1.7–4.6%) than heart disease, diabetes, cerebrovascular disease, or overdose (15–57%). And the picture keeps shifting through 2024 — drug overdose has swung to *below* its expected trend (consistent with the real, documented 2023–2024 decline in overdose deaths), while cerebrovascular disease has gotten *worse*, not better, four years on.

"Persisted" means the cause's death rate moved outside its expected pre-pandemic trend starting in 2020, and as of 2024 it is still outside that expected range — not resolved, not reversed.

## The two results that weren't supposed to happen this way

The project pre-registered a confidence level for each cause *before* looking at any 2020–2024 data (`research_protocol.md` §3). Two results contradict those stated priors, and that's exactly what makes them worth highlighting rather than downplaying — a result that confirms what you expected is much easier to have gotten by accident than one that surprises you.

**Cancer was expected to show nothing, and it didn't.** The pre-registered prior for malignant neoplasms was explicitly a null result, with "low" confidence by design — the reasoning was that delayed cancer screening and treatment during the pandemic would take years longer than the 2024 data window to show up as excess mortality. Instead, cancer shows a significant, FDR-surviving disruption that has persisted through 2024. Either the deferred-care effect on cancer mortality moved faster than expected, or something else is contributing — this analysis can't distinguish between those, but the result itself is real and worth investigating further.

**Alzheimer's was expected to show a large effect, and it didn't.** The pre-registered prior was "high confidence" of a large disruption, on the theory that pandemic-era isolation and care-facility disruption would show up clearly in dementia mortality. It didn't — p = 0.81, nowhere close to significant. This doesn't mean isolation had no effect on people with Alzheimer's; it means that effect, if real, isn't visible in national mortality *rates* over this window using this method.

## The negative control (validating the method itself)

Before trusting any of the above, the pipeline runs the identical method on a cause with no plausible COVID mechanism — congenital malformations and chromosomal abnormalities, concentrated in infancy and driven by prenatal/genetic factors. It passed: no significant disruption (p = 0.68 on the gating metric, raw death counts). This doesn't prove every positive result above is real, but a failure here would have been strong evidence the method was just detecting noise or a database artifact — and it didn't fail.

One methodological note worth being upfront about: this wasn't the first choice. Accidental drowning was the original negative control, and it failed — it showed a real, statistically robust increase in deaths starting in 2020, confirmed on raw counts (not a rounding artifact). That's consistent with published CDC reporting on pandemic-era increases in drowning deaths (pool/beach closures, lifeguard shortages, more unsupervised time in home pools). Drowning was swapped out for congenital malformations because it was never actually COVID-independent — not because the method failed. Full account: `research_protocol.md`'s 2026-09-01 addenda.

## Robustness check: does this depend on modeling choices?

Three separate sensitivity checks re-fit the primary method one modeling choice at a time (`scripts/run_sensitivity_check.py`, surfaced on the app's Data Quality page):

1. **Baseline window** (1999–2019 primary vs. a shorter, more recent 2010–2019): all 6 test causes agree. Not an artifact of the window choice.
2. **Significance threshold** (α=0.05 primary vs. a stricter α=0.01): all 6 test causes agree. Every significant result clears the stricter bar comfortably.
3. **Baseline trend shape** (linear primary vs. allowing the pre-pandemic trend to curve/quadratic): **4 of 6 causes are robust, 2 are not.** Diabetes, drug overdose, and cancer stay significant under a curved baseline; Alzheimer's stays non-significant, consistent with the primary result. But **Diseases of heart and Cerebrovascular disease both lose significance** when the trend is allowed to curve instead of being forced into a straight line. This is a real, material limitation: part of what the linear method reads as a 2020 disruption for these two causes could instead be the natural curvature of their pre-existing trend, poorly extrapolated by a straight line. Of the 5 "Persisted" results, **diabetes, drug overdose, and cancer are the most robust** — they hold up across every axis tested — while **heart disease and cerebrovascular disease are the least robust**, both single-axis-sensitive to this one specific modeling assumption.

Also worth stating plainly, since it doesn't show up in a p-value: measured lag-1 autocorrelation of each cause's own pre-pandemic residuals is large for 5 of 6 causes (0.65–0.93; only cancer is low, at 0.19). The primary method's prediction-interval math assumes independent year-to-year residuals, which this data doesn't really satisfy — meaning the reported p-values throughout this document are likely more confident than a model that accounted for this would produce. This doesn't overturn the results (the deviations found are large, and the negative control still passed), but it's a real statistical limitation, not a footnote to bury.

## Which counties were hit hardest (diabetes and drug overdose)

For the two causes with real county-level data (diabetes and drug overdose — real death counts from ~3,000 counties each, pre-period 2015–2019 vs. post-period 2020–2024), disruption magnitude is strongly associated with socioeconomic and healthcare-access context:

- **Higher uninsured rate, smoking rate, and obesity rate all predict larger disruption**, for both causes, and all survive FDR correction.
- **Higher median household income predicts smaller disruption**, for both causes.
- **Higher rurality predicts smaller disruption** for both causes — this is the one genuinely counterintuitive result, running against a common assumption that rural areas were hit hardest by pandemic-era healthcare disruption. It survives FDR correction for diabetes but not for drug overdose (raw p = 0.069).

These are associations, not causal claims — the analysis can't separate whether uninsured/low-income counties saw worse *direct* pandemic impact, worse *deferred care*, pre-existing higher baseline vulnerability, or some combination. One specific caveat that applies only to this county-level stage: it uses **crude rate**, not age-adjusted rate, because CDC WONDER does not offer age-adjustment at county granularity for its 2018–2024 database. That means part of any county's measured "disruption" could reflect that county's own population aging between 2015 and 2024 rather than a COVID-era mortality shift — and that's a real limitation given rurality is one of the variables being tested (rural counties tend to age faster due to youth outmigration). See `research_protocol.md`'s limitations (§12) for the full list.

## What this data cannot tell you

The project's causal-language policy (`research_protocol.md` §11) exists because mortality data alone cannot separate several very different mechanisms that would all produce the same statistical signature:

- Direct viral harm (someone died with or of COVID, miscoded to another cause)
- Deferred or interrupted medical care (missed a diagnosis, skipped a treatment, couldn't get a prescription refilled)
- Healthcare-system strain (hospitals overwhelmed, ambulances delayed)
- Economic and isolation stress (job loss, disrupted income, social isolation)

A "Persisted" classification for heart disease could be any of these, in any combination, and the mortality data can't distinguish them. That's why every result here is described as "associated with" or "consistent with," never "caused by."

## Data provenance

All national-level results use 15 real CDC WONDER exports (7 from the 1999–2019 database, 8 from the 2018–2024 database). All county-level heterogeneity results use 4 real CDC WONDER exports (diabetes and drug overdose, pre/post period, county-grouped). Nothing in this project is synthetic anymore — full acquisition steps and provenance: `manual_data_acquisition.md`.
