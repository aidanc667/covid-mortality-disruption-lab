"""Plausible-mechanism reasoning for each test cause, grounded in
published literature and hedged per research_protocol.md #11's
causal-language policy: this project's own mortality data cannot test
*why* a disruption happened, only *that* it happened. Everything here is
what the broader research literature has proposed as contributing
mechanisms elsewhere -- background context for interpreting our results,
not something this analysis itself established. Never state these as
proven causes of this project's specific findings.

Each cause's "note" field is a one- or two-sentence caution shown under
the explanation; it deliberately includes real countervailing
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
            "National overdose deaths rose from about 71,000 in 2019 to 92,000 in 2020 and "
            "107,000 in 2021, with the sharpest jump in March-May 2020 as pandemic restrictions "
            "began, matching the 2020–21 jump in this project's data."
        ),
        "mechanisms": [
            ("Using alone, with no one to intervene", "Isolation meant more people used drugs without anyone present who could call for help or administer naloxone if an overdose occurred, widely cited as a leading factor in the 2020-2021 spike."),
            ("A more dangerous drug supply", "Illicitly manufactured fentanyl, far more potent and unpredictable than heroin, was already driving a rising trend before 2020 and was involved in 64% of all U.S. overdose deaths in the year spanning May 2020 to April 2021, the first 12-month period to top 100,000 deaths."),
            ("Disrupted treatment access", "Many treatment programs depended on in-person visits. In a national survey of methadone patients, the share attending counseling in person fell from 83% before the pandemic to 19% in its first months, as most counseling moved to telehealth."),
            ("Economic and psychological stress", "Job loss, disrupted routines, and increased mental health distress are commonly cited as amplifying substance use during the pandemic, though this is harder to measure directly than the supply and access factors above."),
        ],
        "note": "Caution: some studies find a meaningful share of the 2020–21 rise continued a fentanyl-driven trend already underway in late 2019, rather than something the pandemic newly created.",
        "sources": [
            {
                "citation": "Brothers S, Palayew A, Simon C, Coulter A, Strichartz K, Voyles N, Vincent L. Patient experiences of methadone treatment changes during the first wave of COVID-19: a national community-driven survey. Harm Reduct J. 2023;20:31.",
                "url": "https://pmc.ncbi.nlm.nih.gov/articles/PMC9996563/",
            },
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
            "Deaths with diabetes listed anywhere on the death certificate rose more than 30% in "
            "2020 and 2021. About two-thirds of that excess also involved COVID-19; the authors "
            "suggest the rest may reflect indirect effects such as disrupted care. This project counts "
            "diabetes only as the underlying cause, so many of those COVID-involved deaths aren't in "
            "its data."
        ),
        "mechanisms": [
            ("Direct effect of COVID-19 infection", "SARS-CoV-2 infection can worsen blood sugar control, and COVID-19 was involved in about two-thirds of excess diabetes-related deaths in national estimates, though many of those deaths list COVID-19, not diabetes, as the underlying cause."),
            ("Interrupted routine care", "Stay-at-home orders and clinic disruptions reduced outpatient visits and lab monitoring (like A1C testing), delaying detection of worsening blood sugar control."),
            ("Fear of infection at healthcare facilities", "Many people with diabetes delayed seeking care specifically because they were afraid of contracting COVID-19 in a hospital or clinic, leading to missed diagnoses and delayed treatment of complications."),
            ("Disrupted medication and supply access", "Insulin and other medication access, along with routine complication screening (eyes, kidneys, feet), was harder to maintain during periods of restricted in-person care."),
        ],
        "note": "Caution: early in the pandemic, when testing was scarce, some people with diabetes who died of undiagnosed COVID-19 may have been recorded with diabetes as the underlying cause, so part of this rise may be miscoded COVID-19 deaths. How large that share is remains uncertain.",
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
        "note": "Caution: a cardiac death triggered by COVID-19 could be coded as either heart disease or COVID-19, and at least one review called the studies that try to separate the two generally poorly conducted.",
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
            "Fewer people with stroke symptoms reached hospitals during the pandemic, at the same "
            "time COVID-19 infection itself appears to directly raise stroke risk through several "
            "biological pathways."
        ),
        "mechanisms": [
            ("Delayed emergency presentation", "A study spanning many stroke centers worldwide found hospital admissions for stroke fell 19.2% during the pandemic, with steeper drops at centers carrying the highest COVID-19 caseload; a single Hungarian tertiary center reported an even larger 29% drop in ischemic stroke admissions specifically. Quarantine and fear of infection meant some patients missed the narrow treatment window where clot-dissolving drugs and clot-retrieval procedures are effective."),
            ("Hypercoagulation from infection", "SARS-CoV-2 infection is associated with markedly elevated D-dimer levels (a clotting marker), suggesting it can trigger a hypercoagulable state that directly causes ischemic stroke."),
            ("Blood pressure effects", "The way SARS-CoV-2 interacts with the ACE2 receptor can disrupt normal blood pressure regulation, potentially elevating hemorrhagic stroke risk."),
            ("Cytokine storm", "The severe inflammatory immune response some COVID-19 patients experience is itself associated with increased acute stroke risk."),
        ],
        "note": "Caution: a CDC data brief found stroke death rates for adults 45–64 rose through 2021 and then fell, a partial reversal consistent with this project's smaller 2024 gap. Stroke is also one of this project's two least certain results (see Robustness).",
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
            "U.S. cancer screening rates fell 30-60% during pandemic lockdowns. Early modeling "
            "from England projected this could raise breast and colorectal cancer deaths by up to "
            "9.6% and 16.6% within five years, though later evidence suggests the real effect is "
            "smaller (see the caution below)."
        ),
        "mechanisms": [
            ("Postponed screening", "Screening for colorectal, breast, prostate, cervical, and other cancers was widely postponed as hospitals redirected capacity to COVID-19 care, with studies reporting 30-60% declines in screening rates."),
            ("Later-stage diagnosis", "Delays in cancer diagnosis were associated with more advanced disease at detection."),
            ("Delayed or modified treatment", "Chemotherapy, surgery, and other time-sensitive treatments were postponed or altered for many patients during periods of hospital capacity strain. A review of pre-pandemic studies found that each four-week delay in starting treatment was linked to higher mortality, about 6–8% higher for surgery."),
        ],
        "note": "Caution: early 2020 models projected large increases from delayed screening, but later modeling with England's actual 2020–22 deaths found breast and lung cancer deaths close to their pre-pandemic trends. How large any screening-delay effect is remains unsettled.",
        "sources": [
            {
                "citation": "Hanna TP, et al. Mortality due to cancer treatment delay: systematic review and meta-analysis. BMJ. 2020;371:m4087. doi:10.1136/bmj.m4087",
                "url": "https://www.bmj.com/content/371/bmj.m4087",
            },
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
            "Finding no 2020–21 disruption was a surprise, given the prediction of a large effect. "
            "It may say more about how these deaths are counted than about whether the pandemic "
            "affected people with dementia."
        ),
        "mechanisms": [
            ("Many dementia deaths were recorded as COVID-19", (
                "This project counts a death only when Alzheimer's is the underlying cause. When someone "
                "with dementia died of COVID-19, COVID-19 was usually recorded as the underlying cause, "
                "with dementia listed as contributing. Studies counting both found about 94,700 excess "
                "dementia-related deaths in the pandemic's first year, in nursing homes and at home alike, "
                "and far fewer (about 21,600) in the second.")),
            ("A later decline this project did find", (
                "From 2022 on, Alzheimer's deaths ran further and further below trend (−19% by 2024). One "
                "possible explanation is mortality displacement: some people who would have died in these "
                "years died earlier in the pandemic. This project's data shows the decline but can't "
                "confirm why.")),
        ],
        "note": "Caution: \"no significant disruption\" reflects this project's method (underlying cause only, 2020–21 window). Studies that also count dementia as a contributing cause found substantial excess deaths, and this project's 2020–24 check finds a later effect.",
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
