"""Cache manager for incremental analysis."""

from pathlib import Path
from typing import Any

from .file_cache import CacheEntry, FileCache
from .hash import hash_analysis_inputs, hash_content


class CacheManager:
    """Manages caching for incremental analysis.

    Provides high-level operations for checking cache validity,
    storing results, and computing cache keys.
    """

    def __init__(
        self,
        cache_dir: Path | str | None = None,
        ttl_hours: float | None = None,
        enabled: bool = True,
    ):
        """Initialize the cache manager.

        Args:
            cache_dir: Directory for cache files
            ttl_hours: Time-to-live for cache entries
            enabled: Whether caching is enabled
        """
        self.enabled = enabled
        self._cache = FileCache(cache_dir, ttl_hours) if enabled else None

    @property
    def cache(self) -> FileCache | None:
        """Get the underlying file cache."""
        return self._cache

    def is_cached(
        self,
        code: str,
        agent_name: str,
        focus_areas: list[str] | None = None,
    ) -> bool:
        """Check if analysis results are cached.

        Args:
            code: Source code to analyze
            agent_name: Name of the agent
            focus_areas: Optional focus areas

        Returns:
            True if valid cache entry exists
        """
        if not self.enabled or not self._cache:
            return False

        key = self._compute_key(code, agent_name, focus_areas)
        content_hash = hash_content(code)

        entry = self._cache.get(key)
        if entry is None:
            return False

        # Verify content hash matches
        return entry.content_hash == content_hash

    def get_cached(
        self,
        code: str,
        agent_name: str,
        focus_areas: list[str] | None = None,
    ) -> dict[str, Any] | None:
        """Get cached analysis results.

        Args:
            code: Source code to analyze
            agent_name: Name of the agent
            focus_areas: Optional focus areas

        Returns:
            Cached result if valid, None otherwise
        """
        if not self.enabled or not self._cache:
            return None

        key = self._compute_key(code, agent_name, focus_areas)
        content_hash = hash_content(code)

        entry = self._cache.get(key)
        if entry is None:
            return None

        # Verify content hash matches
        if entry.content_hash != content_hash:
            # Content changed, invalidate cache
            self._cache.delete(key)
            return None

        return entry.result

    def cache_result(
        self,
        code: str,
        agent_name: str,
        file_path: str,
        result: dict[str, Any],
        focus_areas: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> CacheEntry | None:
        """Store analysis results in cache.

        Args:
            code: Source code that was analyzed
            agent_name: Name of the agent
            file_path: Path to the analyzed file
            result: Analysis result to cache
            focus_areas: Optional focus areas used
            metadata: Optional additional metadata

        Returns:
            Created cache entry, or None if caching disabled
        """
        if not self.enabled or not self._cache:
            return None

        key = self._compute_key(code, agent_name, focus_areas)
        content_hash = hash_content(code)

        return self._cache.set(
            key=key,
            agent_name=agent_name,
            file_path=file_path,
            content_hash=content_hash,
            result=result,
            metadata={
                **(metadata or {}),
                "focus_areas": focus_areas or [],
            },
        )

    def invalidate(
        self,
        code: str,
        agent_name: str,
        focus_areas: list[str] | None = None,
    ) -> bool:
        """Invalidate a cache entry.

        Args:
            code: Source code
            agent_name: Name of the agent
            focus_areas: Optional focus areas

        Returns:
            True if entry was deleted
        """
        if not self.enabled or not self._cache:
            return False

        key = self._compute_key(code, agent_name, focus_areas)
        return self._cache.delete(key)

    def invalidate_file(self, file_path: str) -> int:
        """Invalidate all cache entries for a file.

        Args:
            file_path: Path to the file

        Returns:
            Number of entries invalidated
        """
        if not self.enabled or not self._cache:
            return 0

        count = 0
        for path in self._cache.cache_dir.rglob("*.json"):
            try:
                entry = self._cache.get(path.stem)
                if entry and entry.file_path == file_path:
                    self._cache.delete(entry.key)
                    count += 1
            except Exception:
                pass

        return count

    def clear(self) -> int:
        """Clear all cache entries.

        Returns:
            Number of entries cleared
        """
        if not self.enabled or not self._cache:
            return 0
        return self._cache.clear()

    def cleanup(self) -> int:
        """Clean up expired cache entries.

        Returns:
            Number of entries removed
        """
        if not self.enabled or not self._cache:
            return 0
        return self._cache.cleanup_expired()

    def stats(self) -> dict[str, Any]:
        """Get cache statistics.

        Returns:
            Dictionary with cache statistics
        """
        if not self.enabled or not self._cache:
            return {"enabled": False}

        stats = self._cache.stats()
        stats["enabled"] = True
        return stats

    def _compute_key(
        self,
        code: str,
        agent_name: str,
        focus_areas: list[str] | None = None,
    ) -> str:
        """Compute cache key for given inputs."""
        return hash_analysis_inputs(code, agent_name, focus_areas)
