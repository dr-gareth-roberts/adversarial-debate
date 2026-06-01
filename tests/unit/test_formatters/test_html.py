"""Tests for the HTML formatter."""

from __future__ import annotations

from html.parser import HTMLParser
from typing import Any

from adversarial_debate.formatters.html import HTMLFormatter


class _WellFormedChecker(HTMLParser):
    """Minimal well-formedness check: every non-void tag is closed in order."""

    VOID = {"meta", "br", "hr", "img", "input", "link"}

    def __init__(self) -> None:
        super().__init__()
        self.stack: list[str] = []
        self.balanced = True

    def handle_starttag(self, tag: str, attrs: Any) -> None:
        if tag not in self.VOID:
            self.stack.append(tag)

    def handle_endtag(self, tag: str) -> None:
        if tag in self.VOID:
            return
        if not self.stack or self.stack[-1] != tag:
            self.balanced = False
        else:
            self.stack.pop()


def _render(data: dict[str, Any]) -> str:
    return HTMLFormatter().format(data)


def test_document_is_well_formed(sample_bundle: dict[str, Any]) -> None:
    out = _render(sample_bundle)
    checker = _WellFormedChecker()
    checker.feed(out)
    assert checker.balanced, "unbalanced HTML tags"
    assert not checker.stack, f"unclosed tags: {checker.stack}"


def test_doctype_and_title(sample_bundle: dict[str, Any]) -> None:
    out = _render(sample_bundle)
    assert out.lstrip().startswith("<!DOCTYPE html>")
    assert "<title>Security Analysis Report" in out


def test_findings_and_verdict_sections_present(sample_bundle: dict[str, Any]) -> None:
    out = _render(sample_bundle)
    assert 'id="summary"' in out
    assert 'id="verdict"' in out
    assert 'id="findings"' in out
    assert "BLOCK" in out


def test_html_special_characters_are_escaped() -> None:
    data = {
        "findings": [
            {
                "title": "XSS <script>alert(1)</script>",
                "severity": "HIGH",
                "description": "Reflected & dangerous",
                "file_path": "a.py",
            }
        ],
        "verdict": {},
    }
    out = _render(data)
    assert "<script>alert(1)</script>" not in out
    assert "&lt;script&gt;" in out
    assert "Reflected &amp; dangerous" in out


def test_severity_count_reflected_in_summary(sample_bundle: dict[str, Any]) -> None:
    out = _render(sample_bundle)
    # Total findings stat value.
    assert ">2</div>" in out
    assert ">CRITICAL</div>" in out


def test_empty_bundle_renders_minimal_document() -> None:
    out = _render({"findings": [], "verdict": {}})
    assert "<!DOCTYPE html>" in out
    assert 'id="findings"' not in out
    assert 'id="verdict"' not in out
