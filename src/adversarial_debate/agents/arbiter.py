"""Arbiter - Judges red team findings and renders verdicts.

This agent reviews findings from BreakAgent, ExploitAgent, and ChaosAgent,
validates them against the codebase context, and decides:
- BLOCK: Critical issues that must be fixed before merge
- WARN: Issues to track but don't block shipping
- PASS: No actionable issues found

The Arbiter is the final decision-maker in the adversarial mesh.
"""

import json
import uuid
from typing import Any

from ..providers import Message, ModelTier
from ..store import BeadType
from ..verdict import (
    ArbiterVerdict,
    ValidatedFinding,
    RejectedFinding,
    RemediationTask,
    VerdictDecision,
    ExploitationDifficulty,
    RemediationEffort,
    FindingValidation,
)
from .base import Agent, AgentContext, AgentOutput


ARBITER_SYSTEM_PROMPT = """You are the Arbiter - the final judge of security and quality findings.

Your role is to review findings from red team agents and make fair, rigorous decisions about what should block a merge, what should be tracked as warnings, and what can be dismissed as false positives.

## Your Judgment Criteria

### For Security Findings (ExploitAgent)
- Is the vulnerability actually exploitable in this context?
- What's the real-world attack surface?
- Are there existing mitigations (WAF, auth, rate limiting)?
- What data/systems are actually at risk?

### For Quality Findings (BreakAgent)
- Will this actually cause problems in production?
- How likely is the edge case to occur?
- What's the blast radius if it fails?
- Is there monitoring that would catch it?

### For Resilience Findings (ChaosAgent)
- How likely is this failure scenario?
- What's the impact if it happens?
- Are there existing fallbacks?
- Is the system designed to handle this?

## Severity Calibration

Adjust severity based on context:
- **Public-facing API**: Increase severity for anything exploitable
- **Internal service**: May reduce severity if behind auth/VPN
- **Data sensitivity**: PII, credentials, financial = higher severity
- **Blast radius**: Affects all users vs. edge case = adjust accordingly

## Verdict Decisions

- **BLOCK**: Use sparingly. Only for issues that:
  - Are definitely exploitable (not theoretical)
  - Have significant real-world impact
  - Cannot ship with even a tracking ticket
  - Include: RCE, auth bypass, data exposure, data corruption

- **WARN**: The balanced choice. For issues that:
  - Are real but have mitigations
  - Are exploitable but require conditions
  - Should be fixed but won't cause immediate harm
  - Include: Most injection vectors with WAF, edge case bugs, resilience gaps

- **PASS**: For:
  - False positives (common with automated tools)
  - Theoretical issues without practical exploit path
  - Already-mitigated vulnerabilities
  - Issues outside the changed code's responsibility

## Output Format

You MUST respond with valid JSON in this exact format:

{
  "decision": "BLOCK|WARN|PASS",
  "decision_rationale": "Clear explanation of why this decision was made",
  "blocking_issues": [
    {
      "original_id": "EXPLOIT-001",
      "original_agent": "ExploitAgent",
      "original_title": "SQL Injection in user lookup",
      "original_severity": "CRITICAL",
      "validation_status": "CONFIRMED|LIKELY|UNCERTAIN",
      "validated_severity": "CRITICAL|HIGH|MEDIUM|LOW",
      "adjusted_severity_reason": "Why severity was changed (if it was)",
      "exploitation_difficulty": "TRIVIAL|EASY|MODERATE|DIFFICULT|THEORETICAL",
      "exploitation_prerequisites": ["Requires authenticated session", "Needs admin role"],
      "real_world_exploitability": 0.0-1.0,
      "impact_description": "What actually happens if exploited",
      "affected_components": ["user_service", "database"],
      "data_at_risk": ["user_emails", "hashed_passwords"],
      "remediation_effort": "MINUTES|HOURS|DAYS|WEEKS",
      "suggested_fix": "Use parameterized queries",
      "fix_code_example": "cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))",
      "workaround": "Temporary mitigation if fix takes time",
      "confidence": 0.0-1.0
    }
  ],
  "warnings": [
    // Same structure as blocking_issues
  ],
  "passed_findings": [
    // Same structure, for findings that are real but don't need action
  ],
  "false_positives": [
    {
      "original_id": "BREAK-003",
      "original_agent": "BreakAgent",
      "original_title": "Integer overflow in counter",
      "original_severity": "MEDIUM",
      "rejection_reason": "Counter is reset daily, cannot reach overflow value",
      "rejection_category": "not_exploitable|false_positive|out_of_scope|duplicate",
      "evidence": "Counter max value is 1M, daily traffic is 10K"
    }
  ],
  "remediation_tasks": [
    {
      "finding_id": "EXPLOIT-001",
      "title": "Fix SQL injection in user lookup",
      "description": "Replace string concatenation with parameterized query",
      "priority": "CRITICAL|HIGH|MEDIUM|LOW",
      "estimated_effort": "MINUTES|HOURS|DAYS|WEEKS",
      "fix_guidance": "Step by step guidance",
      "acceptance_criteria": ["Query uses parameters", "No string interpolation"]
    }
  ],
  "summary": "Human-readable summary of the verdict",
  "key_concerns": ["Main things to be aware of"],
  "recommendations": ["Actions to take beyond immediate fixes"],
  "confidence": 0.0-1.0,
  "assumptions": ["Assumptions made in this judgment"],
  "limitations": ["Things that couldn't be fully assessed"]
}

## Rules

1. Be rigorous but fair - we want to ship code, not block everything
2. False positives are better caught than missed (don't let bad FPs through)
3. Context matters - same finding can be CRITICAL or LOW depending on context
4. Provide actionable fixes - don't just say "fix it"
5. When uncertain, err toward WARN not BLOCK
6. Consider the full picture - multiple small issues may warrant BLOCK together
"""


