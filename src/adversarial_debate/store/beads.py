"""Bead store implementation - append-only JSONL ledger for coordination."""

import contextlib
import fcntl
import json
import os
from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from typing import Any

from ..exceptions import BeadValidationError, DuplicateBeadError


class BeadType(str, Enum):
    """Allowed bead types."""

    BOARD_HEALTH = "board_health"
    PROPOSAL = "proposal"
    CRITIQUE = "critique"
    DECISION = "decision"
    PLAN = "plan"
    TASK = "task"
    PATCH = "patch"
    REVIEW = "review"
    INTEGRATION = "integration"
    POSTHOOK = "posthook"
    REFLECTION = "reflection"
    # Adversarial mesh types
    ATTACK_PLAN = "attack_plan"
    BREAK_ANALYSIS = "break_analysis"
    EXPLOIT_ANALYSIS = "exploit_analysis"
    CRYPTO_ANALYSIS = "crypto_analysis"
    CHAOS_ANALYSIS = "chaos_analysis"
    ARBITER_VERDICT = "arbiter_verdict"
    CROSS_EXAMINATION = "cross_examination"


class ArtefactType(str, Enum):
    """Allowed artefact types."""

    TRELLO_CARD = "trello_card"
    FILE = "file"
    COMMIT = "commit"
    PR = "pr"
    EVAL = "eval"
    PATCH_BUNDLE = "patch_bundle"
    OTHER = "other"


@dataclass
class Artefact:
    """Reference to an artefact produced or consumed by a bead."""

    type: ArtefactType
    ref: str

    def to_dict(self) -> dict[str, str]:
        return {"type": self.type.value, "ref": self.ref}

    @classmethod
    def from_dict(cls, data: dict[str, str]) -> "Artefact":
        return cls(type=ArtefactType(data["type"]), ref=data["ref"])


