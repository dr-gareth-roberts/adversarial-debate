"""Adversarial agents for security analysis.

The adversarial debate system uses multiple specialized agents:

- ExploitAgent: Finds security vulnerabilities (OWASP, CWE)
- BreakAgent: Finds logic bugs and edge cases
- ChaosAgent: Tests resilience and failure handling
- ChaosOrchestrator: Coordinates the attack strategy
- Arbiter: Consolidates findings with confidence scoring
"""

from .arbiter import Arbiter
from .base import Agent, AgentContext, AgentOutput
from .break_agent import BreakAgent
from .chaos_agent import ChaosAgent
from .chaos_orchestrator import ChaosOrchestrator
from .cross_examiner import CrossExaminationAgent
from .crypto_agent import CryptoAgent
from .exploit_agent import ExploitAgent

__all__ = [
    "Agent",
    "AgentContext",
    "AgentOutput",
    "ExploitAgent",
    "BreakAgent",
    "ChaosAgent",
    "ChaosOrchestrator",
    "CrossExaminationAgent",
    "CryptoAgent",
    "Arbiter",
]
