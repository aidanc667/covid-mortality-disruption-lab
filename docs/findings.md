# Findings

**COVID Mortality Disruption Lab** — real CDC WONDER data, 1999–2024. Full methodology and pre-registered hypotheses: [`research_protocol.md`](research_protocol.md). This document summarizes what the completed analysis found; it does not repeat the methodology, only interprets the results.

## The headline

Of the 6 major causes of death tested, **5 show a statistically significant, still-unresolved deviation from their pre-pandemic trend, four years after the pandemic began.** None of the 5 have resolved back to their expected trend by 2024, and none have reversed direction. The one cause with no significant disruption — Alzheimer's disease — is itself a real, meaningful result, not a gap in the data.

| Cause | Result | p-value | Survives FDR | 2020–21 deviation | 2024 deviation |
|---|---|---|---|---|---|
| Drug overdose | Persisted | 5.98 × 10⁻⁸ | Yes | +40.9% | -4.3% |
| Diabetes mellitus | Persisted | 7.99 × 10⁻⁷ | Yes | +26.9% | +15.0% |
| Malignant neoplasms (cancer) | Persisted | 1.94 × 10⁻⁴ | Yes | +1.7% | +4.6% |
| Diseases of heart | Persisted | 3.86 × 10⁻⁵ | Yes | +7.8% | +3.0% |
| Cerebrovascular disease | Persisted | 1.69 × 10⁻³ | Yes | +8.8% | +6.1% |
| Alzheimer's disease | No significant disruption | 0.807 | No | +1.0% | -19.1% |

"Deviation" is the effect size — how far the observed rate is from the expected pre-pandemic trend, as a percent. This matters because significance and magnitude are different claims: diabetes and drug overdose show the largest disruptions (15–41%), while cancer, heart disease, and cerebrovascular disease are all real, FDR-significant, but modest by comparison (3–9%) — heart disease and cerebrovascular disease's deviations dropped substantially once their baseline was corrected (see the robustness section below and `research_protocol.md`'s 2026-09-01 baseline-correction addendum). And the picture keeps shifting through 2024 — drug overdose has swung to *below* its expected trend (consistent with the real, documented 2023–2024 decline in overdose deaths), while heart disease and cerebrovascular disease have both drifted slightly *toward* their expected trend by 2024, not away from it (a reversal of what an earlier, uncorrected baseline for these two causes had shown).

"Persisted" means the cause's death rate moved outside its expected pre-pandemic trend starting in 2020, and as of 2024 it is still outside that expected range — not resolved, not reversed.

## The two results that weren't supposed to happen this way

The project pre-registered a confidence level for each cause *before* looking at any 2020–2024 data (`research_protocol.md` §3). Two results contradict those stated priors, and that's exactly what makes them worth highlighting rather than downplaying — a result that confirms what you expected is much easier to have gotten by accident than one that surprises you.

**Cancer was expected to show nothing, and it didn't.** The pre-registered prior for malignant neoplasms was explicitly a null result, with "low" confidence by design — the reasoning was that delayed cancer screening and treatment during the pandemic would take years longer than the 2024 data window to show up as excess mortality. Instead, cancer shows a significant, FDR-surviving disruption that has persisted through 2024. Either the deferred-care effect on cancer mortality moved faster than expected, or something else is contributing — this analysis can't distinguish between those, but the result itself is real and worth investigating further. Worth being upfront about: the wider literature on this specific question is unsettled in a way that cuts against a simple "screening delays are killing more cancer patients" story — early 2020 models projected large future increases, but more recent modeling using actual pandemic-era England data found lung and breast cancer deaths came in *lower* than pre-pandemic trends would have predicted. This project's own small, real, persisting effect should be read against that uncertainty, not as confirmation of the largest early projections.

**Alzheimer's was expected to show a large effect, and it didn't.** The pre-registered prior was "high confidence" of a large disruption, on the theory that pandemic-era isolation and care-facility disruption would show up clearly in dementia mortality. It didn't — p = 0.81, nowhere close to significant. This doesn't mean isolation had no effect on people with Alzheimer's; it means that effect, if real, isn't visible in national mortality *rates* over this window using this method.

## The negative control (validating the method itself)

Before trusting any of the above, the pipeline runs the identical method on a cause with no *direct* COVID mechanism — congenital malformations and chromosomal abnormalities, concentrated in infancy and driven by prenatal/genetic factors. It passed: no significant disruption (p = 0.68 on the gating metric, raw death counts). This doesn't prove every positive result above is real, but a failure here would have been strong evidence the method was just detecting noise or a database artifact — and it didn't fail.

Two methodological notes worth being upfront about. First: this wasn't the first choice. Accidental drowning was the original negative control, and it failed — it showed a real, statistically robust increase in deaths starting in 2020, confirmed on raw counts (not a rounding artifact). That's consistent with published CDC reporting on pandemic-era increases in drowning deaths (pool/beach closures, lifeguard shortages, more unsupervised time in home pools). Drowning was swapped out for congenital malformations because it was never actually COVID-independent — not because the method failed. Second: "no plausible mechanism at all" would overstate even the replacement control — prenatal and obstetric care (routine visits, anomaly screenings) was also disrupted during the pandemic, a real if smaller and more indirect pathway than the ones behind the 6 test causes. It's meaningfully more insulated than any of them, not hermetically sealed from the pandemic. Full account: `research_protocol.md`'s 2026-09-01 addenda.

