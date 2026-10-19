"""The Findings page's one-sentence takeaway, built from the results rather
than typed in, so it can't drift from chart B. No Streamlit calls here."""
import pandas as pd

_NUMBER_WORDS = ["zero", "one", "two", "three", "four", "five", "six"]


def _number(n: int) -> str:
    return _NUMBER_WORDS[n] if 0 <= n < len(_NUMBER_WORDS) else str(n)


def _in_sentence(name: str) -> str:
    """Lowercase a display name for mid-sentence use, except proper nouns."""
    return name if name.startswith("Alzheimer") else name[0].lower() + name[1:]


def _join(items: list[str]) -> str:
    if len(items) <= 2:
        return " and ".join(items)
    return ", ".join(items[:-1]) + ", and " + items[-1]


def _pct(value: float) -> str:
    return f"{value:+.0f}%".replace("-", "−")


def findings_takeaway(summary: pd.DataFrame, deviations: pd.DataFrame, labels: dict[str, str]) -> str:
    """`summary` needs cause, persistence_class and acute_pct_deviation;
    `deviations` needs cause, year, deviation, expected and significant.
    `labels` maps each test cause to its display name and fixes the set of
    causes considered.

    Counts a cause as off trend in the latest year in either direction, so a
    cause significantly *below* trend (Alzheimer's in 2024) is reported, not
    silently dropped."""
    causes = list(labels)
    summary = summary.set_index("cause").loc[causes]
    latest_year = int(deviations["year"].max())
    latest = deviations[deviations["year"] == latest_year].set_index("cause").loc[causes]
    pct = latest["deviation"] / latest["expected"] * 100

    disrupted = [c for c in causes if summary.loc[c, "persistence_class"] != "No significant disruption"]
    all_rose = all(summary.loc[c, "acute_pct_deviation"] > 0 for c in disrupted)
    verb = "rose significantly above" if all_rose else "moved significantly off"
    first = (
        f"{_number(len(disrupted)).capitalize()} of {_number(len(causes))} causes {verb} their "
        f"pre-pandemic trend in 2020–21."
    )

    off = [c for c in causes if latest.loc[c, "significant"]]
    above = [f"{_in_sentence(labels[c])} ({_pct(pct[c])})" for c in off if pct[c] > 0]
    below = [f"{_in_sentence(labels[c])} ({_pct(pct[c])})" for c in off if pct[c] < 0]
    if not off:
        second = f"By {latest_year}, none remained significantly off trend."
    else:
        parts = []
        if above:
            parts.append(f"{_join(above)} above it")
        if below:
            parts.append(f"{_join(below)} below it")
        second = (
            f"By {latest_year}, {_number(len(off))} {'was' if len(off) == 1 else 'were'} significantly off trend: "
            + ", and ".join(parts) + "."
        )

    back = [c for c in disrupted if not latest.loc[c, "significant"]]
    third = ""
    if back:
        names = [_in_sentence(labels[c]) for c in back]
        names[0] = names[0][0].upper() + names[0][1:]
        third = f" {_join(names)} {'was' if len(back) == 1 else 'were'} back within {'its' if len(back) == 1 else 'their'} normal range."

    return f"{first} {second}{third}"
