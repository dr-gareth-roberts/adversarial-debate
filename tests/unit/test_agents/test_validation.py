"""Validation tests for agent normalization requirements."""

from __future__ import annotations

import json
from datetime import UTC, datetime

import pytest

from adversarial_debate.agents import (
    AgentContext,
    Arbiter,
    BreakAgent,
    ChaosAgent,
    ExploitAgent,
)


def _make_context(inputs: dict[str, object]) -> AgentContext:
    return AgentContext(
        run_id="run-123",
        timestamp_iso=datetime.now(UTC).isoformat(),
        policy={},
        thread_id="thread-123",
        task_id="task-123",
        inputs=inputs,
    )


@pytest.mark.anyio
async def test_exploit_agent_requires_payload(bead_store, mock_provider_factory) -> None:
    response = json.dumps(
        {
            "target": {"file_path": "app.py", "function_name": "handler", "exposure": "public"},
            "findings": [
                {
                    "id": "EXPLOIT-001",
                    "title": "Missing payload",
                    "severity": "HIGH",
                    "exploit": {"description": "No payload"},
                },
                {
                    "id": "EXPLOIT-002",
                    "title": "Has payload",
                    "severity": "HIGH",
                    "exploit": {"payload": "' OR '1'='1"},
                },
            ],
            "attack_surface_analysis": {},
            "confidence": 0.9,
            "assumptions": [],
            "unknowns": [],
        }
    )
    provider = mock_provider_factory([response])
    agent = ExploitAgent(provider, bead_store)
    context = _make_context({"code": "print('hi')", "file_path": "app.py"})

    output = await agent.run(context)

    findings = output.result.get("findings", [])
    assert len(findings) == 1
    assert findings[0]["id"] == "EXPLOIT-002"


@pytest.mark.anyio
async def test_break_agent_requires_poc_code(bead_store, mock_provider_factory) -> None:
    response = json.dumps(
        {
            "target": {"file_path": "app.py", "function_name": "handler"},
            "findings": [
                {
                    "id": "BREAK-001",
                    "title": "Missing PoC",
                    "severity": "MEDIUM",
                    "proof_of_concept": {"description": "No code"},
                },
                {
                    "id": "BREAK-002",
                    "title": "Has PoC",
                    "severity": "MEDIUM",
                    "proof_of_concept": {"code": "raise Exception('boom')"},
                },
            ],
            "attack_vectors_tried": [],
            "code_quality_observations": [],
            "confidence": 0.8,
            "assumptions": [],
            "unknowns": [],
        }
    )
    provider = mock_provider_factory([response])
    agent = BreakAgent(provider, bead_store)
    context = _make_context({"code": "print('hi')", "file_path": "app.py"})

    output = await agent.run(context)

    findings = output.result.get("findings", [])
    assert len(findings) == 1
    assert findings[0]["id"] == "BREAK-002"


@pytest.mark.anyio
async def test_chaos_agent_requires_rollback(bead_store, mock_provider_factory) -> None:
    response = json.dumps(
        {
            "target": {"file_path": "app.py", "function_name": "handler"},
            "dependencies_detected": [],
            "resilience_analysis": {"overall_resilience_score": 50},
            "experiments": [
                {
                    "id": "CHAOS-001",
                    "title": "Missing rollback",
                    "category": "dependency_failure",
                    "failure_mode": "timeout",
                    "experiment": {"description": "no rollback"},
                },
                {
                    "id": "CHAOS-002",
                    "title": "Has rollback",
                    "category": "dependency_failure",
                    "failure_mode": "timeout",
                    "experiment": {
                        "description": "simulate timeout",
                        "rollback": "restore dependency",
                    },
                },
            ],
            "confidence": 0.8,
            "assumptions": [],
            "unknowns": [],
        }
    )
    provider = mock_provider_factory([response])
    agent = ChaosAgent(provider, bead_store)
    context = _make_context({"code": "print('hi')", "file_path": "app.py"})

    output = await agent.run(context)

    experiments = output.result.get("experiments", [])
    assert len(experiments) == 1
    assert experiments[0]["id"] == "CHAOS-002"


@pytest.mark.anyio
async def test_arbiter_flags_unknown_or_missing_ids(bead_store, mock_provider_factory) -> None:
    response = json.dumps(
        {
            "decision": "WARN",
            "decision_rationale": "Check findings",
            "blocking_issues": [
                {
                    "original_id": "EXPLOIT-999",
                    "original_agent": "ExploitAgent",
                    "original_title": "Unknown ID",
                    "original_severity": "HIGH",
                    "validation_status": "CONFIRMED",
                    "validated_severity": "HIGH",
                    "exploitation_difficulty": "MODERATE",
                    "remediation_effort": "HOURS",
                    "confidence": 0.8,
                }
            ],
            "warnings": [
                {
                    "original_agent": "BreakAgent",
                    "original_title": "Missing ID",
                    "original_severity": "LOW",
                    "validation_status": "UNCERTAIN",
                    "validated_severity": "LOW",
                    "exploitation_difficulty": "THEORETICAL",
                    "remediation_effort": "MINUTES",
                    "confidence": 0.5,
                }
            ],
            "passed_findings": [],
            "false_positives": [],
            "remediation_tasks": [],
            "summary": "Summary",
            "key_concerns": [],
            "recommendations": [],
            "confidence": 0.9,
            "assumptions": [],
            "limitations": [],
        }
    )
    provider = mock_provider_factory([response])
    agent = Arbiter(provider, bead_store)
    context = _make_context(
        {
            "findings": [
                {"id": "EXPLOIT-001", "title": "Known ID", "agent": "ExploitAgent"},
            ],
            "changed_files": ["app.py"],
            "original_task": "Test",
        }
    )

    output = await agent.run(context)

    limitations = output.result.get("verdict", {}).get("limitations", [])
    assert any("unknown finding IDs" in item for item in limitations)
    assert any("omitted original_id" in item for item in limitations)
