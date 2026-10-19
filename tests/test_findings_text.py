import pandas as pd

from app.components.findings_text import findings_takeaway

LABELS = {
    "Diseases of heart": "Heart disease",
    "Diabetes mellitus": "Diabetes",
    "Alzheimer's disease": "Alzheimer's disease",
    "Drug overdose": "Drug overdose",
}


def _summary(classes=None, acute=None):
    return pd.DataFrame({
        "cause": list(LABELS),
        "persistence_class": classes or ["Persisted", "Persisted", "No significant disruption", "Persisted"],
        "acute_pct_deviation": acute or [7.8, 26.9, 1.0, 40.9],
    })


def _deviations(significant=(False, True, True, False)):
    # 2024 gaps: heart +3%, diabetes +15%, Alzheimer's -19%, overdose -4%. A 2023 row is
    # included to check that only the latest year is used.
    return pd.DataFrame({
        "cause": [*LABELS, "Diabetes mellitus"],
        "year": [2024, 2024, 2024, 2024, 2023],
        "expected": [100.0, 20.0, 100.0, 25.0, 20.0],
        "deviation": [3.0, 3.0, -19.0, -1.0, 9.0],
        "significant": [*significant, True],
    })


def test_reports_causes_above_and_below_trend_and_those_back_in_range():
    text = findings_takeaway(_summary(), _deviations(), LABELS)
    assert text == (
        "Three of four causes rose significantly above their pre-pandemic trend in 2020–21. "
        "By 2024, two were significantly off trend: diabetes (+15%) above it, and "
        "Alzheimer's disease (−19%) below it. "
        "Heart disease and drug overdose were back within their normal range."
    )


def test_a_cause_significantly_below_trend_is_not_dropped():
    # The bug this replaces: only "still significantly above" causes were named.
    text = findings_takeaway(_summary(), _deviations(), LABELS)
    assert "Alzheimer's disease (−19%) below it" in text


def test_none_off_trend_in_latest_year():
    text = findings_takeaway(_summary(), _deviations(significant=(False, False, False, False)), LABELS)
    assert "By 2024, none remained significantly off trend." in text
    assert "Heart disease, diabetes, and drug overdose were back within their normal range." in text


def test_mixed_direction_acute_disruptions_use_neutral_verb():
    text = findings_takeaway(_summary(acute=[7.8, -26.9, 1.0, 40.9]), _deviations(), LABELS)
    assert text.startswith("Three of four causes moved significantly off their pre-pandemic trend")


def test_baseline_sensitive_causes_are_flagged_after_the_takeaway():
    text = findings_takeaway(_summary(), _deviations(), LABELS,
                             baseline_sensitive=["Diabetes mellitus", "Drug overdose"])
    assert text.endswith(
        " The 2024 results for diabetes and drug overdose depend on which baseline window is used (see Robustness)."
    )


def test_no_flag_sentence_when_nothing_is_baseline_sensitive():
    text = findings_takeaway(_summary(), _deviations(), LABELS, baseline_sensitive=[])
    assert "baseline window" not in text
