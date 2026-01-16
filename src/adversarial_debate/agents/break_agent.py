"""BreakAgent - Adversarial agent that finds logic errors and edge cases.

This agent systematically probes code for:
- Boundary value errors
- Race conditions
- State corruption vulnerabilities
- Type confusion issues
- Resource exhaustion bugs
"""

import json
from typing import Any

from ..providers import Message, ModelTier
from ..store import BeadType
from .base import Agent, AgentContext, AgentOutput

BREAK_AGENT_SYSTEM_PROMPT = """You are a senior QA engineer and chaos engineer with expertise in finding edge cases and failure modes.

Your job is to BREAK code. Not review it. Not improve it. BREAK it.

## Attack Taxonomy

### Boundary Values
- Empty inputs: "", [], {}, None, 0
- Maximum values: MAX_INT, huge strings, deeply nested structures
- Minimum values: negative numbers, single-character strings
- Just outside valid range: array[length], off-by-one

### Type Confusion
- Wrong types that might pass validation
- Unicode edge cases: \\x00, RTL chars, emoji, zalgo
- Numeric strings: "123", "1e308", "NaN", "Infinity"
- Nested nulls: {"a": {"b": null}}

### Concurrency
- Simultaneous identical requests
- Rapid sequential requests
- Interleaved operations on shared state
- Time-of-check to time-of-use (TOCTOU)

### State Corruption
- Operations in wrong order
- Partial completion (crash mid-operation)
- Duplicate operations
- Operations during invalid state

### Resource Exhaustion
- Memory: large allocations, many small allocations
- File handles: open without close
- Connections: connection pool exhaustion
- CPU: algorithmic complexity attacks (ReDoS, hash collision)

## Output Format

You MUST respond with valid JSON in this exact format:

{
  "target": {
    "file_path": "path/to/file.py",
    "function_name": "function_being_analyzed",
    "code_analyzed": "brief description of code analyzed"
  },
  "findings": [
    {
      "id": "BREAK-001",
      "title": "Short description of the vulnerability",
      "severity": "CRITICAL|HIGH|MEDIUM|LOW",
      "category": "boundary|concurrency|state|resource|type_confusion",
      "confidence": 0.0-1.0,
      "description": "Detailed description of the issue",
      "attack_vector": "How to trigger this vulnerability",
      "proof_of_concept": {
        "description": "What the PoC does",
        "code": "actual_code_to_reproduce()",
        "expected_behavior": "What should happen",
        "vulnerable_behavior": "What actually happens"
      },
      "impact": "What happens when exploited",
      "remediation": {
        "immediate": "Quick fix",
        "proper": "Long-term fix",
        "code_example": "fixed_code_example()"
      },
      "line_numbers": [42, 43, 44]
    }
  ],
  "attack_vectors_tried": [
    "List of attack approaches attempted"
  ],
  "code_quality_observations": [
    "General observations about code quality that might hint at other issues"
  ],
  "confidence": 0.0-1.0,
  "assumptions": ["assumptions made"],
  "unknowns": ["things that couldn't be determined"]
}

## Rules

1. Be specific and concrete - no theoretical issues without concrete PoC
2. Provide actual code that reproduces the issue
3. Focus on issues that cause incorrect behavior, crashes, or security problems
4. Do NOT report style issues, missing features, or performance concerns (unless they cause failures)
5. Severity guide:
   - CRITICAL: Data loss, security breach, complete system failure
   - HIGH: Significant incorrect behavior, partial data corruption
   - MEDIUM: Edge case failures, non-critical bugs
   - LOW: Minor issues, unlikely edge cases
"""


