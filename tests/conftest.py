"""Pytest configuration and fixtures for adversarial-debate tests."""

from __future__ import annotations

import json
import os
import tempfile
from collections.abc import Generator
from pathlib import Path
from typing import Any

import pytest

from adversarial_debate.agents import AgentContext
from adversarial_debate.config import Config, LoggingConfig, ProviderConfig, SandboxConfig
from adversarial_debate.providers import LLMProvider, LLMResponse, Message
from adversarial_debate.store import Bead, BeadStore, BeadType

# =============================================================================
# Environment Fixtures
# =============================================================================


@pytest.fixture(autouse=True)
def clean_environment() -> Generator[None, None, None]:
    """Ensure clean environment for each test."""
    # Store original environment
    original_env = os.environ.copy()

    yield

    # Restore original environment
    os.environ.clear()
    os.environ.update(original_env)


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Create a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


# =============================================================================
# Configuration Fixtures
# =============================================================================


@pytest.fixture
def test_config() -> Config:
    """Create a test configuration."""
    return Config(
        provider=ProviderConfig(
            provider="test",
            api_key="test-key",
            model="test-model",
            timeout_seconds=30,
            max_retries=1,
            temperature=0.5,
            max_tokens=1000,
        ),
        logging=LoggingConfig(
            level="DEBUG",
            format="text",
        ),
        sandbox=SandboxConfig(
            use_docker=False,  # Avoid requiring Docker during tests
            timeout_seconds=5,
        ),
        debug=True,
        dry_run=False,
    )


# =============================================================================
# Provider Fixtures
# =============================================================================


class MockLLMProvider(LLMProvider):
    """Mock LLM provider for testing."""

    def __init__(self, responses: list[str] | None = None) -> None:
        self._responses = responses or ['{"result": "test"}']
        self._call_count = 0
        self._calls: list[list[Message]] = []

    @property
    def name(self) -> str:
        return "mock"

    def _default_model(self) -> str:
        return "test-model"

    def get_model_for_tier(self, tier: Any) -> str:
        # Tests don't care about tier routing; return a stable model name.
        return "test-model"

    async def complete(
        self,
        messages: list[Message],
        **kwargs: Any,
    ) -> LLMResponse:
        """Return mock completion."""
        self._calls.append(messages)
        response_text = self._responses[self._call_count % len(self._responses)]
        self._call_count += 1
        return LLMResponse(
            content=response_text,
            model="test-model",
            usage={"input_tokens": 100, "output_tokens": 50},
        )

    @property
    def call_count(self) -> int:
        """Get number of calls made."""
        return self._call_count

    @property
    def calls(self) -> list[list[Message]]:
        """Get all calls made."""
        return self._calls


@pytest.fixture
def mock_provider() -> MockLLMProvider:
    """Create a mock LLM provider."""
    return MockLLMProvider()


@pytest.fixture
def mock_provider_factory() -> type[MockLLMProvider]:
    """Get the MockLLMProvider class for custom instantiation."""
    return MockLLMProvider


# =============================================================================
# Store Fixtures
# =============================================================================


@pytest.fixture
def bead_store(temp_dir: Path) -> BeadStore:
    """Create a temporary bead store."""
    ledger_path = temp_dir / "beads" / "ledger.jsonl"
    return BeadStore(ledger_path)


@pytest.fixture
def sample_bead() -> Bead:
    """Create a sample bead for testing."""
    return Bead(
        bead_id="B-20240101-120000-000001",
        parent_bead_id="ROOT",
        thread_id="test-thread",
        task_id="test-task",
        timestamp_iso="2024-01-01T12:00:00Z",
        agent="TestAgent",
        bead_type=BeadType.EXPLOIT_ANALYSIS,
        payload={"test": "data"},
        artefacts=[],
        idempotency_key="IK-test-001",
        confidence=0.9,
        assumptions=["test assumption"],
        unknowns=["test unknown"],
    )


# =============================================================================
# Agent Fixtures
# =============================================================================


@pytest.fixture
def sample_context() -> AgentContext:
    """Create a sample agent context for testing."""
    return AgentContext(
        thread_id="test-thread",
        task_id="test-task",
        inputs={
            "code": """
def get_user(user_id: str) -> dict:
    query = f"SELECT * FROM users WHERE id = '{user_id}'"
    return db.execute(query)
""",
            "file_path": "src/users.py",
        },
    )


@pytest.fixture
def sample_findings() -> list[dict[str, Any]]:
    """Create sample security findings for testing."""
    return [
        {
            "id": "EXPLOIT-001",
            "agent": "ExploitAgent",
            "title": "SQL Injection in user lookup",
            "severity": "CRITICAL",
            "category": "injection",
            "description": "User ID is directly interpolated into SQL query",
            "location": {
                "file": "src/users.py",
                "line": 2,
                "function": "get_user",
            },
            "evidence": "f\"SELECT * FROM users WHERE id = '{user_id}'\"",
            "cwe": "CWE-89",
            "remediation": "Use parameterized queries",
            "confidence": 0.95,
        },
        {
            "id": "BREAK-001",
            "agent": "BreakAgent",
            "title": "Missing input validation",
            "severity": "MEDIUM",
            "category": "validation",
            "description": "User ID is not validated before use",
            "location": {
                "file": "src/users.py",
                "line": 1,
                "function": "get_user",
            },
            "confidence": 0.8,
        },
    ]


