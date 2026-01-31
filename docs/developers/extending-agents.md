# Extending Agents

Create custom agents to add new types of analysis to the framework.

## Overview

Agents follow a simple pattern:
1. Receive context with code and metadata
2. Build a prompt for the LLM
3. Parse the response into structured findings
4. Emit a bead for the audit trail

## The Agent Base Class

All agents extend the abstract `Agent` class:

```python
from abc import ABC, abstractmethod
from adversarial_debate.agents.base import Agent, AgentContext, AgentOutput
from adversarial_debate.providers import LLMProvider, Message
from adversarial_debate.store import BeadStore, BeadType, Bead


class Agent(ABC):
    def __init__(self, provider: LLMProvider, bead_store: BeadStore):
        self.provider = provider
        self.bead_store = bead_store

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable agent name."""
        ...

    @property
    @abstractmethod
    def bead_type(self) -> BeadType:
        """Type of bead this agent produces."""
        ...

    @property
    def model_tier(self) -> str:
        """Model capability tier (HOSTED_LARGE or HOSTED_SMALL)."""
        return "HOSTED_LARGE"

    @abstractmethod
    def _build_prompt(self, context: AgentContext) -> list[Message]:
        """Build the LLM prompt from context."""
        ...

    @abstractmethod
    def _parse_response(
        self, response: str, context: AgentContext
    ) -> AgentOutput:
        """Parse LLM response into structured output."""
        ...

    async def run(self, context: AgentContext) -> AgentOutput:
        """Execute the agent."""
        # Build prompt
        messages = self._build_prompt(context)

        # Call LLM
        model = self.provider.get_model_for_tier(self.model_tier)
        response = await self.provider.complete(
            messages,
            model=model,
            json_mode=True,
        )

        # Parse response
        result = self._parse_response(response.content, context)

        # Create bead
        bead = self._create_bead(context, result)
        self.bead_store.append(bead)

        # Return output
        return AgentOutput(
            agent_name=self.name,
            result=result,
            beads_out=[bead],
            confidence=result.get("confidence", 0.5),
            assumptions=result.get("assumptions", []),
            unknowns=result.get("unknowns", []),
            errors=[],
        )
```

## Creating a Custom Agent

Let's create an agent that checks for accessibility issues in web code.

### Step 1: Define the Agent

```python
# src/adversarial_debate/agents/accessibility_agent.py

from adversarial_debate.agents.base import Agent, AgentContext, AgentOutput
from adversarial_debate.providers import Message
from adversarial_debate.store import BeadType


class AccessibilityAgent(Agent):
    """Checks for WCAG accessibility violations in web code."""

    @property
    def name(self) -> str:
        return "AccessibilityAgent"

    @property
    def bead_type(self) -> BeadType:
        return BeadType.ACCESSIBILITY_ANALYSIS  # Add to BeadType enum

    @property
    def model_tier(self) -> str:
        return "HOSTED_LARGE"  # Needs reasoning capability

    def _build_prompt(self, context: AgentContext) -> list[Message]:
        code = context.inputs.get("code", "")
        file_path = context.inputs.get("file_path", "unknown")

        system_prompt = """You are an accessibility expert analysing web code for WCAG 2.1 violations.

For each violation found, provide:
- finding_id: Unique identifier (ACC-NNN)
- title: Brief description
- wcag_criterion: The WCAG criterion violated (e.g., "1.1.1 Non-text Content")
- level: A, AA, or AAA
- severity: CRITICAL, HIGH, MEDIUM, LOW
- description: Detailed explanation
- location: file, line, element
- remediation: How to fix
- impact: Effect on users with disabilities

Output valid JSON with a "findings" array."""

        user_prompt = f"""Analyse this code for accessibility issues:

File: {file_path}

```
{code}
```

Focus on:
1. Missing alt text on images
2. Missing form labels
3. Insufficient colour contrast
4. Missing ARIA attributes
5. Keyboard navigation issues
6. Missing skip links
7. Improper heading hierarchy

Return findings as JSON."""

        return [
            Message(role="system", content=system_prompt),
            Message(role="user", content=user_prompt),
        ]

    def _parse_response(
        self, response: str, context: AgentContext
    ) -> AgentOutput:
        import json

        try:
            data = json.loads(response)
        except json.JSONDecodeError:
            return AgentOutput(
                agent_name=self.name,
                result={"findings": [], "error": "Failed to parse response"},
                beads_out=[],
                confidence=0.0,
                assumptions=[],
                unknowns=[],
                errors=["Failed to parse response"],
            )

        findings = data.get("findings", [])

        # Validate and normalise findings
        normalised = []
        for f in findings:
            normalised.append({
                "finding_id": f.get("finding_id", "ACC-???"),
                "title": f.get("title", "Unknown issue"),
                "wcag_criterion": f.get("wcag_criterion", "Unknown"),
                "level": f.get("level", "AA"),
                "severity": f.get("severity", "MEDIUM"),
                "description": f.get("description", ""),
                "location": f.get("location", {}),
                "remediation": f.get("remediation", ""),
                "impact": f.get("impact", ""),
                "agent": self.name,
            })

        return AgentOutput(
            agent_name=self.name,
            result={
                "findings": normalised,
                "summary": {
                    "total_findings": len(normalised),
                    "by_level": self._count_by_level(normalised),
                },
            },
            beads_out=[],  # Beads created in base run() method
            confidence=data.get("confidence", 0.75),
            assumptions=data.get("assumptions", []),
            unknowns=data.get("unknowns", []),
        )

    def _count_by_level(self, findings: list) -> dict:
        counts = {"A": 0, "AA": 0, "AAA": 0}
        for f in findings:
            level = f.get("level", "AA")
            if level in counts:
                counts[level] += 1
        return counts
```