@dataclass
class Bead:
    """A bead is the unit of handoff, audit, and idempotency.

    Required fields match beads/schema.json.
    """

    bead_id: str
    parent_bead_id: str
    thread_id: str
    task_id: str
    timestamp_iso: str
    agent: str
    bead_type: BeadType
    payload: dict[str, Any]
    artefacts: list[Artefact]
    idempotency_key: str
    confidence: float
    assumptions: list[str] = field(default_factory=list)
    unknowns: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Validate bead on creation."""
        if not 0.0 <= self.confidence <= 1.0:
            raise BeadValidationError(
                f"confidence must be in [0, 1], got {self.confidence}",
                bead_id=self.bead_id,
                field="confidence",
                details={"value": self.confidence},
            )
        if len(self.bead_id) < 3:
            raise BeadValidationError(
                f"bead_id must be at least 3 chars, got {self.bead_id!r}",
                bead_id=self.bead_id,
                field="bead_id",
            )
        if len(self.thread_id) < 3:
            raise BeadValidationError(
                f"thread_id must be at least 3 chars, got {self.thread_id!r}",
                bead_id=self.bead_id,
                field="thread_id",
            )
        if len(self.idempotency_key) < 3:
            raise BeadValidationError(
                f"idempotency_key must be at least 3 chars, got {self.idempotency_key!r}",
                bead_id=self.bead_id,
                field="idempotency_key",
            )

    def to_dict(self) -> dict[str, Any]:
        """Convert to JSON-serializable dict."""
        return {
            "bead_id": self.bead_id,
            "parent_bead_id": self.parent_bead_id,
            "thread_id": self.thread_id,
            "task_id": self.task_id,
            "timestamp_iso": self.timestamp_iso,
            "agent": self.agent,
            "bead_type": self.bead_type.value,
            "payload": self.payload,
            "artefacts": [a.to_dict() for a in self.artefacts],
            "idempotency_key": self.idempotency_key,
            "confidence": self.confidence,
            "assumptions": self.assumptions,
            "unknowns": self.unknowns,
        }

    def to_json(self) -> str:
        """Convert to JSON string (single line, no trailing newline)."""
        return json.dumps(self.to_dict(), separators=(",", ":"))

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Bead":
        """Create from dict."""
        return cls(
            bead_id=data["bead_id"],
            parent_bead_id=data["parent_bead_id"],
            thread_id=data["thread_id"],
            task_id=data["task_id"],
            timestamp_iso=data["timestamp_iso"],
            agent=data["agent"],
            bead_type=BeadType(data["bead_type"]),
            payload=data["payload"],
            artefacts=[Artefact.from_dict(a) for a in data["artefacts"]],
            idempotency_key=data["idempotency_key"],
            confidence=data["confidence"],
            assumptions=data.get("assumptions", []),
            unknowns=data.get("unknowns", []),
        )

    @classmethod
    def from_json(cls, line: str) -> "Bead":
        """Parse from JSON line."""
        return cls.from_dict(json.loads(line))


class BeadStore:
    """Append-only JSONL store for beads.

    Thread-safe via file locking for appends.
    """

    def __init__(self, ledger_path: str | Path | None = None):
        """Initialize bead store.

        Args:
            ledger_path: Path to ledger.jsonl. Defaults to beads/ledger.jsonl
                        relative to project root.
        """
        if ledger_path is None:
            # Find project root by looking for beads directory
            current = Path.cwd()
            while current != current.parent:
                if (current / "beads" / "ledger.jsonl").exists():
                    ledger_path = current / "beads" / "ledger.jsonl"
                    break
                current = current.parent
            if ledger_path is None:
                # Default to current directory
                ledger_path = Path("beads/ledger.jsonl")

        self.ledger_path = Path(ledger_path)
        self._ensure_ledger_exists()

    def _ensure_ledger_exists(self) -> None:
        """Create ledger file and directory if needed."""
        secure_dir_mode = 0o700
        secure_file_mode = 0o600

        self.ledger_path.parent.mkdir(parents=True, exist_ok=True, mode=secure_dir_mode)
        with contextlib.suppress(OSError):
            os.chmod(self.ledger_path.parent, secure_dir_mode)

        if not self.ledger_path.exists():
            try:
                fd = os.open(
                    str(self.ledger_path),
                    os.O_CREAT | os.O_EXCL | os.O_WRONLY,
                    secure_file_mode,
                )
                os.close(fd)
            except FileExistsError:
                pass

        with contextlib.suppress(OSError):
            os.chmod(self.ledger_path, secure_file_mode)

    def append(self, bead: Bead) -> None:
        """Append a bead to the ledger (thread-safe).

        Args:
            bead: The bead to append
        """
        line = bead.to_json() + "\n"

        # Use file locking for thread safety
        with open(self.ledger_path, "a") as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            try:
                f.write(line)
            finally:
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)

    def append_idempotent(self, bead: Bead) -> None:
        """Append a bead only if its idempotency key is not already present.

        This is intended for operations where retries are expected and emitting
        duplicate beads would be misleading.

        Raises:
            DuplicateBeadError: If the idempotency key already exists in the ledger.
        """
        line = bead.to_json() + "\n"

        # Atomic check + append under the same lock.
        with open(self.ledger_path, "a+") as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            try:
                f.seek(0)
                for raw in f:
                    raw = raw.strip()
                    if not raw:
                        continue
                    try:
                        existing = json.loads(raw)
                    except json.JSONDecodeError:
                        continue
                    if existing.get("idempotency_key") == bead.idempotency_key:
                        raise DuplicateBeadError(
                            "Duplicate idempotency_key",
                            idempotency_key=bead.idempotency_key,
                        )
                f.seek(0, 2)  # end of file
                f.write(line)
            finally:
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)

    def append_many(self, beads: list[Bead]) -> None:
        """Append multiple beads atomically."""
        lines = "".join(bead.to_json() + "\n" for bead in beads)

        with open(self.ledger_path, "a") as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            try:
                f.write(lines)
            finally:
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)

    def iter_all(self) -> Iterator[Bead]:
        """Iterate over all beads in the ledger."""
        if not self.ledger_path.exists():
            return

        with open(self.ledger_path) as f:
            for line in f:
                line = line.strip()
                if line:
                    yield Bead.from_json(line)

    def query(
        self,
        *,
        thread_id: str | None = None,
        task_id: str | None = None,
        bead_type: BeadType | None = None,
        agent: str | None = None,
        idempotency_key: str | None = None,
        limit: int | None = None,
    ) -> list[Bead]:
        """Query beads with optional filters.

        Args:
            thread_id: Filter by thread (workstream)
            task_id: Filter by task
            bead_type: Filter by type
            agent: Filter by agent name
            idempotency_key: Find by exact idempotency key
            limit: Maximum number of results (from end of ledger)

        Returns:
            List of matching beads (most recent last)
        """
        results: list[Bead] = []

        for bead in self.iter_all():
            if thread_id is not None and bead.thread_id != thread_id:
                continue
            if task_id is not None and bead.task_id != task_id:
                continue
            if bead_type is not None and bead.bead_type != bead_type:
                continue
            if agent is not None and bead.agent != agent:
                continue
            if idempotency_key is not None and bead.idempotency_key != idempotency_key:
                continue
            results.append(bead)

        if limit is not None:
            results = results[-limit:]

        return results

    def has_idempotency_key(self, key: str) -> bool:
        """Check if an idempotency key already exists.

        This is the primary "already done?" check before external actions.
        """
        return any(bead.idempotency_key == key for bead in self.iter_all())

    def get_by_id(self, bead_id: str) -> Bead | None:
        """Get a bead by its ID."""
        for bead in self.iter_all():
            if bead.bead_id == bead_id:
                return bead
        return None

    def get_bead(self, bead_id: str) -> Bead | None:
        """Backwards-compatible alias for get_by_id()."""
        return self.get_by_id(bead_id)

    def get_all(self) -> list[Bead]:
        """Get all beads in the ledger."""
        return list(self.iter_all())

    def search(self, query: str, *, limit: int | None = None) -> list[Bead]:
        """Naive full-text search across bead JSON.

        This is intended for small-to-medium ledgers. For large ledgers, prefer
        external indexing or a dedicated store.
        """
        q = query.strip().lower()
        if not q:
            return []

        matches: list[Bead] = []
        for bead in self.iter_all():
            haystack = json.dumps(bead.to_dict(), separators=(",", ":"), default=str).lower()
            if q in haystack:
                matches.append(bead)

        if limit is not None:
            return matches[-limit:]
        return matches

    def get_children(self, parent_bead_id: str) -> list[Bead]:
        """Get all beads that reference a parent bead."""
        return [b for b in self.iter_all() if b.parent_bead_id == parent_bead_id]

    def count(self) -> int:
        """Count total beads in ledger."""
        return sum(1 for _ in self.iter_all())

    @staticmethod
    def generate_bead_id(prefix: str = "B") -> str:
        """Generate a unique bead ID.

        Format: B-YYYYMMDD-HHMMSS-NNNNNN
        """
        now = datetime.now(UTC)
        date_part = now.strftime("%Y%m%d-%H%M%S")
        # Add microseconds for uniqueness
        micro_part = f"{now.microsecond:06d}"
        return f"{prefix}-{date_part}-{micro_part}"

    @staticmethod
    def now_iso() -> str:
        """Get current timestamp in ISO format."""
        return datetime.now(UTC).isoformat()
