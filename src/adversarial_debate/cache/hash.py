"""Content hashing utilities for cache invalidation."""

import hashlib
from pathlib import Path


def normalize_code(code: str) -> str:
    """Normalize source code for stable hashing and caching.

    This is intentionally conservative: it normalizes line endings and trims
    trailing whitespace per line so semantically-identical edits (e.g. CRLF vs
    LF, trailing spaces) do not thrash the cache.
    """
    # Normalize line endings
    normalized = code.replace("\r\n", "\n").replace("\r", "\n")
    # Trim trailing whitespace per line (idempotent)
    normalized = "\n".join(line.rstrip() for line in normalized.split("\n"))
    return normalized


def hash_content(content: str, algorithm: str = "sha256") -> str:
    """Hash string content.

    Args:
        content: String content to hash
        algorithm: Hash algorithm (default: sha256)

    Returns:
        Hex digest of the hash
    """
    h = hashlib.new(algorithm)
    h.update(content.encode("utf-8"))
    return h.hexdigest()


def hash_file(path: Path | str, algorithm: str = "sha256") -> str:
    """Hash file contents.

    Args:
        path: Path to file
        algorithm: Hash algorithm (default: sha256)

    Returns:
        Hex digest of the hash
    """
    path = Path(path)
    h = hashlib.new(algorithm)

    with open(path, "rb") as f:
        # Read in chunks for large files
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)

    return h.hexdigest()


def hash_file_content(path: Path | str, algorithm: str = "sha256") -> str:
    """Backward-compatible alias for hashing file content.

    Historically, some callers used `hash_file_content`; keep it as a thin
    wrapper to avoid unnecessary API churn.
    """
    return hash_file(path, algorithm=algorithm)


def hash_files(paths: list[Path | str], algorithm: str = "sha256") -> str:
    """Hash multiple files together.

    Creates a combined hash that changes if any file changes.

    Args:
        paths: List of file paths
        algorithm: Hash algorithm (default: sha256)

    Returns:
        Hex digest of the combined hash
    """
    h = hashlib.new(algorithm)

    # Sort paths for consistent ordering
    sorted_paths = sorted(Path(p) for p in paths)

    for path in sorted_paths:
        # Include path in hash for rename detection
        h.update(str(path).encode("utf-8"))
        h.update(b"\x00")  # Separator

        if path.exists():
            with open(path, "rb") as f:
                for chunk in iter(lambda: f.read(65536), b""):
                    h.update(chunk)
        h.update(b"\x01")  # File boundary

    return h.hexdigest()


def hash_analysis_inputs(
    code: str,
    agent_name: str,
    focus_areas: list[str] | None = None,
    config_hash: str | None = None,
) -> str:
    """Hash analysis inputs to create a cache key.

    Args:
        code: Source code being analyzed
        agent_name: Name of the agent performing analysis
        focus_areas: Optional focus areas for the analysis
        config_hash: Optional hash of the configuration

    Returns:
        Hex digest cache key
    """
    h = hashlib.sha256()

    # Include agent name
    h.update(agent_name.encode("utf-8"))
    h.update(b"\x00")

    # Include code
    h.update(code.encode("utf-8"))
    h.update(b"\x00")

    # Include focus areas (sorted for consistency)
    if focus_areas:
        for area in sorted(focus_areas):
            h.update(area.encode("utf-8"))
            h.update(b"\x00")
    h.update(b"\x01")

    # Include config hash if provided
    if config_hash:
        h.update(config_hash.encode("utf-8"))

    return h.hexdigest()
