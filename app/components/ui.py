"""Small HTML building blocks for the redesigned pages. Each *_html function
is pure (returns a string and escapes every interpolated value) so it can be
unit-tested; pages hand the result to st.html. All classes are prefixed
`cmd-` and BASE_CSS styles only those classes, never Streamlit's own
internal elements, so a Streamlit upgrade can't silently break the look."""
import re
from html import escape

import streamlit as st

_HEX = re.compile(r"#[0-9A-Fa-f]{6}")

BASE_CSS = """<style>
:root {
  --cmd-text: #15212B; --cmd-muted: #5A6875; --cmd-border: #D5DCE3; --cmd-surface: #FFFFFF;
  --cmd-serif: "Source Serif 4", Georgia, serif;
  --cmd-mono: "IBM Plex Mono", ui-monospace, SFMono-Regular, monospace;
}
.cmd-eyebrow { font-family: var(--cmd-mono); font-size: 0.74rem; letter-spacing: 0.04em;
  text-transform: uppercase; color: var(--cmd-muted); }
.cmd-eyebrow b { background: var(--cmd-text); color: #fff; font-weight: 500; padding: 2px 7px;
  border-radius: 2px; margin-right: 8px; }
.cmd-subtitle { font-family: var(--cmd-serif); font-size: 1.35rem; line-height: 1.3;
  color: var(--cmd-muted); margin: 0 0 1rem; }
.cmd-question { font-size: 1.05rem; line-height: 1.6; color: var(--cmd-text); max-width: 34rem; margin: 0; }
.cmd-takeaway { font-family: var(--cmd-serif); font-size: 1.2rem; line-height: 1.45; color: var(--cmd-text);
  border-left: 3px solid #2C5D86; padding: 2px 0 2px 14px; margin: 0 0 0.5rem; max-width: 52rem; }
.cmd-chips { display: flex; flex-wrap: wrap; gap: 6px; }
.cmd-chip { display: inline-flex; align-items: center; gap: 6px; font-size: 0.8rem; font-weight: 500;
  padding: 3px 10px; background: var(--cmd-surface); border: 1px solid var(--cmd-border);
  border-radius: 3px; color: var(--cmd-text); }
.cmd-chip i { width: 7px; height: 7px; border-radius: 50%; display: inline-block; }
.cmd-strip { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 14px; }
.cmd-kpi { background: var(--cmd-surface); border: 1px solid var(--cmd-border); border-radius: 4px;
  padding: 16px 18px; }
.cmd-kpi-value { font-family: var(--cmd-mono); font-size: 1.85rem; font-weight: 500; line-height: 1.1;
  color: var(--cmd-text); font-variant-numeric: tabular-nums; overflow-wrap: anywhere; }
.cmd-kpi-unit { font-family: "IBM Plex Sans", sans-serif; font-size: 0.9rem; font-weight: 500; margin-left: 8px;
  color: var(--cmd-text); }
.cmd-kpi-value.cmd-kpi-word { font-family: var(--cmd-serif); font-size: 1.45rem; font-weight: 600; }
.cmd-kpi-caption { font-size: 0.8rem; color: var(--cmd-muted); margin-top: 8px; line-height: 1.45; }
@media (max-width: 900px) {
  .cmd-strip { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .cmd-kpi-unit { display: block; margin: 4px 0 0; }
}
.cmd-why { font-size: 1rem; line-height: 1.6; color: var(--cmd-text); margin: 0 0 10px; }
</style>"""


def inject_base_css() -> None:
    st.html(BASE_CSS)


def eyebrow_html(tag: str, text: str) -> str:
    return f'<div class="cmd-eyebrow"><b>{escape(tag)}</b>{escape(text)}</div>'


def hero_text_html(subtitle: str, question: str, question_label: str = "Research Question:") -> str:
    return (
        f'<p class="cmd-subtitle">{escape(subtitle)}</p>'
        f'<p class="cmd-question"><b>{escape(question_label)}</b> {escape(question)}</p>'
    )


def why_html(text: str) -> str:
    """Home's "Why this matters" paragraph, with a little room below it for the button."""
    return f'<p class="cmd-why"><b>Why this matters.</b> {escape(text)}</p>'


def takeaway_html(text: str) -> str:
    """The one-sentence lede under an interior page's title."""
    return f'<p class="cmd-takeaway">{escape(text)}</p>'


def cause_chips_html(chips: list[tuple[str, str]]) -> str:
    parts = []
    for label, color in chips:
        if not _HEX.fullmatch(color):
            raise ValueError(f"chip color must be #RRGGBB, got {color!r}")
        parts.append(f'<span class="cmd-chip"><i style="background:{color}"></i>{escape(label)}</span>')
    return f'<div class="cmd-chips">{"".join(parts)}</div>'


# Values longer than this are words ("Pre-registered"), not numbers; they're
# set in the serif at a smaller size so they fit the card instead of wrapping.
_MAX_NUMERIC_VALUE_LEN = 6


def metric_strip_html(items: list[tuple[str, str, str]]) -> str:
    cards = "".join(
        f'<div class="cmd-kpi"><div class="cmd-kpi-value'
        f'{" cmd-kpi-word" if len(value) > _MAX_NUMERIC_VALUE_LEN else ""}">{escape(value)}'
        f'<span class="cmd-kpi-unit">{escape(unit)}</span></div>'
        f'<div class="cmd-kpi-caption">{escape(caption)}</div></div>'
        for value, unit, caption in items
    )
    return f'<div class="cmd-strip">{cards}</div>'
