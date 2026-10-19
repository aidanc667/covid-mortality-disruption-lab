"""Latest-year status under each cause's primary baseline window and the
other window (research_protocol.md, 2026-10-19 reversal addendum).

The primary 2020-21 test already has a baseline-window sensitivity check
(scripts/run_sensitivity_check.py). This covers the latest year's status
(above / below / within the 95% prediction interval), which turned out to
be more sensitive: a straight line fit to 1999-2019 vs. 2010-2019 can
disagree by several percent five years out.
"""
from __future__ import annotations

import pandas as pd

from src.analysis.excess_mortality import compute_deviations, fit_baseline_trend


def _status(dev) -> str:
    if not dev.significant:
        return "within"
    return "above" if dev.deviation > 0 else "below"


def latest_year_window_check(
    series: pd.DataFrame,
    causes: list[str],
    primary_start: dict[str, int],
    windows: tuple[int, int] = (1999, 2010),
    value_col: str = "age_adjusted_rate",
    baseline_end: int = 2019,
) -> pd.DataFrame:
    """`series` needs cause, year, and `value_col`. For each cause, fits a
    straight line on [start, baseline_end] for its primary start year and for
    the other one in `windows`, and reports the latest year's percent gap and
    status under each. `baseline_sensitive` is True when the two statuses differ."""
    rows = []
    latest_year = int(series["year"].max())
    for cause in causes:
        s = series[series["cause"] == cause].sort_values("year")
        primary = primary_start.get(cause, windows[0])
        alternate = windows[1] if primary == windows[0] else windows[0]
        result = {"cause": cause, "latest_year": latest_year}
        for label, start in (("primary", primary), ("alt", alternate)):
            base = s[(s["year"] >= start) & (s["year"] <= baseline_end)]
            trend = fit_baseline_trend(base["year"].to_numpy(), base[value_col].to_numpy())
            last = s[s["year"] == latest_year]
            (dev,) = compute_deviations(trend, last["year"].to_numpy(), last[value_col].to_numpy())
            result[f"{label}_window"] = f"{start}-{baseline_end}"
            result[f"{label}_pct"] = dev.deviation / dev.expected * 100
            result[f"{label}_status"] = _status(dev)
        result["baseline_sensitive"] = result["primary_status"] != result["alt_status"]
        rows.append(result)
    return pd.DataFrame(rows)
