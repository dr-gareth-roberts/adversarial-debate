"""Base agent class for adversarial debate agents."""

import json
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..providers import LLMProvider, Message, ModelTier
from ..store import Bead, BeadStore, BeadType


@dataclass
class AgentContext:
    """Context passed to an agent for execution.

    Contains all the information an agent needs to do its work.
    """
    # Run metadata
    run_id: str
    timestamp_iso: str

    # Policy and constraints
    policy: dict[str, Any]

    # Bead context
    thread_id: str
    task_id: str = ""
    parent_bead_id: str = ""
    recent_beads: list[Bead] = field(default_factory=list)

    # Task-specific inputs (varies by agent type)
    inputs: dict[str, Any] = field(default_factory=dict)

    # Repo context
    repo_files: dict[str, str] = field(default_factory=dict)  # path -> content

    def to_dict(self) -> dict[str, Any]:
        """Convert to dict for prompt injection."""
        return {
            "run_id": self.run_id,
            "timestamp_iso": self.timestamp_iso,
            "thread_id": self.thread_id,
            "task_id": self.task_id,
            "parent_bead_id": self.parent_bead_id,
            "policy": self.policy,
            "recent_beads": [b.to_dict() for b in self.recent_beads],
            "inputs": self.inputs,
            "repo_files": self.repo_files,
        }


@dataclass
class AgentOutput:
    """Output from an agent execution.

    All agents produce structured output that includes beads.
    """
    # Agent identification
    agent_name: str

    # Primary output (agent-specific structure)
    result: dict[str, Any]

    # Beads to append
    beads_out: list[Bead]

    # Confidence and epistemic status
    confidence: float
    assumptions: list[str] = field(default_factory=list)
    unknowns: list[str] = field(default_factory=list)

    # Errors (if any)
    errors: list[str] = field(default_factory=list)

    @property
    def success(self) -> bool:
        return len(self.errors) == 0


class Agent(ABC):
    """Base class for all agents in the adversarial debate system.

    Agents are stateless processors that:
    1. Receive context (beads, policy, task inputs)
    2. Call an LLM with a structured prompt
    3. Parse the response into structured output
    4. Emit beads for coordination
    """

    def __init__(
        self,
        provider: LLMProvider,
        bead_store: BeadStore,
        prompts_dir: Path | None = None,
    ):
        self.provider = provider
        self.bead_store = bead_store
        self.prompts_dir = prompts_dir or self._find_prompts_dir()

    @property
    @abstractmethod
    def name(self) -> str:
        """Agent name (e.g., 'ExploitAgent', 'BreakAgent')."""
        ...

    @property
    @abstractmethod
    def bead_type(self) -> BeadType:
        """Type of bead this agent produces."""
        ...

    @property
    def model_tier(self) -> ModelTier:
        """Default model tier for this agent."""
        return ModelTier.HOSTED_SMALL

    @abstractmethod
    def _build_prompt(self, context: AgentContext) -> list[Message]:
        """Build the prompt messages for the LLM.

        Subclasses implement this to construct agent-specific prompts.
        """
        ...

    @abstractmethod
    def _parse_response(
        self,
        response: str,
        context: AgentContext,
    ) -> AgentOutput:
        """Parse LLM response into structured output.

        Subclasses implement this to handle agent-specific output schemas.
        """
        ...

    async def run(self, context: AgentContext) -> AgentOutput:
        """Execute the agent with the given context.

        This is the main entry point for running an agent.
        """
        # Build prompt
        messages = self._build_prompt(context)

        # Get model for tier
        model = self.provider.get_model_for_tier(self.model_tier)

        # Call LLM
        response = await self.provider.complete(
            messages,
            model=model,
            json_mode=True,
        )

        # Parse response
        output = self._parse_response(response.content, context)

        # Append beads to store
        if output.beads_out:
            self.bead_store.append_many(output.beads_out)

        return output

    def _load_prompt_template(self, filename: str) -> str:
        """Load a prompt template from the prompts directory."""
        path = self.prompts_dir / filename
        if not path.exists():
            raise FileNotFoundError(f"Prompt template not found: {path}")
        return path.read_text()

    def _load_constraints(self) -> str:
        """Load the hard constraints that apply to all agents."""
        try:
            return self._load_prompt_template("Constraints.md")
        except FileNotFoundError:
            return ""

    def _find_prompts_dir(self) -> Path:
        """Find the prompts directory relative to project root."""
        current = Path.cwd()
        while current != current.parent:
            prompts_dir = current / "prompts"
            if prompts_dir.exists():
                return prompts_dir
            current = current.parent
        return Path("prompts")

    def _create_bead(
        self,
        context: AgentContext,
        payload: dict[str, Any],
        artefacts: list[dict[str, str]] | None = None,
        confidence: float = 0.8,
        assumptions: list[str] | None = None,
        unknowns: list[str] | None = None,
    ) -> Bead:
        """Helper to create a bead with standard fields."""
        from ..store import Artefact, ArtefactType

        bead_artefacts = []
        if artefacts:
            for a in artefacts:
                bead_artefacts.append(Artefact(
                    type=ArtefactType(a["type"]),
                    ref=a["ref"],
                ))

        return Bead(
            bead_id=BeadStore.generate_bead_id(),
            parent_bead_id=context.parent_bead_id,
            thread_id=context.thread_id,
            task_id=context.task_id,
            timestamp_iso=context.timestamp_iso,
            agent=self.name,
            bead_type=self.bead_type,
            payload=payload,
            artefacts=bead_artefacts,
            idempotency_key=self._generate_idempotency_key(context),
            confidence=confidence,
            assumptions=assumptions or [],
            unknowns=unknowns or [],
        )

    def _generate_idempotency_key(self, context: AgentContext) -> str:
        """Generate an idempotency key for this agent run."""
        parts = [f"IK-{self.bead_type.value}", context.thread_id]
        if context.task_id:
            parts.append(context.task_id)
        return "-".join(parts)

    def _parse_json_response(self, response: str) -> dict[str, Any]:
        """Parse JSON from LLM response, handling markdown code blocks."""
        content = response.strip()

        # Strategy 1: Try to extract JSON from markdown code blocks
        if "```" in content:
            code_block_match = re.search(
                r'```(?:json)?\s*\n(.*?)\n```', content, re.DOTALL
            )
            if code_block_match:
                content = code_block_match.group(1).strip()

        # Strategy 2: Find first { and last } to extract JSON object
        first_brace = content.find('{')
        last_brace = content.rfind('}')

        if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
            content = content[first_brace:last_brace + 1]

        try:
            return json.loads(content)
        except json.JSONDecodeError as e:
            # Try removing trailing commas
            try:
                cleaned = re.sub(r',(\s*[}\]])', r'\1', content)
                return json.loads(cleaned)
            except json.JSONDecodeError:
                raise json.JSONDecodeError(
                    f"Failed to parse JSON: {e}. Content: {content[:200]}...",
                    e.doc,
                    e.pos
                )
