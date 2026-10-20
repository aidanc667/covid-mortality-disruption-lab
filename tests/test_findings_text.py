import pandas as pd

from app.components.findings_text import findings_takeaway, trend_vs_reference_note

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


# --- trend_vs_reference_note: "above trend" is not "above 2019" ---

NOTE_LABELS = {"A": "Diabetes", "B": "Cancer", "C": "Drug overdose", "D": "Heart disease"}


def _note_inputs(rates_2019, rates_2024, significant, deviation_sign):
    series = pd.DataFrame({
        "cause": list(NOTE_LABELS) * 2,
        "year": [2019] * 4 + [2024] * 4,
        "age_adjusted_rate": rates_2019 + rates_2024,
    })
    deviations = pd.DataFrame({
        "cause": list(NOTE_LABELS), "year": [2024] * 4,
        "deviation": deviation_sign, "expected": [1.0] * 4, "significant": significant,
    })
    return series, deviations


def test_note_explains_each_case_against_the_2019_rate():
    # A: above trend, 2024 within 3% of 2019 -> "back at its 2019 level".
    # B: above trend, 2024 well below 2019 -> "kept falling, more slowly".
    # C: within range, 2024 ~7% above 2019 -> "still 7% above".
    # D: within range and below 2019 -> not mentioned.
    series, deviations = _note_inputs(
        rates_2019=[21.6, 146.2, 21.6, 161.5], rates_2024=[21.7, 139.4, 23.1, 157.6],
        significant=[True, True, False, False], deviation_sign=[2.8, 6.1, -1.0, 4.6],
    )
    assert trend_vs_reference_note(series, deviations, NOTE_LABELS) == (
        "\"Trend\" means where each cause's pre-2020 trend line pointed, not its 2019 level. "
        "Diabetes's 2024 rate was back at its 2019 level (21.7 vs. 21.6); it reads as above trend "
        "because its trend line was still falling. Cancer kept falling (146.2 in 2019, 139.4 in 2024), "
        "just more slowly than its trend. Drug overdose is back within its normal range but still 7% "
        "above its 2019 rate."
    )


def test_note_is_empty_when_nothing_needs_explaining():
    series, deviations = _note_inputs(
        rates_2019=[21.6, 146.2, 21.6, 161.5], rates_2024=[21.0, 140.0, 20.0, 150.0],
        significant=[False, False, False, False], deviation_sign=[1.0, 1.0, -1.0, 1.0],
    )
    assert trend_vs_reference_note(series, deviations, NOTE_LABELS) == ""
