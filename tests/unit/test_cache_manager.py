"""Tests for the incremental-analysis cache manager."""

from __future__ import annotations

from pathlib import Path

import pytest

from adversarial_debate.cache.manager import CacheManager

CODE = "def f():\n    return 1\n"
AGENT = "ExploitAgent"
RESULT = {"findings": [{"id": "X"}]}


@pytest.fixture
def manager(tmp_path: Path) -> CacheManager:
    return CacheManager(cache_dir=tmp_path / "cache", enabled=True)


class TestDisabledManager:
    def test_all_operations_are_noops(self, tmp_path: Path) -> None:
        mgr = CacheManager(cache_dir=tmp_path, enabled=False)
        assert mgr.cache is None
        assert mgr.is_cached(CODE, AGENT) is False
        assert mgr.get_cached(CODE, AGENT) is None
        assert mgr.cache_result(CODE, AGENT, "f.py", RESULT) is None
        assert mgr.invalidate(CODE, AGENT) is False
        assert mgr.invalidate_file("f.py") == 0
        assert mgr.clear() == 0
        assert mgr.cleanup() == 0
        assert mgr.stats() == {"enabled": False}


class TestRoundTrip:
    def test_store_then_retrieve(self, manager: CacheManager) -> None:
        assert manager.is_cached(CODE, AGENT) is False
        entry = manager.cache_result(CODE, AGENT, "f.py", RESULT, focus_areas=["sql"])
        assert entry is not None
        assert manager.is_cached(CODE, AGENT, focus_areas=["sql"]) is True
        assert manager.get_cached(CODE, AGENT, focus_areas=["sql"]) == RESULT

    def test_focus_areas_change_the_key(self, manager: CacheManager) -> None:
        manager.cache_result(CODE, AGENT, "f.py", RESULT, focus_areas=["sql"])
        # Different focus areas → different key → cache miss.
        assert manager.is_cached(CODE, AGENT, focus_areas=["xss"]) is False

    def test_changed_content_invalidates_entry(self, manager: CacheManager) -> None:
        manager.cache_result(CODE, AGENT, "f.py", RESULT)
        # Cache the original, then mutate the code while reusing nothing else.
        changed = CODE + "# edit\n"
        assert manager.get_cached(changed, AGENT) is None


class TestInvalidation:
    def test_invalidate_specific_entry(self, manager: CacheManager) -> None:
        manager.cache_result(CODE, AGENT, "f.py", RESULT)
        assert manager.invalidate(CODE, AGENT) is True
        assert manager.is_cached(CODE, AGENT) is False

    def test_invalidate_file_removes_matching_entries(self, manager: CacheManager) -> None:
        manager.cache_result(CODE, AGENT, "target.py", RESULT)
        manager.cache_result("other()\n", "BreakAgent", "other.py", RESULT)
        removed = manager.invalidate_file("target.py")
        assert removed == 1
        assert manager.is_cached(CODE, AGENT) is False
        # The unrelated entry survives.
        assert manager.is_cached("other()\n", "BreakAgent") is True

    def test_clear_removes_all(self, manager: CacheManager) -> None:
        manager.cache_result(CODE, AGENT, "f.py", RESULT)
        manager.cache_result("g()\n", AGENT, "g.py", RESULT)
        assert manager.clear() == 2
        assert manager.is_cached(CODE, AGENT) is False


class TestStats:
    def test_stats_reports_enabled(self, manager: CacheManager) -> None:
        manager.cache_result(CODE, AGENT, "f.py", RESULT)
        stats = manager.stats()
        assert stats["enabled"] is True
        assert stats["total_entries"] >= 1

    def test_cleanup_returns_count(self, manager: CacheManager) -> None:
        manager.cache_result(CODE, AGENT, "f.py", RESULT)
        # Nothing is expired with the default TTL, so cleanup removes nothing.
        assert manager.cleanup() == 0
