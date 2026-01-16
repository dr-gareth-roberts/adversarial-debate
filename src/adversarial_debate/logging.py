"""Structured logging for adversarial-debate.

This module provides consistent logging across all components with
support for both human-readable and JSON formats.
"""

import json
import logging
import sys
from collections.abc import MutableMapping
from datetime import UTC, datetime
from typing import Any

from .config import LoggingConfig


class StructuredFormatter(logging.Formatter):
    """JSON formatter for structured logging.

    Outputs log records as single-line JSON objects for easy parsing
    by log aggregation systems.
    """

    def format(self, record: logging.LogRecord) -> str:
        """Format the log record as JSON."""
        log_data: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # Add extra fields from record
        for key in ["agent_name", "thread_id", "task_id", "bead_id", "duration_ms"]:
            if hasattr(record, key):
                log_data[key] = getattr(record, key)

        # Add any extra data passed via extra dict
        if hasattr(record, "extra_data") and record.extra_data:
            log_data["data"] = record.extra_data

        return json.dumps(log_data, separators=(",", ":"), default=str)


class HumanReadableFormatter(logging.Formatter):
    """Human-readable formatter with optional color support.

    Formats logs in a clear, readable format suitable for terminal output.
    """

    COLORS = {
        "DEBUG": "\033[36m",  # Cyan
        "INFO": "\033[32m",  # Green
        "WARNING": "\033[33m",  # Yellow
        "ERROR": "\033[31m",  # Red
        "CRITICAL": "\033[35m",  # Magenta
        "RESET": "\033[0m",
    }

    def __init__(self, use_colors: bool = True, include_timestamp: bool = True) -> None:
        super().__init__()
        self.use_colors = use_colors and sys.stderr.isatty()
        self.include_timestamp = include_timestamp

    def format(self, record: logging.LogRecord) -> str:
        """Format the log record as human-readable text."""
        parts = []

        # Timestamp
        if self.include_timestamp:
            timestamp = datetime.now(UTC).strftime("%H:%M:%S")
            parts.append(f"[{timestamp}]")

        # Level with optional color
        level = record.levelname
        if self.use_colors:
            color = self.COLORS.get(level, "")
            reset = self.COLORS["RESET"]
            parts.append(f"{color}{level:8s}{reset}")
        else:
            parts.append(f"{level:8s}")

        # Logger name (shortened)
        logger_name = record.name
        if logger_name.startswith("adversarial_debate."):
            logger_name = logger_name[19:]  # Remove prefix
        parts.append(f"[{logger_name}]")

        # Agent context if present
        if hasattr(record, "agent_name") and record.agent_name:
            parts.append(f"({record.agent_name})")

        # Message
        parts.append(record.getMessage())

        # Duration if present
        if hasattr(record, "duration_ms") and record.duration_ms:
            parts.append(f"({record.duration_ms}ms)")

        result = " ".join(parts)

        # Exception info
        if record.exc_info:
            result += "\n" + self.formatException(record.exc_info)

        return result


class AgentLoggerAdapter(logging.LoggerAdapter[logging.Logger]):
    """Logger adapter that adds agent context to log records.

    Use this adapter when logging from within an agent to automatically
    include agent name, thread ID, and task ID in all log messages.
    """

    def __init__(
        self,
        logger: logging.Logger,
        agent_name: str,
        thread_id: str | None = None,
        task_id: str | None = None,
    ) -> None:
        super().__init__(logger, {})
        self.agent_name = agent_name
        self.thread_id = thread_id
        self.task_id = task_id

    def process(
        self, msg: Any, kwargs: MutableMapping[str, Any]
    ) -> tuple[Any, MutableMapping[str, Any]]:
        """Add agent context to the log record."""
        extra = dict(kwargs.get("extra", {}))
        extra["agent_name"] = self.agent_name
        if self.thread_id:
            extra["thread_id"] = self.thread_id
        if self.task_id:
            extra["task_id"] = self.task_id
        kwargs["extra"] = extra
        return msg, kwargs

    def with_context(
        self,
        thread_id: str | None = None,
        task_id: str | None = None,
    ) -> "AgentLoggerAdapter":
        """Create a new adapter with updated context."""
        return AgentLoggerAdapter(
            self.logger,
            self.agent_name,
            thread_id or self.thread_id,
            task_id or self.task_id,
        )


def setup_logging(config: LoggingConfig | None = None) -> None:
    """Configure logging for the application.

    Args:
        config: Logging configuration. Uses defaults if not provided.
    """
    if config is None:
        config = LoggingConfig()

    # Get root logger for our package
    root_logger = logging.getLogger("adversarial_debate")
    root_logger.setLevel(getattr(logging, config.level.upper()))

    # Remove existing handlers
    root_logger.handlers.clear()

    # Create formatter based on config
    if config.format.lower() == "json":
        formatter: logging.Formatter = StructuredFormatter()
    else:
        formatter = HumanReadableFormatter(
            use_colors=True,
            include_timestamp=config.include_timestamps,
        )

    # Console handler
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # File handler if configured
    if config.file_path:
        file_handler = logging.FileHandler(config.file_path)
        # Always use JSON for file output
        file_handler.setFormatter(StructuredFormatter())
        root_logger.addHandler(file_handler)

    # Don't propagate to root logger
    root_logger.propagate = False


def get_logger(name: str) -> logging.Logger:
    """Get a logger for a module.

    Args:
        name: Module name (usually __name__)

    Returns:
        Logger instance
    """
    # Ensure name is under our namespace
    if not name.startswith("adversarial_debate"):
        name = f"adversarial_debate.{name}"
    return logging.getLogger(name)


def get_agent_logger(
    agent_name: str,
    thread_id: str | None = None,
    task_id: str | None = None,
) -> AgentLoggerAdapter:
    """Get a logger adapter for an agent.

    Args:
        agent_name: Name of the agent
        thread_id: Optional thread/workstream ID
        task_id: Optional task ID

    Returns:
        AgentLoggerAdapter instance
    """
    logger = get_logger(f"agents.{agent_name.lower()}")
    return AgentLoggerAdapter(logger, agent_name, thread_id, task_id)


__all__ = [
    "StructuredFormatter",
    "HumanReadableFormatter",
    "AgentLoggerAdapter",
    "setup_logging",
    "get_logger",
    "get_agent_logger",
]
