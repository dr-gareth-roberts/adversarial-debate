"""Tests for the JSON formatter."""

from __future__ import annotations

import json
from typing import Any

from adversarial_debate.formatters.base import FormatterConfig
from adversarial_debate.formatters.json import JSONFormatter


def test_format_round_trips_bundle(sample_bundle: dict[str, Any]) -> None:
    output = JSONFormatter().format(sample_bundle)
    parsed = json.loads(output)
    assert parsed == sample_bundle


def test_pretty_output_is_indented(sample_bundle: dict[str, Any]) -> None:
    output = JSONFormatter(FormatterConfig(pretty=True)).format(sample_bundle)
    assert "\n  " in output


def test_compact_output_has_no_indentation(sample_bundle: dict[str, Any]) -> None:
    output = JSONFormatter(FormatterConfig(pretty=False)).format(sample_bundle)
    assert "\n" not in output


def test_non_serialisable_values_fall_back_to_str() -> None:
    class Opaque:
        def __str__(self) -> str:
            return "opaque-value"

    output = JSONFormatter().format({"value": Opaque()})
    assert json.loads(output) == {"value": "opaque-value"}


def test_unicode_is_preserved_not_escaped() -> None:
    output = JSONFormatter().format({"title": "SQL Injection — crítico"})
    assert "crítico" in output
    assert "\\u" not in output


def test_format_findings_helper_wraps_list(sample_findings: list[dict[str, Any]]) -> None:
    output = JSONFormatter().format_findings(sample_findings)
    assert json.loads(output) == {"findings": sample_findings}


def test_format_verdict_helper_wraps_dict(sample_verdict: dict[str, Any]) -> None:
    output = JSONFormatter().format_verdict(sample_verdict)
    assert json.loads(output) == {"verdict": sample_verdict}
