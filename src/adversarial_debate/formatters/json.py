"""JSON output formatter."""

import json
from typing import Any

from .base import Formatter, FormatterConfig, OutputFormat


class JSONFormatter(Formatter):
    """JSON output formatter.

    Outputs results as formatted JSON for programmatic consumption.
    """

    def __init__(self, config: FormatterConfig | None = None):
        super().__init__(config)

    @property
    def format_type(self) -> OutputFormat:
        return OutputFormat.JSON

    @property
    def file_extension(self) -> str:
        return ".json"

    @property
    def content_type(self) -> str:
        return "application/json"

    def format(self, data: dict[str, Any]) -> str:
        """Format data as JSON.

        Args:
            data: Data to format

        Returns:
            JSON string
        """
        indent = 2 if self.config.pretty else None
        return json.dumps(data, indent=indent, default=str, ensure_ascii=False)
