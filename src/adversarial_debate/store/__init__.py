"""Bead store for event-sourced coordination.

Beads are the unit of handoff, audit, and idempotency in the adversarial debate system.
Each agent action produces a bead that records what happened.
"""

from .beads import Artefact, ArtefactType, Bead, BeadStore, BeadType

__all__ = [
    "BeadStore",
    "Bead",
    "BeadType",
    "Artefact",
    "ArtefactType",
]
