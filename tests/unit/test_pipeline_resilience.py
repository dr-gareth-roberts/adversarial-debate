"""Resilience tests for the pipeline's parallel agent execution."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from adversarial_debate.agents import BreakAgent, ChaosAgent, CryptoAgent, ExploitAgent
from adversarial_debate.agents.base import AgentOutput
from adversarial_debate.config import Config
from adversarial_debate.services.pipeline import PipelineConfig, PipelineService


@pytest.mark.anyio
async def test_one_agent_failure_does_not_discard_others(
    bead_store, mock_provider, monkeypatch
) -> None:
    """A single agent raising must not throw away the other agents' findings.

    Regression guard for asyncio.gather(return_exceptions=True): the failed
    agent is replaced by an empty sentinel carrying the error; the rest survive.
    """
    service = PipelineService(Config(), mock_provider, bead_store)
    exploit = ExploitAgent(mock_provider, bead_store)
    breaker = BreakAgent(mock_provider, bead_store)
    chaos = ChaosAgent(mock_provider, bead_store)
    crypto = CryptoAgent(mock_provider, bead_store)

    async def ok(_ctx: object) -> AgentOutput:
        return AgentOutput(
            agent_name="ok", result={"findings": [{"id": "F"}]}, beads_out=[], confidence=0.9
        )

    async def boom(_ctx: object) -> AgentOutput:
        raise RuntimeError("simulated rate limit")

    monkeypatch.setattr(exploit, "run", boom)
    monkeypatch.setattr(breaker, "run", ok)
    monkeypatch.setattr(chaos, "run", ok)
    monkeypatch.setattr(crypto, "run", ok)

    outputs = await service._run_agents_parallel(
        exploit,
        breaker,
        chaos,
        crypto,
        run_id="run-1",
        timestamp=datetime.now(UTC),
        code="print('x')",
        files=["app.py"],
        hints_by_agent={},
        pipeline_config=PipelineConfig(target="app.py", parallel=4, cache_enabled=False),
    )

    # Failed agent -> empty sentinel carrying the error.
    assert outputs["exploit"].errors
    assert outputs["exploit"].result == {}
    # The other three survived intact.
    for key in ("break", "chaos", "crypto"):
        assert outputs[key].result.get("findings") == [{"id": "F"}]
        assert not outputs[key].errors
