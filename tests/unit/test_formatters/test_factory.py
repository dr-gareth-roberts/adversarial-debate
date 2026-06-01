"""Tests for the formatter factory (``get_formatter``)."""

from __future__ import annotations

import pytest

from adversarial_debate.formatters import (
    HTMLFormatter,
    JSONFormatter,
    MarkdownFormatter,
    OutputFormat,
    SARIFFormatter,
    get_formatter,
)
from adversarial_debate.formatters.base import FormatterConfig


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("json", JSONFormatter),
        ("sarif", SARIFFormatter),
        ("html", HTMLFormatter),
        ("markdown", MarkdownFormatter),
    ],
)
def test_get_formatter_by_string(name: str, expected: type) -> None:
    formatter = get_formatter(name)
    assert isinstance(formatter, expected)


def test_get_formatter_is_case_insensitive() -> None:
    assert isinstance(get_formatter("JSON"), JSONFormatter)
    assert isinstance(get_formatter("Sarif"), SARIFFormatter)


def test_get_formatter_by_enum() -> None:
    assert isinstance(get_formatter(OutputFormat.HTML), HTMLFormatter)


def test_get_formatter_passes_config_through() -> None:
    config = FormatterConfig(tool_name="custom-tool", tool_version="9.9.9")
    formatter = get_formatter("json", config)
    assert formatter.config.tool_name == "custom-tool"
    assert formatter.config.tool_version == "9.9.9"


def test_get_formatter_unknown_format_raises() -> None:
    with pytest.raises(ValueError, match="Unknown format|not a valid"):
        get_formatter("yaml")


def test_formatter_metadata_properties_are_consistent() -> None:
    expected = {
        OutputFormat.JSON: (".json", "application/json"),
        OutputFormat.SARIF: (".sarif", "application/sarif+json"),
        OutputFormat.HTML: (".html", "text/html"),
        OutputFormat.MARKDOWN: (".md", "text/markdown"),
    }
    for fmt, (ext, content_type) in expected.items():
        formatter = get_formatter(fmt)
        assert formatter.format_type == fmt
        assert formatter.file_extension == ext
        assert formatter.content_type == content_type