class Arbiter(Agent):
    """Final judge of red team findings.

    This agent:
    1. Reviews findings from BreakAgent, ExploitAgent, ChaosAgent
    2. Validates each finding against codebase context
    3. Assesses real-world exploitability and impact
    4. Renders BLOCK/WARN/PASS verdict
    5. Creates remediation tasks for issues that need fixing

    Produces ARBITER_VERDICT beads with:
    - verdict: The final decision (BLOCK/WARN/PASS)
    - blocking_issues: Issues that block the merge
    - warnings: Issues to track but don't block
    - false_positives: Rejected findings
    """

    @property
    def name(self) -> str:
        return "Arbiter"

    @property
    def bead_type(self) -> BeadType:
        return BeadType.ARBITER_VERDICT

    @property
    def model_tier(self) -> ModelTier:
        # Critical decisions require strong reasoning
        return ModelTier.HOSTED_LARGE

    def _build_prompt(self, context: AgentContext) -> list[Message]:
        """Build prompt with findings and context."""
        # Get findings from red team agents
        findings = context.inputs.get("findings", [])
        original_task = context.inputs.get("original_task", "Unknown task")
        changed_files = context.inputs.get("changed_files", [])

        # Codebase context
        public_facing = context.inputs.get("public_facing", "unknown")
        data_sensitivity = context.inputs.get("data_sensitivity", "unknown")
        security_controls = context.inputs.get("security_controls", [])
        existing_mitigations = context.inputs.get("existing_mitigations", [])

        # Historical context
        similar_past_findings = context.inputs.get("similar_past_findings", [])
        false_positive_rates = context.inputs.get("false_positive_rates", {})

        # Build user message
        user_parts = ["## Red Team Findings", ""]

        if findings:
            user_parts.append("```json")
            # Limit findings size
            findings_json = json.dumps(findings, indent=2)
            if len(findings_json) > 10000:
                # Truncate but keep valid JSON
                findings_json = json.dumps(findings[:20], indent=2)
                user_parts.append(findings_json)
                user_parts.append("```")
                user_parts.append(f"_(Showing first 20 of {len(findings)} findings)_")
            else:
                user_parts.append(findings_json)
                user_parts.append("```")
            user_parts.append("")
        else:
            user_parts.append("_No findings to review_")
            user_parts.append("")

        # Blue team context
        user_parts.extend([
            "## Blue Team Context",
            "",
            f"**Original Task:** {original_task}",
            "",
            "**Files Changed:**",
        ])
        for f in changed_files[:20]:
            if isinstance(f, dict):
                user_parts.append(f"- `{f.get('path', f)}`")
            else:
                user_parts.append(f"- `{f}`")
        if len(changed_files) > 20:
            user_parts.append(f"- _... and {len(changed_files) - 20} more_")
        user_parts.append("")

        # Codebase context
        user_parts.extend([
            "## Codebase Context",
            "",
            f"- **Public-facing:** {public_facing}",
            f"- **Data sensitivity:** {data_sensitivity}",
        ])

        if security_controls:
            user_parts.append(f"- **Security controls:** {', '.join(security_controls)}")
        if existing_mitigations:
            user_parts.append(f"- **Existing mitigations:** {', '.join(existing_mitigations)}")
        user_parts.append("")

        # Historical context
        if similar_past_findings or false_positive_rates:
            user_parts.append("## Historical Context")
            user_parts.append("")
            if similar_past_findings:
                user_parts.append("**Similar past findings:**")
                for finding in similar_past_findings[:5]:
                    if isinstance(finding, dict):
                        user_parts.append(f"- {finding.get('type', 'Unknown')}: {finding.get('resolution', 'Unknown')}")
                    else:
                        user_parts.append(f"- {finding}")
                user_parts.append("")
            if false_positive_rates:
                user_parts.append("**Agent false positive rates:**")
                for agent, rate in false_positive_rates.items():
                    user_parts.append(f"- {agent}: {rate}")
                user_parts.append("")

        # Mission
        user_parts.extend([
            "## Your Mission",
            "",
            "For each finding:",
            "1. Is this a real issue or false positive?",
            "2. What's the true severity in this context?",
            "3. Can this be exploited in practice?",
            "4. What's the remediation effort?",
            "",
            "Then make a verdict:",
            "- **BLOCK**: Critical/High issues that must be fixed before merge",
            "- **WARN**: Medium/Low issues that should be tracked but don't block",
            "- **PASS**: No actionable issues",
            "",
            "Be rigorous but not paranoid. We want to ship code, not block everything.",
            "",
            "Respond with valid JSON matching the schema in your instructions.",
        ])

        return [
            Message(role="system", content=ARBITER_SYSTEM_PROMPT),
            Message(role="user", content="\n".join(user_parts)),
        ]

    def _parse_response(
        self,
        response: str,
        context: AgentContext,
    ) -> AgentOutput:
        """Parse response into structured verdict."""
        try:
            data = self._parse_json_response(response)
        except json.JSONDecodeError as e:
            return AgentOutput(
                agent_name=self.name,
                result={
                    "verdict": None,
                    "error": f"Failed to parse response: {e}",
                },
                beads_out=[],
                confidence=0.0,
                errors=[f"Failed to parse response as JSON: {e}"],
            )

        # Parse decision
        decision = self._parse_decision(data.get("decision", "PASS"))

        # Parse findings
        blocking_issues = self._parse_validated_findings(data.get("blocking_issues", []))
        warnings = self._parse_validated_findings(data.get("warnings", []))
        passed_findings = self._parse_validated_findings(data.get("passed_findings", []))
        false_positives = self._parse_rejected_findings(data.get("false_positives", []))

        # Parse remediation tasks
        remediation_tasks = self._parse_remediation_tasks(data.get("remediation_tasks", []))

        # Calculate total remediation effort
        total_effort = self._calculate_total_effort(blocking_issues + warnings)

        # Create verdict
        verdict = ArbiterVerdict(
            verdict_id=f"VERDICT-{uuid.uuid4().hex[:8]}",
            thread_id=context.thread_id,
            task_id=context.task_id,
            decision=decision,
            decision_rationale=data.get("decision_rationale", ""),
            blocking_issues=blocking_issues,
            warnings=warnings,
            passed_findings=passed_findings,
            false_positives=false_positives,
            remediation_tasks=remediation_tasks,
            total_remediation_effort=total_effort,
            summary=data.get("summary", ""),
            key_concerns=data.get("key_concerns", []),
            recommendations=data.get("recommendations", []),
            findings_analyzed=len(blocking_issues) + len(warnings) + len(passed_findings) + len(false_positives),
            confidence=data.get("confidence", 0.8),
            assumptions=data.get("assumptions", []),
            limitations=data.get("limitations", []),
        )

        # Create bead payload
        payload = {
            "verdict_id": verdict.verdict_id,
            "decision": verdict.decision.value,
            "blocking_count": len(blocking_issues),
            "warning_count": len(warnings),
            "false_positive_count": len(false_positives),
            "findings_analyzed": verdict.findings_analyzed,
            "should_block": verdict.should_block(),
            "total_remediation_effort": verdict.total_remediation_effort.value,
        }

        bead = self._create_bead(
            context,
            payload=payload,
            artefacts=[],
            confidence=data.get("confidence", 0.8),
            assumptions=data.get("assumptions", []),
            unknowns=data.get("limitations", []),
        )

        return AgentOutput(
            agent_name=self.name,
            result={
                "verdict": verdict.to_dict(),
                "summary": {
                    "decision": verdict.decision.value,
                    "blocking_issues": len(blocking_issues),
                    "warnings": len(warnings),
                    "passed": len(passed_findings),
                    "false_positives": len(false_positives),
                    "remediation_tasks": len(remediation_tasks),
                    "should_block": verdict.should_block(),
                },
                "report": verdict.generate_summary_report(),
            },
            beads_out=[bead],
            confidence=data.get("confidence", 0.8),
            assumptions=data.get("assumptions", []),
            unknowns=data.get("limitations", []),
        )

    def _parse_decision(self, decision: str) -> VerdictDecision:
        """Parse verdict decision string."""
        try:
            return VerdictDecision(decision.upper())
        except ValueError:
            return VerdictDecision.PASS

    def _parse_validated_findings(
        self,
        findings_data: list[dict[str, Any]],
    ) -> list[ValidatedFinding]:
        """Parse validated findings from response."""
        findings = []

        for f in findings_data:
            # Parse validation status
            try:
                validation_status = FindingValidation(f.get("validation_status", "CONFIRMED"))
            except ValueError:
                validation_status = FindingValidation.CONFIRMED

            # Parse exploitation difficulty
            try:
                exploitation_difficulty = ExploitationDifficulty(
                    f.get("exploitation_difficulty", "MODERATE")
                )
            except ValueError:
                exploitation_difficulty = ExploitationDifficulty.MODERATE

            # Parse remediation effort
            try:
                remediation_effort = RemediationEffort(f.get("remediation_effort", "HOURS"))
            except ValueError:
                remediation_effort = RemediationEffort.HOURS

            findings.append(
                ValidatedFinding(
                    original_id=f.get("original_id", ""),
                    original_agent=f.get("original_agent", ""),
                    original_title=f.get("original_title", ""),
                    original_severity=f.get("original_severity", ""),
                    validation_status=validation_status,
                    validated_severity=f.get("validated_severity", f.get("original_severity", "MEDIUM")),
                    adjusted_severity_reason=f.get("adjusted_severity_reason", ""),
                    exploitation_difficulty=exploitation_difficulty,
                    exploitation_prerequisites=f.get("exploitation_prerequisites", []),
                    real_world_exploitability=f.get("real_world_exploitability", 0.5),
                    impact_description=f.get("impact_description", ""),
                    affected_components=f.get("affected_components", []),
                    data_at_risk=f.get("data_at_risk", []),
                    remediation_effort=remediation_effort,
                    suggested_fix=f.get("suggested_fix", ""),
                    fix_code_example=f.get("fix_code_example", ""),
                    workaround=f.get("workaround", ""),
                    confidence=f.get("confidence", 0.8),
                )
            )

        return findings

    def _parse_rejected_findings(
        self,
        findings_data: list[dict[str, Any]],
    ) -> list[RejectedFinding]:
        """Parse rejected findings from response."""
        findings = []

        for f in findings_data:
            findings.append(
                RejectedFinding(
                    original_id=f.get("original_id", ""),
                    original_agent=f.get("original_agent", ""),
                    original_title=f.get("original_title", ""),
                    original_severity=f.get("original_severity", ""),
                    rejection_reason=f.get("rejection_reason", ""),
                    rejection_category=f.get("rejection_category", "false_positive"),
                    evidence=f.get("evidence", ""),
                    duplicate_of=f.get("duplicate_of", ""),
                )
            )

        return findings

    def _parse_remediation_tasks(
        self,
        tasks_data: list[dict[str, Any]],
    ) -> list[RemediationTask]:
        """Parse remediation tasks from response."""
        tasks = []

        for t in tasks_data:
            try:
                effort = RemediationEffort(t.get("estimated_effort", "HOURS"))
            except ValueError:
                effort = RemediationEffort.HOURS

            tasks.append(
                RemediationTask(
                    finding_id=t.get("finding_id", ""),
                    title=t.get("title", ""),
                    description=t.get("description", ""),
                    priority=t.get("priority", "MEDIUM"),
                    estimated_effort=effort,
                    assigned_to=t.get("assigned_to", ""),
                    deadline=t.get("deadline", ""),
                    fix_guidance=t.get("fix_guidance", ""),
                    acceptance_criteria=t.get("acceptance_criteria", []),
                )
            )

        return tasks

    def _calculate_total_effort(
        self,
        findings: list[ValidatedFinding],
    ) -> RemediationEffort:
        """Calculate total remediation effort from findings."""
        if not findings:
            return RemediationEffort.MINUTES

        # Map efforts to hours
        effort_hours = {
            RemediationEffort.MINUTES: 0.5,
            RemediationEffort.HOURS: 4,
            RemediationEffort.DAYS: 16,
            RemediationEffort.WEEKS: 80,
        }

        total_hours = sum(
            effort_hours.get(f.remediation_effort, 4) for f in findings
        )

        # Convert back to effort level
        if total_hours <= 0.5:
            return RemediationEffort.MINUTES
        elif total_hours <= 8:
            return RemediationEffort.HOURS
        elif total_hours <= 40:
            return RemediationEffort.DAYS
        else:
            return RemediationEffort.WEEKS

    def _generate_idempotency_key(self, context: AgentContext) -> str:
        """Generate idempotency key for verdict."""
        return f"IK-verdict-{context.thread_id}-{context.task_id}"

    # =========================================================================
    # UTILITY METHODS FOR VERDICT HANDLING
    # =========================================================================

    @staticmethod
    def should_auto_block(verdict: ArbiterVerdict) -> bool:
        """Check if verdict should automatically block based on severity.

        Auto-block conditions:
        - Any CRITICAL severity blocking issue with TRIVIAL exploitation
        - Multiple HIGH severity blocking issues
        - Any finding with data_at_risk containing credentials/PII
        """
        for issue in verdict.blocking_issues:
            # Critical + Easy to exploit = auto block
            if (
                issue.validated_severity == "CRITICAL"
                and issue.exploitation_difficulty
                in (ExploitationDifficulty.TRIVIAL, ExploitationDifficulty.EASY)
            ):
                return True

            # Sensitive data at risk
            sensitive_keywords = ["password", "credential", "token", "pii", "ssn", "credit"]
            for data in issue.data_at_risk:
                if any(kw in data.lower() for kw in sensitive_keywords):
                    return True

        # Multiple high severity issues
        high_count = sum(
            1 for i in verdict.blocking_issues if i.validated_severity == "HIGH"
        )
        if high_count >= 3:
            return True

        return False

    @staticmethod
    def create_ticket_summary(verdict: ArbiterVerdict) -> str:
        """Create a summary suitable for a tracking ticket."""
        lines = [
            f"## Security Review: {verdict.decision.value}",
            "",
            verdict.summary,
            "",
            "### Findings Summary",
            f"- Blocking: {len(verdict.blocking_issues)}",
            f"- Warnings: {len(verdict.warnings)}",
            f"- False Positives: {len(verdict.false_positives)}",
            "",
        ]

        if verdict.blocking_issues:
            lines.append("### Must Fix")
            for issue in verdict.blocking_issues:
                lines.append(f"- [ ] **{issue.original_id}**: {issue.original_title}")
                lines.append(f"  - Severity: {issue.validated_severity}")
                lines.append(f"  - Effort: {issue.remediation_effort.value}")
            lines.append("")

        if verdict.warnings:
            lines.append("### Should Fix")
            for issue in verdict.warnings:
                lines.append(f"- [ ] **{issue.original_id}**: {issue.original_title}")
            lines.append("")

        return "\n".join(lines)

    @staticmethod
    def get_priority_sorted_issues(
        verdict: ArbiterVerdict,
    ) -> list[ValidatedFinding]:
        """Get all issues sorted by priority (exploitation difficulty + severity)."""
        all_issues = verdict.blocking_issues + verdict.warnings

        # Sort by: severity (CRITICAL first), then exploitation difficulty (TRIVIAL first)
        severity_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
        difficulty_order = {
            ExploitationDifficulty.TRIVIAL: 0,
            ExploitationDifficulty.EASY: 1,
            ExploitationDifficulty.MODERATE: 2,
            ExploitationDifficulty.DIFFICULT: 3,
            ExploitationDifficulty.THEORETICAL: 4,
        }

        return sorted(
            all_issues,
            key=lambda i: (
                severity_order.get(i.validated_severity, 99),
                difficulty_order.get(i.exploitation_difficulty, 99),
            ),
        )
