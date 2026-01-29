"""Adversarial Debate - AI Red Team Security Testing Framework.

A multi-agent adversarial system for automated security analysis that uses
competing AI agents to find vulnerabilities through structured debate.

Architecture:
    ChaosOrchestrator → ExploitAgent → BreakAgent → ChaosAgent → Arbiter
                     ↘      ↓           ↓           ↓      ↙
                        Findings merged and arbitrated

Example Usage:
    >>> import asyncio
    >>> from datetime import UTC, datetime
    >>> from adversarial_debate import ExploitAgent, AgentContext, BeadStore
    >>> from adversarial_debate import get_provider
    >>>
    >>> provider = get_provider("anthropic")
    >>> store = BeadStore()
    >>> agent = ExploitAgent(provider, store)
    >>> context = AgentContext(
    ...     run_id="analysis-001",
    ...     timestamp_iso=datetime.now(UTC).isoformat(),
    ...     policy={},
    ...     thread_id="analysis-001",
    ...     task_id="security-review",
    ...     inputs={"code": "def get_user(id): ...", "file_path": "app.py"},
    ... )
    >>> output = asyncio.run(agent.run(context))
"""

from .agents import (
    Agent,
    AgentContext,
    AgentOutput,
    Arbiter,
    BreakAgent,
    ChaosAgent,
    ChaosOrchestrator,
    CrossExaminationAgent,
    ExploitAgent,
)
from .attack_plan import (
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
from .config import (
    Config,
    LoggingConfig,
    ProviderConfig,
    get_config,
    set_config,
)
from .exceptions import (
    AdversarialDebateError,
    AgentError,
    AgentExecutionError,
    AgentParseError,
    AgentTimeoutError,
    BeadValidationError,
    ConfigError,
    ConfigValidationError,
    ProviderConnectionError,
    ProviderError,
    ProviderRateLimitError,
    SandboxError,
    SandboxExecutionError,
    SandboxTimeoutError,
    StoreError,
)
from .logging import (
    get_agent_logger,
    get_logger,
    setup_logging,
)
from .providers import (
    AnthropicProvider,
    LLMProvider,
    LLMResponse,
    Message,
    MockProvider,
    ModelTier,
    get_provider,
)
from .sandbox import (
    ExecutionResult,
    SandboxConfig,
    SandboxExecutor,
    SandboxSecurityError,
)
from .store import (
    Artefact,
    ArtefactType,
    Bead,
    BeadStore,
    BeadType,
)
from .verdict import (
    ArbiterVerdict,
    ExploitationDifficulty,
    FindingValidation,
    RejectedFinding,
    RemediationEffort,
    RemediationTask,
    ValidatedFinding,
    VerdictDecision,
)

__version__ = "0.1.0"

__all__ = [
    # Version
    "__version__",
    # Agents
    "Agent",
    "AgentContext",
    "AgentOutput",
    "ExploitAgent",
    "BreakAgent",
    "ChaosAgent",
    "ChaosOrchestrator",
    "CrossExaminationAgent",
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
    "MockProvider",
    "get_provider",
    # Store
    "BeadStore",
    "Bead",
    "BeadType",
    "Artefact",
    "ArtefactType",
    # Verdict types
    "VerdictDecision",
    "ExploitationDifficulty",
    "RemediationEffort",
    "FindingValidation",
    "ValidatedFinding",
    "RejectedFinding",
    "RemediationTask",
    "ArbiterVerdict",
    # Attack plan types
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
    # Exceptions
    "AdversarialDebateError",
    "AgentError",
    "AgentExecutionError",
    "AgentParseError",
    "AgentTimeoutError",
    "ProviderError",
    "ProviderRateLimitError",
    "ProviderConnectionError",
    "SandboxError",
    "SandboxExecutionError",
    "SandboxTimeoutError",
    "StoreError",
    "BeadValidationError",
    "ConfigError",
    "ConfigValidationError",
    # Configuration
    "Config",
    "ProviderConfig",
    "LoggingConfig",
    "get_config",
    "set_config",
    # Logging
    "setup_logging",
    "get_logger",
    "get_agent_logger",
]
