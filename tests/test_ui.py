import pytest

from app.components.ui import (
    BASE_CSS,
    cause_chips_html,
    eyebrow_html,
    hero_text_html,
    metric_strip_html,
)


def test_every_helper_escapes_its_text():
    hostile = '<script>alert("x")</script>'
    outputs = [
        eyebrow_html(hostile, hostile),
        hero_text_html(hostile, hostile),
        cause_chips_html([(hostile, "#B3261E")]),
        metric_strip_html([(hostile, hostile, hostile)]),
    ]
    for out in outputs:
        assert "<script>" not in out
        assert "&lt;script&gt;" in out


def test_cause_chips_rejects_non_hex_color():
    # A color goes into a style attribute; anything but #RRGGBB could inject CSS.
    with pytest.raises(ValueError, match="RRGGBB"):
        cause_chips_html([("Diabetes", "red; background:url(x)")])


def test_cause_chips_renders_one_chip_per_cause_in_order():
    out = cause_chips_html([("Diabetes", "#B3261E"), ("Stroke", "#7A5C99")])
    assert out.count('class="cmd-chip"') == 2
    assert out.index("Diabetes") < out.index("Stroke")
    assert "#B3261E" in out


def test_metric_strip_renders_value_unit_caption():
    out = metric_strip_html([("926", "counties analyzed", "Diabetes; 641 for drug overdose")])
    assert out.count('class="cmd-kpi"') == 1
    for text in ("926", "counties analyzed", "Diabetes; 641 for drug overdose"):
        assert text in out


def test_base_css_only_styles_its_own_classes():
    # Guard against regressing into DataForensics-style overrides of
    # Streamlit internals, which break across Streamlit releases.
    assert "data-testid" not in BASE_CSS
    assert BASE_CSS.lstrip().startswith("<style>")


def test_metric_strip_sets_word_values_in_the_smaller_word_style():
    out = metric_strip_html([("926", "counties", "c"), ("Pre-registered", "", "c")])
    assert out.count("cmd-kpi-word") == 1
    assert out.index("cmd-kpi-word") > out.index("926")
