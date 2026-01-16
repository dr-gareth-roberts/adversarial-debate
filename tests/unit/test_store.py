"""Unit tests for the bead store module."""

from __future__ import annotations

import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import pytest

from adversarial_debate.store import (
    BeadStore,
    Bead,
    BeadType,
    Artefact,
    DuplicateBeadError,
    BeadValidationError,
)


class TestBead:
    """Tests for Bead dataclass."""

    def test_bead_creation(self) -> None:
        """Test creating a bead with valid data."""
        bead = Bead(
            bead_id="B-20240101-120000-000001",
            parent_bead_id="ROOT",
            thread_id="thread-001",
            task_id="task-001",
            timestamp_iso="2024-01-01T12:00:00Z",
            agent="ExploitAgent",
            bead_type=BeadType.EXPLOIT_ANALYSIS,
            payload={"finding": "test"},
            artefacts=[],
            idempotency_key="IK-001",
            confidence=0.9,
            assumptions=[],
            unknowns=[],
        )

        assert bead.bead_id == "B-20240101-120000-000001"
        assert bead.agent == "ExploitAgent"
        assert bead.bead_type == BeadType.EXPLOIT_ANALYSIS
        assert bead.confidence == 0.9

    def test_bead_with_artefacts(self) -> None:
        """Test creating a bead with artefacts."""
        artefact = Artefact(
            artefact_id="A-001",
            artefact_type="code_snippet",
            content="def test(): pass",
            metadata={"language": "python"},
        )

        bead = Bead(
            bead_id="B-001",
            parent_bead_id="ROOT",
            thread_id="thread-001",
            task_id="task-001",
            timestamp_iso="2024-01-01T12:00:00Z",
            agent="TestAgent",
            bead_type=BeadType.EXPLOIT_ANALYSIS,
            payload={},
            artefacts=[artefact],
            idempotency_key="IK-001",
            confidence=0.9,
            assumptions=[],
            unknowns=[],
        )

        assert len(bead.artefacts) == 1
        assert bead.artefacts[0].artefact_type == "code_snippet"

    def test_bead_to_dict(self, sample_bead: Bead) -> None:
        """Test converting bead to dictionary."""
        bead_dict = sample_bead.to_dict()

        assert isinstance(bead_dict, dict)
        assert bead_dict["bead_id"] == sample_bead.bead_id
        assert bead_dict["agent"] == sample_bead.agent
        assert bead_dict["confidence"] == sample_bead.confidence

    def test_bead_from_dict(self) -> None:
        """Test creating bead from dictionary."""
        bead_dict = {
            "bead_id": "B-001",
            "parent_bead_id": "ROOT",
            "thread_id": "thread-001",
            "task_id": "task-001",
            "timestamp_iso": "2024-01-01T12:00:00Z",
            "agent": "TestAgent",
            "bead_type": "EXPLOIT_ANALYSIS",
            "payload": {"test": "data"},
            "artefacts": [],
            "idempotency_key": "IK-001",
            "confidence": 0.85,
            "assumptions": [],
            "unknowns": [],
        }

        bead = Bead.from_dict(bead_dict)

        assert bead.bead_id == "B-001"
        assert bead.bead_type == BeadType.EXPLOIT_ANALYSIS
        assert bead.confidence == 0.85


