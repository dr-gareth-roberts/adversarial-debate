"""Base formatter abstraction."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class OutputFormat(str, Enum):
    """Supported output formats."""

    JSON = "json"
    SARIF = "sarif"
    HTML = "html"
    MARKDOWN = "markdown"


@dataclass
class FormatterConfig:
    """Configuration for output formatters."""

    pretty: bool = True
    include_metadata: bool = True
    include_raw_findings: bool = False
    tool_name: str = "adversarial-debate"
    tool_version: str = "0.1.0"
    extra: dict[str, Any] = field(default_factory=dict)


class Formatter(ABC):
    """Abstract base class for output formatters."""

    def __init__(self, config: FormatterConfig | None = None):
        self.config = config or FormatterConfig()

    @property
    @abstractmethod
    def format_type(self) -> OutputFormat:
        """The output format type."""
        ...

    @property
    @abstractmethod
    def file_extension(self) -> str:
        """File extension for this format (e.g., '.json', '.sarif')."""
        ...

    @property
    @abstractmethod
    def content_type(self) -> str:
        """MIME content type for this format."""
        ...

    @abstractmethod
    def format(self, data: dict[str, Any]) -> str:
        """Format the data for output.

        Args:
            data: Analysis results (findings, verdict, etc.)

        Returns:
            Formatted string output
        """
        ...

    def format_findings(self, findings: list[dict[str, Any]]) -> str:
        """Format a list of findings.

        Args:
            findings: List of finding dictionaries

        Returns:
            Formatted string output
        """
        return self.format({"findings": findings})

    def format_verdict(self, verdict: dict[str, Any]) -> str:
        """Format an arbiter verdict.

        Args:
            verdict: Verdict dictionary

        Returns:
            Formatted string output
        """
        return self.format({"verdict": verdict})
