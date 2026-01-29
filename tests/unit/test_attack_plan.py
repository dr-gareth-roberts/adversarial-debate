"""Unit tests for attack plan types."""

import pytest

from adversarial_debate.attack_plan import (
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


class TestAgentType:
    """Tests for AgentType enum."""

    def test_values(self) -> None:
        """Test enum values."""
        assert AgentType.BREAK_AGENT.value == "BreakAgent"
        assert AgentType.EXPLOIT_AGENT.value == "ExploitAgent"
        assert AgentType.CHAOS_AGENT.value == "ChaosAgent"

    def test_from_string(self) -> None:
        """Test creating from string."""
        assert AgentType("BreakAgent") == AgentType.BREAK_AGENT
        assert AgentType("ExploitAgent") == AgentType.EXPLOIT_AGENT
        assert AgentType("ChaosAgent") == AgentType.CHAOS_AGENT


class TestAttackPriority:
    """Tests for AttackPriority enum."""

    def test_ordering(self) -> None:
        """Test priority ordering (lower is higher priority)."""
        assert AttackPriority.CRITICAL.value < AttackPriority.HIGH.value
        assert AttackPriority.HIGH.value < AttackPriority.MEDIUM.value
        assert AttackPriority.MEDIUM.value < AttackPriority.LOW.value
        assert AttackPriority.LOW.value < AttackPriority.MINIMAL.value

    def test_values(self) -> None:
        """Test numeric values."""
        assert AttackPriority.CRITICAL.value == 1
        assert AttackPriority.MINIMAL.value == 5


class TestRiskLevel:
    """Tests for RiskLevel enum."""

    def test_values(self) -> None:
        """Test enum values."""
        assert RiskLevel.LOW.value == "LOW"
        assert RiskLevel.MEDIUM.value == "MEDIUM"
        assert RiskLevel.HIGH.value == "HIGH"
        assert RiskLevel.CRITICAL.value == "CRITICAL"


class TestAttackVector:
    """Tests for AttackVector dataclass."""

    def test_creation(self) -> None:
        """Test creating an attack vector."""
        vector = AttackVector(
            name="SQL Injection",
            description="Test for SQL injection vulnerabilities",
            category="injection",
            payload_hints=["' OR '1'='1", "'; DROP TABLE--"],
            expected_behavior="Query should be parameterized",
            success_indicators=["returns all rows", "SQL error"],
        )
        assert vector.name == "SQL Injection"
        assert len(vector.payload_hints) == 2

    def test_to_dict_and_from_dict(self) -> None:
        """Test round-trip conversion."""
        original = AttackVector(
            name="XSS",
            description="Cross-site scripting",
            category="xss",
            payload_hints=["<script>alert(1)</script>"],
        )
        data = original.to_dict()
        restored = AttackVector.from_dict(data)
        assert restored.name == original.name
        assert restored.category == original.category


class TestAttack:
    """Tests for Attack dataclass."""

    def test_creation(self) -> None:
        """Test creating an attack."""
        attack = Attack(
            id="ATK-001",
            agent=AgentType.EXPLOIT_AGENT,
            target_file="src/users.py",
            target_function="get_user",
            priority=AttackPriority.CRITICAL,
            attack_vectors=[],
            time_budget_seconds=60,
            rationale="High risk SQL query",
        )
        assert attack.id == "ATK-001"
        assert attack.agent == AgentType.EXPLOIT_AGENT
        assert attack.priority == AttackPriority.CRITICAL

    def test_to_dict_and_from_dict(self) -> None:
        """Test round-trip conversion."""
        original = Attack(
            id="ATK-002",
            agent=AgentType.BREAK_AGENT,
            target_file="src/auth.py",
            target_function=None,
            priority=AttackPriority.HIGH,
            attack_vectors=[
                AttackVector(
                    name="Edge Case",
                    description="Test boundary conditions",
                    category="logic",
                )
            ],
            time_budget_seconds=90,
            rationale="Complex auth logic",
            depends_on=["ATK-001"],
            can_parallel_with=["ATK-003"],
            hints=["Check line 42"],
        )
        data = original.to_dict()
        restored = Attack.from_dict(data)
        assert restored.id == original.id
        assert restored.agent == original.agent
        assert restored.target_function == original.target_function
        assert len(restored.attack_vectors) == 1
        assert restored.depends_on == ["ATK-001"]


class TestParallelGroup:
    """Tests for ParallelGroup dataclass."""

    def test_creation(self) -> None:
        """Test creating a parallel group."""
        group = ParallelGroup(
            group_id="PG-001",
            attack_ids=["ATK-001", "ATK-002"],
            estimated_duration_seconds=120,
        )
        assert group.group_id == "PG-001"
        assert len(group.attack_ids) == 2

    def test_to_dict_and_from_dict(self) -> None:
        """Test round-trip conversion."""
        original = ParallelGroup(
            group_id="PG-002",
            attack_ids=["ATK-003", "ATK-004", "ATK-005"],
            estimated_duration_seconds=180,
            resource_requirements={"memory": "2GB"},
        )
        data = original.to_dict()
        restored = ParallelGroup.from_dict(data)
        assert restored.group_id == original.group_id
        assert restored.attack_ids == original.attack_ids
        assert restored.resource_requirements == original.resource_requirements


class TestFileRiskProfile:
    """Tests for FileRiskProfile dataclass."""

    def test_creation(self) -> None:
        """Test creating a file risk profile."""
        profile = FileRiskProfile(
            file_path="src/api/users.py",
            risk_score=75,
            risk_factors=["handles user input", "database queries"],
            recommended_agents=[AgentType.EXPLOIT_AGENT, AgentType.BREAK_AGENT],
            attack_vectors=["SQL injection", "IDOR"],
            exposure="public",
            data_sensitivity="high",
        )
        assert profile.risk_score == 75
        assert len(profile.recommended_agents) == 2

    def test_to_dict_and_from_dict(self) -> None:
        """Test round-trip conversion."""
        original = FileRiskProfile(
            file_path="src/utils.py",
            risk_score=25,
            risk_factors=["utility functions"],
            recommended_agents=[AgentType.BREAK_AGENT],
            attack_vectors=["edge cases"],
            exposure="internal",
            data_sensitivity="low",
        )
        data = original.to_dict()
        restored = FileRiskProfile.from_dict(data)
        assert restored.file_path == original.file_path
        assert restored.risk_score == original.risk_score
        assert restored.recommended_agents == original.recommended_agents


class TestAttackSurface:
    """Tests for AttackSurface dataclass."""

    def test_creation(self) -> None:
        """Test creating an attack surface."""
        surface = AttackSurface(
            files=[],
            total_risk_score=50,
            highest_risk_file="src/api.py",
            primary_concerns=["SQL injection", "Auth bypass"],
            recommended_focus_areas=["Database layer"],
        )
        assert surface.total_risk_score == 50
        assert len(surface.primary_concerns) == 2


class TestAttackPlan:
    """Tests for AttackPlan dataclass."""

    @pytest.fixture
    def sample_attacks(self) -> list[Attack]:
        """Create sample attacks for testing."""
        return [
            Attack(
                id="ATK-001",
                agent=AgentType.EXPLOIT_AGENT,
                target_file="src/users.py",
                target_function="get_user",
                priority=AttackPriority.CRITICAL,
                attack_vectors=[],
                time_budget_seconds=60,
                rationale="SQL injection risk",
                depends_on=[],
            ),
            Attack(
                id="ATK-002",
                agent=AgentType.BREAK_AGENT,
                target_file="src/users.py",
                target_function="validate_user",
                priority=AttackPriority.HIGH,
                attack_vectors=[],
                time_budget_seconds=45,
                rationale="Input validation",
                depends_on=["ATK-001"],
            ),
            Attack(
                id="ATK-003",
                agent=AgentType.CHAOS_AGENT,
                target_file="src/api.py",
                target_function=None,
                priority=AttackPriority.MEDIUM,
                attack_vectors=[],
                time_budget_seconds=60,
                rationale="Resilience testing",
                depends_on=[],
            ),
        ]

    def test_creation(self, sample_attacks: list[Attack]) -> None:
        """Test creating an attack plan."""
        plan = AttackPlan(
            plan_id="PLAN-001",
            thread_id="thread-1",
            task_id="task-1",
            risk_level=RiskLevel.HIGH,
            risk_factors=["User input handling"],
            risk_score=75,
            attacks=sample_attacks,
            parallel_groups=[],
            execution_order=["ATK-001", "ATK-002", "ATK-003"],
            skipped=[],
            estimated_total_duration_seconds=165,
            attack_surface_summary="3 files analyzed",
        )
        assert plan.plan_id == "PLAN-001"
        assert len(plan.attacks) == 3

    def test_get_attack_by_id(self, sample_attacks: list[Attack]) -> None:
        """Test finding attack by ID."""
        plan = AttackPlan(
            plan_id="PLAN-001",
            thread_id="thread-1",
            task_id="task-1",
            risk_level=RiskLevel.HIGH,
            risk_factors=[],
            risk_score=50,
            attacks=sample_attacks,
            parallel_groups=[],
            execution_order=[],
            skipped=[],
            estimated_total_duration_seconds=0,
            attack_surface_summary="",
        )
        attack = plan.get_attack_by_id("ATK-002")
        assert attack is not None
        assert attack.id == "ATK-002"
        assert plan.get_attack_by_id("ATK-999") is None

    def test_get_attacks_by_agent(self, sample_attacks: list[Attack]) -> None:
        """Test filtering attacks by agent type."""
        plan = AttackPlan(
            plan_id="PLAN-001",
            thread_id="thread-1",
            task_id="task-1",
            risk_level=RiskLevel.HIGH,
            risk_factors=[],
            risk_score=50,
            attacks=sample_attacks,
            parallel_groups=[],
            execution_order=[],
            skipped=[],
            estimated_total_duration_seconds=0,
            attack_surface_summary="",
        )
        exploit_attacks = plan.get_attacks_by_agent(AgentType.EXPLOIT_AGENT)
        assert len(exploit_attacks) == 1
        assert exploit_attacks[0].id == "ATK-001"

    def test_get_attacks_by_priority(self, sample_attacks: list[Attack]) -> None:
        """Test filtering attacks by priority."""
        plan = AttackPlan(
            plan_id="PLAN-001",
            thread_id="thread-1",
            task_id="task-1",
            risk_level=RiskLevel.HIGH,
            risk_factors=[],
            risk_score=50,
            attacks=sample_attacks,
            parallel_groups=[],
            execution_order=[],
            skipped=[],
            estimated_total_duration_seconds=0,
            attack_surface_summary="",
        )
        critical_attacks = plan.get_attacks_by_priority(AttackPriority.CRITICAL)
        assert len(critical_attacks) == 1
        assert critical_attacks[0].id == "ATK-001"

    def test_get_ready_attacks(self, sample_attacks: list[Attack]) -> None:
        """Test finding attacks ready to execute."""
        plan = AttackPlan(
            plan_id="PLAN-001",
            thread_id="thread-1",
            task_id="task-1",
            risk_level=RiskLevel.HIGH,
            risk_factors=[],
            risk_score=50,
            attacks=sample_attacks,
            parallel_groups=[],
            execution_order=[],
            skipped=[],
            estimated_total_duration_seconds=0,
            attack_surface_summary="",
        )
        # Initially, ATK-001 and ATK-003 should be ready (no dependencies)
        ready = plan.get_ready_attacks(set())
        ready_ids = {a.id for a in ready}
        assert "ATK-001" in ready_ids
        assert "ATK-003" in ready_ids
        assert "ATK-002" not in ready_ids  # Depends on ATK-001

        # After ATK-001 completes, ATK-002 should be ready
        ready_after = plan.get_ready_attacks({"ATK-001"})
        ready_after_ids = {a.id for a in ready_after}
        assert "ATK-002" in ready_after_ids

    def test_to_dict_and_from_dict(self, sample_attacks: list[Attack]) -> None:
        """Test round-trip conversion."""
        original = AttackPlan(
            plan_id="PLAN-001",
            thread_id="thread-1",
            task_id="task-1",
            risk_level=RiskLevel.HIGH,
            risk_factors=["User input"],
            risk_score=75,
            attacks=sample_attacks,
            parallel_groups=[
                ParallelGroup(
                    group_id="PG-001",
                    attack_ids=["ATK-001", "ATK-003"],
                    estimated_duration_seconds=60,
                )
            ],
            execution_order=["ATK-001", "ATK-003", "ATK-002"],
            skipped=[
                SkipReason(
                    target="src/config.py",
                    reason="Static configuration",
                    category="low_risk",
                )
            ],
            estimated_total_duration_seconds=165,
            attack_surface_summary="Test summary",
            recommendations=["Focus on auth"],
        )
        data = original.to_dict()
        restored = AttackPlan.from_dict(data)
        assert restored.plan_id == original.plan_id
        assert restored.risk_level == original.risk_level
        assert len(restored.attacks) == len(original.attacks)
        assert len(restored.parallel_groups) == 1
        assert len(restored.skipped) == 1