### Step 2: Add the BeadType

```python
# src/adversarial_debate/store/beads.py

class BeadType(str, Enum):
    ATTACK_PLAN = "ATTACK_PLAN"
    EXPLOIT_ANALYSIS = "EXPLOIT_ANALYSIS"
    BREAK_ANALYSIS = "BREAK_ANALYSIS"
    CHAOS_ANALYSIS = "CHAOS_ANALYSIS"
    CRYPTO_ANALYSIS = "CRYPTO_ANALYSIS"
    ARBITER_VERDICT = "ARBITER_VERDICT"
    ACCESSIBILITY_ANALYSIS = "ACCESSIBILITY_ANALYSIS"  # Add this
```

### Step 3: Export the Agent

```python
# src/adversarial_debate/agents/__init__.py

from .accessibility_agent import AccessibilityAgent

__all__ = [
    # ... existing exports
    "AccessibilityAgent",
]
```

### Step 4: Add Tests

```python
# tests/unit/test_agents/test_accessibility_agent.py

import pytest
from adversarial_debate.agents import AccessibilityAgent
from adversarial_debate.providers import MockProvider
from adversarial_debate.store import BeadStore
from adversarial_debate import AgentContext


@pytest.fixture
def agent():
    provider = MockProvider()
    store = BeadStore(":memory:")
    return AccessibilityAgent(provider, store)


@pytest.fixture
def context():
    return AgentContext(
        run_id="test-001",
        timestamp_iso="2024-01-15T14:30:22Z",
        policy={},
        thread_id="test",
        task_id="accessibility",
        inputs={
            "code": '<img src="logo.png">',
            "file_path": "index.html",
        },
    )


@pytest.mark.asyncio
async def test_agent_name(agent):
    assert agent.name == "AccessibilityAgent"


@pytest.mark.asyncio
async def test_finds_missing_alt(agent, context):
    output = await agent.run(context)
    assert output.success
    # Add assertions based on mock response
```

## Prompt Engineering Tips

### System Prompt Structure

```python
system_prompt = """You are a [ROLE] analysing code for [PURPOSE].

EXPERTISE:
- [Domain knowledge 1]
- [Domain knowledge 2]

OUTPUT FORMAT:
Return valid JSON with this structure:
{
    "findings": [
        {
            "finding_id": "PREFIX-NNN",
            "title": "...",
            ...
        }
    ],
    "confidence": 0.0-1.0,
    "assumptions": ["..."],
    "unknowns": ["..."]
}

GUIDELINES:
- [Specific instruction 1]
- [Specific instruction 2]"""
```

### User Prompt Structure

```python
user_prompt = f"""Analyse this code:

File: {file_path}
Function: {function_name}

```{language}
{code}
```

Context:
{additional_context}

Focus on:
{focus_areas}

Additional hints:
{hints}"""
```

### Response Parsing

Always handle parsing errors gracefully:

