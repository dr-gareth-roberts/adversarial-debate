"""File-based cache storage for analysis results."""

import contextlib
import json
import os
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any


@dataclass
class CacheEntry:
    """A cached analysis result."""

    key: str
    agent_name: str
    file_path: str
    content_hash: str
    result: dict[str, Any]
    created_at: str
    expires_at: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def is_expired(self) -> bool:
        """Check if this cache entry has expired."""
        if not self.expires_at:
            return False
        expires = datetime.fromisoformat(self.expires_at)
        return datetime.now(UTC) > expires

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "key": self.key,
            "agent_name": self.agent_name,
            "file_path": self.file_path,
            "content_hash": self.content_hash,
            "result": self.result,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CacheEntry":
        """Create from dictionary."""
        return cls(
            key=data["key"],
            agent_name=data["agent_name"],
            file_path=data["file_path"],
            content_hash=data["content_hash"],
            result=data["result"],
            created_at=data["created_at"],
            expires_at=data.get("expires_at"),
            metadata=data.get("metadata", {}),
        )


class FileCache:
    """File-based cache for analysis results.

    Stores cache entries as individual JSON files in a cache directory.
    Supports TTL-based expiration and content-hash-based invalidation.
    """

    DEFAULT_CACHE_DIR = ".adversarial-cache"
    DEFAULT_TTL_HOURS = 24 * 7  # 1 week

    def __init__(
        self,
        cache_dir: Path | str | None = None,
        ttl_hours: float | None = None,
    ):
        """Initialize the file cache.

        Args:
            cache_dir: Directory for cache files (default: .adversarial-cache)
            ttl_hours: Time-to-live in hours (default: 168 hours / 1 week)
        """
        self.cache_dir = Path(cache_dir or self.DEFAULT_CACHE_DIR)
        self.ttl = timedelta(hours=ttl_hours or self.DEFAULT_TTL_HOURS)
        self._ensure_cache_dir()

    def _ensure_cache_dir(self) -> None:
        """Create cache directory if it doesn't exist."""
        secure_dir_mode = 0o700
        secure_file_mode = 0o600

        self.cache_dir.mkdir(parents=True, exist_ok=True, mode=secure_dir_mode)
        with contextlib.suppress(OSError):
            os.chmod(self.cache_dir, secure_dir_mode)

        # Add .gitignore to prevent committing cache
        gitignore = self.cache_dir / ".gitignore"
        if not gitignore.exists():
            try:
                fd = os.open(
                    str(gitignore),
                    os.O_CREAT | os.O_EXCL | os.O_WRONLY,
                    secure_file_mode,
                )
            except FileExistsError:
                pass
            else:
                with os.fdopen(fd, "w", encoding="utf-8") as f:
                    f.write("*\n!.gitignore\n")
                with contextlib.suppress(OSError):
                    os.chmod(gitignore, secure_file_mode)

    def _key_to_path(self, key: str) -> Path:
        """Convert a cache key to a file path."""
        # Use first 2 chars as subdirectory for better file distribution
        subdir = key[:2] if len(key) >= 2 else "00"
        return self.cache_dir / subdir / f"{key}.json"

    def get(self, key: str) -> CacheEntry | None:
        """Get a cache entry by key.

        Args:
            key: Cache key

        Returns:
            CacheEntry if found and valid, None otherwise
        """
        path = self._key_to_path(key)
        if not path.exists():
            return None

        try:
            with open(path) as f:
                data = json.load(f)
            entry = CacheEntry.from_dict(data)

            # Check expiration
            if entry.is_expired():
                self.delete(key)
                return None

            return entry
        except (json.JSONDecodeError, KeyError, OSError):
            # Invalid cache entry, remove it
            self.delete(key)
            return None

    def set(
        self,
        key: str,
        agent_name: str,
        file_path: str,
        content_hash: str,
        result: dict[str, Any],
        metadata: dict[str, Any] | None = None,
    ) -> CacheEntry:
        """Store a cache entry.

        Args:
            key: Cache key
            agent_name: Name of the agent that produced the result
            file_path: Path to the analyzed file
            content_hash: Hash of the analyzed content
            result: Analysis result to cache
            metadata: Optional additional metadata

        Returns:
            The created CacheEntry
        """
        now = datetime.now(UTC)
        entry = CacheEntry(
            key=key,
            agent_name=agent_name,
            file_path=file_path,
            content_hash=content_hash,
            result=result,
            created_at=now.isoformat(),
            expires_at=(now + self.ttl).isoformat(),
            metadata=metadata or {},
        )

        path = self._key_to_path(key)
        secure_dir_mode = 0o700
        secure_file_mode = 0o600
        path.parent.mkdir(parents=True, exist_ok=True, mode=secure_dir_mode)
        with contextlib.suppress(OSError):
            os.chmod(path.parent, secure_dir_mode)

        fd = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, secure_file_mode)
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(entry.to_dict(), f, indent=2, default=str)
        with contextlib.suppress(OSError):
            os.chmod(path, secure_file_mode)

        return entry

    def delete(self, key: str) -> bool:
        """Delete a cache entry.

        Args:
            key: Cache key

        Returns:
            True if entry was deleted, False if not found
        """
        path = self._key_to_path(key)
        if path.exists():
            path.unlink()
            return True
        return False

    def clear(self) -> int:
        """Clear all cache entries.

        Returns:
            Number of entries deleted
        """
        count = 0
        for path in self.cache_dir.rglob("*.json"):
            path.unlink()
            count += 1
        return count

    def cleanup_expired(self) -> int:
        """Remove expired cache entries.

        Returns:
            Number of entries removed
        """
        count = 0
        for path in self.cache_dir.rglob("*.json"):
            try:
                with open(path) as f:
                    data = json.load(f)
                entry = CacheEntry.from_dict(data)
                if entry.is_expired():
                    path.unlink()
                    count += 1
            except (json.JSONDecodeError, KeyError, OSError):
                # Invalid entry, remove it
                path.unlink()
                count += 1
        return count

    def stats(self) -> dict[str, Any]:
        """Get cache statistics.

        Returns:
            Dictionary with cache statistics
        """
        total = 0
        expired = 0
        total_size = 0
        by_agent: dict[str, int] = {}

        for path in self.cache_dir.rglob("*.json"):
            total += 1
            total_size += path.stat().st_size

            try:
                with open(path) as f:
                    data = json.load(f)
                entry = CacheEntry.from_dict(data)

                agent = entry.agent_name
                by_agent[agent] = by_agent.get(agent, 0) + 1

                if entry.is_expired():
                    expired += 1
            except (json.JSONDecodeError, KeyError, OSError):
                expired += 1

        return {
            "total_entries": total,
            "expired_entries": expired,
            "valid_entries": total - expired,
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "by_agent": by_agent,
            "cache_dir": str(self.cache_dir),
        }
