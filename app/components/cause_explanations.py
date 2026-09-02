"""Plausible-mechanism reasoning for each test cause, grounded in
published literature and hedged per research_protocol.md #11's
causal-language policy: this project's own mortality data cannot test
*why* a disruption happened, only *that* it happened. Everything here is
what the broader research literature has proposed as contributing
mechanisms elsewhere -- background context for interpreting our results,
not something this analysis itself established. Never state these as
proven causes of this project's specific findings.

Each cause's "note" field deliberately includes real countervailing
evidence, not just supportive citations -- found on a self-audit
(2026-09-01) that the initial research pass only searched for literature
explaining results already in hand, never for skepticism, contested
findings, or confounds. Diabetes and heart disease both carry a genuine
coding/attribution-confound caveat; cerebrovascular disease notes a
national partial-reversal pattern this project's own persistence finding
doesn't fully match; cancer's note was revised after finding more recent
modeling suggests the true mortality impact may be smaller than early
2020 projections, not merely delayed.
"""

CAUSE_EXPLANATIONS = {
    "Drug overdose": {
        "summary": (
            "National overdose deaths rose from about 71,000 in 2019 to 93,000 in 2020 and "
            "107,000 in 2021, with the sharpest jump in March-May 2020 as pandemic restrictions "
            "began, a timeline that lines up closely with what this project's own data shows."
        ),
        "mechanisms": [
            ("Using alone, with no one to intervene", "Isolation meant more people used drugs without anyone present who could call for help or administer naloxone if an overdose occurred, widely cited as a leading factor in the 2020-2021 spike."),
            ("A more dangerous drug supply", "Illicitly manufactured fentanyl, far more potent and unpredictable than heroin, was already driving a rising trend before 2020 and was involved in 64% of all U.S. overdose deaths in the year spanning May 2020 to April 2021, the first 12-month period to top 100,000 deaths."),
            ("Disrupted treatment access", "In-clinic methadone treatment dropped by about two-thirds and counseling by about 38% early in the pandemic, as many treatment programs required in-person visits that became harder to access."),
            ("Economic and psychological stress", "Job loss, disrupted routines, and increased mental health distress are commonly cited as amplifying substance use during the pandemic, though this is harder to measure directly than the supply and access factors above."),
        ],
        "note": (
            "One important caution from the research literature itself: some analyses suggest a "
            "meaningful share of the 2020-2021 increase was a continuation of a fentanyl-driven "
            "trend already underway since mid-to-late 2019, not something the pandemic newly "
            "created. Our own finding that overdose deaths swung to below the expected trend by "
            "2024 is consistent with the broader national decline reported for that period."
        ),
        "sources": [
            {
                "citation": "Centers for Disease Control and Prevention. Increase in Fatal Drug Overdoses Across the United States Driven by Synthetic Opioids Before and During the COVID-19 Pandemic. CDC Health Advisory CDCHAN-00438. December 17, 2020.",
                "url": "https://cdc.gov/overdose-prevention/media/pdfs/2024/03/Increase-in-fatal-drug-overdoses-across-us-driven-by-synthetic-opioids-before-and-during-COVID-19.pdf",
            },
            {
                "citation": "O'Donnell J, Tanz LJ, Gladden RM, Davis NL, Bitting J. Trends in and Characteristics of Drug Overdose Deaths Involving Illicitly Manufactured Fentanyls — United States, 2019-2020. MMWR Morb Mortal Wkly Rep. 2021;70(50):1740-1746. doi:10.15585/mmwr.mm7050e3",
                "url": "https://pmc.ncbi.nlm.nih.gov/articles/PMC8675656/",
            },
            {
                "citation": "Commonwealth Fund. The Spike in Drug Overdose Deaths During the COVID-19 Pandemic and Policy Options to Move Forward. Commonwealth Fund To the Point (blog). 2021.",
                "url": "https://www.commonwealthfund.org/blog/2021/spike-drug-overdose-deaths-during-covid-19-pandemic-and-policy-options-move-forward",
            },
            {
                "citation": "Lee H, Singh GK. Estimating the impact of the COVID-19 pandemic on rising trends in drug overdose mortality in the United States, 2018-2021. Ann Epidemiol. 2023;77:85-89. doi:10.1016/j.annepidem.2022.11.007",
                "url": "https://pmc.ncbi.nlm.nih.gov/articles/PMC9703855/",
            },
        ],
    },
    "Diabetes mellitus": {
        "summary": (
            "U.S. diabetes-related mortality rose more than 30% in the first two years of the "
            "pandemic, with roughly two-thirds of that excess attributed directly to COVID-19 "
            "infection itself and the rest to disrupted routine care."
        ),
        "mechanisms": [
            ("Direct effect of COVID-19 infection", "SARS-CoV-2 infection can worsen glycemic control and was the single largest contributor to excess diabetes-related mortality in published national estimates, accounting for roughly two-thirds of the excess."),
            ("Interrupted routine care", "Stay-at-home orders and clinic disruptions reduced outpatient visits and lab monitoring (like A1C testing), delaying detection of worsening blood sugar control."),
            ("Fear of infection at healthcare facilities", "Many people with diabetes delayed seeking care specifically because they were afraid of contracting COVID-19 in a hospital or clinic, leading to missed diagnoses and delayed treatment of complications."),
            ("Disrupted medication and supply access", "Insulin and other medication access, along with routine complication screening (eyes, kidneys, feet), was harder to maintain during periods of restricted in-person care."),
        ],
        "note": (
            "A real counterpoint worth including, not just the supportive case above: some of this "
            "excess may be a coding/attribution artifact rather than a true increase in diabetes "
            "deaths. CDC guidance during the pandemic allowed a presumptive COVID-19 underlying-cause "
            "code without lab confirmation, and research has found evidence that SARS-CoV-2 was "
            "sometimes substituted for competing causes of death on certificates, meaning some of "
            "the reported diabetes-mortality rise could reflect how deaths were coded, not only how "
            "many actually occurred. This doesn't cancel out the finding (excess mortality still "
            "shows up even in analyses designed to account for this), but it's a genuine source of "
            "uncertainty in the exact magnitude."
        ),
        "sources": [
            {
                "citation": "Lv F, Gao X, Huang AH, et al. Excess diabetes mellitus-related deaths during the COVID-19 pandemic in the United States. eClinicalMedicine. 2022;54:101671. doi:10.1016/j.eclinm.2022.101671",
                "url": "https://www.thelancet.com/journals/eclinm/article/PIIS2589-5370(22)00401-1/fulltext",
            },
            {
                "citation": "The impact of the COVID-19 pandemic on diabetes-related mortality. 2024. (Author list not independently verified against the publisher's paywalled record; cited by title/publisher only.)",
                "url": "https://www.sciencedirect.com/science/article/pii/S2666970624000404",
            },
        ],
    },
    "Diseases of heart": {
        "summary": (
            "COVID-19 infection itself can directly injure the heart, and the pandemic also "
            "disrupted the routine and emergency care that manages cardiovascular disease, two "
            "distinct pathways that likely compound each other."
        ),
        "mechanisms": [
            ("Direct viral cardiac injury", "COVID-19 can cause myocardial injury through direct viral invasion of heart muscle cells, systemic inflammation (notably elevated IL-6), and increased metabolic demand on an already-stressed heart. Myocardial injury is one of the most common complications in hospitalized COVID-19 patients."),
            ("Increased clotting risk", "COVID-19 activates the coagulation cascade and damages blood vessel linings, raising the risk of blood clots that can trigger heart attacks independent of any pre-existing heart disease."),
            ("Deferred emergency and routine care", "Fear of hospitals during pandemic surges, plus reduced capacity for elective cardiac procedures, plausibly delayed treatment for both acute cardiac events and routine management of hypertension and cholesterol."),
            ("Compounding for existing heart disease", "People with pre-existing cardiovascular disease who contracted COVID-19 faced substantially higher in-hospital mortality risk than those without it."),
        ],
        "note": (
            "One methodological correction and one real caveat, not just the supportive case above. "
            "First: this project's own sensitivity check initially found heart disease's significant "
            "disruption depended on assuming the pre-pandemic trend was a straight line, because a "
            "straight line fit across 1999-2019 was already diverging from heart disease's real "
            "(steep-decline-then-plateau) trajectory before 2020 even happened. Corrected by fitting "
            "the baseline to the most recent decade (2010-2019, still a straight line, just a shorter "
            "and more relevant window). This makes the result more confidently significant, not less "
            "(p=3.9e-5), while cutting the reported effect size from an overstated +26% to a "
            "defensible +7.8%. See the Robustness section and research_protocol.md's 2026-09-01 "
            "addendum for the full investigation. Second, a real, unresolved caveat: the broader "
            "literature itself flags attribution as a genuine confound here. A death in a cardiac "
            "patient triggered by COVID-19 infection could reasonably be coded as either heart disease "
            "or COVID-19 depending on documentation practices, and at least one review of this "
            "literature specifically described the underlying studies as \"generally poorly "
            "conducted,\" calling for better designs before drawing firm conclusions about how much "
            "of the excess is genuinely cardiovascular versus miscoded COVID."
        ),
        "sources": [
            {
                "citation": "Lee CCE, Ali K, Connell D, Mordi IR, George J, Lang EMSL, Lang CC. COVID-19-Associated Cardiovascular Complications. Diseases. 2021;9(3):47. doi:10.3390/diseases9030047",
                "url": "https://www.ncbi.nlm.nih.gov/pmc/articles/PMC8293160/",
            },
            {
                "citation": "Li S, Wang J, Yan Y, Zhang Z, Gong W, Nie S. Clinical Characterization and Possible Pathological Mechanism of Acute Myocardial Injury in COVID-19. Front Cardiovasc Med. 2022;9:862571. doi:10.3389/fcvm.2022.862571",
                "url": "https://www.ncbi.nlm.nih.gov/pmc/articles/PMC8979292/",
            },
        ],
    },
    "Cerebrovascular disease": {
        "summary": (
            "A global multi-center study found stroke hospital admissions fell 19.2% during the "
            "pandemic, at the same time COVID-19 infection itself appears to directly raise stroke "
            "risk through several biological pathways."
        ),
        "mechanisms": [
            ("Delayed emergency presentation", "A study spanning many stroke centers worldwide found hospital admissions for stroke fell 19.2% during the pandemic, with steeper drops at centers carrying the highest COVID-19 caseload; a single Hungarian tertiary center reported an even larger 29% drop in ischemic stroke admissions specifically. Quarantine and fear of infection meant some patients missed the narrow treatment window where clot-dissolving drugs and clot-retrieval procedures are effective."),
            ("Hypercoagulation from infection", "SARS-CoV-2 infection is associated with markedly elevated D-dimer levels (a clotting marker), suggesting it can trigger a hypercoagulable state that directly causes ischemic stroke."),
            ("Blood pressure effects", "The way SARS-CoV-2 interacts with the ACE2 receptor can disrupt normal blood pressure regulation, potentially elevating hemorrhagic stroke risk."),
            ("Cytokine storm", "The severe inflammatory immune response some COVID-19 patients experience is itself associated with increased acute stroke risk."),
        ],
        "note": (
            "Like heart disease, this cause's baseline was corrected from the full 1999-2019 range "
            "to a shorter, more recent 2010-2019 window, after finding the longer straight-line fit "
            "was already diverging from the real (steep-decline-then-plateau) trajectory before 2020 "
            "(research_protocol.md's 2026-09-01 addendum has the full investigation). That correction "
            "cut the reported effect size from an overstated +37% to a more defensible +8.8%. Unlike "
            "heart disease, though, this one isn't fully resolved: cerebrovascular disease is still "
            "this project's single most uncertain \"Persisted\" result. Its significance is real under "
            "the corrected baseline but doesn't fully survive an alternate curved-trend check either "
            "(p=0.096, close to but not under 0.05). See the Robustness section. One thing the "
            "correction did resolve: a CDC data brief found the U.S. stroke death rate for adults "
            "45-64 rose through 2021 but then declined through 2022, a partial reversal, and this "
            "project's own corrected numbers now tell a consistent story rather than a conflicting "
            "one. The deviation from trend eases slightly by 2024 (+6.1%, down from +8.8% in "
            "2020-21) instead of the growing gap an earlier, uncorrected baseline had shown."
        ),
        "sources": [
            {
                "citation": "Wang Z, Yang Y, Liang X, Gao B, Liu M, Li W, Chen Z, Wang Z. COVID-19 Associated Ischemic Stroke and Hemorrhagic Stroke: Incidence, Potential Pathological Mechanism, and Management. Front Neurol. 2020;11:571996. doi:10.3389/fneur.2020.571996",
                "url": "https://pmc.ncbi.nlm.nih.gov/articles/PMC7652923/",
            },
            {
                "citation": "Nogueira RG, Abdalkader M, Qureshi MM, et al. Global impact of COVID-19 on stroke care. Int J Stroke. 2021;16(5):573-584. doi:10.1177/1747493021991652",
                "url": "https://pmc.ncbi.nlm.nih.gov/articles/PMC8010375/",
            },
            {
                "citation": "Héja M, Fekete I, Márton S, Horváth L, Fekete K. Impact of COVID-19 pandemic on acute stroke care in a tertiary stroke centre. Sci Rep. 2024;14:31408. doi:10.1038/s41598-024-83016-z",
                "url": "https://www.nature.com/articles/s41598-024-83016-z",
            },
            {
                "citation": "Curtin SC. Stroke Death Rates Among Adults Ages 45-64 by Region and Race and Hispanic Origin: United States, 2002-2022. NCHS Data Brief No. 505. August 2024.",
                "url": "https://www.cdc.gov/nchs/products/databriefs/db505.htm",
            },
        ],
    },
    "Malignant neoplasms": {
        "summary": (
            "U.S. cancer screening rates fell 30-60% during pandemic lockdowns, and a modeling "
            "study using England's national cancer registry projected this kind of delay could raise "
            "breast and colorectal cancer deaths by up to 9.6% and 16.6% respectively within five "
            "years, a longer-horizon effect our 2024 data window may be catching only the earliest "
            "part of."
        ),
        "mechanisms": [
            ("Postponed screening", "Screening for colorectal, breast, prostate, cervical, and other cancers was widely postponed as hospitals redirected capacity to COVID-19 care, with studies reporting 30-60% declines in screening rates."),
            ("Later-stage diagnosis", "Delays in cancer diagnosis were significantly associated with more advanced disease stage at detection. One study found mortality risk increased measurably with just a four-week diagnostic delay."),
            ("Delayed or modified treatment", "Chemotherapy, surgery, and other time-sensitive treatments were postponed or altered for many patients during periods of hospital capacity strain."),
        ],
        "note": (
            "This project's own pre-registered prior expected NO disruption to show up within the "
            "2024 data window, reasoning that these deferred-care effects on mortality would take "
            "longer to appear. A small, real, FDR-significant effect showed up anyway, modest "
            "next to heart disease or overdose, but real. Early 2020 modeling projected large future "
            "mortality increases from screening delays, but more recent modeling using actual "
            "pandemic-era England data found lung and breast cancer deaths came in *lower* than "
            "pre-pandemic trends would have predicted, not higher. That's a genuinely important "
            "update, not just a footnote. The honest reading isn't \"this project's data window caught only "
            "the beginning of a larger effect\"; it's that the size and timing of any true screening-"
            "delay mortality impact is still unsettled in the wider literature, and this project's "
            "small, real, persisting signal should be read against that uncertainty rather than as "
            "confirmation of the largest early projections."
        ),
        "sources": [
            {
                "citation": "Maringe C, Spicer J, Morris M, Purushotham A, Nolte E, Sullivan R, Rachet B, Aggarwal A. The impact of the COVID-19 pandemic on cancer deaths due to delays in diagnosis in England, UK: a national, population-based, modelling study. Lancet Oncol. 2020;21(8):1023-1034. doi:10.1016/S1470-2045(20)30388-0",
                "url": "https://www.thelancet.com/journals/lanonc/article/PIIS1470-2045(20)30388-0/fulltext",
            },
            {
                "citation": "Arik A, Cairns AJG, Streftaris G. Cancer mortality projection: disparities, COVID-19, and late diagnosis impact. arXiv:2405.05643 [stat.AP]. 2024. doi:10.48550/arXiv.2405.05643",
                "url": "https://arxiv.org/abs/2405.05643",
            },
            {
                "citation": "Wells CR, Galvani AP. Impact of the COVID-19 pandemic on cancer incidence and mortality. Lancet Public Health. 2022;7(6):e490-e491. doi:10.1016/S2468-2667(22)00111-6",
                "url": "https://www.thelancet.com/journals/lanpub/article/PIIS2468-2667(22)00111-6/fulltext",
            },
        ],
    },
    "Alzheimer's disease": {
        "summary": (
            "Our result, no significant disruption, is genuinely surprising given the "
            "pre-registered high-confidence prior, and it may partly reflect a real limitation of "
            "how this specific analysis counts Alzheimer's deaths, not necessarily an absence of "
            "any real pandemic effect."
        ),
        "mechanisms": [
            ("A definitional gap in our own method", "This project counts a death only when Alzheimer's is coded as the sole *underlying* cause of death. Published national research that instead counts Alzheimer's and related dementias as an underlying OR contributing cause found a large excess: an estimated 94,688 excess deaths with ADRD involved in the pandemic's first year alone. Many dementia patients who died of COVID-19 likely had COVID-19, not Alzheimer's, recorded as the underlying cause, with dementia listed only as a contributing condition, invisible to our narrower query."),
            ("Isolation and care-facility disruption (the original hypothesis)", "The pre-registered reasoning was that pandemic isolation and disrupted nursing-home/care-facility routines would show up as excess Alzheimer's mortality, and broader published research confirms this was real, particularly in the pandemic's first year and especially in long-term care settings."),
            ("A pattern that faded fast", "Published research also found the excess ADRD mortality reported using the broader (underlying-or-contributing) definition declined sharply from the first pandemic year to the second, consistent with a real but short-lived effect that a 2020-2024 analysis using only 2020-2021 as its 'acute' window might partially miss if it faded unusually quickly for this specific cause."),
            ("A later decline this project did find", "Pooling all five post-2020 years instead of just the acute window turns up a real signal the acute-only test misses: Alzheimer's mortality ran increasingly below trend by 2023-2024. One plausible explanation is mortality displacement (sometimes called 'harvesting'): patients who would otherwise have died in these later years may already have died earlier in the pandemic. This project's own data can't confirm that mechanism, only the later decline itself. See the Deep dive tab for the numbers."),
        ],
        "note": (
            "This is one of this project's most important nuances: 'no significant disruption' "
            "describes what our specific method (underlying-cause-only, national rate) found for "
            "the pre-registered 2020-2021 window. It does not mean isolation and care-facility "
            "disruption had no real effect on people with Alzheimer's. Broader research using a "
            "different, more inclusive definition of how a dementia death is counted found a "
            "substantial one, and this project's own full-period check (2020-2024) finds a real, "
            "later effect too, just not the immediate one originally hypothesized."
        ),
        "sources": [
            {
                "citation": "Chen R, Charpignon ML, Raquib RV, Wang J, Meza E, Aschmann HE, DeVost MA, Mooney A, Bibbins-Domingo K, Riley AR, Kiang MV, Chen YH, Stokes AC, Glymour MM. Excess Mortality With Alzheimer Disease and Related Dementias as an Underlying or Contributing Cause During the COVID-19 Pandemic in the US. JAMA Neurol. 2023;80(9):919-928. doi:10.1001/jamaneurol.2023.2226",
                "url": "https://jamanetwork.com/journals/jamaneurology/fullarticle/2806770",
            },
            {
                "citation": "Li S, Han L, Shi H, Chong MKC, Zhao S, Ran J. Excess deaths from Alzheimer's disease and Parkinson's disease during the COVID-19 pandemic in the USA. Age Ageing. 2022;51(12):afac277. doi:10.1093/ageing/afac277",
                "url": "https://academic.oup.com/ageing/article/51/12/afac277/6936401",
            },
        ],
    },
}
