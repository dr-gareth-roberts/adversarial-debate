"""Tests for file-watching functionality.

The polling loop in ``FileWatcher.start`` is time-driven; these tests exercise
the deterministic core instead — pattern filtering, change detection,
deduplication, and the runner's change-handling callback.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from adversarial_debate import watch as watch_module
from adversarial_debate.watch import (
    FileWatcher,
    WatchConfig,
    WatchEvent,
    WatchRunner,
)


class TestWatchConfig:
    def test_defaults(self) -> None:
        config = WatchConfig()
        assert config.patterns == ["*.py"]
        assert config.debounce_seconds == 0.5
        assert config.recursive is True
        assert config.ignore_patterns  # populated from DEFAULT_IGNORE_PATTERNS


class TestWatchEvent:
    def test_timestamp_defaulted(self) -> None:
        event = WatchEvent(Path("a.py"), "modified")
        assert event.event_type == "modified"
        assert event.timestamp > 0


class TestShouldWatch:
    def test_matches_include_pattern(self) -> None:
        watcher = FileWatcher([], WatchConfig(patterns=["*.py"], ignore_patterns=[]))
        assert watcher._should_watch(Path("module.py")) is True
        assert watcher._should_watch(Path("notes.txt")) is False

    def test_ignore_pattern_wins(self) -> None:
        watcher = FileWatcher([], WatchConfig(patterns=["*.py"], ignore_patterns=["build/*"]))
        assert watcher._should_watch(Path("build/module.py")) is False


class TestChangeDetection:
    def _watcher(self, tmp_path: Path) -> FileWatcher:
        return FileWatcher([tmp_path], WatchConfig(patterns=["*.py"], ignore_patterns=[]))

    def test_detects_created_files(self, tmp_path: Path) -> None:
        watcher = self._watcher(tmp_path)
        watcher._file_mtimes = watcher._get_watched_files()  # empty baseline

        (tmp_path / "new.py").write_text("x = 1\n")
        events = watcher._check_for_changes()

        assert [e.event_type for e in events] == ["created"]
        assert events[0].path.name == "new.py"

    def test_detects_deleted_files(self, tmp_path: Path) -> None:
        target = tmp_path / "gone.py"
        target.write_text("x = 1\n")
        watcher = self._watcher(tmp_path)
        watcher._file_mtimes = watcher._get_watched_files()

        target.unlink()
        events = watcher._check_for_changes()

        assert [e.event_type for e in events] == ["deleted"]

    def test_detects_modified_files(self, tmp_path: Path) -> None:
        target = tmp_path / "mod.py"
        target.write_text("x = 1\n")
        watcher = self._watcher(tmp_path)
        watcher._file_mtimes = watcher._get_watched_files()

        # Force a strictly newer mtime without relying on wall-clock resolution.
        future = watcher._file_mtimes[target] + 100
        import os

        os.utime(target, (future, future))
        events = watcher._check_for_changes()

        assert [e.event_type for e in events] == ["modified"]

    def test_non_matching_files_ignored(self, tmp_path: Path) -> None:
        watcher = self._watcher(tmp_path)
        watcher._file_mtimes = watcher._get_watched_files()
        (tmp_path / "data.txt").write_text("ignored")
        assert watcher._check_for_changes() == []


class TestDeduplicateEvents:
    def test_keeps_latest_event_per_path(self) -> None:
        watcher = FileWatcher([])
        path = Path("a.py")
        older = WatchEvent(path, "created", timestamp=1.0)
        newer = WatchEvent(path, "modified", timestamp=2.0)
        deduped = watcher._deduplicate_events([older, newer])
        assert len(deduped) == 1
        assert deduped[0].event_type == "modified"

    def test_distinct_paths_preserved(self) -> None:
        watcher = FileWatcher([])
        events = [WatchEvent(Path("a.py"), "modified"), WatchEvent(Path("b.py"), "modified")]
        assert len(watcher._deduplicate_events(events)) == 2


class TestStop:
    def test_stop_sets_running_false(self) -> None:
        watcher = FileWatcher([])
        watcher._running = True
        watcher.stop()
        assert watcher._running is False


class TestWatchRunnerOnChange:
    async def test_sync_callback_invoked_once_with_changed_paths(self) -> None:
        # Regression: a synchronous callback must run exactly once per change
        # batch (it was previously invoked twice — once to probe the result
        # type and again via asyncio.to_thread).
        calls: list[list[Path]] = []
        runner = WatchRunner([], analyze_callback=lambda paths: calls.append(list(paths)))

        await runner._on_change(
            [
                WatchEvent(Path("a.py"), "modified"),
                WatchEvent(Path("b.py"), "deleted"),  # excluded
            ]
        )

        assert calls == [[Path("a.py")]]

    async def test_async_callback_awaited(self) -> None:
        seen: list[list[Path]] = []

        async def analyze(paths: list[Path]) -> None:
            seen.append(paths)

        runner = WatchRunner([], analyze_callback=analyze)
        await runner._on_change([WatchEvent(Path("c.py"), "created")])
        assert seen == [[Path("c.py")]]

    async def test_no_changed_paths_skips_callback(self) -> None:
        calls: list[list[Path]] = []
        runner = WatchRunner([], analyze_callback=lambda paths: calls.append(paths))
        await runner._on_change([WatchEvent(Path("a.py"), "deleted")])
        assert calls == []

    async def test_callback_exception_is_swallowed(self) -> None:
        def boom(paths: list[Path]) -> None:
            raise RuntimeError("analysis blew up")

        runner = WatchRunner([], analyze_callback=boom)
        # Should not propagate — the runner logs and continues.
        await runner._on_change([WatchEvent(Path("a.py"), "modified")])

    def test_stop_without_watcher_is_safe(self) -> None:
        runner = WatchRunner([], analyze_callback=lambda paths: None)
        runner.stop()  # no watcher created yet — must not raise


class TestWatchRunnerInitialAnalysis:
    """The initial-analysis path in ``run`` shares the coroutine-detection
    bugfix with ``_on_change``; cover it too so a regression in either path is
    caught. ``FileWatcher.start`` (the endless polling loop) is stubbed out so
    ``run`` returns after the single initial scan."""

    @pytest.fixture(autouse=True)
    def _no_polling(self, monkeypatch: pytest.MonkeyPatch) -> None:
        async def _noop(self: FileWatcher, poll_interval: float = 0.5) -> None:
            return None

        monkeypatch.setattr(watch_module.FileWatcher, "start", _noop)

    async def test_sync_callback_invoked_once(self, tmp_path: Path) -> None:
        (tmp_path / "a.py").write_text("x = 1\n")
        (tmp_path / "b.py").write_text("y = 2\n")
        calls: list[list[Path]] = []

        runner = WatchRunner([tmp_path], analyze_callback=lambda paths: calls.append(list(paths)))
        await runner.run()

        assert len(calls) == 1
        assert {p.name for p in calls[0]} == {"a.py", "b.py"}

    async def test_async_callback_awaited_once(self, tmp_path: Path) -> None:
        (tmp_path / "a.py").write_text("x = 1\n")
        seen: list[list[Path]] = []

        async def analyze(paths: list[Path]) -> None:
            seen.append(list(paths))

        runner = WatchRunner([tmp_path], analyze_callback=analyze)
        await runner.run()

        assert len(seen) == 1
        assert seen[0][0].name == "a.py"


@pytest.mark.parametrize("recursive", [True, False])
def test_get_watched_files_respects_recursive(tmp_path: Path, recursive: bool) -> None:
    (tmp_path / "top.py").write_text("x = 1\n")
    nested = tmp_path / "pkg"
    nested.mkdir()
    (nested / "deep.py").write_text("y = 2\n")

    watcher = FileWatcher(
        [tmp_path], WatchConfig(patterns=["*.py"], ignore_patterns=[], recursive=recursive)
    )
    files = {p.name for p in watcher._get_watched_files()}

    assert "top.py" in files
    assert ("deep.py" in files) is recursive
