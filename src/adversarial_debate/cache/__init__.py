"""Incremental analysis cache for adversarial-debate.

Provides caching of analysis results to avoid re-analyzing unchanged files.
Uses content hashing to detect changes and invalidate cache entries.
"""

from .file_cache import FileCache
from .hash import hash_content, hash_file, hash_file_content, normalize_code
from .manager import CacheManager

__all__ = [
    "CacheManager",
    "FileCache",
    "hash_content",
    "hash_file",
    "hash_file_content",
    "normalize_code",
]
