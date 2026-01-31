"""Helpers for consistent path filtering in CLI and watch mode."""

from __future__ import annotations

from fnmatch import fnmatch
from pathlib import Path

DEFAULT_IGNORE_PATTERNS: list[str] = [
    "__pycache__/*",
    "*.pyc",
    ".git/*",
    ".adversarial-cache/*",
    "*.egg-info/*",
    ".tox/*",
    ".pytest_cache/*",
    "node_modules/*",
    "venv/*",
    ".venv/*",
]


def path_matches_any(path: Path, patterns: list[str]) -> bool:
    """Return True if path matches any pattern (supports nested subpaths)."""
    posix_path = path.as_posix()
    for pattern in patterns:
        if fnmatch(posix_path, pattern) or fnmatch(path.name, pattern):
            return True
        parts = path.parts
        for idx in range(len(parts)):
            subpath = "/".join(parts[idx:])
            if fnmatch(subpath, pattern):
                return True
    return False