## Robustness check: does this depend on modeling choices?

**A baseline correction, found through this exact process.** Heart disease and cerebrovascular disease originally used the same 1999–2019 baseline window as the other four causes, and under that window the quadratic sensitivity check below found their significance didn't hold up. Investigating why (§12 of `research_protocol.md`, 2026-09-01 addendum) found the straight-line baseline was measurably misdescribing both causes' actual pre-pandemic trajectory — both declined steeply through the 2000s, then flattened out, and a single straight line across the full period sits well below the real, flattened values by 2019 (17.7 points off for heart disease, 5.8 off for cerebrovascular disease — found using only 1999–2019 data, with no reference to what happened after 2020). A curved baseline fits this history far better, but was rejected as the fix: extrapolated forward it predicts *rising* rates through 2024 for both causes, the well-documented failure mode of polynomial extrapolation. A shorter, more recent linear window (2010–2019) does not have that problem, matches the flattened recent trend, and is now this project's baseline for these two causes only; the other four causes are unaffected and still use 1999–2019. This does not make either result disappear — both remain significant, heart disease more so than before — but their reported deviation drops from an overstated 26–37% to a defensible 8–9%.

With that correction in place, three separate sensitivity checks re-fit the primary method one modeling choice at a time (`scripts/run_sensitivity_check.py`, surfaced on the app's Data Quality page):

1. **Baseline window**: all 6 test causes agree that a plausible alternate window doesn't change the classification (for heart disease and cerebrovascular disease, the alternate compared is now the original 1999–2019 window, since 2010–2019 is the primary).
2. **Significance threshold** (α=0.05 primary vs. a stricter α=0.01): 5 of 6 test causes agree. Cerebrovascular disease disagrees — at the stricter threshold, its individual post-acute years (2022–2024) no longer each clear a 99% interval, so the three-way classification shifts to "Resolved" even though the underlying acute-period p-value (0.0017) still clears α=0.01 on its own.
3. **Baseline trend shape** (linear vs. allowing the pre-pandemic trend to curve/quadratic), now compared on each cause's own corrected baseline: **5 of 6 causes are robust, 1 is not.** Heart disease is now fully robust to this check (p stays significant under both a straight line and a curve on its 2010–2019 window). Cerebrovascular disease is substantially improved but still not fully robust (p moves from 0.36 under the old full-range comparison to a much closer 0.096 under the corrected window — better, but still on the wrong side of 0.05). Diabetes, drug overdose, and cancer were never affected by any of this and remain the most robust of the 5 disrupted causes.

Net effect: heart disease's finding is now on solid footing across every check run. Cerebrovascular disease's finding is real and much better-supported than before the correction, but it remains this project's single most uncertain "Persisted" classification — reported as such, not smoothed over.

Also worth stating plainly, since it doesn't show up in a p-value: measured lag-1 autocorrelation of each cause's own pre-pandemic residuals is large for most causes (heart disease and cerebrovascular disease's dropped sharply after the baseline correction, from 0.92/0.93 to 0.12/0.50, since the shorter window's residuals are far less serially smooth than the full 21-year decline). The primary method's prediction-interval math assumes independent year-to-year residuals, which the remaining causes' baselines don't fully satisfy — meaning some reported p-values in this document are likely more confident than a model that accounted for this would produce. This doesn't overturn the results, but it's a real statistical limitation, not a footnote to bury.

## Which counties were hit hardest (diabetes and drug overdose)

For the two causes with real county-level data (diabetes and drug overdose — real death counts pulled for ~3,000 counties each, pre-period 2015–2019 vs. post-period 2020–2024), disruption magnitude is strongly associated with socioeconomic and healthcare-access context. Only counties with at least 2 non-suppressed years in both periods are actually usable in the regression — 926 of ~3,147 for diabetes, 641 of ~3,147 for drug overdose — which matters a lot for the rurality result specifically (see below).

- **Higher uninsured rate, smoking rate, and obesity rate all predict larger disruption**, for both causes, and all survive FDR correction.
- **Higher median household income predicts smaller disruption**, for both causes.
- **Higher rurality predicts smaller disruption** for both causes — the one genuinely counterintuitive result, running against a common assumption that rural areas were hit hardest by pandemic-era healthcare disruption. It survives FDR correction for diabetes but not for drug overdose (raw p = 0.069). **This one needs an important caveat, found on a self-audit of this project's own most surprising finding**: the counties *excluded* from the regression (too few non-suppressed years) are far more rural on average than the counties included — 77.7% rural excluded vs. 31.5% included for diabetes, 74.4% vs. 23.8% for overdose — so this result describes suburban/small-city counties much more than it describes rural America. Splitting the included counties at their own median rurality shows the two causes aren't equally trustworthy here: for **diabetes**, the relationship holds up and even strengthens among the more-rural half of the included sample (p=0.003) — for **drug overdose**, it's driven almost entirely by the less-rural half and isn't significant at all among the more-rural half (p=0.40). The overdose rurality finding should be read with real skepticism; the diabetes one, less so. Full numbers: `research_protocol.md`'s 2026-09-01 addenda, and the Geographic Heterogeneity page.

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
