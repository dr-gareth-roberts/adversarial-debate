"""ChaosOrchestrator - Coordinates red team agents for adversarial testing.

This agent analyzes code changes and creates attack plans that assign work
to BreakAgent, ExploitAgent, and ChaosAgent based on:
- File types and contents
- Historical vulnerability patterns
- Risk assessment of changes
- Available time budget
"""

import contextlib
import json
import uuid
from typing import Any

from ..attack_plan import (
    AgentType,
    Attack,
    AttackPlan,
    AttackPriority,
    AttackSurface,
    AttackVector,
    FileRiskProfile,
    ParallelGroup,
    RiskLevel,
    SkipReason,
)
from ..providers import Message, ModelTier
from ..store import BeadType
from .base import Agent, AgentContext, AgentOutput

CHAOS_ORCHESTRATOR_SYSTEM_PROMPT = """\
You are a red team coordinator planning adversarial attacks against
code changes.

Your job is to analyze code changes and create an attack plan that assigns work to three specialized
agents:

## Red Team Agents

### BreakAgent
- Finds logic errors, edge cases, race conditions
- Best for: Complex algorithms, state machines, concurrent code, input validation
- Attack vectors: Boundary values, type confusion, state corruption, resource exhaustion

### ExploitAgent
- Finds security vulnerabilities (OWASP Top 10)
- Best for: User input handling, authentication, data access, external integrations
- Attack vectors: SQL injection, XSS, command injection, IDOR, SSRF, etc.

### ChaosAgent
- Tests resilience to infrastructure failures
- Best for: External dependencies, network calls, database access, caching
- Attack vectors: Dependency failures, timeouts, network issues, resource pressure

### CryptoAgent
- Finds cryptographic and auth-adjacent weaknesses
- Best for: Password hashing, token/JWT handling, key management, randomness
- Attack vectors: weak algorithms, hardcoded secrets, predictable randomness, timing issues

## Risk Assessment Factors

Consider these when prioritizing:
- **Exposure**: Public-facing code is higher risk than internal
- **Data sensitivity**: Code handling PII, credentials, or financial data is critical
- **Complexity**: Complex logic is more likely to have bugs
- **Change size**: Larger changes have more attack surface
- **Historical patterns**: Similar code that had vulnerabilities before

## Output Format

You MUST respond with valid JSON in this exact format:

{
  "attack_surface_analysis": {
    "files": [
      {
        "file_path": "path/to/file.py",
        "risk_score": 85,
        "risk_factors": ["handles user input", "database queries"],
        "recommended_agents": ["ExploitAgent", "BreakAgent"],
        "attack_vectors": ["SQL injection", "boundary values"],
        "exposure": "public",
        "data_sensitivity": "high"
      }
    ],
    "total_risk_score": 85,
    "highest_risk_file": "path/to/file.py",
    "primary_concerns": ["list of main security/stability concerns"],
    "recommended_focus_areas": ["where to spend most effort"]
  },
  "risk_level": "HIGH",
  "risk_factors": ["list of overall risk factors"],
  "attacks": [
    {
      "id": "ATK-001",
      "agent": "ExploitAgent",
      "target_file": "path/to/file.py",
      "target_function": null,
      "priority": 1,
      "attack_vectors": [
        {
          "name": "SQL Injection",
          "description": "Test user_id parameter for SQL injection",
          "category": "injection",
          "payload_hints": ["' OR '1'='1", "'; DROP TABLE--"],
          "expected_behavior": "Query should be parameterized",
          "success_indicators": ["returns all rows", "SQL error in response"]
        }
      ],
      "time_budget_seconds": 60,
      "rationale": "Why this attack is important",
      "depends_on": [],
      "can_parallel_with": ["ATK-002", "ATK-003"],
      "hints": ["Check the query construction on line 42"]
    }
  ],
  "parallel_groups": [
    {
      "group_id": "PG-001",
      "attack_ids": ["ATK-001", "ATK-002"],
      "estimated_duration_seconds": 120
    }
  ],
  "execution_order": ["ATK-001", "ATK-002", "ATK-003"],
  "skipped": [
    {
      "target": "path/to/safe_file.py",
      "reason": "Static configuration with no user input",
      "category": "low_risk"
    }
  ],
  "recommendations": ["Overall recommendations for the red team"],
  "confidence": 0.8,
  "assumptions": ["assumptions made"],
  "unknowns": ["things that couldn't be determined"]
}

Field constraints:
- risk_level: one of LOW|MEDIUM|HIGH|CRITICAL
- attacks[].agent: one of BreakAgent|ExploitAgent|ChaosAgent|CryptoAgent
- risk_score, total_risk_score: integer 0-100
- priority: integer 1-5 (1 = highest priority)
- confidence: float 0.0-1.0
- exposure: one of public|authenticated|internal
- data_sensitivity: one of high|medium|low
- target_function: string or null

## Rules

1. Assign the RIGHT agent for each target - don't use ExploitAgent for resilience testing
2. Higher priority (lower number) for higher risk targets
3. Group independent attacks for parallel execution
4. Skip low-value targets with explanation
5. Include specific attack vectors and hints for each assignment
6. Consider dependencies - some attacks should run after others
7. Be thorough but practical - focus effort where it matters most
"""


