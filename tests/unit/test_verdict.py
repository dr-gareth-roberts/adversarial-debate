"""Unit tests for verdict types."""

import pytest

from adversarial_debate.verdict import (
    ArbiterVerdict,
    ExploitationDifficulty,
    FindingValidation,
    RejectedFinding,
    RemediationEffort,
    RemediationTask,
    ValidatedFinding,
    VerdictDecision,
)


class TestVerdictDecision:
    """Tests for VerdictDecision enum."""

    def test_values(self) -> None:
        """Test enum values."""
        assert VerdictDecision.BLOCK.value == "BLOCK"
        assert VerdictDecision.WARN.value == "WARN"
        assert VerdictDecision.PASS.value == "PASS"

    def test_from_string(self) -> None:
        """Test creating from string."""
        assert VerdictDecision("BLOCK") == VerdictDecision.BLOCK
        assert VerdictDecision("WARN") == VerdictDecision.WARN
        assert VerdictDecision("PASS") == VerdictDecision.PASS

    def test_invalid_value(self) -> None:
        """Test invalid value raises error."""
        with pytest.raises(ValueError):
            VerdictDecision("INVALID")


class TestExploitationDifficulty:
    """Tests for ExploitationDifficulty enum."""

    def test_ordering(self) -> None:
        """Test that difficulties are ordered."""
        difficulties = [
            ExploitationDifficulty.TRIVIAL,
            ExploitationDifficulty.EASY,
            ExploitationDifficulty.MODERATE,
            ExploitationDifficulty.DIFFICULT,
            ExploitationDifficulty.THEORETICAL,
        ]
        assert len(difficulties) == 5

    def test_string_values(self) -> None:
        """Test string representation."""
        assert ExploitationDifficulty.TRIVIAL.value == "TRIVIAL"
        assert ExploitationDifficulty.THEORETICAL.value == "THEORETICAL"


class TestRemediationEffort:
    """Tests for RemediationEffort enum."""

    def test_values(self) -> None:
        """Test enum values."""
        assert RemediationEffort.MINUTES.value == "MINUTES"
        assert RemediationEffort.HOURS.value == "HOURS"
        assert RemediationEffort.DAYS.value == "DAYS"
        assert RemediationEffort.WEEKS.value == "WEEKS"


class TestValidatedFinding:
    """Tests for ValidatedFinding dataclass."""

    def test_creation(self) -> None:
        """Test creating a validated finding."""
        finding = ValidatedFinding(
            original_id="EXPLOIT-001",
            original_agent="ExploitAgent",
            original_title="SQL Injection",
            original_severity="CRITICAL",
            validation_status=FindingValidation.CONFIRMED,
            validated_severity="HIGH",
            adjusted_severity_reason="Internal API",
            exploitation_difficulty=ExploitationDifficulty.MODERATE,
            exploitation_prerequisites=["authenticated"],
            real_world_exploitability=0.7,
            impact_description="Data exposure",
            affected_components=["user_service"],
            data_at_risk=["user_emails"],
            remediation_effort=RemediationEffort.HOURS,
            suggested_fix="Use parameterized queries",
            fix_code_example="cursor.execute('SELECT ?', (val,))",
            workaround="Input validation",
            confidence=0.85,
        )
        assert finding.original_id == "EXPLOIT-001"
        assert finding.validation_status == FindingValidation.CONFIRMED

    def test_to_dict(self) -> None:
        """Test converting to dict."""
        finding = ValidatedFinding(
            original_id="EXPLOIT-001",
            original_agent="ExploitAgent",
            original_title="SQL Injection",
            original_severity="CRITICAL",
            validation_status=FindingValidation.CONFIRMED,
            validated_severity="HIGH",
            adjusted_severity_reason="Internal API",
            exploitation_difficulty=ExploitationDifficulty.MODERATE,
            exploitation_prerequisites=[],
            real_world_exploitability=0.7,
            impact_description="Data exposure",
            affected_components=[],
            data_at_risk=[],
            remediation_effort=RemediationEffort.HOURS,
            suggested_fix="",
            fix_code_example="",
            workaround="",
            confidence=0.85,
        )
        data = finding.to_dict()
        assert data["original_id"] == "EXPLOIT-001"
        assert data["validation_status"] == "CONFIRMED"
        assert data["exploitation_difficulty"] == "MODERATE"
        assert data["remediation_effort"] == "HOURS"

    def test_from_dict(self) -> None:
        """Test creating from dict."""
        data = {
            "original_id": "EXPLOIT-001",
            "original_agent": "ExploitAgent",
            "original_title": "Test",
            "original_severity": "HIGH",
            "validation_status": "LIKELY",
            "validated_severity": "MEDIUM",
            "exploitation_difficulty": "EASY",
            "remediation_effort": "DAYS",
            "confidence": 0.9,
        }
        finding = ValidatedFinding.from_dict(data)
        assert finding.original_id == "EXPLOIT-001"
        assert finding.validation_status == FindingValidation.LIKELY
        assert finding.exploitation_difficulty == ExploitationDifficulty.EASY
        assert finding.remediation_effort == RemediationEffort.DAYS


class TestRejectedFinding:
    """Tests for RejectedFinding dataclass."""

    def test_creation(self) -> None:
        """Test creating a rejected finding."""
        finding = RejectedFinding(
            original_id="BREAK-001",
            original_agent="BreakAgent",
            original_title="False Positive",
            original_severity="MEDIUM",
            rejection_reason="Not exploitable in this context",
            rejection_category="false_positive",
            evidence="Counter resets daily",
        )
        assert finding.original_id == "BREAK-001"
        assert finding.rejection_category == "false_positive"

    def test_to_dict_and_from_dict(self) -> None:
        """Test round-trip conversion."""
        original = RejectedFinding(
            original_id="TEST-001",
            original_agent="TestAgent",
            original_title="Test Finding",
            original_severity="LOW",
            rejection_reason="Test reason",
            rejection_category="out_of_scope",
            evidence="Test evidence",
            duplicate_of="OTHER-001",
        )
        data = original.to_dict()
        restored = RejectedFinding.from_dict(data)
        assert restored.original_id == original.original_id
        assert restored.duplicate_of == original.duplicate_of


