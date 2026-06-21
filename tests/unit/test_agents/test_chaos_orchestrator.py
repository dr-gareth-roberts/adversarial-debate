"""Comprehensive tests for ChaosOrchestrator parallel execution logic."""

import pytest

from adversarial_debate.agents.base import AgentContext
from adversarial_debate.agents.chaos_orchestrator import ChaosOrchestrator
from adversarial_debate.attack_plan import (
    AgentType,
    Attack,
    AttackPlan,
    AttackPriority,
    AttackVector,
    ParallelGroup,
    RiskLevel,
)


class TestChaosOrchestratorExecutionBatches:
    """Tests for ChaosOrchestrator.get_execution_batches() method."""

    @pytest.fixture
    def sample_attack(self):
        """Create a sample attack for testing."""
        return Attack(
            id="ATK-001",
            agent=AgentType.EXPLOIT_AGENT,
            target_file="test.py",
            target_function=None,
            priority=AttackPriority.HIGH,
            attack_vectors=[
                AttackVector(
                    name="SQL Injection",
                    description="Test for SQL injection",
                    category="injection",
                )
            ],
            time_budget_seconds=60,
            rationale="Endpoint handles user input directly in a query",
            depends_on=[],
        )

    @pytest.fixture
    def sample_context(self):
        """Create a sample agent context."""
        return AgentContext(
            run_id="test-run",
            timestamp_iso="2026-06-21T12:00:00Z",
            policy={},
            thread_id="test-thread",
            task_id="test-task",
            inputs={},
        )

    def test_empty_plan_returns_empty_batches(self):
        """Test that an empty plan returns no batches."""
        plan = AttackPlan(
            plan_id="PLAN-001",
            thread_id="test-thread",
            task_id="test-task",
            risk_level=RiskLevel.MEDIUM,
            risk_factors=[],
            risk_score=0,
            attacks=[],
            parallel_groups=[],
            execution_order=[],
            skipped=[],
            estimated_total_duration_seconds=0,
            attack_surface_summary="No attacks planned",
        )

        batches = ChaosOrchestrator.get_execution_batches(plan)

        assert batches == []

    def test_single_attack_single_batch(self, sample_attack):
        """Test that a single attack creates one batch."""
        plan = AttackPlan(
            plan_id="PLAN-001",
            thread_id="test-thread",
            task_id="test-task",
            risk_level=RiskLevel.MEDIUM,
            risk_factors=[],
            risk_score=50,
            attacks=[sample_attack],
            parallel_groups=[],
            execution_order=["ATK-001"],
            skipped=[],
            estimated_total_duration_seconds=60,
            attack_surface_summary="Single attack on test.py",
        )

        batches = ChaosOrchestrator.get_execution_batches(plan)

        assert len(batches) == 1
        assert len(batches[0]) == 1
        assert batches[0][0].id == "ATK-001"

    def test_parallel_groups_create_separate_batches(self):
        """Test that parallel groups create separate batches."""
        attack1 = Attack(
            id="ATK-001",
            agent=AgentType.EXPLOIT_AGENT,
            target_file="test1.py",
            target_function=None,
            priority=AttackPriority.HIGH,
            attack_vectors=[],
            time_budget_seconds=60,
            rationale="Exploit-class risk on test1.py",
            depends_on=[],
        )
        attack2 = Attack(
            id="ATK-002",
            agent=AgentType.BREAK_AGENT,
            target_file="test2.py",
            target_function=None,
            priority=AttackPriority.MEDIUM,
            attack_vectors=[],
            time_budget_seconds=60,
            rationale="Logic edge cases in test2.py",
            depends_on=[],
        )
        attack3 = Attack(
            id="ATK-003",
            agent=AgentType.CHAOS_AGENT,
            target_file="test3.py",
            target_function=None,
            priority=AttackPriority.LOW,
            attack_vectors=[],
            time_budget_seconds=60,
            rationale="Resilience testing on test3.py",
            depends_on=[],
        )

        parallel_group1 = ParallelGroup(
            group_id="PG-001",
            attack_ids=["ATK-001", "ATK-002"],
            estimated_duration_seconds=60,
        )
        parallel_group2 = ParallelGroup(
            group_id="PG-002",
            attack_ids=["ATK-003"],
            estimated_duration_seconds=60,
        )

        plan = AttackPlan(
            plan_id="PLAN-001",
            thread_id="test-thread",
            task_id="test-task",
            risk_level=RiskLevel.MEDIUM,
            risk_factors=[],
            risk_score=60,
            attacks=[attack1, attack2, attack3],
            parallel_groups=[parallel_group1, parallel_group2],
            execution_order=["ATK-001", "ATK-002", "ATK-003"],
            skipped=[],
            estimated_total_duration_seconds=180,
            attack_surface_summary="Three attacks across two parallel groups",
        )

        batches = ChaosOrchestrator.get_execution_batches(plan)

        assert len(batches) == 2
        assert len(batches[0]) == 2
        assert {a.id for a in batches[0]} == {"ATK-001", "ATK-002"}
        assert len(batches[1]) == 1
        assert batches[1][0].id == "ATK-003"

    def test_dependencies_create_sequential_batches(self):
        """Test that dependencies create sequential batches."""
        attack1 = Attack(
            id="ATK-001",
            agent=AgentType.EXPLOIT_AGENT,
            target_file="test1.py",
            target_function=None,
            priority=AttackPriority.HIGH,
            attack_vectors=[],
            time_budget_seconds=60,
            rationale="Root attack on test1.py",
            depends_on=[],
        )
        attack2 = Attack(
            id="ATK-002",
            agent=AgentType.BREAK_AGENT,
            target_file="test2.py",
            target_function=None,
            priority=AttackPriority.MEDIUM,
            attack_vectors=[],
            time_budget_seconds=60,
            rationale="Follow-up that needs ATK-001 results",
            depends_on=["ATK-001"],
        )
        attack3 = Attack(
            id="ATK-003",
            agent=AgentType.CHAOS_AGENT,
            target_file="test3.py",
            target_function=None,
            priority=AttackPriority.LOW,
            attack_vectors=[],
            time_budget_seconds=60,
            rationale="Final attack that needs ATK-002 results",
            depends_on=["ATK-002"],
        )

        plan = AttackPlan(
            plan_id="PLAN-001",
            thread_id="test-thread",
            task_id="test-task",
            risk_level=RiskLevel.MEDIUM,
            risk_factors=[],
            risk_score=60,
            attacks=[attack1, attack2, attack3],
            parallel_groups=[],
            execution_order=["ATK-001", "ATK-002", "ATK-003"],
            skipped=[],
            estimated_total_duration_seconds=180,
            attack_surface_summary="Sequential dependency chain of three attacks",
        )

        batches = ChaosOrchestrator.get_execution_batches(plan)

        assert len(batches) == 3
        assert batches[0][0].id == "ATK-001"
        assert batches[1][0].id == "ATK-002"
        assert batches[2][0].id == "ATK-003"

    def test_independent_attacks_parallelize(self):
        """Test that independent attacks are batched together."""
        attack1 = Attack(
            id="ATK-001",
            agent=AgentType.EXPLOIT_AGENT,
            target_file="test1.py",
            target_function=None,
            priority=AttackPriority.HIGH,
            attack_vectors=[],
            time_budget_seconds=60,
            rationale="Independent attack on test1.py",
            depends_on=[],
        )
        attack2 = Attack(
            id="ATK-002",
            agent=AgentType.BREAK_AGENT,
            target_file="test2.py",
            target_function=None,
            priority=AttackPriority.MEDIUM,
            attack_vectors=[],
            time_budget_seconds=60,
            rationale="Independent attack on test2.py",
            depends_on=[],
        )
        attack3 = Attack(
            id="ATK-003",
            agent=AgentType.CHAOS_AGENT,
            target_file="test3.py",
            target_function=None,
            priority=AttackPriority.LOW,
            attack_vectors=[],
            time_budget_seconds=60,
            rationale="Independent attack on test3.py",
            depends_on=[],
        )

        plan = AttackPlan(
            plan_id="PLAN-001",
            thread_id="test-thread",
            task_id="test-task",
            risk_level=RiskLevel.MEDIUM,
            risk_factors=[],
            risk_score=60,
            attacks=[attack1, attack2, attack3],
            parallel_groups=[],
            execution_order=["ATK-001", "ATK-002", "ATK-003"],
            skipped=[],
            estimated_total_duration_seconds=180,
            attack_surface_summary="Three fully independent attacks",
        )

        batches = ChaosOrchestrator.get_execution_batches(plan)

        # All independent attacks should be in one batch
        assert len(batches) == 1
        assert len(batches[0]) == 3
        assert {a.id for a in batches[0]} == {"ATK-001", "ATK-002", "ATK-003"}

    def test_mixed_dependencies_and_parallel(self):
        """Test mixed dependencies and parallel attacks."""
        attack1 = Attack(
            id="ATK-001",
            agent=AgentType.EXPLOIT_AGENT,
            target_file="test1.py",
            target_function=None,
            priority=AttackPriority.HIGH,
            attack_vectors=[],
            time_budget_seconds=60,
            rationale="Independent attack feeding ATK-003",
            depends_on=[],
        )
        attack2 = Attack(
            id="ATK-002",
            agent=AgentType.BREAK_AGENT,
            target_file="test2.py",
            target_function=None,
            priority=AttackPriority.MEDIUM,
            attack_vectors=[],
            time_budget_seconds=60,
            rationale="Independent attack feeding ATK-003",
            depends_on=[],
        )
        attack3 = Attack(
            id="ATK-003",
            agent=AgentType.CHAOS_AGENT,
            target_file="test3.py",
            target_function=None,
            priority=AttackPriority.LOW,
            attack_vectors=[],
            time_budget_seconds=60,
            rationale="Depends on both ATK-001 and ATK-002",
            depends_on=["ATK-001", "ATK-002"],
        )

        plan = AttackPlan(
            plan_id="PLAN-001",
            thread_id="test-thread",
            task_id="test-task",
            risk_level=RiskLevel.MEDIUM,
            risk_factors=[],
            risk_score=60,
            attacks=[attack1, attack2, attack3],
            parallel_groups=[],
            execution_order=["ATK-001", "ATK-002", "ATK-003"],
            skipped=[],
            estimated_total_duration_seconds=180,
            attack_surface_summary="Two independent attacks fanning into a third",
        )

        batches = ChaosOrchestrator.get_execution_batches(plan)

        # First batch: ATK-001 and ATK-002 (independent)
        # Second batch: ATK-003 (depends on both)
        assert len(batches) == 2
        assert len(batches[0]) == 2
        assert {a.id for a in batches[0]} == {"ATK-001", "ATK-002"}
        assert len(batches[1]) == 1
        assert batches[1][0].id == "ATK-003"

    def test_priority_sorting_within_batch(self):
        """Test that attacks are sorted by priority within a batch."""
        attack1 = Attack(
            id="ATK-001",
            agent=AgentType.EXPLOIT_AGENT,
            target_file="test1.py",
            target_function=None,
            priority=AttackPriority.LOW,
            attack_vectors=[],
            time_budget_seconds=60,
            rationale="Low-priority independent attack",
            depends_on=[],
        )
        attack2 = Attack(
            id="ATK-002",
            agent=AgentType.BREAK_AGENT,
            target_file="test2.py",
            target_function=None,
            priority=AttackPriority.CRITICAL,
            attack_vectors=[],
            time_budget_seconds=60,
            rationale="Critical-priority independent attack",
            depends_on=[],
        )
        attack3 = Attack(
            id="ATK-003",
            agent=AgentType.CHAOS_AGENT,
            target_file="test3.py",
            target_function=None,
            priority=AttackPriority.HIGH,
            attack_vectors=[],
            time_budget_seconds=60,
            rationale="High-priority independent attack",
            depends_on=[],
        )

        plan = AttackPlan(
            plan_id="PLAN-001",
            thread_id="test-thread",
            task_id="test-task",
            risk_level=RiskLevel.HIGH,
            risk_factors=[],
            risk_score=80,
            attacks=[attack1, attack2, attack3],
            parallel_groups=[],
            execution_order=["ATK-002", "ATK-003", "ATK-001"],
            skipped=[],
            estimated_total_duration_seconds=180,
            attack_surface_summary="Three independent attacks of varying priority",
        )

        batches = ChaosOrchestrator.get_execution_batches(plan)

        assert len(batches) == 1
        # Should be sorted: CRITICAL, HIGH, LOW
        assert batches[0][0].priority == AttackPriority.CRITICAL
        assert batches[0][1].priority == AttackPriority.HIGH
        assert batches[0][2].priority == AttackPriority.LOW

    def test_circular_dependency_handling(self):
        """Test that circular dependencies are handled gracefully."""
        attack1 = Attack(
            id="ATK-001",
            agent=AgentType.EXPLOIT_AGENT,
            target_file="test1.py",
            target_function=None,
            priority=AttackPriority.HIGH,
            attack_vectors=[],
            time_budget_seconds=60,
            rationale="Part of a circular dependency with ATK-002",
            depends_on=["ATK-002"],
        )
        attack2 = Attack(
            id="ATK-002",
            agent=AgentType.BREAK_AGENT,
            target_file="test2.py",
            target_function=None,
            priority=AttackPriority.MEDIUM,
            attack_vectors=[],
            time_budget_seconds=60,
            rationale="Part of a circular dependency with ATK-001",
            depends_on=["ATK-001"],
        )

        plan = AttackPlan(
            plan_id="PLAN-001",
            thread_id="test-thread",
            task_id="test-task",
            risk_level=RiskLevel.MEDIUM,
            risk_factors=[],
            risk_score=50,
            attacks=[attack1, attack2],
            parallel_groups=[],
            execution_order=["ATK-001", "ATK-002"],
            skipped=[],
            estimated_total_duration_seconds=120,
            attack_surface_summary="Two attacks with a circular dependency",
        )

        # Should not hang or raise exception
        batches = ChaosOrchestrator.get_execution_batches(plan)

        # Should break the cycle by forcing one attack to run
        assert len(batches) >= 1
        # All attacks should be included
        all_attack_ids = {a.id for batch in batches for a in batch}
        assert all_attack_ids == {"ATK-001", "ATK-002"}

    def test_parallel_groups_override_dependencies(self):
        """Test that parallel groups take precedence over dependencies."""
        attack1 = Attack(
            id="ATK-001",
            agent=AgentType.EXPLOIT_AGENT,
            target_file="test1.py",
            target_function=None,
            priority=AttackPriority.HIGH,
            attack_vectors=[],
            time_budget_seconds=60,
            rationale="Declares a dependency but grouped for parallel execution",
            depends_on=["ATK-002"],  # Dependency says sequential
        )
        attack2 = Attack(
            id="ATK-002",
            agent=AgentType.BREAK_AGENT,
            target_file="test2.py",
            target_function=None,
            priority=AttackPriority.MEDIUM,
            attack_vectors=[],
            time_budget_seconds=60,
            rationale="Grouped for parallel execution with ATK-001",
            depends_on=[],
        )

        # But parallel group says they can run together
        parallel_group = ParallelGroup(
            group_id="PG-001",
            attack_ids=["ATK-001", "ATK-002"],
            estimated_duration_seconds=60,
        )

        plan = AttackPlan(
            plan_id="PLAN-001",
            thread_id="test-thread",
            task_id="test-task",
            risk_level=RiskLevel.MEDIUM,
            risk_factors=[],
            risk_score=50,
            attacks=[attack1, attack2],
            parallel_groups=[parallel_group],
            execution_order=["ATK-001", "ATK-002"],
            skipped=[],
            estimated_total_duration_seconds=120,
            attack_surface_summary="Parallel group overriding a declared dependency",
        )

        batches = ChaosOrchestrator.get_execution_batches(plan)

        # Parallel group should override dependencies
        assert len(batches) == 1
        assert len(batches[0]) == 2

    def test_partial_parallel_groups(self):
        """Test when parallel groups don't cover all attacks."""
        attack1 = Attack(
            id="ATK-001",
            agent=AgentType.EXPLOIT_AGENT,
            target_file="test1.py",
            target_function=None,
            priority=AttackPriority.HIGH,
            attack_vectors=[],
            time_budget_seconds=60,
            rationale="Grouped attack on test1.py",
            depends_on=[],
        )
        attack2 = Attack(
            id="ATK-002",
            agent=AgentType.BREAK_AGENT,
            target_file="test2.py",
            target_function=None,
            priority=AttackPriority.MEDIUM,
            attack_vectors=[],
            time_budget_seconds=60,
            rationale="Grouped attack on test2.py",
            depends_on=[],
        )
        attack3 = Attack(
            id="ATK-003",
            agent=AgentType.CHAOS_AGENT,
            target_file="test3.py",
            target_function=None,
            priority=AttackPriority.LOW,
            attack_vectors=[],
            time_budget_seconds=60,
            rationale="Ungrouped attack on test3.py",
            depends_on=[],
        )

        # Only first two attacks in parallel group
        parallel_group = ParallelGroup(
            group_id="PG-001",
            attack_ids=["ATK-001", "ATK-002"],
            estimated_duration_seconds=60,
        )

        plan = AttackPlan(
            plan_id="PLAN-001",
            thread_id="test-thread",
            task_id="test-task",
            risk_level=RiskLevel.MEDIUM,
            risk_factors=[],
            risk_score=60,
            attacks=[attack1, attack2, attack3],
            parallel_groups=[parallel_group],
            execution_order=["ATK-001", "ATK-002", "ATK-003"],
            skipped=[],
            estimated_total_duration_seconds=180,
            attack_surface_summary="One parallel group plus one ungrouped attack",
        )

        batches = ChaosOrchestrator.get_execution_batches(plan)

        # First batch from parallel group, second batch for remaining attack
        assert len(batches) == 2
        assert len(batches[0]) == 2
        assert {a.id for a in batches[0]} == {"ATK-001", "ATK-002"}
        assert len(batches[1]) == 1
        assert batches[1][0].id == "ATK-003"

    def test_complex_dependency_chain(self):
        """Test complex dependency chain with multiple levels."""
        attack1 = Attack(
            id="ATK-001",
            agent=AgentType.EXPLOIT_AGENT,
            target_file="test1.py",
            target_function=None,
            priority=AttackPriority.HIGH,
            attack_vectors=[],
            time_budget_seconds=60,
            rationale="Root attack feeding ATK-002 and ATK-003",
            depends_on=[],
        )
        attack2 = Attack(
            id="ATK-002",
            agent=AgentType.BREAK_AGENT,
            target_file="test2.py",
            target_function=None,
            priority=AttackPriority.MEDIUM,
            attack_vectors=[],
            time_budget_seconds=60,
            rationale="Depends on ATK-001",
            depends_on=["ATK-001"],
        )
        attack3 = Attack(
            id="ATK-003",
            agent=AgentType.CHAOS_AGENT,
            target_file="test3.py",
            target_function=None,
            priority=AttackPriority.LOW,
            attack_vectors=[],
            time_budget_seconds=60,
            rationale="Depends on ATK-001",
            depends_on=["ATK-001"],
        )
        attack4 = Attack(
            id="ATK-004",
            agent=AgentType.CRYPTO_AGENT,
            target_file="test4.py",
            target_function=None,
            priority=AttackPriority.CRITICAL,
            attack_vectors=[],
            time_budget_seconds=60,
            rationale="Depends on ATK-002 and ATK-003",
            depends_on=["ATK-002", "ATK-003"],
        )

        plan = AttackPlan(
            plan_id="PLAN-001",
            thread_id="test-thread",
            task_id="test-task",
            risk_level=RiskLevel.HIGH,
            risk_factors=[],
            risk_score=85,
            attacks=[attack1, attack2, attack3, attack4],
            parallel_groups=[],
            execution_order=["ATK-001", "ATK-002", "ATK-003", "ATK-004"],
            skipped=[],
            estimated_total_duration_seconds=240,
            attack_surface_summary="Diamond-shaped dependency chain of four attacks",
        )

        batches = ChaosOrchestrator.get_execution_batches(plan)

        # Batch 1: ATK-001 (no dependencies)
        # Batch 2: ATK-002 and ATK-003 (both depend on ATK-001, can run in parallel)
        # Batch 3: ATK-004 (depends on ATK-002 and ATK-003)
        assert len(batches) == 3
        assert batches[0][0].id == "ATK-001"
        assert len(batches[1]) == 2
        assert {a.id for a in batches[1]} == {"ATK-002", "ATK-003"}
        assert batches[2][0].id == "ATK-004"

    def test_nonexistent_dependency_ignored(self):
        """Test that nonexistent dependencies are ignored."""
        attack1 = Attack(
            id="ATK-001",
            agent=AgentType.EXPLOIT_AGENT,
            target_file="test1.py",
            target_function=None,
            priority=AttackPriority.HIGH,
            attack_vectors=[],
            time_budget_seconds=60,
            rationale="Depends on an attack that does not exist in the plan",
            depends_on=["ATK-999"],  # Nonexistent dependency
        )

        plan = AttackPlan(
            plan_id="PLAN-001",
            thread_id="test-thread",
            task_id="test-task",
            risk_level=RiskLevel.MEDIUM,
            risk_factors=[],
            risk_score=50,
            attacks=[attack1],
            parallel_groups=[],
            execution_order=["ATK-001"],
            skipped=[],
            estimated_total_duration_seconds=60,
            attack_surface_summary="Single attack with a dangling dependency",
        )

        # Should not raise exception
        batches = ChaosOrchestrator.get_execution_batches(plan)

        assert len(batches) == 1
        assert batches[0][0].id == "ATK-001"