class ChaosOrchestrator(Agent):
    """Orchestrator that coordinates red team agents.

    This agent:
    1. Analyzes code changes to identify attack surface
    2. Assesses risk level and prioritizes targets
    3. Assigns work to appropriate red team agents
    4. Creates execution plan with parallelization

    Produces ATTACK_PLAN beads with:
    - attack_plan: Structured plan for red team execution
    - risk_assessment: Overall risk level and factors
    - attack_surface: Analysis of vulnerable areas
    """

    @property
    def name(self) -> str:
        return "ChaosOrchestrator"

    @property
    def bead_type(self) -> BeadType:
        return BeadType.ATTACK_PLAN

    @property
    def model_tier(self) -> ModelTier:
        # Needs to understand code and make strategic decisions
        return ModelTier.HOSTED_SMALL

    def _build_prompt(self, context: AgentContext) -> list[Message]:
        """Build prompt with code changes and context."""
        # Get changed files and their contents
        changed_files = context.inputs.get("changed_files", [])
        patches = context.inputs.get("patches", {})
        patches_summary = context.inputs.get("patches_summary", "")

        # Codebase context
        framework = context.inputs.get("framework", "unknown")
        language = context.inputs.get("language", "python")
        exposure = context.inputs.get("exposure", "internal")

        # Historical data
        historical_findings = context.inputs.get("historical_findings", [])
        agent_success_rates = context.inputs.get("agent_success_rates", {})

        # Time budget
        time_budget = context.inputs.get("time_budget_seconds", 300)

        # Build user message
        user_parts = ["## Code Changes to Analyze", ""]

        if changed_files:
            user_parts.extend(["### Changed Files", ""])
            for f in changed_files:
                if isinstance(f, dict):
                    path = f.get("path", f)
                    change_type = f.get("change_type", "modified")
                    user_parts.append(f"- `{path}` ({change_type})")
                else:
                    user_parts.append(f"- `{f}`")
            user_parts.append("")

        if patches:
            user_parts.extend(["### Patches", ""])
            for file_path, patch in patches.items():
                user_parts.extend([f"**{file_path}:**", "```diff"])
                # Limit patch size
                if len(patch) > 2000:
                    user_parts.append(patch[:2000] + "\n... (truncated)")
                else:
                    user_parts.append(patch)
                user_parts.extend(["```", ""])
        elif patches_summary:
            user_parts.extend(["### Patches Summary", "", patches_summary, ""])

        # Codebase context
        user_parts.extend(
            [
                "## Codebase Context",
                "",
                f"- **Framework:** {framework}",
                f"- **Language:** {language}",
                f"- **Exposure:** {exposure}",
                "",
            ]
        )

        # Historical findings
        if historical_findings:
            user_parts.extend(
                ["## Historical Red Team Data", "", "Previous findings in similar code:"]
            )
            for finding in historical_findings[:5]:  # Limit to 5
                if isinstance(finding, dict):
                    kind = finding.get("type", "unknown")
                    description = finding.get("description", "")
                    user_parts.append(f"- {kind}: {description}")
                else:
                    user_parts.append(f"- {finding}")
            user_parts.append("")

        # Agent success rates
        if agent_success_rates:
            user_parts.append("Agent success rates:")
            user_parts.extend(f"- {agent}: {rate}" for agent, rate in agent_success_rates.items())
            user_parts.append("")

        # Constraints
        user_parts.extend(
            [
                "## Constraints",
                "",
                f"- **Time budget:** {time_budget} seconds total",
                "- **Max parallel agents:** 3",
                "",
            ]
        )

        # Mission
        user_parts.extend(
            [
                "## Your Mission",
                "",
                "Create an attack plan that:",
                "1. Identifies the attack surface in these changes",
                "2. Assigns appropriate red team agents to targets",
                "3. Prioritizes based on risk",
                "4. Optimizes for parallel execution",
                "5. Skips low-value targets with explanation",
                "",
                "Respond with valid JSON matching the schema in your instructions.",
            ]
        )

        return [
            Message(role="system", content=CHAOS_ORCHESTRATOR_SYSTEM_PROMPT),
            Message(role="user", content="\n".join(user_parts)),
        ]

    def _parse_response(
        self,
        response: str,
        context: AgentContext,
    ) -> AgentOutput:
        """Parse response into structured attack plan."""
        try:
            data = self._parse_json_response(response)
        except json.JSONDecodeError as e:
            return AgentOutput(
                agent_name=self.name,
                result={
                    "attack_plan": None,
                    "error": f"Failed to parse response: {e}",
                },
                beads_out=[],
                confidence=0.0,
                errors=[f"Failed to parse response as JSON: {e}"],
            )

        # Parse attack surface analysis
        attack_surface = self._parse_attack_surface(data.get("attack_surface_analysis", {}))

        # Parse attacks
        attacks = self._parse_attacks(data.get("attacks", []), context)

        # Parse parallel groups
        parallel_groups = self._parse_parallel_groups(data.get("parallel_groups", []))

        # Parse skipped items
        skipped = self._parse_skipped(data.get("skipped", []))

        # Create attack plan
        plan = AttackPlan(
            plan_id=f"PLAN-{uuid.uuid4().hex[:8]}",
            thread_id=context.thread_id,
            task_id=context.task_id,
            risk_level=self._parse_risk_level(data.get("risk_level", "MEDIUM")),
            risk_factors=data.get("risk_factors", []),
            risk_score=attack_surface.total_risk_score if attack_surface else 50,
            attacks=attacks,
            parallel_groups=parallel_groups,
            execution_order=data.get("execution_order", [a.id for a in attacks]),
            skipped=skipped,
            estimated_total_duration_seconds=sum(a.time_budget_seconds for a in attacks),
            attack_surface_summary=self._summarize_attack_surface(attack_surface),
            recommendations=data.get("recommendations", []),
        )

        # Create bead payload
        payload = {
            "plan_id": plan.plan_id,
            "risk_level": plan.risk_level.value,
            "risk_score": plan.risk_score,
            "attack_count": len(plan.attacks),
            "attacks_by_agent": {
                "BreakAgent": len(plan.get_attacks_by_agent(AgentType.BREAK_AGENT)),
                "ExploitAgent": len(plan.get_attacks_by_agent(AgentType.EXPLOIT_AGENT)),
                "ChaosAgent": len(plan.get_attacks_by_agent(AgentType.CHAOS_AGENT)),
                "CryptoAgent": len(plan.get_attacks_by_agent(AgentType.CRYPTO_AGENT)),
            },
            "parallel_groups": len(plan.parallel_groups),
            "skipped_count": len(plan.skipped),
            "estimated_duration": plan.estimated_total_duration_seconds,
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
                "attack_plan": plan.to_dict(),
                "attack_surface": attack_surface.to_dict() if attack_surface else None,
                "summary": {
                    "risk_level": plan.risk_level.value,
                    "total_attacks": len(plan.attacks),
                    "by_agent": payload["attacks_by_agent"],
                    "by_priority": {
                        "critical": len(plan.get_attacks_by_priority(AttackPriority.CRITICAL)),
                        "high": len(plan.get_attacks_by_priority(AttackPriority.HIGH)),
                        "medium": len(plan.get_attacks_by_priority(AttackPriority.MEDIUM)),
                        "low": len(plan.get_attacks_by_priority(AttackPriority.LOW)),
                    },
                    "parallel_groups": len(plan.parallel_groups),
                    "skipped": len(plan.skipped),
                    "estimated_duration_seconds": plan.estimated_total_duration_seconds,
                },
            },
            beads_out=[bead],
            confidence=data.get("confidence", 0.8),
            assumptions=data.get("assumptions", []),
            unknowns=data.get("unknowns", []),
        )

    def _parse_attack_surface(self, data: dict[str, Any]) -> AttackSurface | None:
        """Parse attack surface analysis from response."""
        if not data:
            return None

        files = []
        for f in data.get("files", []):
            agents = []
            for agent_name in f.get("recommended_agents", []):
                with contextlib.suppress(ValueError):
                    agents.append(AgentType(agent_name))

            files.append(
                FileRiskProfile(
                    file_path=f.get("file_path", ""),
                    risk_score=f.get("risk_score", 50),
                    risk_factors=f.get("risk_factors", []),
                    recommended_agents=agents,
                    attack_vectors=f.get("attack_vectors", []),
                    exposure=f.get("exposure", "internal"),
                    data_sensitivity=f.get("data_sensitivity", "medium"),
                )
            )

        return AttackSurface(
            files=files,
            total_risk_score=data.get("total_risk_score", 50),
            highest_risk_file=data.get("highest_risk_file"),
            primary_concerns=data.get("primary_concerns", []),
            recommended_focus_areas=data.get("recommended_focus_areas", []),
        )

    def _parse_attacks(
        self,
        attacks_data: list[dict[str, Any]],
        context: AgentContext,
    ) -> list[Attack]:
        """Parse attack assignments from response."""
        attacks = []

        for i, a in enumerate(attacks_data):
            # Parse agent type
            try:
                agent = AgentType(a.get("agent", "BreakAgent"))
            except ValueError:
                agent = AgentType.BREAK_AGENT

            # Parse priority
            try:
                priority = AttackPriority(a.get("priority", 3))
            except ValueError:
                priority = AttackPriority.MEDIUM

            # Parse attack vectors
            vectors = [
                AttackVector(
                    name=v.get("name", ""),
                    description=v.get("description", ""),
                    category=v.get("category", ""),
                    payload_hints=v.get("payload_hints", []),
                    expected_behavior=v.get("expected_behavior", ""),
                    success_indicators=v.get("success_indicators", []),
                )
                for v in a.get("attack_vectors", [])
            ]

            attack = Attack(
                id=a.get("id", f"ATK-{i + 1:03d}"),
                agent=agent,
                target_file=a.get("target_file", ""),
                target_function=a.get("target_function"),
                priority=priority,
                attack_vectors=vectors,
                time_budget_seconds=a.get("time_budget_seconds", 60),
                rationale=a.get("rationale", ""),
                depends_on=a.get("depends_on", []),
                can_parallel_with=a.get("can_parallel_with", []),
                code_context=a.get("code_context", {}),
                hints=a.get("hints", []),
            )
            attacks.append(attack)

        return attacks

    def _parse_parallel_groups(self, groups_data: list[dict[str, Any]]) -> list[ParallelGroup]:
        """Parse parallel execution groups from response."""
        return [
            ParallelGroup(
                group_id=g.get("group_id", f"PG-{i + 1:03d}"),
                attack_ids=g.get("attack_ids", []),
                estimated_duration_seconds=g.get("estimated_duration_seconds", 60),
                resource_requirements=g.get("resource_requirements", {}),
            )
            for i, g in enumerate(groups_data)
        ]

    def _parse_skipped(self, skipped_data: list[dict[str, Any]]) -> list[SkipReason]:
        """Parse skipped items from response."""
        return [
            SkipReason(
                target=s.get("target", ""),
                reason=s.get("reason", ""),
                category=s.get("category", "low_risk"),
            )
            for s in skipped_data
        ]

    def _parse_risk_level(self, level: str) -> RiskLevel:
        """Parse risk level string."""
        try:
            return RiskLevel(level.upper())
        except ValueError:
            return RiskLevel.MEDIUM

    def _summarize_attack_surface(self, surface: AttackSurface | None) -> str:
        """Create a summary of the attack surface."""
        if not surface:
            return "Attack surface not analyzed"

        parts = [f"Risk score: {surface.total_risk_score}/100"]

        if surface.highest_risk_file:
            parts.append(f"Highest risk: {surface.highest_risk_file}")

        if surface.primary_concerns:
            parts.append(f"Concerns: {', '.join(surface.primary_concerns[:3])}")

        return "; ".join(parts)

    def _generate_idempotency_key(self, context: AgentContext) -> str:
        """Generate idempotency key for attack plan."""
        return f"IK-plan-{context.thread_id}-{context.task_id}"

    # =========================================================================
    # UTILITY METHODS FOR PLAN EXECUTION
    # =========================================================================

    @staticmethod
    def create_agent_context_for_attack(
        attack: Attack,
        base_context: AgentContext,
        code: str,
    ) -> AgentContext:
        """Create context for a red team agent from an attack assignment.

        Args:
            attack: The attack assignment
            base_context: Original context from orchestrator
            code: Target code to analyze

        Returns:
            AgentContext configured for the assigned agent
        """
        inputs: dict[str, Any] = {
            "code": code,
            "file_path": attack.target_file,
            "function_name": attack.target_function,
            "attack_hints": [v.name for v in attack.attack_vectors],
            "focus_areas": [v.category for v in attack.attack_vectors],
            "hints": attack.hints,
            "code_context": attack.code_context,
            "time_budget": attack.time_budget_seconds,
        }

        # Add vector-specific hints
        payload_hints: list[str] = []
        success_indicators: list[str] = []
        for vector in attack.attack_vectors:
            if vector.payload_hints:
                payload_hints.extend(vector.payload_hints)
            if vector.success_indicators:
                success_indicators.extend(vector.success_indicators)

        if payload_hints:
            inputs["payload_hints"] = payload_hints
        if success_indicators:
            inputs["success_indicators"] = success_indicators

        return AgentContext(
            run_id=base_context.run_id,
            timestamp_iso=base_context.timestamp_iso,
            policy=base_context.policy,
            thread_id=base_context.thread_id,
            task_id=f"{base_context.task_id}-{attack.id}" if base_context.task_id else attack.id,
            inputs=inputs,
        )

    @staticmethod
    def get_execution_batches(plan: AttackPlan) -> list[list[Attack]]:
        """Get attacks organized into sequential batches for execution.

        Each batch contains attacks that can run in parallel.

        Args:
            plan: The attack plan

        Returns:
            List of batches, each containing attacks to run in parallel
        """
        if not plan.attacks:
            return []

        # If parallel groups are defined, use them
        if plan.parallel_groups:
            batches = []
            processed = set()

            for group in plan.parallel_groups:
                batch = []
                for attack_id in group.attack_ids:
                    attack = plan.get_attack_by_id(attack_id)
                    if attack and attack_id not in processed:
                        batch.append(attack)
                        processed.add(attack_id)
                if batch:
                    batches.append(batch)

            # Add any remaining attacks as individual batches
            batches.extend([attack] for attack in plan.attacks if attack.id not in processed)

            return batches

        # Otherwise, create batches based on dependencies
        batches = []
        completed: set[str] = set()

        while len(completed) < len(plan.attacks):
            if not (batch := plan.get_ready_attacks(completed)):
                # No ready attacks - might have circular deps or all done
                if remaining := [a for a in plan.attacks if a.id not in completed]:
                    batch = [remaining[0]]  # Break cycle
                else:
                    break

            # Sort batch by priority
            batch.sort(key=lambda a: a.priority.value)
            batches.append(batch)
            completed.update(a.id for a in batch)

        return batches
