"""Adversarial Debate - AI Red Team Security Testing Framework.

A multi-agent adversarial system for automated security analysis that uses
competing AI agents to find vulnerabilities through structured debate.

Architecture:
    ChaosOrchestrator → ExploitAgent → BreakAgent → ChaosAgent → Arbiter
                     ↘      ↓           ↓           ↓      ↙
                        Findings merged and arbitrated
"""

from .agents import (
    Agent,
    AgentContext,
    AgentOutput,
    ExploitAgent,
    BreakAgent,
    ChaosAgent,
    ChaosOrchestrator,
    Arbiter,
)
from .sandbox import (
    SandboxExecutor,
    SandboxConfig,
    ExecutionResult,
    SandboxSecurityError,
)
from .providers import (
    LLMProvider,
    LLMResponse,
    Message,
    ModelTier,
    AnthropicProvider,
    get_provider,
)
from .store import (
    BeadStore,
    Bead,
    BeadType,
    Artefact,
    ArtefactType,
)

__version__ = "0.1.0"

__all__ = [
    # Agents
    "Agent",
    "AgentContext",
    "AgentOutput",
    "ExploitAgent",
    "BreakAgent",
    "ChaosAgent",
    "ChaosOrchestrator",
    "Arbiter",
    # Sandbox
    "SandboxExecutor",
    "SandboxConfig",
    "ExecutionResult",
    "SandboxSecurityError",
    # Providers
    "LLMProvider",
    "LLMResponse",
    "Message",
    "ModelTier",
    "AnthropicProvider",
    "get_provider",
    # Store
    "BeadStore",
    "Bead",
    "BeadType",
    "Artefact",
    "ArtefactType",
]
