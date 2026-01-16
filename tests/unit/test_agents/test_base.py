"""Unit tests for base agent functionality."""

import pytest

from adversarial_debate.agents import Agent, AgentContext, AgentOutput
from adversarial_debate.providers import Message, ModelTier
from adversarial_debate.store import BeadType


class TestAgentContext:
    """Tests for AgentContext dataclass."""

    def test_creation(self) -> None:
        """Test creating agent context."""
        context = AgentContext(
            run_id="run-123",
            timestamp_iso="2024-01-01T00:00:00Z",
            policy={"max_wip": 5},
            thread_id="thread-1",
            task_id="task-1",
            inputs={"code": "print('hello')"},
        )
        assert context.run_id == "run-123"
        assert context.timestamp_iso == "2024-01-01T00:00:00Z"
        assert context.policy == {"max_wip": 5}
        assert context.thread_id == "thread-1"
        assert context.task_id == "task-1"
        assert context.inputs["code"] == "print('hello')"

    def test_with_defaults(self) -> None:
        """Test context with default values."""
        context = AgentContext(
            run_id="run-456",
            timestamp_iso="2024-01-01T00:00:00Z",
            policy={},
            thread_id="thread-1",
        )
        assert context.inputs == {}
        assert context.task_id == ""
        assert context.parent_bead_id == ""
        assert context.recent_beads == []
        assert context.repo_files == {}

    def test_to_dict(self) -> None:
        """Test converting context to dict."""
        context = AgentContext(
            run_id="run-789",
            timestamp_iso="2024-01-01T12:00:00Z",
            policy={"budget": 100},
            thread_id="thread-1",
            task_id="task-1",
            inputs={"key": "value"},
        )
        result = context.to_dict()
        assert result["run_id"] == "run-789"
        assert result["timestamp_iso"] == "2024-01-01T12:00:00Z"
        assert result["thread_id"] == "thread-1"
        assert result["policy"] == {"budget": 100}


class TestAgentOutput:
    """Tests for AgentOutput dataclass."""

    def test_creation(self) -> None:
        """Test creating agent output."""
        output = AgentOutput(
            agent_name="TestAgent",
            result={"findings": []},
            beads_out=[],
            confidence=0.9,
        )
        assert output.agent_name == "TestAgent"
        assert output.confidence == 0.9
        assert output.errors == []

    def test_with_errors(self) -> None:
        """Test output with errors."""
        output = AgentOutput(
            agent_name="TestAgent",
            result={},
            beads_out=[],
            confidence=0.0,
            errors=["Parse error", "Validation error"],
        )
        assert len(output.errors) == 2

    def test_with_assumptions(self) -> None:
        """Test output with assumptions and unknowns."""
        output = AgentOutput(
            agent_name="TestAgent",
            result={},
            beads_out=[],
            confidence=0.7,
            assumptions=["Code is Python 3.11"],
            unknowns=["Runtime behavior"],
        )
        assert output.assumptions == ["Code is Python 3.11"]
        assert output.unknowns == ["Runtime behavior"]
