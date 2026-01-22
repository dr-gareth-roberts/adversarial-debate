"""ChaosAgent - Adversarial agent for resilience testing through chaos engineering.

This agent designs chaos experiments to test system resilience by analyzing code for:
- Dependency failures (database, cache, external APIs)
- Network chaos (latency, packet loss, partitions)
- Resource pressure (memory, CPU, disk, connections)
- Time chaos (clock skew, timezone issues)
- State chaos (corruption, duplicates, ordering)

Unlike BreakAgent which finds bugs, ChaosAgent identifies resilience gaps and proposes
experiments to verify the system's failure handling.
"""

import json
from typing import Any

from ..providers import Message, ModelTier
from ..store import BeadType
from .base import Agent, AgentContext, AgentOutput

CHAOS_AGENT_SYSTEM_PROMPT = """You are a chaos engineer designing experiments to test system resilience.

Your job is to identify how code might fail under adverse conditions and design safe experiments to verify resilience.

## Chaos Experiment Categories

### Dependency Failures
- Database unavailable (connection refused)
- Database slow (5+ second latency)
- Database returns errors (deadlock, constraint violation)
- Cache unavailable (Redis down)
- Cache returns stale data
- External API timeout (30+ seconds)
- External API returns 5xx errors
- External API returns malformed data

### Network Chaos
- High latency (500ms+ added to all calls)
- Packet loss (10%, 50%, 90%)
- Network partition (can't reach specific service)
- DNS failure (NXDOMAIN, timeout)
- Connection reset mid-request
- SSL/TLS errors (certificate expired, handshake failure)

### Resource Pressure
- Memory pressure (approaching OOM)
- CPU saturation (100% utilization)
- Disk full
- File descriptor exhaustion
- Connection pool exhaustion
- Thread pool exhaustion

### Time Chaos
- Clock skew forward (NTP jump, VM resume)
- Clock skew backward (rare but happens)
- Leap second handling
- Timezone changes at runtime
- Slow system clock (clock drift)

### State Chaos
- Corrupted data in storage/cache
- Inconsistent state between services
- Duplicate messages/events
- Out-of-order messages
- Missing messages

## Analysis Framework

For the target code, analyze:

1. **DEPENDENCIES**: What external systems does this code depend on?
2. **FAILURE MODES**: For each dependency, what happens if it fails?
3. **FALLBACKS**: Does the code have fallback behavior?
4. **TIMEOUTS**: Are there appropriate timeouts?
5. **RETRIES**: Is there retry logic? Is it safe (idempotent)?
6. **CIRCUIT BREAKERS**: Is there circuit breaker pattern?
7. **GRACEFUL DEGRADATION**: Can the system partially function?

## Output Format

You MUST respond with valid JSON in this exact format:

{
  "target": {
    "file_path": "path/to/file.py",
    "function_name": "function_being_analyzed",
    "code_analyzed": "brief description"
  },
  "dependencies_detected": [
    {
      "name": "PostgreSQL Database",
      "type": "database|cache|api|filesystem|queue",
      "evidence": ["connection = psycopg2.connect()", "cursor.execute(query)"],
      "criticality": "critical|important|optional"
    }
  ],
  "resilience_analysis": {
    "has_timeouts": true/false,
    "has_retries": true/false,
    "has_circuit_breaker": true/false,
    "has_fallbacks": true/false,
    "has_health_checks": true/false,
    "overall_resilience_score": 0-100
  },
  "experiments": [
    {
      "id": "CHAOS-001",
      "title": "Short description of experiment",
      "category": "dependency_failure|network_chaos|resource_pressure|time_chaos|state_chaos",
      "target_dependency": "What component/service is targeted",
      "failure_mode": "unavailable|timeout|slow|error|corrupt|intermittent",
      "severity_if_vulnerable": "CRITICAL|HIGH|MEDIUM|LOW",
      "experiment": {
        "description": "What this experiment does",
        "method": "How to run it (tc, toxiproxy, docker stop, etc)",
        "duration_seconds": 60,
        "safe_to_automate": true/false,
        "requires_isolation": true/false,
        "rollback": "How to restore normal operation"
      },
      "hypothesis": {
        "expected_resilient_behavior": "What should happen if code is resilient",
        "predicted_actual_behavior": "What will actually happen based on code analysis",
        "prediction_confidence": 0.0-1.0
      },
      "evidence": {
        "code_location": "file.py:42",
        "problematic_code": "The specific code that's vulnerable",
        "missing_patterns": ["What resilience patterns are missing"]
      },
      "remediation": {
        "immediate": "Quick fix to add resilience",
        "proper": "Proper long-term fix",
        "code_example": "Example of resilient code"
      }
    }
  ],
  "confidence": 0.0-1.0,
  "assumptions": ["assumptions made"],
  "unknowns": ["things that couldn't be determined"]
}

## Rules

1. Focus on experiments that reveal real weaknesses
2. Every experiment must be safely executable
3. Include rollback instructions for each experiment
4. Differentiate between "will definitely fail" and "might fail"
5. Prioritize experiments by impact and likelihood
6. Consider both individual failures and cascading effects
"""