class TestChaosOrchestratorAgentContext:
    """Tests for ChaosOrchestrator.create_agent_context_for_attack() method."""

    @pytest.fixture
    def base_context(self):
        """Create a base agent context."""
        return AgentContext(
            run_id="test-run",
            timestamp_iso="2026-06-21T12:00:00Z",
            policy={},
            thread_id="test-thread",
            task_id="test-task",
            inputs={"exposure": "public"},
        )

    def test_context_creation_basic(self, base_context):
        """Test basic context creation for an attack."""
        attack = Attack(
            id="ATK-001",
            agent=AgentType.EXPLOIT_AGENT,
            target_file="test.py",
            target_function=None,
            priority=AttackPriority.HIGH,
            attack_vectors=[
                AttackVector(
                    name="SQL Injection",
                    description="Test for SQL injection",
                    category="injection",
                )
            ],
            time_budget_seconds=60,
            rationale="Endpoint handles user input directly in a query",
            depends_on=[],
        )

        code = "def test(): pass"

        context = ChaosOrchestrator.create_agent_context_for_attack(attack, base_context, code)

        assert context.run_id == "test-run"
        assert context.thread_id == "test-thread"
        assert context.task_id == "test-task-ATK-001"
        assert context.inputs["code"] == code
        assert context.inputs["file_path"] == "test.py"
        assert context.inputs["time_budget"] == 60
        assert "SQL Injection" in context.inputs["attack_hints"]
        assert "injection" in context.inputs["focus_areas"]

    def test_context_with_multiple_vectors(self, base_context):
        """Test context creation with multiple attack vectors."""
        attack = Attack(
            id="ATK-001",
            agent=AgentType.EXPLOIT_AGENT,
            target_file="test.py",
            target_function=None,
            priority=AttackPriority.HIGH,
            attack_vectors=[
                AttackVector(
                    name="SQL Injection",
                    description="Test for SQL injection",
                    category="injection",
                    payload_hints=["' OR '1'='1"],
                    success_indicators=["returns all rows"],
                ),
                AttackVector(
                    name="XSS",
                    description="Test for XSS",
                    category="xss",
                    payload_hints=["<script>alert(1)</script>"],
                    success_indicators=["script executes"],
                ),
            ],
            time_budget_seconds=60,
            rationale="Endpoint reflects user input without sanitisation",
            depends_on=[],
        )

        code = "def test(): pass"

        context = ChaosOrchestrator.create_agent_context_for_attack(attack, base_context, code)

        assert len(context.inputs["attack_hints"]) == 2
        assert "SQL Injection" in context.inputs["attack_hints"]
        assert "XSS" in context.inputs["attack_hints"]
        assert len(context.inputs["focus_areas"]) == 2
        assert "injection" in context.inputs["focus_areas"]
        assert "xss" in context.inputs["focus_areas"]
        assert len(context.inputs["payload_hints"]) == 2
        assert len(context.inputs["success_indicators"]) == 2

    def test_context_with_target_function(self, base_context):
        """Test context creation with target function."""
        attack = Attack(
            id="ATK-001",
            agent=AgentType.EXPLOIT_AGENT,
            target_file="test.py",
            target_function="vulnerable_function",
            priority=AttackPriority.HIGH,
            attack_vectors=[],
            time_budget_seconds=60,
            rationale="A specific function appears vulnerable",
            depends_on=[],
        )

        code = "def vulnerable_function(): pass"

        context = ChaosOrchestrator.create_agent_context_for_attack(attack, base_context, code)

        assert context.inputs["function_name"] == "vulnerable_function"

    def test_context_with_hints(self, base_context):
        """Test context creation with hints."""
        attack = Attack(
            id="ATK-001",
            agent=AgentType.EXPLOIT_AGENT,
            target_file="test.py",
            target_function=None,
            priority=AttackPriority.HIGH,
            attack_vectors=[],
            time_budget_seconds=60,
            rationale="Orchestrator surfaced specific lines worth inspecting",
            depends_on=[],
            hints=["Check line 42", "Look at user input handling"],
        )

        code = "def test(): pass"

        context = ChaosOrchestrator.create_agent_context_for_attack(attack, base_context, code)

        assert len(context.inputs["hints"]) == 2
        assert "Check line 42" in context.inputs["hints"]
        assert "Look at user input handling" in context.inputs["hints"]

    def test_context_with_code_context(self, base_context):
        """Test context creation with code context."""
        attack = Attack(
            id="ATK-001",
            agent=AgentType.EXPLOIT_AGENT,
            target_file="test.py",
            target_function=None,
            priority=AttackPriority.HIGH,
            attack_vectors=[],
            time_budget_seconds=60,
            rationale="Surrounding code context should reach the agent",
            depends_on=[],
            code_context={"imports": ["os", "sys"], "functions": ["main"]},
        )

        code = "def test(): pass"

        context = ChaosOrchestrator.create_agent_context_for_attack(attack, base_context, code)

        assert context.inputs["code_context"] == {
            "imports": ["os", "sys"],
            "functions": ["main"],
        }

    def test_context_task_id_without_base_task(self, base_context):
        """Test context creation when base context has no task_id."""
        base_context.task_id = ""

        attack = Attack(
            id="ATK-001",
            agent=AgentType.EXPLOIT_AGENT,
            target_file="test.py",
            target_function=None,
            priority=AttackPriority.HIGH,
            attack_vectors=[],
            time_budget_seconds=60,
            rationale="Attack runs without a base task id",
            depends_on=[],
        )

        code = "def test(): pass"

        context = ChaosOrchestrator.create_agent_context_for_attack(attack, base_context, code)

        # Should use attack ID directly
        assert context.task_id == "ATK-001"

    def test_context_preserves_policy(self, base_context):
        """Test that context preserves policy from base context."""
        base_context.policy = {"max_severity": "HIGH", "require_verification": True}

        attack = Attack(
            id="ATK-001",
            agent=AgentType.EXPLOIT_AGENT,
            target_file="test.py",
            target_function=None,
            priority=AttackPriority.HIGH,
            attack_vectors=[],
            time_budget_seconds=60,
            rationale="Policy from the orchestrator must reach the agent",
            depends_on=[],
        )

        code = "def test(): pass"

        context = ChaosOrchestrator.create_agent_context_for_attack(attack, base_context, code)

        assert context.policy == {"max_severity": "HIGH", "require_verification": True}

    def test_context_empty_vectors(self, base_context):
        """Test context creation with empty attack vectors."""
        attack = Attack(
            id="ATK-001",
            agent=AgentType.EXPLOIT_AGENT,
            target_file="test.py",
            target_function=None,
            priority=AttackPriority.HIGH,
            attack_vectors=[],
            time_budget_seconds=60,
            rationale="Attack with no specific vectors yet",
            depends_on=[],
        )

        code = "def test(): pass"

        context = ChaosOrchestrator.create_agent_context_for_attack(attack, base_context, code)

        # Should not include empty lists
        assert "attack_hints" not in context.inputs or context.inputs["attack_hints"] == []
        assert "focus_areas" not in context.inputs or context.inputs["focus_areas"] == []
        assert "payload_hints" not in context.inputs or context.inputs["payload_hints"] == []
        assert (
            "success_indicators" not in context.inputs or context.inputs["success_indicators"] == []
        )
