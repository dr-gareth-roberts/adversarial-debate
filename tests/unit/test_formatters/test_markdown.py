"""Tests for the Markdown formatter."""

from __future__ import annotations

from typing import Any

from adversarial_debate.formatters.markdown import MarkdownFormatter


def _render(data: dict[str, Any]) -> str:
    return MarkdownFormatter().format(data)


def test_header_and_footer_present(sample_bundle: dict[str, Any]) -> None:
    out = _render(sample_bundle)
    assert out.startswith("# 🛡️ Security Analysis Report")
    assert "adversarial-debate" in out


def test_summary_counts_findings(sample_bundle: dict[str, Any]) -> None:
    out = _render(sample_bundle)
    assert "**Total Findings:** 2" in out
    assert "| 🔴 CRITICAL | 1 |" in out
    assert "| 🟡 MEDIUM | 1 |" in out


def test_verdict_decision_rendered(sample_bundle: dict[str, Any]) -> None:
    out = _render(sample_bundle)
    assert "## Verdict" in out
    assert "🚫 BLOCK" in out
    assert "One critical SQL injection must be fixed before merge." in out


def test_findings_sorted_by_severity(sample_bundle: dict[str, Any]) -> None:
    out = _render(sample_bundle)
    assert out.index("SQL Injection in user lookup") < out.index("Unvalidated pagination input")


def test_finding_details_rendered(sample_bundle: dict[str, Any]) -> None:
    out = _render(sample_bundle)
    assert "| CWE | [CWE-89](https://cwe.mitre.org/data/definitions/89.html) |" in out
    assert "| Confidence | 95% |" in out
    assert "| Agent | ExploitAgent |" in out
    assert "**💡 Remediation:**" in out


def test_code_snippet_language_inferred_from_extension(sample_bundle: dict[str, Any]) -> None:
    out = _render(sample_bundle)
    assert "```python" in out


def test_attack_steps_render_strings_and_dicts(sample_bundle: dict[str, Any]) -> None:
    out = _render(sample_bundle)
    assert "1. Send id=1 OR 1=1" in out
    # The break finding's step is a dict with a description.
    assert "Pass a negative page size" in out


def test_empty_bundle_still_produces_report() -> None:
    out = _render({"findings": [], "verdict": {}})
    assert "# 🛡️ Security Analysis Report" in out
    assert "**Total Findings:** 0" in out
    # No verdict section when verdict is empty.
    assert "## Verdict" not in out


def test_format_findings_helper(sample_findings: list[dict[str, Any]]) -> None:
    out = MarkdownFormatter().format_findings(sample_findings)
    assert "## Findings" in out
    assert "SQL Injection in user lookup" in out