class ChaosAgent(Agent):
    """Chaos engineering agent that tests system resilience.

    This agent:
    1. Analyzes code to identify dependencies and failure points
    2. Designs chaos experiments to test resilience
    3. Predicts behavior under failure conditions
    4. Suggests resilience improvements

    Produces CHAOS_ANALYSIS beads with:
    - experiments: List of proposed chaos experiments
    - dependencies_detected: What the code depends on
    - resilience_analysis: Current resilience posture
    """

    @property
    def name(self) -> str:
        return "ChaosAgent"

    @property
    def bead_type(self) -> BeadType:
        return BeadType.CHAOS_ANALYSIS

    @property
    def model_tier(self) -> ModelTier:
        # More structured output, moderate reasoning needed
        return ModelTier.HOSTED_SMALL

    def _build_prompt(self, context: AgentContext) -> list[Message]:
        """Build the ChaosAgent prompt with infrastructure context."""
        target_code = context.inputs.get("code", "")
        file_path = context.inputs.get("file_path", "unknown")
        function_name = context.inputs.get("function_name", "")
        language = context.inputs.get("language", "python")

        # Infrastructure context
        infra_context = context.inputs.get("infrastructure", {})
        dependencies = infra_context.get("dependencies", [])
        external_services = infra_context.get("external_services", [])
        database = infra_context.get("database", "unknown")
        cache = infra_context.get("cache", "none")
        message_queue = infra_context.get("queue", "none")

        # Focus areas for chaos testing
        focus_areas = context.inputs.get("focus_areas", [])
        exclude_categories = context.inputs.get("exclude_categories", [])

        # Build the user message
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

        # Add infrastructure context
        user_message_parts.append("## Infrastructure Context")
        user_message_parts.append("")

        if dependencies:
            user_message_parts.append(f"- **Known Dependencies:** {', '.join(dependencies)}")
        if external_services:
            user_message_parts.append(f"- **External Services:** {', '.join(external_services)}")
        if database and database != "unknown":
            user_message_parts.append(f"- **Database:** {database}")
        if cache and cache != "none":
            user_message_parts.append(f"- **Cache:** {cache}")
        if message_queue and message_queue != "none":
            user_message_parts.append(f"- **Message Queue:** {message_queue}")

        if not any([dependencies, external_services, database != "unknown", cache != "none"]):
            user_message_parts.append("- Infer dependencies from code patterns")

        user_message_parts.append("")

        # Add focus areas if specified
        if focus_areas:
            user_message_parts.append("## Focus Areas")
            user_message_parts.append("")
            for area in focus_areas:
                user_message_parts.append(f"- {area}")
            user_message_parts.append("")

        # Add exclusions if specified
        if exclude_categories:
            user_message_parts.append("## Exclude These Categories")
            user_message_parts.append("")
            for cat in exclude_categories:
                user_message_parts.append(f"- {cat}")
            user_message_parts.append("")

        # Final instructions
        user_message_parts.extend([
            "## Your Mission",
            "",
            "Design chaos experiments to test this code's resilience. For each experiment:",
            "1. What failure are you simulating?",
            "2. What is the expected resilient behavior?",
            "3. What will actually happen (based on code analysis)?",
            "4. How to run the experiment safely",
            "5. How to remediate any gaps found",
            "",
            "Focus on:",
            "- What happens when dependencies fail?",
            "- What happens under resource pressure?",
            "- What happens with network issues?",
            "- What happens with timing/clock issues?",
            "",
            "Respond with valid JSON matching the schema in your instructions.",
        ])

        return [
            Message(role="system", content=CHAOS_AGENT_SYSTEM_PROMPT),
            Message(role="user", content="\n".join(user_message_parts)),
        ]

    def _parse_response(
        self,
        response: str,
        context: AgentContext,
    ) -> AgentOutput:
        """Parse ChaosAgent response into structured experiments."""
        try:
            data = self._parse_json_response(response)
        except json.JSONDecodeError as e:
            return AgentOutput(
                agent_name=self.name,
                result={
                    "experiments": [],
                    "error": f"Failed to parse response: {e}",
                },
                beads_out=[],
                confidence=0.0,
                errors=[f"Failed to parse response as JSON: {e}"],
            )

        experiments = data.get("experiments", [])
        target = data.get("target", {})
        dependencies = data.get("dependencies_detected", [])
        resilience_analysis = data.get("resilience_analysis", {})

        # Validate and normalize experiments
        normalized_experiments = []
        for i, exp in enumerate(experiments):
            normalized = self._normalize_experiment(exp, i, context)
            if normalized:
                normalized_experiments.append(normalized)

        # Calculate risk assessment
        risk_assessment = self._assess_risk(normalized_experiments, resilience_analysis)

        # Create the bead payload
        payload = {
            "target": target,
            "experiments_count": len(normalized_experiments),
            "experiments_by_category": self._count_by_category(normalized_experiments),
            "dependencies_detected": len(dependencies),
            "resilience_score": resilience_analysis.get("overall_resilience_score", 0),
            "risk_assessment": risk_assessment,
            "high_risk_count": sum(
                1 for e in normalized_experiments
                if e.get("severity_if_vulnerable") in ("CRITICAL", "HIGH")
            ),
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
                "dependencies_detected": dependencies,
                "resilience_analysis": resilience_analysis,
                "experiments": normalized_experiments,
                "risk_assessment": risk_assessment,
                "summary": {
                    "total_experiments": len(normalized_experiments),
                    "by_category": self._count_by_category(normalized_experiments),
                    "by_severity": self._count_by_severity(normalized_experiments),
                    "automatable": sum(
                        1 for e in normalized_experiments
                        if e.get("experiment", {}).get("safe_to_automate", False)
                    ),
                },
            },
            beads_out=[bead],
            confidence=data.get("confidence", 0.8),
            assumptions=data.get("assumptions", []),
            unknowns=data.get("unknowns", []),
        )

    def _normalize_experiment(
        self,
        experiment: dict[str, Any],
        index: int,
        context: AgentContext,
    ) -> dict[str, Any] | None:
        """Normalize and validate an experiment."""
        if not experiment.get("title"):
            return None

        experiment_block = experiment.get("experiment", {})
        if not experiment_block.get("rollback"):
            return None

        # Generate ID if not provided
        exp_id = experiment.get("id", f"CHAOS-{index + 1:03d}")

        # Normalize category
        category = experiment.get("category", "dependency_failure").lower()
        valid_categories = (
            "dependency_failure",
            "network_chaos",
            "resource_pressure",
            "time_chaos",
            "state_chaos",
        )
        if category not in valid_categories:
            category = "dependency_failure"

        # Normalize failure mode
        failure_mode = experiment.get("failure_mode", "unavailable").lower()
        valid_modes = (
            "unavailable",
            "timeout",
            "slow",
            "error",
            "corrupt",
            "intermittent",
            "partial",
        )
        if failure_mode not in valid_modes:
            failure_mode = "unavailable"

        # Normalize severity
        severity = experiment.get("severity_if_vulnerable", "MEDIUM").upper()
        if severity not in ("CRITICAL", "HIGH", "MEDIUM", "LOW"):
            severity = "MEDIUM"

        return {
            "id": exp_id,
            "title": experiment.get("title", ""),
            "category": category,
            "target_dependency": experiment.get("target_dependency", ""),
            "failure_mode": failure_mode,
            "severity_if_vulnerable": severity,
            "experiment": {
                "description": experiment_block.get("description", ""),
                "method": experiment_block.get("method", ""),
                "duration_seconds": experiment_block.get("duration_seconds", 60),
                "safe_to_automate": experiment_block.get("safe_to_automate", False),
                "requires_isolation": experiment_block.get("requires_isolation", False),
                "rollback": experiment_block.get("rollback", ""),
            },
            "hypothesis": experiment.get("hypothesis", {}),
            "evidence": experiment.get("evidence", {}),
            "remediation": experiment.get("remediation", {}),
            "file_path": context.inputs.get("file_path", ""),
            "agent": self.name,
            "thread_id": context.thread_id,
            "task_id": context.task_id,
        }

    def _assess_risk(
        self,
        experiments: list[dict[str, Any]],
        resilience_analysis: dict[str, Any],
    ) -> dict[str, Any]:
        """Assess overall risk based on experiments and resilience."""
        if not experiments:
            return {
                "level": "UNKNOWN",
                "score": 0,
                "summary": "No experiments generated",
            }

        # Count high-severity vulnerabilities
        critical_count = sum(
            1 for e in experiments
            if e.get("severity_if_vulnerable") == "CRITICAL"
        )
        high_count = sum(
            1 for e in experiments
            if e.get("severity_if_vulnerable") == "HIGH"
        )

        # Get resilience score
        resilience_score = resilience_analysis.get("overall_resilience_score", 50)

        # Calculate risk score (higher = more risk)
        risk_score = (
            critical_count * 25 +
            high_count * 15 +
            (100 - resilience_score)
        )

        # Normalize to 0-100
        risk_score = min(100, max(0, risk_score))

        # Determine risk level
        if risk_score >= 75 or critical_count > 0:
            level = "CRITICAL"
        elif risk_score >= 50 or high_count > 1:
            level = "HIGH"
        elif risk_score >= 25:
            level = "MEDIUM"
        else:
            level = "LOW"

        # Generate summary
        issues = []
        if not resilience_analysis.get("has_timeouts"):
            issues.append("missing timeouts")
        if not resilience_analysis.get("has_retries"):
            issues.append("no retry logic")
        if not resilience_analysis.get("has_circuit_breaker"):
            issues.append("no circuit breaker")
        if not resilience_analysis.get("has_fallbacks"):
            issues.append("no fallback behavior")

        summary = f"Risk {level}"
        if issues:
            summary += f": {', '.join(issues[:3])}"

        return {
            "level": level,
            "score": risk_score,
            "critical_experiments": critical_count,
            "high_experiments": high_count,
            "resilience_score": resilience_score,
            "missing_patterns": issues,
            "summary": summary,
        }

    def _count_by_category(self, experiments: list[dict[str, Any]]) -> dict[str, int]:
        """Count experiments by category."""
        counts: dict[str, int] = {}
        for e in experiments:
            category = e.get("category", "other")
            counts[category] = counts.get(category, 0) + 1
        return counts

    def _count_by_severity(self, experiments: list[dict[str, Any]]) -> dict[str, int]:
        """Count experiments by severity."""
        counts = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
        for e in experiments:
            severity = e.get("severity_if_vulnerable", "MEDIUM")
            if severity in counts:
                counts[severity] += 1
        return counts

    def _generate_idempotency_key(self, context: AgentContext) -> str:
        """Generate idempotency key for chaos analysis."""
        file_path = context.inputs.get("file_path", "unknown")
        return f"IK-chaos-{context.thread_id}-{context.task_id}-{file_path.replace('/', '_')}"