```python
def _parse_response(self, response: str, context: AgentContext) -> AgentOutput:
    import json

    # Try to extract JSON from markdown code blocks
    if "```json" in response:
        start = response.find("```json") + 7
        end = response.find("```", start)
        response = response[start:end].strip()
    elif "```" in response:
        start = response.find("```") + 3
        end = response.find("```", start)
        response = response[start:end].strip()

    try:
        data = json.loads(response)
    except json.JSONDecodeError as e:
        return AgentOutput(
            agent_name=self.name,
            result={
                "findings": [],
                "error": f"JSON parse error: {e}",
                "raw_response": response[:500],
            },
            beads_out=[],
            confidence=0.0,
            errors=[f"JSON parse error: {e}"],
        )

    return self._normalise_findings(data)
```

## Model Tier Selection

Choose the appropriate model tier:

| Tier | Use When | Examples |
|------|----------|----------|
| `HOSTED_LARGE` | Complex reasoning, nuanced analysis | ExploitAgent, BreakAgent, Arbiter |
| `HOSTED_SMALL` | Structured tasks, simpler patterns | ChaosOrchestrator, ChaosAgent |

```python
@property
def model_tier(self) -> str:
    # For complex security reasoning
    return "HOSTED_LARGE"

    # For simpler, structured tasks
    # return "HOSTED_SMALL"
```

## Integrating with the Pipeline

### Add to Orchestrator Assignments

Update the ChaosOrchestrator to assign your agent:

```python
# In chaos_orchestrator.py

def _assign_agent(self, file_info: dict) -> list[AgentType]:
    agents = []

    # Existing assignments...

    # Add accessibility agent for HTML/JSX files
    if file_info["path"].endswith((".html", ".jsx", ".tsx")):
        agents.append(AgentType.ACCESSIBILITY_AGENT)

    return agents
```

### Add to CLI

```python
# In cli_commands.py

AGENT_MAP = {
    "exploit": ExploitAgent,
    "break": BreakAgent,
    "chaos": ChaosAgent,
    "crypto": CryptoAgent,
    "accessibility": AccessibilityAgent,  # Add this
}
```

## Best Practices

### 1. Keep Prompts Focused

Each agent should focus on one domain. Don't try to detect everything.

### 2. Validate All Inputs

```python
def _build_prompt(self, context: AgentContext) -> list[Message]:
    code = context.inputs.get("code")
    if not code:
        raise ValueError("Code is required")

    if len(code) > 100_000:
        code = code[:100_000]  # Truncate to fit context
```

### 3. Normalise Findings

Ensure consistent output structure:

```python
def _normalise_finding(self, raw: dict) -> dict:
    return {
        "finding_id": raw.get("finding_id", "UNKNOWN"),
        "title": raw.get("title", "Unknown issue"),
        "severity": raw.get("severity", "MEDIUM").upper(),
        "description": raw.get("description", ""),
        "location": {
            "file": raw.get("location", {}).get("file", "unknown"),
            "line": raw.get("location", {}).get("line", 0),
        },
        "remediation": raw.get("remediation", ""),
        "confidence": float(raw.get("confidence", 0.5)),
        "agent": self.name,
    }
```

### 4. Handle Errors Gracefully

```python
async def run(self, context: AgentContext) -> AgentOutput:
    try:
        return await super().run(context)
    except ProviderError as e:
        return AgentOutput(
            agent_name=self.name,
            result={"error": str(e)},
            beads_out=[],
            confidence=0.0,
            assumptions=[],
            unknowns=[],
            errors=[str(e)],
        )
```

### 5. Document Your Agent

Add docstrings and type hints:

```python
class AccessibilityAgent(Agent):
    """Analyses web code for WCAG 2.1 accessibility violations.

    This agent identifies issues that affect users with disabilities,
    including missing alt text, form labels, and ARIA attributes.

    Input Context:
        code: The HTML/JSX code to analyse
        file_path: Path to the file
        wcag_level: Target WCAG level (A, AA, AAA)

    Output:
        findings: List of accessibility violations
        summary: Count by WCAG level
    """
```

## See Also

- [Python API Guide](python-api.md) — Using agents
- [Extending Providers](extending-providers.md) — Custom LLM backends
- [Testing Guide](testing.md) — Testing agents
- [Agent Reference](../reference/agents.md) — Existing agent details
