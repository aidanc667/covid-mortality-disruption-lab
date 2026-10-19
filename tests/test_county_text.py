import pandas as pd

from app.components.county_text import county_pattern_sentences

LABELS = {"Diseases of heart": "Heart disease", "Diabetes mellitus": "Diabetes", "Drug overdose": "Drug overdose"}


def _het(rows):
    return pd.DataFrame(rows, columns=["cause", "variable", "slope", "fdr_significant"])


def test_same_direction_for_every_cause_is_summarized_as_all():
    het = _het([(c, "pct_smokers", 10.0, True) for c in LABELS])
    assert county_pattern_sentences(het, LABELS)[0] == "For all three causes, higher smoking rates went with larger disruption."


def test_mixed_directions_list_each_group_and_ignore_non_significant_slopes():
    het = _het([
        ("Diseases of heart", "pct_rural", 13.6, True),
        ("Diabetes mellitus", "pct_rural", 1.0, False),   # positive but fails FDR -> "no significant link"
        ("Drug overdose", "pct_rural", -3.2, True),
    ])
    rural = next(s for s in county_pattern_sentences(het, LABELS) if "rurality" in s)
    assert rural == (
        "Higher rurality went with larger disruption for heart disease; "
        "smaller disruption for drug overdose; no significant link for diabetes."
    )


def test_all_negative_income():
    het = _het([(c, "median_income_chr", -0.0001, True) for c in LABELS])
    income = next(s for s in county_pattern_sentences(het, LABELS) if "income" in s)
    assert income == "For all three causes, higher household income went with smaller disruption."


def test_measure_with_no_rows_reports_no_link():
    het = _het([(c, "pct_smokers", 10.0, True) for c in LABELS])
    obesity = next(s for s in county_pattern_sentences(het, LABELS) if "obesity" in s)
    assert obesity == (
        "No significant link between obesity rates and disruption for heart disease, diabetes, and drug overdose."
    )


def test_rurality_split_reading_cases():
    from app.components.county_text import rurality_split_reading
    assert rurality_split_reading(2.0, 0.01, 3.0, 0.02) == "The pattern holds in both halves."
    # Diabetes, pooled data: more rural half -5.4 (p=0.041), less rural half +4.7 (p=0.0074).
    assert rurality_split_reading(-5.4, 0.041, 4.7, 0.0074).startswith("The two halves point in opposite directions")
    # Heart disease: more rural half not significant (p=0.88), less rural half p<0.0001.
    assert rurality_split_reading(-1.7, 0.88, 23.2, 1e-6) == (
        "The overall result comes mainly from the less rural half; the other half shows no significant link."
    )
    assert rurality_split_reading(1.0, 0.3, 1.0, 0.4) == "Neither half shows a significant link on its own."



def test_split_reading_when_full_sample_is_not_significant():
    from app.components.county_text import rurality_split_reading
    assert rurality_split_reading(-1.0, 0.5, 4.0, 0.01, full_significant=False) == (
        "Only the less rural half shows a significant link; the full sample doesn't."
    )


def test_rurality_change_outcomes():
    from app.components.county_text import rurality_change, rurality_change_is_notable
    # Real cases: diabetes -3.6 (FDR) -> +1.0 (n.s.); overdose -3.9 (p=0.069) -> +2.3 (FDR).
    assert rurality_change(-3.6, True, 1.0, False) == "disappears"
    assert rurality_change(-3.9, False, 2.3, True) == "reverses"
    assert rurality_change(-3.0, True, -2.0, True) == "holds"
    assert rurality_change(2.0, True, 3.0, True) == "no earlier pattern"
    assert rurality_change_is_notable("disappears", earlier_significant=True)
    assert rurality_change_is_notable("reverses", earlier_significant=False)
    # A non-significant earlier slope that is still non-significant isn't a change worth flagging.
    assert not rurality_change_is_notable("disappears", earlier_significant=False)
    assert not rurality_change_is_notable("holds", earlier_significant=True)
