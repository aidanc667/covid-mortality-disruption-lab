"""Plain-language summary of the county regressions across causes, built
from heterogeneity_summary so the app, the PDF, and the docs can't drift
from the results. No Streamlit imports: scripts/generate_report.py uses it too."""
import pandas as pd

# How each county measure reads in a sentence, in the order they're reported.
PLAIN_VARIABLES = {
    "pct_smokers": "smoking rates",
    "pct_uninsured_chr": "uninsured rates",
    "pct_obese": "obesity rates",
    "median_income_chr": "household income",
    "pct_rural": "rurality",
}

_NUMBER_WORDS = ["zero", "one", "two", "three", "four", "five", "six"]


def _join(items: list[str]) -> str:
    if len(items) <= 2:
        return " and ".join(items)
    return ", ".join(items[:-1]) + ", and " + items[-1]


def _in_sentence(name: str) -> str:
    return name if name.startswith("Alzheimer") else name[0].lower() + name[1:]


def county_pattern_sentences(het: pd.DataFrame, labels: dict[str, str]) -> list[str]:
    """One sentence per county measure, counting only FDR-significant
    associations. `het` needs cause, variable, slope and fdr_significant;
    `labels` maps each cause to its display name and fixes which causes and
    in what order they're listed."""
    causes = [c for c in labels if c in set(het["cause"])]
    n_word = _NUMBER_WORDS[len(causes)] if len(causes) < len(_NUMBER_WORDS) else str(len(causes))
    sentences = []
    for variable, phrase in PLAIN_VARIABLES.items():
        rows = het[het["variable"] == variable].set_index("cause")
        larger = [c for c in causes if c in rows.index and rows.loc[c, "fdr_significant"] and rows.loc[c, "slope"] > 0]
        smaller = [c for c in causes if c in rows.index and rows.loc[c, "fdr_significant"] and rows.loc[c, "slope"] < 0]
        neither = [c for c in causes if c not in larger and c not in smaller]

        def names(cs: list[str]) -> str:
            return _join([_in_sentence(labels[c]) for c in cs])

        if len(larger) == len(causes):
            sentences.append(f"For all {n_word} causes, higher {phrase} went with larger disruption.")
        elif len(smaller) == len(causes):
            sentences.append(f"For all {n_word} causes, higher {phrase} went with smaller disruption.")
        elif not larger and not smaller:
            sentences.append(f"No significant link between {phrase} and disruption for {names(neither)}.")
        else:
            parts = []
            if larger:
                parts.append(f"larger disruption for {names(larger)}")
            if smaller:
                parts.append(f"smaller disruption for {names(smaller)}")
            if neither:
                parts.append(f"no significant link for {names(neither)}")
            sentences.append(f"Higher {phrase} went with " + "; ".join(parts) + ".")
    return sentences


def rurality_split_reading(upper_slope: float, upper_p: float, lower_slope: float, lower_p: float,
                           alpha: float = 0.05) -> str:
    """How to read the rurality slope when the included counties are split at
    their median rurality (upper = more rural half, lower = less rural half)."""
    upper_sig, lower_sig = upper_p < alpha, lower_p < alpha
    if upper_sig and lower_sig and (upper_slope > 0) == (lower_slope > 0):
        return "The pattern holds in both halves."
    if upper_sig and lower_sig:
        return "The two halves point in opposite directions, so the overall rurality result isn't one simple pattern."
    if upper_sig or lower_sig:
        return (f"The overall result comes mainly from the {'more' if upper_sig else 'less'} rural half; "
                "the other half shows no significant link.")
    return "Neither half shows a significant link on its own."
