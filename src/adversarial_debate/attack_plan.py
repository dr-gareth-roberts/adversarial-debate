"""Attack plan types for ChaosOrchestrator coordination.

This module defines the data structures used by the ChaosOrchestrator to
create and manage attack plans for the red team agents.
"""

import contextlib
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class AgentType(str, Enum):
    """Types of red team agents."""

    BREAK_AGENT = "BreakAgent"
    EXPLOIT_AGENT = "ExploitAgent"
    CHAOS_AGENT = "ChaosAgent"


class AttackPriority(int, Enum):
    """Priority levels for attack assignments.

    Lower values indicate higher priority.
    """

    CRITICAL = 1
    HIGH = 2
    MEDIUM = 3
    LOW = 4
    MINIMAL = 5


class RiskLevel(str, Enum):
    """Overall risk level assessment."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


@dataclass
class AttackVector:
    """A specific attack vector to test.

    This describes a particular vulnerability type or test case
    that an agent should attempt against a target.
    """

    name: str
    description: str
    category: str  # injection, auth, crypto, etc.
    payload_hints: list[str] = field(default_factory=list)
    expected_behavior: str = ""
    success_indicators: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to JSON-serializable dict."""
        return {
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "payload_hints": self.payload_hints,
            "expected_behavior": self.expected_behavior,
            "success_indicators": self.success_indicators,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AttackVector":
        """Create from dict."""
        return cls(
            name=data["name"],
            description=data.get("description", ""),
            category=data.get("category", ""),
            payload_hints=data.get("payload_hints", []),
            expected_behavior=data.get("expected_behavior", ""),
            success_indicators=data.get("success_indicators", []),
        )


@dataclass
class Attack:
    """A single attack assignment for a red team agent.

    This describes what agent should attack what target using
    which vectors, along with timing and dependency information.
    """

    id: str
    agent: AgentType
    target_file: str
    target_function: str | None
    priority: AttackPriority
    attack_vectors: list[AttackVector]
    time_budget_seconds: int
    rationale: str
    depends_on: list[str] = field(default_factory=list)
    can_parallel_with: list[str] = field(default_factory=list)
    code_context: dict[str, Any] = field(default_factory=dict)
    hints: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to JSON-serializable dict."""
        return {
            "id": self.id,
            "agent": self.agent.value,
            "target_file": self.target_file,
            "target_function": self.target_function,
            "priority": self.priority.value,
            "attack_vectors": [v.to_dict() for v in self.attack_vectors],
            "time_budget_seconds": self.time_budget_seconds,
            "rationale": self.rationale,
            "depends_on": self.depends_on,
            "can_parallel_with": self.can_parallel_with,
            "code_context": self.code_context,
            "hints": self.hints,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Attack":
        """Create from dict."""
        return cls(
            id=data["id"],
            agent=AgentType(data["agent"]),
            target_file=data["target_file"],
            target_function=data.get("target_function"),
            priority=AttackPriority(data.get("priority", 3)),
            attack_vectors=[AttackVector.from_dict(v) for v in data.get("attack_vectors", [])],
            time_budget_seconds=data.get("time_budget_seconds", 60),
            rationale=data.get("rationale", ""),
            depends_on=data.get("depends_on", []),
            can_parallel_with=data.get("can_parallel_with", []),
            code_context=data.get("code_context", {}),
            hints=data.get("hints", []),
        )


@dataclass
class ParallelGroup:
    """A group of attacks that can be executed in parallel.

    Attacks in the same group have no dependencies on each other
    and can safely run concurrently.
    """

    group_id: str
    attack_ids: list[str]
    estimated_duration_seconds: int
    resource_requirements: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to JSON-serializable dict."""
        return {
            "group_id": self.group_id,
            "attack_ids": self.attack_ids,
            "estimated_duration_seconds": self.estimated_duration_seconds,
            "resource_requirements": self.resource_requirements,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ParallelGroup":
        """Create from dict."""
        return cls(
            group_id=data["group_id"],
            attack_ids=data.get("attack_ids", []),
            estimated_duration_seconds=data.get("estimated_duration_seconds", 60),
            resource_requirements=data.get("resource_requirements", {}),
        )


@dataclass
class SkipReason:
    """Reason for skipping a potential attack target.

    Documents why a file or function was not assigned to any agent,
    useful for audit and coverage analysis.
    """

    target: str
    reason: str
    category: str  # low_risk, out_of_scope, already_covered, etc.

    def to_dict(self) -> dict[str, Any]:
        """Convert to JSON-serializable dict."""
        return {
            "target": self.target,
            "reason": self.reason,
            "category": self.category,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SkipReason":
        """Create from dict."""
        return cls(
            target=data["target"],
            reason=data.get("reason", ""),
            category=data.get("category", "low_risk"),
        )


@dataclass
class FileRiskProfile:
    """Risk assessment for a single file in the attack surface.

    Captures what makes a file risky and which agents should analyze it.
    """

    file_path: str
    risk_score: int  # 0-100
    risk_factors: list[str]
    recommended_agents: list[AgentType]
    attack_vectors: list[str]
    exposure: str  # public, authenticated, internal
    data_sensitivity: str  # high, medium, low

    def to_dict(self) -> dict[str, Any]:
        """Convert to JSON-serializable dict."""
        return {
            "file_path": self.file_path,
            "risk_score": self.risk_score,
            "risk_factors": self.risk_factors,
            "recommended_agents": [a.value for a in self.recommended_agents],
            "attack_vectors": self.attack_vectors,
            "exposure": self.exposure,
            "data_sensitivity": self.data_sensitivity,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "FileRiskProfile":
        """Create from dict."""
        agents = []
        for agent_name in data.get("recommended_agents", []):
            with contextlib.suppress(ValueError):
                agents.append(AgentType(agent_name))
        return cls(
            file_path=data["file_path"],
            risk_score=data.get("risk_score", 50),
            risk_factors=data.get("risk_factors", []),
            recommended_agents=agents,
            attack_vectors=data.get("attack_vectors", []),
            exposure=data.get("exposure", "internal"),
            data_sensitivity=data.get("data_sensitivity", "medium"),
        )


@dataclass
class AttackSurface:
    """Analysis of the attack surface for a set of changes.

    Aggregates file risk profiles and identifies key concerns.
    """

    files: list[FileRiskProfile]
    total_risk_score: int  # 0-100
    highest_risk_file: str | None
    primary_concerns: list[str]
    recommended_focus_areas: list[str]

    def to_dict(self) -> dict[str, Any]:
        """Convert to JSON-serializable dict."""
        return {
            "files": [f.to_dict() for f in self.files],
            "total_risk_score": self.total_risk_score,
            "highest_risk_file": self.highest_risk_file,
            "primary_concerns": self.primary_concerns,
            "recommended_focus_areas": self.recommended_focus_areas,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AttackSurface":
        """Create from dict."""
        return cls(
            files=[FileRiskProfile.from_dict(f) for f in data.get("files", [])],
            total_risk_score=data.get("total_risk_score", 50),
            highest_risk_file=data.get("highest_risk_file"),
            primary_concerns=data.get("primary_concerns", []),
            recommended_focus_areas=data.get("recommended_focus_areas", []),
        )


@dataclass
class AttackPlan:
    """Complete attack plan from ChaosOrchestrator.

    This is the main output that coordinates all red team activity,
    including attack assignments, parallelization, and skip reasons.
    """

    plan_id: str
    thread_id: str
    task_id: str
    risk_level: RiskLevel
    risk_factors: list[str]
    risk_score: int  # 0-100
    attacks: list[Attack]
    parallel_groups: list[ParallelGroup]
    execution_order: list[str]  # Attack IDs in execution order
    skipped: list[SkipReason]
    estimated_total_duration_seconds: int
    attack_surface_summary: str
    recommendations: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to JSON-serializable dict."""
        return {
            "plan_id": self.plan_id,
            "thread_id": self.thread_id,
            "task_id": self.task_id,
            "risk_level": self.risk_level.value,
            "risk_factors": self.risk_factors,
            "risk_score": self.risk_score,
            "attacks": [a.to_dict() for a in self.attacks],
            "parallel_groups": [g.to_dict() for g in self.parallel_groups],
            "execution_order": self.execution_order,
            "skipped": [s.to_dict() for s in self.skipped],
            "estimated_total_duration_seconds": self.estimated_total_duration_seconds,
            "attack_surface_summary": self.attack_surface_summary,
            "recommendations": self.recommendations,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AttackPlan":
        """Create from dict."""
        return cls(
            plan_id=data["plan_id"],
            thread_id=data["thread_id"],
            task_id=data["task_id"],
            risk_level=RiskLevel(data.get("risk_level", "MEDIUM")),
            risk_factors=data.get("risk_factors", []),
            risk_score=data.get("risk_score", 50),
            attacks=[Attack.from_dict(a) for a in data.get("attacks", [])],
            parallel_groups=[ParallelGroup.from_dict(g) for g in data.get("parallel_groups", [])],
            execution_order=data.get("execution_order", []),
            skipped=[SkipReason.from_dict(s) for s in data.get("skipped", [])],
            estimated_total_duration_seconds=data.get("estimated_total_duration_seconds", 0),
            attack_surface_summary=data.get("attack_surface_summary", ""),
            recommendations=data.get("recommendations", []),
        )

    def get_attack_by_id(self, attack_id: str) -> Attack | None:
        """Find an attack by its ID."""
        for attack in self.attacks:
            if attack.id == attack_id:
                return attack
        return None

    def get_attacks_by_agent(self, agent_type: AgentType) -> list[Attack]:
        """Get all attacks assigned to a specific agent type."""
        return [a for a in self.attacks if a.agent == agent_type]

    def get_attacks_by_priority(self, priority: AttackPriority) -> list[Attack]:
        """Get all attacks with a specific priority."""
        return [a for a in self.attacks if a.priority == priority]

    def get_ready_attacks(self, completed: set[str]) -> list[Attack]:
        """Get attacks whose dependencies are satisfied.

        Args:
            completed: Set of attack IDs that have completed

        Returns:
            List of attacks ready to execute
        """
        ready = []
        for attack in self.attacks:
            if attack.id in completed:
                continue
            if all(dep in completed for dep in attack.depends_on):
                ready.append(attack)
        return ready

    def get_critical_path(self) -> list[Attack]:
        """Get attacks on the critical path (sequential dependencies).

        Returns attacks that form the longest dependency chain.
        """
        # Find longest path using DFS with memoization
        memo: dict[str, int] = {}

        def depth(attack_id: str) -> int:
            if attack_id in memo:
                return memo[attack_id]
            attack = self.get_attack_by_id(attack_id)
            if not attack or not attack.depends_on:
                memo[attack_id] = 1
                return 1
            max_dep = max(depth(d) for d in attack.depends_on if self.get_attack_by_id(d))
            memo[attack_id] = max_dep + 1
            return memo[attack_id]

        # Calculate depths
        for attack in self.attacks:
            depth(attack.id)

        # Find the longest path
        if not memo:
            return []

        max_depth = max(memo.values())
        critical_ids = [aid for aid, d in memo.items() if d == max_depth]

        # Reconstruct path
        result: list[Attack] = []
        current_ids = critical_ids
        while current_ids:
            found_attack: Attack | None = None
            for aid in current_ids:
                found_attack = self.get_attack_by_id(aid)
                if found_attack is not None:
                    result.append(found_attack)
                    break
            # Move to dependencies
            if found_attack is not None:
                current_ids = found_attack.depends_on
            else:
                break

        return list(reversed(result))


__all__ = [
    "AgentType",
    "AttackPriority",
    "RiskLevel",
    "AttackVector",
    "Attack",
    "ParallelGroup",
    "SkipReason",
    "FileRiskProfile",
    "AttackSurface",
    "AttackPlan",
]
