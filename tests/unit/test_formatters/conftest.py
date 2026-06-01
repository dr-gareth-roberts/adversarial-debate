"""Shared fixtures for formatter tests.

The formatters consume the canonical results bundle produced by
``adversarial_debate.results.build_results_bundle`` — a mapping with
``metadata``, ``findings`` (flat, normalised) and ``verdict`` keys. The
fixtures below mirror that shape so formatter tests exercise realistic data.
"""

from __future__ import annotations

from typing import Any

import pytest


@pytest.fixture
def sample_findings() -> list[dict[str, Any]]:
    """Two normalised findings spanning severities, agents and optional fields."""
    return [
        {
            "id": "EXPLOIT-001",
            "finding_type": "exploit",
            "agent": "ExploitAgent",
            "title": "SQL Injection in user lookup",
            "severity": "CRITICAL",
            "description": "User ID is interpolated directly into a SQL query.",
            "category": "A03:2021-Injection",
            "cwe": 89,
            "confidence": 0.95,
            "file_path": "src/app.py",
            "line": 12,
            "code_snippet": 'query = f"SELECT * FROM users WHERE id = {user_id}"',
            "impact": "Full read access to the users table.",
            "remediation": "Use parameterised queries.",
            "exploitation_difficulty": "EASY",
            "reproduction_steps": ["Send id=1 OR 1=1", "Observe every row returned"],
            "fingerprint": "fp-exploit-001",
        },
        {
            "id": "BREAK-001",
            "finding_type": "break",
            "agent": "BreakAgent",
            "title": "Unvalidated pagination input",
            "severity": "MEDIUM",
            "description": "The page size is not validated before use.",
            "category": "validation",
            "confidence": 0.7,
            "file_path": "src/app.py",
            "line": 8,
            "reproduction_steps": [{"description": "Pass a negative page size"}],
            "fingerprint": "fp-break-001",
        },
    ]


@pytest.fixture
def sample_verdict() -> dict[str, Any]:
    """A blocking verdict with a populated summary."""
    return {
        "summary": {
            "decision": "BLOCK",
            "blocking_issues": 1,
            "warnings": 1,
            "passed": 0,
            "false_positives": 0,
            "report": "One critical SQL injection must be fixed before merge.",
        },
    }


@pytest.fixture
def sample_bundle(
    sample_findings: list[dict[str, Any]],
    sample_verdict: dict[str, Any],
) -> dict[str, Any]:
    """A complete results bundle (metadata + findings + verdict)."""
    return {
        "metadata": {
            "run_id": "run-123",
            "target": "src/app.py",
            "provider": "mock",
            "finding_counts": {
                "total": 2,
                "by_severity": {"CRITICAL": 1, "MEDIUM": 1},
            },
        },
        "findings": sample_findings,
        "verdict": sample_verdict,
    }