class TestBeadStore:
    """Tests for BeadStore."""

    @pytest.fixture
    def store(self, temp_dir: Path) -> BeadStore:
        """Create a temporary bead store."""
        ledger_path = temp_dir / "beads" / "ledger.jsonl"
        return BeadStore(ledger_path)

    def test_store_creation(self, temp_dir: Path) -> None:
        """Test creating a new bead store."""
        ledger_path = temp_dir / "beads" / "ledger.jsonl"
        store = BeadStore(ledger_path)

        assert store.ledger_path == ledger_path
        assert ledger_path.parent.exists()

    def test_add_bead(self, store: BeadStore, sample_bead: Bead) -> None:
        """Test adding a bead to the store."""
        store.add_bead(sample_bead)

        # Verify bead was added
        retrieved = store.get_bead(sample_bead.bead_id)
        assert retrieved is not None
        assert retrieved.bead_id == sample_bead.bead_id

    def test_add_duplicate_bead(self, store: BeadStore, sample_bead: Bead) -> None:
        """Test that adding duplicate bead raises error."""
        store.add_bead(sample_bead)

        with pytest.raises(DuplicateBeadError):
            store.add_bead(sample_bead)

    def test_get_bead_not_found(self, store: BeadStore) -> None:
        """Test getting a non-existent bead."""
        bead = store.get_bead("nonexistent-id")
        assert bead is None

    def test_query_by_thread(self, store: BeadStore) -> None:
        """Test querying beads by thread ID."""
        # Add beads with different threads
        bead1 = Bead(
            bead_id="B-001",
            parent_bead_id="ROOT",
            thread_id="thread-A",
            task_id="task-001",
            timestamp_iso="2024-01-01T12:00:00Z",
            agent="TestAgent",
            bead_type=BeadType.EXPLOIT_ANALYSIS,
            payload={},
            artefacts=[],
            idempotency_key="IK-001",
            confidence=0.9,
            assumptions=[],
            unknowns=[],
        )

        bead2 = Bead(
            bead_id="B-002",
            parent_bead_id="ROOT",
            thread_id="thread-B",
            task_id="task-002",
            timestamp_iso="2024-01-01T12:00:01Z",
            agent="TestAgent",
            bead_type=BeadType.EXPLOIT_ANALYSIS,
            payload={},
            artefacts=[],
            idempotency_key="IK-002",
            confidence=0.8,
            assumptions=[],
            unknowns=[],
        )

        store.add_bead(bead1)
        store.add_bead(bead2)

        # Query by thread
        results = store.query(thread_id="thread-A")
        assert len(results) == 1
        assert results[0].bead_id == "B-001"

    def test_query_by_agent(self, store: BeadStore) -> None:
        """Test querying beads by agent name."""
        bead1 = Bead(
            bead_id="B-001",
            parent_bead_id="ROOT",
            thread_id="thread-001",
            task_id="task-001",
            timestamp_iso="2024-01-01T12:00:00Z",
            agent="ExploitAgent",
            bead_type=BeadType.EXPLOIT_ANALYSIS,
            payload={},
            artefacts=[],
            idempotency_key="IK-001",
            confidence=0.9,
            assumptions=[],
            unknowns=[],
        )

        bead2 = Bead(
            bead_id="B-002",
            parent_bead_id="ROOT",
            thread_id="thread-001",
            task_id="task-001",
            timestamp_iso="2024-01-01T12:00:01Z",
            agent="BreakAgent",
            bead_type=BeadType.BREAK_ANALYSIS,
            payload={},
            artefacts=[],
            idempotency_key="IK-002",
            confidence=0.8,
            assumptions=[],
            unknowns=[],
        )

        store.add_bead(bead1)
        store.add_bead(bead2)

        results = store.query(agent="ExploitAgent")
        assert len(results) == 1
        assert results[0].agent == "ExploitAgent"

    def test_query_by_bead_type(self, store: BeadStore) -> None:
        """Test querying beads by type."""
        bead1 = Bead(
            bead_id="B-001",
            parent_bead_id="ROOT",
            thread_id="thread-001",
            task_id="task-001",
            timestamp_iso="2024-01-01T12:00:00Z",
            agent="TestAgent",
            bead_type=BeadType.EXPLOIT_ANALYSIS,
            payload={},
            artefacts=[],
            idempotency_key="IK-001",
            confidence=0.9,
            assumptions=[],
            unknowns=[],
        )

        bead2 = Bead(
            bead_id="B-002",
            parent_bead_id="ROOT",
            thread_id="thread-001",
            task_id="task-001",
            timestamp_iso="2024-01-01T12:00:01Z",
            agent="TestAgent",
            bead_type=BeadType.CHAOS_ANALYSIS,
            payload={},
            artefacts=[],
            idempotency_key="IK-002",
            confidence=0.8,
            assumptions=[],
            unknowns=[],
        )

        store.add_bead(bead1)
        store.add_bead(bead2)

        results = store.query(bead_type=BeadType.EXPLOIT_ANALYSIS)
        assert len(results) == 1
        assert results[0].bead_type == BeadType.EXPLOIT_ANALYSIS

    def test_full_text_search(self, store: BeadStore) -> None:
        """Test full-text search across beads."""
        bead = Bead(
            bead_id="B-001",
            parent_bead_id="ROOT",
            thread_id="thread-001",
            task_id="task-001",
            timestamp_iso="2024-01-01T12:00:00Z",
            agent="ExploitAgent",
            bead_type=BeadType.EXPLOIT_ANALYSIS,
            payload={"finding": "SQL injection vulnerability in user query"},
            artefacts=[],
            idempotency_key="IK-001",
            confidence=0.9,
            assumptions=[],
            unknowns=[],
        )

        store.add_bead(bead)

        # Search should find the bead
        results = store.search("SQL injection")
        assert len(results) >= 1

        # Search for something not present
        results = store.search("XSS vulnerability")
        # May or may not find depending on implementation

    def test_persistence(self, temp_dir: Path) -> None:
        """Test that beads persist across store instances."""
        ledger_path = temp_dir / "beads" / "ledger.jsonl"

        # Create first store and add bead
        store1 = BeadStore(ledger_path)
        bead = Bead(
            bead_id="B-persist-001",
            parent_bead_id="ROOT",
            thread_id="thread-001",
            task_id="task-001",
            timestamp_iso="2024-01-01T12:00:00Z",
            agent="TestAgent",
            bead_type=BeadType.EXPLOIT_ANALYSIS,
            payload={"test": "persistence"},
            artefacts=[],
            idempotency_key="IK-persist-001",
            confidence=0.9,
            assumptions=[],
            unknowns=[],
        )
        store1.add_bead(bead)

        # Create second store and verify bead exists
        store2 = BeadStore(ledger_path)
        retrieved = store2.get_bead("B-persist-001")

        assert retrieved is not None
        assert retrieved.payload == {"test": "persistence"}

    def test_ledger_file_format(self, store: BeadStore, temp_dir: Path) -> None:
        """Test that ledger file is valid JSONL."""
        bead = Bead(
            bead_id="B-001",
            parent_bead_id="ROOT",
            thread_id="thread-001",
            task_id="task-001",
            timestamp_iso="2024-01-01T12:00:00Z",
            agent="TestAgent",
            bead_type=BeadType.EXPLOIT_ANALYSIS,
            payload={"key": "value"},
            artefacts=[],
            idempotency_key="IK-001",
            confidence=0.9,
            assumptions=[],
            unknowns=[],
        )
        store.add_bead(bead)

        # Read ledger file and verify format
        ledger_content = store.ledger_path.read_text()
        lines = ledger_content.strip().split("\n")

        for line in lines:
            # Each line should be valid JSON
            parsed = json.loads(line)
            assert "bead_id" in parsed

    def test_query_limit(self, store: BeadStore) -> None:
        """Test query result limiting."""
        # Add multiple beads
        for i in range(10):
            bead = Bead(
                bead_id=f"B-{i:03d}",
                parent_bead_id="ROOT",
                thread_id="thread-001",
                task_id="task-001",
                timestamp_iso=f"2024-01-01T12:00:{i:02d}Z",
                agent="TestAgent",
                bead_type=BeadType.EXPLOIT_ANALYSIS,
                payload={},
                artefacts=[],
                idempotency_key=f"IK-{i:03d}",
                confidence=0.9,
                assumptions=[],
                unknowns=[],
            )
            store.add_bead(bead)

        # Query with limit
        results = store.query(limit=5)
        assert len(results) == 5

    def test_empty_store_query(self, store: BeadStore) -> None:
        """Test querying an empty store."""
        results = store.query()
        assert results == []

    def test_get_all_beads(self, store: BeadStore) -> None:
        """Test getting all beads from store."""
        # Add a few beads
        for i in range(3):
            bead = Bead(
                bead_id=f"B-{i:03d}",
                parent_bead_id="ROOT",
                thread_id="thread-001",
                task_id="task-001",
                timestamp_iso=f"2024-01-01T12:00:{i:02d}Z",
                agent="TestAgent",
                bead_type=BeadType.EXPLOIT_ANALYSIS,
                payload={},
                artefacts=[],
                idempotency_key=f"IK-{i:03d}",
                confidence=0.9,
                assumptions=[],
                unknowns=[],
            )
            store.add_bead(bead)

        all_beads = store.get_all()
        assert len(all_beads) == 3


class TestBeadIdGeneration:
    """Tests for bead ID generation."""

    def test_idempotent_bead_id(self) -> None:
        """Test that same inputs produce same bead ID."""
        from adversarial_debate.store import compute_bead_id

        id1 = compute_bead_id("agent", "run-001", {"key": "value"})
        id2 = compute_bead_id("agent", "run-001", {"key": "value"})

        assert id1 == id2

    def test_different_inputs_different_ids(self) -> None:
        """Test that different inputs produce different IDs."""
        from adversarial_debate.store import compute_bead_id

        id1 = compute_bead_id("agent", "run-001", {"key": "value1"})
        id2 = compute_bead_id("agent", "run-001", {"key": "value2"})

        assert id1 != id2

    def test_bead_id_format(self) -> None:
        """Test that bead IDs have expected format."""
        from adversarial_debate.store import compute_bead_id

        bead_id = compute_bead_id("agent", "run-001", {"key": "value"})

        # Should be a hex string (SHA-256 produces 64 hex chars)
        assert len(bead_id) == 64
        assert all(c in "0123456789abcdef" for c in bead_id)
