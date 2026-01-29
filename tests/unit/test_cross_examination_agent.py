"""Unit tests for CrossExaminationAgent wiring."""

from __future__ import annotations

from adversarial_debate.agents import CrossExaminationAgent
from adversarial_debate.agents.cross_examiner import _enforce_repro_dismissal
from adversarial_debate.store import BeadType


def test_cross_examination_agent_metadata() -> None:
    agent = CrossExaminationAgent(provider=object(), bead_store=object())  # type: ignore[arg-type]
    assert agent.name == "CrossExaminationAgent"
    # Note: we don't run the agent here; just validate wiring.
    assert BeadType.CROSS_EXAMINATION.value == "cross_examination"


def test_cross_exam_auto_dismisses_missing_repro() -> None:
    findings = [
        {
            "fingerprint": "fp-1",
            "severity": "HIGH",
            "reproduction_steps": [],
            "debate": {"resolution": "UPHOLD"},
        },
        {
            "fingerprint": "fp-2",
            "severity": "HIGH",
            "reproduction_steps": ["curl ..."],
            "debate": {"resolution": "UPHOLD"},
        },
    ]
    filtered, counts = _enforce_repro_dismissal(findings)
    assert [f["fingerprint"] for f in filtered] == ["fp-2"]
    assert counts["dismissed"] == 1
