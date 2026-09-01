# Findings

**COVID Mortality Disruption Lab** — real CDC WONDER data, 1999–2024. Full methodology and pre-registered hypotheses: [`research_protocol.md`](research_protocol.md). This document summarizes what the completed analysis found; it does not repeat the methodology, only interprets the results.

## The headline

Of the 6 major causes of death tested, **5 show a statistically significant, still-unresolved deviation from their pre-pandemic trend, four years after the pandemic began.** None of the 5 have resolved back to their expected trend by 2024, and none have reversed direction. The one cause with no significant disruption — Alzheimer's disease — is itself a real, meaningful result, not a gap in the data.

| Cause | Result | p-value | Survives FDR correction |
|---|---|---|---|
| Drug overdose | Persisted | 5.98 × 10⁻⁸ | Yes |
| Diabetes mellitus | Persisted | 7.99 × 10⁻⁷ | Yes |
| Malignant neoplasms (cancer) | Persisted | 1.94 × 10⁻⁴ | Yes |
| Diseases of heart | Persisted | 6.33 × 10⁻⁴ | Yes |
| Cerebrovascular disease | Persisted | 1.42 × 10⁻³ | Yes |
| Alzheimer's disease | No significant disruption | 0.807 | No |

"Persisted" means the cause's death rate moved outside its expected pre-pandemic trend starting in 2020, and as of 2024 it is still outside that expected range — not resolved, not reversed.

## The two results that weren't supposed to happen this way

The project pre-registered a confidence level for each cause *before* looking at any 2020–2024 data (`research_protocol.md` §3). Two results contradict those stated priors, and that's exactly what makes them worth highlighting rather than downplaying — a result that confirms what you expected is much easier to have gotten by accident than one that surprises you.

**Cancer was expected to show nothing, and it didn't.** The pre-registered prior for malignant neoplasms was explicitly a null result, with "low" confidence by design — the reasoning was that delayed cancer screening and treatment during the pandemic would take years longer than the 2024 data window to show up as excess mortality. Instead, cancer shows a significant, FDR-surviving disruption that has persisted through 2024. Either the deferred-care effect on cancer mortality moved faster than expected, or something else is contributing — this analysis can't distinguish between those, but the result itself is real and worth investigating further.

**Alzheimer's was expected to show a large effect, and it didn't.** The pre-registered prior was "high confidence" of a large disruption, on the theory that pandemic-era isolation and care-facility disruption would show up clearly in dementia mortality. It didn't — p = 0.81, nowhere close to significant. This doesn't mean isolation had no effect on people with Alzheimer's; it means that effect, if real, isn't visible in national mortality *rates* over this window using this method.

## The negative control (validating the method itself)

Before trusting any of the above, the pipeline runs the identical method on a cause with no plausible COVID mechanism — congenital malformations and chromosomal abnormalities, concentrated in infancy and driven by prenatal/genetic factors. It passed: no significant disruption (p = 0.68 on the gating metric, raw death counts). This doesn't prove every positive result above is real, but a failure here would have been strong evidence the method was just detecting noise or a database artifact — and it didn't fail.

One methodological note worth being upfront about: this wasn't the first choice. Accidental drowning was the original negative control, and it failed — it showed a real, statistically robust increase in deaths starting in 2020, confirmed on raw counts (not a rounding artifact). That's consistent with published CDC reporting on pandemic-era increases in drowning deaths (pool/beach closures, lifeguard shortages, more unsupervised time in home pools). Drowning was swapped out for congenital malformations because it was never actually COVID-independent — not because the method failed. Full account: `research_protocol.md`'s 2026-09-01 addenda.

## Robustness check

The primary method fits its "expected trend" baseline using 1999–2019 mortality data. A sensitivity analysis re-ran the identical method with a shorter, more recent baseline (2010–2019) to check whether the choice of window drives the results. **All 6 test causes classify identically under both windows** — same result, same FDR-significance, just tighter p-values under the shorter window. The results aren't an artifact of the baseline window choice. (`scripts/run_sensitivity_check.py`, surfaced on the app's Data Quality page.)

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