# =============================================================================
# Response Fixtures
# =============================================================================


@pytest.fixture
def exploit_agent_response() -> str:
    """Sample ExploitAgent response."""
    return json.dumps(
        {
            "findings": [
                {
                    "id": "EXPLOIT-001",
                    "title": "SQL Injection",
                    "severity": "CRITICAL",
                    "category": "injection",
                    "cwe": "CWE-89",
                    "description": "SQL injection vulnerability found",
                    "location": {"file": "test.py", "line": 10},
                    "evidence": "SELECT * FROM users WHERE id = '{}'",
                    "attack_scenario": "Attacker can extract data",
                    "remediation": "Use parameterized queries",
                    "confidence": 0.9,
                }
            ],
            "analysis_summary": "Found 1 critical vulnerability",
            "confidence": 0.85,
        }
    )


@pytest.fixture
def arbiter_response() -> str:
    """Sample Arbiter response."""
    return json.dumps(
        {
            "decision": "WARN",
            "decision_rationale": "Issues found but not critical",
            "blocking_issues": [],
            "warnings": [
                {
                    "original_id": "EXPLOIT-001",
                    "original_agent": "ExploitAgent",
                    "original_title": "SQL Injection",
                    "original_severity": "CRITICAL",
                    "validation_status": "CONFIRMED",
                    "validated_severity": "HIGH",
                    "adjusted_severity_reason": "Internal API with auth",
                    "exploitation_difficulty": "MODERATE",
                    "exploitation_prerequisites": ["authenticated"],
                    "real_world_exploitability": 0.6,
                    "impact_description": "Data exposure possible",
                    "affected_components": ["user_service"],
                    "data_at_risk": ["user_emails"],
                    "remediation_effort": "HOURS",
                    "suggested_fix": "Use parameterized queries",
                    "fix_code_example": (
                        "cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))"
                    ),
                    "workaround": "Add input validation",
                    "confidence": 0.85,
                }
            ],
            "passed_findings": [],
            "false_positives": [],
            "remediation_tasks": [
                {
                    "finding_id": "EXPLOIT-001",
                    "title": "Fix SQL injection",
                    "description": "Replace string interpolation with parameterized query",
                    "priority": "HIGH",
                    "estimated_effort": "HOURS",
                    "fix_guidance": "Use cursor.execute with parameters",
                    "acceptance_criteria": ["No string interpolation in queries"],
                }
            ],
            "summary": "One high severity issue requiring attention",
            "key_concerns": ["SQL injection in user service"],
            "recommendations": ["Review all database queries"],
            "confidence": 0.85,
            "assumptions": [],
            "limitations": [],
        }
    )


@pytest.fixture
def orchestrator_response() -> str:
    """Sample ChaosOrchestrator response."""
    return json.dumps(
        {
            "attack_surface_analysis": {
                "files": [
                    {
                        "file_path": "test.py",
                        "risk_score": 75,
                        "risk_factors": ["handles user input", "database queries"],
                        "recommended_agents": ["ExploitAgent", "BreakAgent"],
                        "attack_vectors": ["SQL injection", "input validation"],
                        "exposure": "authenticated",
                        "data_sensitivity": "high",
                    }
                ],
                "total_risk_score": 75,
                "highest_risk_file": "test.py",
                "primary_concerns": ["SQL injection"],
                "recommended_focus_areas": ["Database queries"],
            },
            "risk_level": "HIGH",
            "risk_factors": ["User input handling", "Database access"],
            "attacks": [
                {
                    "id": "ATK-001",
                    "agent": "ExploitAgent",
                    "target_file": "test.py",
                    "target_function": "get_user",
                    "priority": 1,
                    "attack_vectors": [
                        {
                            "name": "SQL Injection",
                            "description": "Test for SQL injection",
                            "category": "injection",
                            "payload_hints": ["' OR '1'='1"],
                            "expected_behavior": "Query should be parameterized",
                            "success_indicators": ["returns all rows"],
                        }
                    ],
                    "time_budget_seconds": 60,
                    "rationale": "High risk SQL query",
                    "depends_on": [],
                    "can_parallel_with": ["ATK-002"],
                    "hints": ["Check line 2"],
                }
            ],
            "parallel_groups": [
                {
                    "group_id": "PG-001",
                    "attack_ids": ["ATK-001"],
                    "estimated_duration_seconds": 60,
                }
            ],
            "execution_order": ["ATK-001"],
            "skipped": [],
            "recommendations": ["Focus on database layer"],
            "confidence": 0.8,
            "assumptions": [],
            "unknowns": [],
        }
    )


# =============================================================================
# Utility Functions
# =============================================================================


def assert_valid_json(text: str) -> dict[str, Any]:
    """Assert that text is valid JSON and return parsed dict."""
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        pytest.fail(f"Invalid JSON: {e}\nText: {text[:500]}")
