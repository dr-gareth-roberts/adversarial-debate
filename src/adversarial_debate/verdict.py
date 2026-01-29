"""Verdict types for Arbiter decision making.

This module defines the data structures used by the Arbiter agent to render
verdicts on security findings from the red team agents.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class VerdictDecision(str, Enum):
    """Final verdict decision for a security review."""

    BLOCK = "BLOCK"  # Critical issues that must be fixed before merge
    WARN = "WARN"  # Issues to track but don't block shipping
    PASS = "PASS"  # No actionable issues found  # noqa: S105


class ExploitationDifficulty(str, Enum):
    """How difficult it is to exploit a vulnerability."""

    TRIVIAL = "TRIVIAL"  # Script kiddie level, automated tools exist
    EASY = "EASY"  # Straightforward for experienced attacker
    MODERATE = "MODERATE"  # Requires some effort and knowledge
    DIFFICULT = "DIFFICULT"  # Needs expert knowledge and resources
    THEORETICAL = "THEORETICAL"  # Possible in theory but impractical


class RemediationEffort(str, Enum):
    """Estimated time to remediate an issue."""

    MINUTES = "MINUTES"  # Quick fix, less than an hour
    HOURS = "HOURS"  # Same day fix
    DAYS = "DAYS"  # Multi-day effort
    WEEKS = "WEEKS"  # Significant refactoring required


class FindingValidation(str, Enum):
    """Validation status of a reported finding."""

    CONFIRMED = "CONFIRMED"  # Definitely a real issue
    LIKELY = "LIKELY"  # Probably real but not 100% confirmed
    UNCERTAIN = "UNCERTAIN"  # Needs more investigation


@dataclass
class ValidatedFinding:
    """A finding that has been validated by the Arbiter.

    This represents a security or quality issue that the Arbiter has reviewed
    and determined to be a real concern (blocking, warning, or passed).
    """

    original_id: str
    original_agent: str
    original_title: str
    original_severity: str
    validation_status: FindingValidation
    validated_severity: str
    adjusted_severity_reason: str
    exploitation_difficulty: ExploitationDifficulty
    exploitation_prerequisites: list[str]
    real_world_exploitability: float  # 0.0 to 1.0
    impact_description: str
    affected_components: list[str]
    data_at_risk: list[str]
    remediation_effort: RemediationEffort
    suggested_fix: str
    fix_code_example: str
    workaround: str
    confidence: float  # 0.0 to 1.0

    def to_dict(self) -> dict[str, Any]:
        """Convert to JSON-serializable dict."""
        return {
            "original_id": self.original_id,
            "original_agent": self.original_agent,
            "original_title": self.original_title,
            "original_severity": self.original_severity,
            "validation_status": self.validation_status.value,
            "validated_severity": self.validated_severity,
            "adjusted_severity_reason": self.adjusted_severity_reason,
            "exploitation_difficulty": self.exploitation_difficulty.value,
            "exploitation_prerequisites": self.exploitation_prerequisites,
            "real_world_exploitability": self.real_world_exploitability,
            "impact_description": self.impact_description,
            "affected_components": self.affected_components,
            "data_at_risk": self.data_at_risk,
            "remediation_effort": self.remediation_effort.value,
            "suggested_fix": self.suggested_fix,
            "fix_code_example": self.fix_code_example,
            "workaround": self.workaround,
            "confidence": self.confidence,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ValidatedFinding":
        """Create from dict."""
        return cls(
            original_id=data["original_id"],
            original_agent=data["original_agent"],
            original_title=data["original_title"],
            original_severity=data["original_severity"],
            validation_status=FindingValidation(data["validation_status"]),
            validated_severity=data["validated_severity"],
            adjusted_severity_reason=data.get("adjusted_severity_reason", ""),
            exploitation_difficulty=ExploitationDifficulty(data["exploitation_difficulty"]),
            exploitation_prerequisites=data.get("exploitation_prerequisites", []),
            real_world_exploitability=data.get("real_world_exploitability", 0.5),
            impact_description=data.get("impact_description", ""),
            affected_components=data.get("affected_components", []),
            data_at_risk=data.get("data_at_risk", []),
            remediation_effort=RemediationEffort(data["remediation_effort"]),
            suggested_fix=data.get("suggested_fix", ""),
            fix_code_example=data.get("fix_code_example", ""),
            workaround=data.get("workaround", ""),
            confidence=data.get("confidence", 0.8),
        )


@dataclass
class RejectedFinding:
    """A finding that was rejected as a false positive or out of scope."""

    original_id: str
    original_agent: str
    original_title: str
    original_severity: str
    rejection_reason: str
    rejection_category: str  # not_exploitable, false_positive, out_of_scope, duplicate
    evidence: str
    duplicate_of: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Convert to JSON-serializable dict."""
        return {
            "original_id": self.original_id,
            "original_agent": self.original_agent,
            "original_title": self.original_title,
            "original_severity": self.original_severity,
            "rejection_reason": self.rejection_reason,
            "rejection_category": self.rejection_category,
            "evidence": self.evidence,
            "duplicate_of": self.duplicate_of,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RejectedFinding":
        """Create from dict."""
        return cls(
            original_id=data["original_id"],
            original_agent=data["original_agent"],
            original_title=data["original_title"],
            original_severity=data["original_severity"],
            rejection_reason=data["rejection_reason"],
            rejection_category=data.get("rejection_category", "false_positive"),
            evidence=data.get("evidence", ""),
            duplicate_of=data.get("duplicate_of", ""),
        )


@dataclass
class RemediationTask:
    """A task to remediate a security finding."""

    finding_id: str
    title: str
    description: str
    priority: str  # CRITICAL, HIGH, MEDIUM, LOW
    estimated_effort: RemediationEffort
    assigned_to: str
    deadline: str
    fix_guidance: str
    acceptance_criteria: list[str]

    def to_dict(self) -> dict[str, Any]:
        """Convert to JSON-serializable dict."""
        return {
            "finding_id": self.finding_id,
            "title": self.title,
            "description": self.description,
            "priority": self.priority,
            "estimated_effort": self.estimated_effort.value,
            "assigned_to": self.assigned_to,
            "deadline": self.deadline,
            "fix_guidance": self.fix_guidance,
            "acceptance_criteria": self.acceptance_criteria,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RemediationTask":
        """Create from dict."""
        return cls(
            finding_id=data["finding_id"],
            title=data["title"],
            description=data.get("description", ""),
            priority=data.get("priority", "MEDIUM"),
            estimated_effort=RemediationEffort(data.get("estimated_effort", "HOURS")),
            assigned_to=data.get("assigned_to", ""),
            deadline=data.get("deadline", ""),
            fix_guidance=data.get("fix_guidance", ""),
            acceptance_criteria=data.get("acceptance_criteria", []),
        )


@dataclass
class ArbiterVerdict:
    """Complete verdict from the Arbiter agent.

    This is the final output of the security review process, containing
    all validated findings, rejected findings, and remediation tasks.
    """

    verdict_id: str
    thread_id: str
    task_id: str
    decision: VerdictDecision
    decision_rationale: str
    blocking_issues: list[ValidatedFinding]
    warnings: list[ValidatedFinding]
    passed_findings: list[ValidatedFinding]
    false_positives: list[RejectedFinding]
    remediation_tasks: list[RemediationTask]
    total_remediation_effort: RemediationEffort
    summary: str
    key_concerns: list[str]
    recommendations: list[str]
    findings_analyzed: int
    confidence: float  # 0.0 to 1.0
    assumptions: list[str] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)

    def should_block(self) -> bool:
        """Check if this verdict should block the merge.

        Returns True if the decision is BLOCK or there are blocking issues.
        """
        return self.decision == VerdictDecision.BLOCK or len(self.blocking_issues) > 0

    def to_dict(self) -> dict[str, Any]:
        """Convert to JSON-serializable dict."""
        return {
            "verdict_id": self.verdict_id,
            "thread_id": self.thread_id,
            "task_id": self.task_id,
            "decision": self.decision.value,
            "decision_rationale": self.decision_rationale,
            "blocking_issues": [f.to_dict() for f in self.blocking_issues],
            "warnings": [f.to_dict() for f in self.warnings],
            "passed_findings": [f.to_dict() for f in self.passed_findings],
            "false_positives": [f.to_dict() for f in self.false_positives],
            "remediation_tasks": [t.to_dict() for t in self.remediation_tasks],
            "total_remediation_effort": self.total_remediation_effort.value,
            "summary": self.summary,
            "key_concerns": self.key_concerns,
            "recommendations": self.recommendations,
            "findings_analyzed": self.findings_analyzed,
            "confidence": self.confidence,
            "assumptions": self.assumptions,
            "limitations": self.limitations,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ArbiterVerdict":
        """Create from dict."""
        blocking = [ValidatedFinding.from_dict(f) for f in data.get("blocking_issues", [])]
        warnings = [ValidatedFinding.from_dict(f) for f in data.get("warnings", [])]
        passed = [ValidatedFinding.from_dict(f) for f in data.get("passed_findings", [])]
        rejected = [RejectedFinding.from_dict(f) for f in data.get("false_positives", [])]
        tasks = [RemediationTask.from_dict(t) for t in data.get("remediation_tasks", [])]
        effort_str = data.get("total_remediation_effort", "HOURS")
        return cls(
            verdict_id=data["verdict_id"],
            thread_id=data["thread_id"],
            task_id=data["task_id"],
            decision=VerdictDecision(data["decision"]),
            decision_rationale=data.get("decision_rationale", ""),
            blocking_issues=blocking,
            warnings=warnings,
            passed_findings=passed,
            false_positives=rejected,
            remediation_tasks=tasks,
            total_remediation_effort=RemediationEffort(effort_str),
            summary=data.get("summary", ""),
            key_concerns=data.get("key_concerns", []),
            recommendations=data.get("recommendations", []),
            findings_analyzed=data.get("findings_analyzed", 0),
            confidence=data.get("confidence", 0.8),
            assumptions=data.get("assumptions", []),
            limitations=data.get("limitations", []),
        )

    def generate_summary_report(self) -> str:
        """Generate a human-readable summary report of the verdict."""
        lines = [
            f"# Security Review Verdict: {self.decision.value}",
            "",
            self.summary,
            "",
            "## Summary Statistics",
            f"- Findings analyzed: {self.findings_analyzed}",
            f"- Blocking issues: {len(self.blocking_issues)}",
            f"- Warnings: {len(self.warnings)}",
            f"- Passed: {len(self.passed_findings)}",
            f"- False positives: {len(self.false_positives)}",
            f"- Estimated remediation: {self.total_remediation_effort.value}",
            f"- Confidence: {self.confidence:.0%}",
            "",
        ]

        if self.key_concerns:
            lines.append("## Key Concerns")
            for concern in self.key_concerns:
                lines.append(f"- {concern}")
            lines.append("")

        if self.blocking_issues:
            lines.append("## Blocking Issues (Must Fix)")
            for issue in self.blocking_issues:
                lines.append(f"### {issue.original_id}: {issue.original_title}")
                lines.append(f"- Severity: {issue.validated_severity}")
                lines.append(f"- Exploitation: {issue.exploitation_difficulty.value}")
                lines.append(f"- Effort: {issue.remediation_effort.value}")
                if issue.suggested_fix:
                    lines.append(f"- Fix: {issue.suggested_fix}")
                lines.append("")

        if self.warnings:
            lines.append("## Warnings (Should Fix)")
            for issue in self.warnings:
                title = f"**{issue.original_id}**: {issue.original_title}"
                lines.append(f"- {title} ({issue.validated_severity})")
            lines.append("")

        if self.recommendations:
            lines.append("## Recommendations")
            for rec in self.recommendations:
                lines.append(f"- {rec}")
            lines.append("")

        return "\n".join(lines)


__all__ = [
    "VerdictDecision",
    "ExploitationDifficulty",
    "RemediationEffort",
    "FindingValidation",
    "ValidatedFinding",
    "RejectedFinding",
    "RemediationTask",
    "ArbiterVerdict",
]
