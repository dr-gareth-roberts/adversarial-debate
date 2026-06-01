#!/usr/bin/env python3
"""Quickstart: the smallest possible end-to-end analysis.

Run it with zero setup — it uses the deterministic *mock* provider by default,
so no API key is required:

    python examples/quickstart.py

To run a real analysis, point it at a provider and supply a key:

    LLM_PROVIDER=anthropic ANTHROPIC_API_KEY=sk-... python examples/quickstart.py

This is intentionally tiny: one agent, one snippet, results printed. For richer
flows see ``basic_analysis.py`` (all agents + arbiter) and ``single_agent.py``.
"""

from __future__ import annotations

import asyncio
import os
import tempfile
from datetime import UTC, datetime
from pathlib import Path

from adversarial_debate import AgentContext, BeadStore, ExploitAgent, get_provider

# A tiny snippet with an obvious SQL-injection bug for the agent to find.
CODE = '''
def get_user(user_id: str):
    """Look up a user by id."""
    query = f"SELECT * FROM users WHERE id = '{user_id}'"
    return db.execute(query)
'''


async def main() -> None:
    provider_name = os.getenv("LLM_PROVIDER", "mock")
    if provider_name == "mock":
        print("Running with the deterministic MOCK provider — no real analysis.")
        print("Set LLM_PROVIDER=anthropic and ANTHROPIC_API_KEY for a real run.\n")

    provider = get_provider(provider_name)
    store = BeadStore(Path(tempfile.mkdtemp()) / "ledger.jsonl")
    agent = ExploitAgent(provider, store)

    context = AgentContext(
        run_id="quickstart",
        timestamp_iso=datetime.now(UTC).isoformat(),
        policy={},
        thread_id="quickstart",
        task_id="analysis",
        inputs={"code": CODE, "file_path": "app.py", "language": "python"},
    )

    output = await agent.run(context)
    findings = output.result.get("findings", [])

    print(f"{agent.name} found {len(findings)} finding(s):")
    for finding in findings:
        severity = str(finding.get("severity", "UNKNOWN")).upper()
        print(f"  [{severity}] {finding.get('title', 'Untitled')}")


if __name__ == "__main__":
    asyncio.run(main())
