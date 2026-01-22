"""Output formatters for adversarial-debate results.

Supports multiple output formats for integration with various tools:
- JSON: Native format for programmatic consumption
- SARIF: Static Analysis Results Interchange Format (GitHub Code Scanning)
- HTML: Human-readable reports
- Markdown: Documentation-friendly output
"""

from .base import Formatter, FormatterConfig, OutputFormat
from .html import HTMLFormatter
from .json import JSONFormatter
from .markdown import MarkdownFormatter
from .sarif import SARIFFormatter


def get_formatter(format_type: str | OutputFormat, config: FormatterConfig | None = None) -> Formatter:
    """Get a formatter by type.

    Args:
        format_type: Format type ('json', 'sarif', 'html', 'markdown')
        config: Optional formatter configuration

    Returns:
        Configured formatter instance
    """
    if isinstance(format_type, str):
        format_type = OutputFormat(format_type.lower())

    formatters = {
        OutputFormat.JSON: JSONFormatter,
        OutputFormat.SARIF: SARIFFormatter,
        OutputFormat.HTML: HTMLFormatter,
        OutputFormat.MARKDOWN: MarkdownFormatter,
    }

    formatter_class = formatters.get(format_type)
    if formatter_class is None:
        raise ValueError(
            f"Unknown format: {format_type}. "
            f"Available: {', '.join(f.value for f in OutputFormat)}"
        )

    return formatter_class(config)


__all__ = [
    "Formatter",
    "FormatterConfig",
    "OutputFormat",
    "JSONFormatter",
    "SARIFFormatter",
    "HTMLFormatter",
    "MarkdownFormatter",
    "get_formatter",
]