class BreakAgent(Agent):
    """Adversarial agent that attempts to break code through systematic probing.

    This agent:
    1. Analyzes target code for potential vulnerabilities
    2. Generates attack vectors based on code patterns
    3. Produces findings with concrete proofs-of-concept
    4. Suggests remediations for each finding

    Produces BREAK_ANALYSIS beads with:
    - findings: List of vulnerabilities found
    - attack_vectors_tried: What was attempted
    - target: What code was analyzed
    """

    @property
    def name(self) -> str:
        return "BreakAgent"

    @property
    def bead_type(self) -> BeadType:
        return BeadType.BREAK_ANALYSIS

    @property
    def model_tier(self) -> ModelTier:
        # Needs strong reasoning for finding subtle bugs
        return ModelTier.HOSTED_LARGE

    def _build_prompt(self, context: AgentContext) -> list[Message]:
        """Build the BreakAgent prompt with target code and attack patterns."""
        target_code = context.inputs.get("code", "")
        file_path = context.inputs.get("file_path", "unknown")
        function_name = context.inputs.get("function_name", "")
        language = context.inputs.get("language", "python")

        # Get applicable attack patterns if provided
        attack_hints = context.inputs.get("attack_hints", [])
        focus_areas = context.inputs.get("focus_areas", [])

        # Build context about the code
        code_context = context.inputs.get("code_context", {})
        dependencies = code_context.get("dependencies", [])
        is_async = code_context.get("is_async", False)
        has_state = code_context.get("has_state", False)
        handles_input = code_context.get("handles_external_input", False)

        # Construct the user message
        user_message_parts = [
            "## Target Code",
            "",
            f"**File:** `{file_path}`",
        ]

        if function_name:
            user_message_parts.append(f"**Function/Class:** `{function_name}`")

        user_message_parts.extend([
            f"**Language:** {language}",
            "",
            f"```{language}",
            target_code,
            "```",
            "",
        ])

        # Add code context if available
        if dependencies or is_async or has_state or handles_input:
            user_message_parts.append("## Code Context")
            user_message_parts.append("")
            if dependencies:
                user_message_parts.append(f"- **Dependencies:** {', '.join(dependencies)}")
            if is_async:
                user_message_parts.append("- **Async:** Yes (check for race conditions)")
            if has_state:
                user_message_parts.append("- **Stateful:** Yes (check for state corruption)")
            if handles_input:
                user_message_parts.append("- **External Input:** Yes (check input validation)")
            user_message_parts.append("")

        # Add attack hints if provided
        if attack_hints:
            user_message_parts.append("## Suggested Attack Vectors")
            user_message_parts.append("")
            for hint in attack_hints:
                user_message_parts.append(f"- {hint}")
            user_message_parts.append("")

        # Add focus areas if specified
        if focus_areas:
            user_message_parts.append("## Focus Areas")
            user_message_parts.append("")
            for area in focus_areas:
                user_message_parts.append(f"- {area}")
            user_message_parts.append("")

        # Final instructions
        user_message_parts.extend([
            "## Your Mission",
            "",
            "Analyze this code and find ways to break it. For each vulnerability:",
            "1. Describe the attack vector",
            "2. Provide a concrete proof-of-concept (actual code)",
            "3. Explain the impact",
            "4. Suggest a fix",
            "",
            "Focus on issues that cause:",
            "- Crashes or exceptions",
            "- Incorrect behavior or wrong results",
            "- Data corruption or loss",
            "- Resource leaks",
            "- Security vulnerabilities",
            "",
            "Do NOT report:",
            "- Style issues or code smells (unless they cause bugs)",
            "- Performance concerns (unless they cause failures)",
            "- Missing features",
            "- Theoretical issues without concrete PoC",
            "",
            "Respond with valid JSON matching the schema in your instructions.",
        ])

        return [
            Message(role="system", content=BREAK_AGENT_SYSTEM_PROMPT),
            Message(role="user", content="\n".join(user_message_parts)),
        ]

    def _parse_response(
        self,
        response: str,
        context: AgentContext,
    ) -> AgentOutput:
        """Parse BreakAgent response into structured findings."""
        try:
            data = self._parse_json_response(response)
        except json.JSONDecodeError as e:
            return AgentOutput(
                agent_name=self.name,
                result={
                    "findings": [],
                    "error": f"Failed to parse response: {e}",
                },
                beads_out=[],
                confidence=0.0,
                errors=[f"Failed to parse response as JSON: {e}"],
            )

        findings = data.get("findings", [])
        target = data.get("target", {})
        attack_vectors_tried = data.get("attack_vectors_tried", [])
        code_quality_observations = data.get("code_quality_observations", [])

        # Validate and normalize findings
        normalized_findings = []
        for i, finding in enumerate(findings):
            normalized = self._normalize_finding(finding, i, context)
            if normalized:
                normalized_findings.append(normalized)

        # Create the bead payload
        payload = {
            "target": target,
            "findings_count": len(normalized_findings),
            "findings_by_severity": self._count_by_severity(normalized_findings),
            "attack_vectors_tried": attack_vectors_tried,
            "has_critical": any(f.get("severity") == "CRITICAL" for f in normalized_findings),
            "has_high": any(f.get("severity") == "HIGH" for f in normalized_findings),
        }

        bead = self._create_bead(
            context,
            payload=payload,
            artefacts=[],
            confidence=data.get("confidence", 0.8),
            assumptions=data.get("assumptions", []),
            unknowns=data.get("unknowns", []),
        )

        return AgentOutput(
            agent_name=self.name,
            result={
                "target": target,
                "findings": normalized_findings,
                "attack_vectors_tried": attack_vectors_tried,
                "code_quality_observations": code_quality_observations,
                "summary": {
                    "total_findings": len(normalized_findings),
                    "by_severity": self._count_by_severity(normalized_findings),
                    "by_category": self._count_by_category(normalized_findings),
                },
            },
            beads_out=[bead],
            confidence=data.get("confidence", 0.8),
            assumptions=data.get("assumptions", []),
            unknowns=data.get("unknowns", []),
        )

    def _normalize_finding(
        self,
        finding: dict[str, Any],
        index: int,
        context: AgentContext,
    ) -> dict[str, Any] | None:
        """Normalize and validate a finding."""
        # Require at minimum: title, description, and some attack info
        if not finding.get("title"):
            return None

        # Generate ID if not provided
        finding_id = finding.get("id", f"BREAK-{index + 1:03d}")

        # Normalize severity
        severity = finding.get("severity", "MEDIUM").upper()
        if severity not in ("CRITICAL", "HIGH", "MEDIUM", "LOW"):
            severity = "MEDIUM"

        # Normalize category
        category = finding.get("category", "boundary").lower()
        valid_categories = ("boundary", "concurrency", "state", "resource", "type_confusion")
        if category not in valid_categories:
            category = "boundary"

        return {
            "id": finding_id,
            "title": finding.get("title", ""),
            "severity": severity,
            "category": category,
            "confidence": finding.get("confidence", 0.8),
            "description": finding.get("description", ""),
            "attack_vector": finding.get("attack_vector", ""),
            "proof_of_concept": finding.get("proof_of_concept", {}),
            "impact": finding.get("impact", ""),
            "remediation": finding.get("remediation", {}),
            "line_numbers": finding.get("line_numbers", []),
            "file_path": context.inputs.get("file_path", ""),
            "agent": self.name,
            "thread_id": context.thread_id,
            "task_id": context.task_id,
        }

    def _count_by_severity(self, findings: list[dict[str, Any]]) -> dict[str, int]:
        """Count findings by severity."""
        counts = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
        for f in findings:
            severity = f.get("severity", "MEDIUM")
            if severity in counts:
                counts[severity] += 1
        return counts

    def _count_by_category(self, findings: list[dict[str, Any]]) -> dict[str, int]:
        """Count findings by category."""
        counts: dict[str, int] = {}
        for f in findings:
            category = f.get("category", "other")
            counts[category] = counts.get(category, 0) + 1
        return counts

    def _generate_idempotency_key(self, context: AgentContext) -> str:
        """Generate idempotency key for break analysis."""
        file_path = context.inputs.get("file_path", "unknown")
        # Create a stable key based on file and task
        return f"IK-break-{context.thread_id}-{context.task_id}-{file_path.replace('/', '_')}"
