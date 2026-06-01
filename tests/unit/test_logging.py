"""Tests for structured logging."""

from __future__ import annotations

import json
import logging
from collections.abc import Generator
from pathlib import Path

import pytest

from adversarial_debate.config import LoggingConfig
from adversarial_debate.logging import (
    AgentLoggerAdapter,
    HumanReadableFormatter,
    StructuredFormatter,
    get_agent_logger,
    get_logger,
    setup_logging,
)


def _record(**extra: object) -> logging.LogRecord:
    record = logging.LogRecord(
        name="adversarial_debate.agents.exploit",
        level=logging.INFO,
        pathname=__file__,
        lineno=10,
        msg="hello %s",
        args=("world",),
        exc_info=None,
    )
    for key, value in extra.items():
        setattr(record, key, value)
    return record


@pytest.fixture(autouse=True)
def restore_package_logger() -> Generator[None, None, None]:
    """setup_logging mutates the package logger — snapshot and restore it."""
    pkg = logging.getLogger("adversarial_debate")
    saved_handlers = pkg.handlers[:]
    saved_level = pkg.level
    saved_propagate = pkg.propagate
    yield
    pkg.handlers[:] = saved_handlers
    pkg.setLevel(saved_level)
    pkg.propagate = saved_propagate


class TestStructuredFormatter:
    def test_emits_single_line_json(self) -> None:
        out = StructuredFormatter().format(_record())
        assert "\n" not in out
        parsed = json.loads(out)
        assert parsed["message"] == "hello world"
        assert parsed["level"] == "INFO"
        assert parsed["logger"] == "adversarial_debate.agents.exploit"

    def test_includes_known_extra_fields(self) -> None:
        out = StructuredFormatter().format(_record(agent_name="ExploitAgent", duration_ms=42))
        parsed = json.loads(out)
        assert parsed["agent_name"] == "ExploitAgent"
        assert parsed["duration_ms"] == 42

    def test_includes_extra_data_payload(self) -> None:
        out = StructuredFormatter().format(_record(extra_data={"k": "v"}))
        assert json.loads(out)["data"] == {"k": "v"}

    def test_includes_exception(self) -> None:
        try:
            raise ValueError("boom")
        except ValueError:
            import sys

            record = _record()
            record.exc_info = sys.exc_info()
        out = StructuredFormatter().format(record)
        assert "ValueError" in json.loads(out)["exception"]


class TestHumanReadableFormatter:
    def test_plain_output_has_level_and_shortened_name(self) -> None:
        formatter = HumanReadableFormatter(use_colors=False)
        out = formatter.format(_record())
        assert "INFO" in out
        # Package prefix stripped from logger name.
        assert "[agents.exploit]" in out
        assert "hello world" in out

    def test_timestamp_can_be_disabled(self) -> None:
        out = HumanReadableFormatter(use_colors=False, include_timestamp=False).format(_record())
        assert not out.startswith("[")

    def test_agent_and_duration_rendered(self) -> None:
        out = HumanReadableFormatter(use_colors=False).format(
            _record(agent_name="ExploitAgent", duration_ms=12)
        )
        assert "(ExploitAgent)" in out
        assert "(12ms)" in out

    def test_colors_disabled_when_not_a_tty(self) -> None:
        # In the test runner stderr is not a TTY, so colours must be suppressed.
        formatter = HumanReadableFormatter(use_colors=True)
        assert formatter.use_colors is False
        assert "\033[" not in formatter.format(_record())


class TestAgentLoggerAdapter:
    def test_process_injects_context(self) -> None:
        adapter = AgentLoggerAdapter(
            logging.getLogger("adversarial_debate.x"),
            "ExploitAgent",
            thread_id="t1",
            task_id="task1",
        )
        _msg, kwargs = adapter.process("m", {})
        assert kwargs["extra"]["agent_name"] == "ExploitAgent"
        assert kwargs["extra"]["thread_id"] == "t1"
        assert kwargs["extra"]["task_id"] == "task1"

    def test_with_context_overrides_only_provided(self) -> None:
        adapter = AgentLoggerAdapter(
            logging.getLogger("adversarial_debate.x"), "A", thread_id="t1", task_id="task1"
        )
        updated = adapter.with_context(thread_id="t2")
        assert updated.thread_id == "t2"
        assert updated.task_id == "task1"
        assert updated.agent_name == "A"


class TestGetLogger:
    def test_namespaces_bare_names(self) -> None:
        assert get_logger("cache").name == "adversarial_debate.cache"

    def test_leaves_namespaced_names_untouched(self) -> None:
        assert get_logger("adversarial_debate.foo").name == "adversarial_debate.foo"

    def test_get_agent_logger_returns_adapter(self) -> None:
        adapter = get_agent_logger("ExploitAgent", thread_id="t")
        assert isinstance(adapter, AgentLoggerAdapter)
        assert adapter.logger.name == "adversarial_debate.agents.exploitagent"


class TestSetupLogging:
    def test_json_format_installs_structured_formatter(self) -> None:
        setup_logging(LoggingConfig(level="DEBUG", format="json"))
        pkg = logging.getLogger("adversarial_debate")
        assert pkg.level == logging.DEBUG
        assert pkg.propagate is False
        assert any(isinstance(h.formatter, StructuredFormatter) for h in pkg.handlers)

    def test_text_format_installs_human_formatter(self) -> None:
        setup_logging(LoggingConfig(level="INFO", format="text"))
        pkg = logging.getLogger("adversarial_debate")
        assert any(isinstance(h.formatter, HumanReadableFormatter) for h in pkg.handlers)

    def test_handlers_are_reset_between_calls(self) -> None:
        setup_logging(LoggingConfig(level="INFO", format="text"))
        first = len(logging.getLogger("adversarial_debate").handlers)
        setup_logging(LoggingConfig(level="INFO", format="text"))
        assert len(logging.getLogger("adversarial_debate").handlers) == first

    def test_file_handler_added_when_path_configured(self, tmp_path: Path) -> None:
        log_file = tmp_path / "ad.log"
        setup_logging(LoggingConfig(level="INFO", format="text", file_path=str(log_file)))
        pkg = logging.getLogger("adversarial_debate")
        try:
            file_handlers = [h for h in pkg.handlers if isinstance(h, logging.FileHandler)]
            assert len(file_handlers) == 1
            # File output is always JSON regardless of console format.
            assert isinstance(file_handlers[0].formatter, StructuredFormatter)
        finally:
            for handler in pkg.handlers:
                handler.close()

    def test_defaults_when_no_config(self) -> None:
        setup_logging()
        assert logging.getLogger("adversarial_debate").handlers
