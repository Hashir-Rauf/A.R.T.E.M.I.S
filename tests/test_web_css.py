"""Guards on the stylesheet itself.

These exist because of a bug that cost a long debugging session and was
invisible in every way that usually catches things: the page loaded, the tests
passed, the DOM contained the right text, and the computed styles looked
plausible. Only a screenshot showed the title and the metric numbers were not
being painted at all.

The cause is that Gradio rewrites user CSS to prefix every selector with its
container class, and that rewrite drops any declaration whose value spans a
newline. A rule survives; only its value is silently emptied. For text that is
painted by clipping a gradient into the glyphs, an emptied background plus a
transparent fill means invisible text.

Both rules below are cheap, and both fail loudly the moment someone reformats
the stylesheet in the obvious, tidy-looking way that reintroduces the bug.
"""

from __future__ import annotations

import re

import pytest

pytest.importorskip("gradio", reason="Gradio is not installed")

from artemis.ui.web import CSS  # noqa: E402

# Declarations, ignoring the contents of comments.
_COMMENTS = re.compile(r"/\*.*?\*/", re.S)
_DECLARATION = re.compile(r"([a-zA-Z-]+)\s*:\s*([^;{}]*);")


def _without_comments() -> str:
    return _COMMENTS.sub("", CSS)


def test_no_declaration_value_spans_a_newline() -> None:
    """Gradio's selector rewrite empties any value that wraps a line."""
    offenders = [
        f"{prop}: {' '.join(value.split())[:60]}"
        for prop, value in _DECLARATION.findall(_without_comments())
        if "\n" in value
    ]
    assert not offenders, (
        "These declarations wrap onto a second line, and Gradio will drop their "
        "values when it prefixes the selectors. Put each value on one line:\n  "
        + "\n  ".join(offenders)
    )


def test_gradient_clipped_text_uses_the_longhand() -> None:
    """`background:` does not survive the rewrite here; `background-image:` does.

    Any rule that clips a gradient into text must therefore declare the gradient
    with the longhand, or the text renders invisible.
    """
    css = _without_comments()
    bad = []
    for match in re.finditer(r"([^{}]+)\{([^{}]*)\}", css):
        selector, body = match.group(1).strip(), match.group(2)
        if "background-clip" not in body:
            continue
        if re.search(r"(^|[;\s])background\s*:", body):
            bad.append(" ".join(selector.split()))
    assert not bad, (
        "These rules clip a gradient into text but use the `background` "
        "shorthand, whose value Gradio drops. Use `background-image` instead:\n  "
        + "\n  ".join(bad)
    )


def test_clipped_text_rules_also_set_a_transparent_fill() -> None:
    """Clipping without a transparent fill paints a solid block over the text."""
    css = _without_comments()
    for match in re.finditer(r"([^{}]+)\{([^{}]*)\}", css):
        selector, body = match.group(1).strip(), match.group(2)
        if "background-clip" not in body:
            continue
        assert "-webkit-text-fill-color" in body, (
            f"{' '.join(selector.split())} clips a background to text but never "
            "makes the fill transparent, so the gradient is hidden behind the "
            "glyph colour."
        )


def test_the_two_known_gradient_text_rules_are_present() -> None:
    """The title and the metric numbers are the rules this bug hit."""
    css = _without_comments()
    for selector in (".a-title", ".a-metric-n"):
        rule = re.search(re.escape(selector) + r"\s*\{([^}]*)\}", css)
        assert rule, f"{selector} is missing from the stylesheet"
        body = rule.group(1)
        assert "background-image" in body
        assert "background-clip" in body
        assert "-webkit-text-fill-color" in body
