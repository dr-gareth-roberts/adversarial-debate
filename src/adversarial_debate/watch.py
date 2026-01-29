"""File watching functionality for continuous analysis.

Provides a watch mode that monitors file changes and re-runs
analysis automatically when files are modified.
"""

import asyncio
import contextlib
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .logging import get_logger

logger = get_logger(__name__)


@dataclass
class WatchEvent:
    """A file system change event."""

    path: Path
    event_type: str  # "created", "modified", "deleted"
    timestamp: float = field(default_factory=time.time)


@dataclass
class WatchConfig:
    """Configuration for file watching."""

    patterns: list[str] = field(default_factory=lambda: ["*.py"])
    ignore_patterns: list[str] = field(
        default_factory=lambda: [
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
    )
    debounce_seconds: float = 0.5
    recursive: bool = True


class FileWatcher:
    """Watches files for changes using polling.

    A simple, cross-platform file watcher that polls for changes.
    For production use, consider using watchdog library.
    """

    def __init__(
        self,
        paths: Sequence[Path | str],
        config: WatchConfig | None = None,
        on_change: Callable[[list[WatchEvent]], Any] | None = None,
    ):
        """Initialize the file watcher.

        Args:
            paths: Directories or files to watch
            config: Watch configuration
            on_change: Callback for change events
        """
        self.paths = [Path(p) for p in paths]
        self.config = config or WatchConfig()
        self.on_change = on_change
        self._running = False
        self._file_mtimes: dict[Path, float] = {}
        self._pending_events: list[WatchEvent] = []
        self._last_callback: float = 0

    def _matches_pattern(self, path: Path, patterns: list[str]) -> bool:
        """Check if path matches any of the patterns."""
        from fnmatch import fnmatch

        path_str = str(path)
        for pattern in patterns:
            if fnmatch(path_str, pattern) or fnmatch(path.name, pattern):
                return True
        return False

    def _should_watch(self, path: Path) -> bool:
        """Check if a path should be watched."""
        # Check ignore patterns first
        if self._matches_pattern(path, self.config.ignore_patterns):
            return False

        # Check include patterns
        return self._matches_pattern(path, self.config.patterns)

    def _get_watched_files(self) -> dict[Path, float]:
        """Get all watched files with their modification times."""
        files: dict[Path, float] = {}

        for watch_path in self.paths:
            if watch_path.is_file():
                if self._should_watch(watch_path):
                    with contextlib.suppress(OSError):
                        files[watch_path] = watch_path.stat().st_mtime
            elif watch_path.is_dir():
                glob_pattern = "**/*" if self.config.recursive else "*"
                for file_path in watch_path.glob(glob_pattern):
                    if file_path.is_file() and self._should_watch(file_path):
                        with contextlib.suppress(OSError):
                            files[file_path] = file_path.stat().st_mtime

        return files

    def _check_for_changes(self) -> list[WatchEvent]:
        """Check for file changes since last check."""
        events = []
        current_files = self._get_watched_files()

        # Check for modified and deleted files
        for path, mtime in self._file_mtimes.items():
            if path in current_files:
                if current_files[path] > mtime:
                    events.append(WatchEvent(path, "modified"))
            else:
                events.append(WatchEvent(path, "deleted"))

        # Check for new files
        for path in current_files:
            if path not in self._file_mtimes:
                events.append(WatchEvent(path, "created"))

        # Update stored mtimes
        self._file_mtimes = current_files

        return events

    async def start(self, poll_interval: float = 0.5) -> None:
        """Start watching for file changes.

        Args:
            poll_interval: How often to check for changes (seconds)
        """
        logger.info(f"Starting file watcher for {len(self.paths)} path(s)")
        self._running = True

        # Initial scan
        self._file_mtimes = self._get_watched_files()
        logger.info(f"Watching {len(self._file_mtimes)} files")

        while self._running:
            try:
                events = self._check_for_changes()

                if events:
                    self._pending_events.extend(events)

                    # Debounce: wait for events to settle
                    now = time.time()
                    if (
                        now - self._last_callback >= self.config.debounce_seconds
                        and self._pending_events
                        and self.on_change
                    ):
                        # Group and deduplicate events
                        unique_events = self._deduplicate_events(self._pending_events)
                        self._pending_events = []
                        self._last_callback = now

                        logger.info(f"Detected {len(unique_events)} change(s)")
                        try:
                            result = self.on_change(unique_events)
                            if asyncio.iscoroutine(result):
                                await result
                        except Exception as e:
                            logger.error(f"Error in change callback: {e}")

                await asyncio.sleep(poll_interval)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in file watcher: {e}")
                await asyncio.sleep(1)  # Backoff on error

    def stop(self) -> None:
        """Stop the file watcher."""
        self._running = False
        logger.info("File watcher stopped")

    def _deduplicate_events(self, events: list[WatchEvent]) -> list[WatchEvent]:
        """Deduplicate events, keeping the latest for each path."""
        by_path: dict[Path, WatchEvent] = {}
        for event in events:
            existing = by_path.get(event.path)
            if existing is None or event.timestamp > existing.timestamp:
                by_path[event.path] = event
        return list(by_path.values())


class WatchRunner:
    """Runs analysis in watch mode."""

    def __init__(
        self,
        target_paths: list[Path | str],
        analyze_callback: Callable[[list[Path]], Any],
        watch_config: WatchConfig | None = None,
    ):
        """Initialize the watch runner.

        Args:
            target_paths: Paths to watch
            analyze_callback: Function to call when files change
            watch_config: Watch configuration
        """
        self.target_paths = [Path(p) for p in target_paths]
        self.analyze_callback = analyze_callback
        self.watch_config = watch_config or WatchConfig()
        self._watcher: FileWatcher | None = None
        self._analysis_task: asyncio.Task[Any] | None = None

    async def _on_change(self, events: list[WatchEvent]) -> None:
        """Handle file change events."""
        # Cancel any running analysis
        if self._analysis_task and not self._analysis_task.done():
            self._analysis_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._analysis_task

        # Get changed file paths
        changed_paths = [
            event.path for event in events if event.event_type in ("created", "modified")
        ]

        if not changed_paths:
            return

        # Start new analysis
        logger.info(f"Re-analyzing {len(changed_paths)} changed file(s)")
        try:
            result = self.analyze_callback(changed_paths)
            if asyncio.iscoroutine(result):
                self._analysis_task = asyncio.create_task(result)
                await self._analysis_task
        except asyncio.CancelledError:
            logger.info("Analysis cancelled due to new changes")
        except Exception as e:
            logger.error(f"Analysis failed: {e}")

    async def run(self) -> None:
        """Start the watch runner."""
        self._watcher = FileWatcher(
            self.target_paths,
            self.watch_config,
            on_change=self._on_change,
        )

        print(f"🔍 Watching for changes in {len(self.target_paths)} path(s)...")
        print("Press Ctrl+C to stop\n")

        try:
            # Run initial analysis
            all_files = list(self._watcher._get_watched_files().keys())
            if all_files:
                print(f"Running initial analysis on {len(all_files)} file(s)...\n")
                result = self.analyze_callback(all_files)
                if asyncio.iscoroutine(result):
                    await result

            # Start watching
            await self._watcher.start()
        except KeyboardInterrupt:
            print("\n\n👋 Watch mode stopped")
        finally:
            if self._watcher:
                self._watcher.stop()

    def stop(self) -> None:
        """Stop the watch runner."""
        if self._watcher:
            self._watcher.stop()
