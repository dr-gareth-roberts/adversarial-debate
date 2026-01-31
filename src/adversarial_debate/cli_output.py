"""CLI output helpers for adversarial-debate."""

from __future__ import annotations

import json
import sys
from typing import Any


def print_json(data: dict[str, Any]) -> None:
    """Print data as formatted JSON."""
    print(json.dumps(data, indent=2, default=str))


def print_error(message: str) -> None:
    """Print an error message to stderr."""
    print(f"Error: {message}", file=sys.stderr)
