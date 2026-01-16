"""Adversarial agents for security analysis.

The adversarial debate system uses multiple specialized agents:

- ExploitAgent: Finds security vulnerabilities (OWASP, CWE)
- BreakAgent: Finds logic bugs and edge cases
- ChaosAgent: Tests resilience and failure handling
- ChaosOrchestrator: Coordinates the attack strategy
- Arbiter: Consolidates findings with confidence scoring
"""

from .base import Agent, AgentContext, AgentOutput
from .exploit_agent import ExploitAgent
from .break_agent import BreakAgent
from .chaos_agent import ChaosAgent
from .chaos_orchestrator import ChaosOrchestrator
from .arbiter import Arbiter

__all__ = [
    "Agent",
    "AgentContext",
    "AgentOutput",
    "ExploitAgent",
    "BreakAgent",
    "ChaosAgent",
    "ChaosOrchestrator",
    "Arbiter",
]