class TestRemediationTask:
    """Tests for RemediationTask dataclass."""

    def test_creation(self) -> None:
        """Test creating a remediation task."""
        task = RemediationTask(
            finding_id="EXPLOIT-001",
            title="Fix SQL Injection",
            description="Replace string interpolation",
            priority="HIGH",
            estimated_effort=RemediationEffort.HOURS,
            assigned_to="",
            deadline="",
            fix_guidance="Use parameterized queries",
            acceptance_criteria=["No string interpolation"],
        )
        assert task.finding_id == "EXPLOIT-001"
        assert task.estimated_effort == RemediationEffort.HOURS


class TestArbiterVerdict:
    """Tests for ArbiterVerdict dataclass."""

    def test_should_block_with_block_decision(self) -> None:
        """Test should_block returns True for BLOCK decision."""
        verdict = ArbiterVerdict(
            verdict_id="V-001",
            thread_id="thread-1",
            task_id="task-1",
            decision=VerdictDecision.BLOCK,
            decision_rationale="Critical issues found",
            blocking_issues=[],
            warnings=[],
            passed_findings=[],
            false_positives=[],
            remediation_tasks=[],
            total_remediation_effort=RemediationEffort.DAYS,
            summary="Must block",
            key_concerns=["SQL injection"],
            recommendations=[],
            findings_analyzed=5,
            confidence=0.9,
        )
        assert verdict.should_block() is True

    def test_should_block_with_blocking_issues(self) -> None:
        """Test should_block returns True when blocking_issues exist."""
        blocking_issue = ValidatedFinding(
            original_id="EXPLOIT-001",
            original_agent="ExploitAgent",
            original_title="Critical Issue",
            original_severity="CRITICAL",
            validation_status=FindingValidation.CONFIRMED,
            validated_severity="CRITICAL",
            adjusted_severity_reason="",
            exploitation_difficulty=ExploitationDifficulty.TRIVIAL,
            exploitation_prerequisites=[],
            real_world_exploitability=0.95,
            impact_description="Full system compromise",
            affected_components=[],
            data_at_risk=[],
            remediation_effort=RemediationEffort.HOURS,
            suggested_fix="",
            fix_code_example="",
            workaround="",
            confidence=0.95,
        )
        verdict = ArbiterVerdict(
            verdict_id="V-001",
            thread_id="thread-1",
            task_id="task-1",
            decision=VerdictDecision.WARN,  # Even with WARN decision
            decision_rationale="Issues found",
            blocking_issues=[blocking_issue],  # Has blocking issues
            warnings=[],
            passed_findings=[],
            false_positives=[],
            remediation_tasks=[],
            total_remediation_effort=RemediationEffort.HOURS,
            summary="Has blocking issues",
            key_concerns=[],
            recommendations=[],
            findings_analyzed=1,
            confidence=0.9,
        )
        assert verdict.should_block() is True

    def test_should_not_block_with_pass(self) -> None:
        """Test should_block returns False for PASS with no blocking issues."""
        verdict = ArbiterVerdict(
            verdict_id="V-001",
            thread_id="thread-1",
            task_id="task-1",
            decision=VerdictDecision.PASS,
            decision_rationale="All clear",
            blocking_issues=[],
            warnings=[],
            passed_findings=[],
            false_positives=[],
            remediation_tasks=[],
            total_remediation_effort=RemediationEffort.MINUTES,
            summary="No issues",
            key_concerns=[],
            recommendations=[],
            findings_analyzed=0,
            confidence=0.95,
        )
        assert verdict.should_block() is False

    def test_generate_summary_report(self) -> None:
        """Test summary report generation."""
        verdict = ArbiterVerdict(
            verdict_id="V-001",
            thread_id="thread-1",
            task_id="task-1",
            decision=VerdictDecision.WARN,
            decision_rationale="Minor issues",
            blocking_issues=[],
            warnings=[],
            passed_findings=[],
            false_positives=[],
            remediation_tasks=[],
            total_remediation_effort=RemediationEffort.HOURS,
            summary="Review complete",
            key_concerns=["Input validation"],
            recommendations=["Add more tests"],
            findings_analyzed=3,
            confidence=0.85,
        )
        report = verdict.generate_summary_report()
        assert "WARN" in report
        assert "Review complete" in report
        assert "Input validation" in report
        assert "85%" in report

    def test_to_dict_and_from_dict(self) -> None:
        """Test round-trip conversion."""
        original = ArbiterVerdict(
            verdict_id="V-001",
            thread_id="thread-1",
            task_id="task-1",
            decision=VerdictDecision.PASS,
            decision_rationale="All good",
            blocking_issues=[],
            warnings=[],
            passed_findings=[],
            false_positives=[],
            remediation_tasks=[],
            total_remediation_effort=RemediationEffort.MINUTES,
            summary="Clean",
            key_concerns=[],
            recommendations=[],
            findings_analyzed=0,
            confidence=1.0,
            assumptions=["Code reviewed"],
            limitations=["No runtime testing"],
        )
        data = original.to_dict()
        restored = ArbiterVerdict.from_dict(data)
        assert restored.verdict_id == original.verdict_id
        assert restored.decision == original.decision
        assert restored.assumptions == original.assumptions
        assert restored.limitations == original.limitations
