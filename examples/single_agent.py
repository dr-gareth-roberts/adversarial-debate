#!/usr/bin/env python3
"""Single agent example: Run targeted analysis with one agent.

This example shows how to use a single agent for targeted analysis,
which is useful when you want to focus on specific vulnerability types.
"""

import argparse
import asyncio
from datetime import UTC, datetime
from pathlib import Path

from adversarial_debate import (
    AgentContext,
    AnthropicProvider,
    BeadStore,
    BreakAgent,
    ChaosAgent,
    ExploitAgent,
)


async def analyze_file(
    file_path: Path,
    agent_type: str = "exploit",
) -> dict:
    """Analyze a single file with a specific agent.

    Args:
        file_path: Path to the file to analyze.
        agent_type: Which agent to use ('exploit', 'break', or 'chaos').

    Returns:
        Analysis results dictionary.
    """
    # Read the file
    code = file_path.read_text()

    # Initialize components
    provider = AnthropicProvider()
    store = BeadStore(":memory:")

    # Select agent
    agents = {
        "exploit": ExploitAgent(provider, store),
        "break": BreakAgent(provider, store),
        "chaos": ChaosAgent(provider, store),
    }

    if agent_type not in agents:
        raise ValueError(f"Unknown agent type: {agent_type}. Choose from: {list(agents.keys())}")

    agent = agents[agent_type]

    # Build context
    context = AgentContext(
        run_id=f"single-{agent_type}-001",
        timestamp_iso=datetime.now(UTC).isoformat(),
        policy={},
        thread_id="thread-001",
        task_id="task-001",
        inputs={
            "code": code,
            "file_path": str(file_path),
            "language": file_path.suffix.lstrip(".") or "python",
            "exposure": "public",
        },
    )

    # Run analysis
    result = await agent.run(context)
    return result.result


def print_findings(findings: list, agent_type: str) -> None:
    """Pretty print findings."""
    agent_descriptions = {
        "exploit": "Security Vulnerabilities (OWASP Top 10)",
        "break": "Logic Bugs and Edge Cases",
        "chaos": "Resilience and Failure Mode Issues",
    }

    print()
    print("=" * 60)
    print(f"Agent: {agent_descriptions.get(agent_type, agent_type)}")
    print("=" * 60)
    print()

    if not findings:
        print("No findings.")
        return

    for i, finding in enumerate(findings, 1):
        severity = finding.get("severity", "unknown").upper()
        title = finding.get("title", "Untitled")
        confidence = finding.get("confidence", 0)
        location = finding.get("location", {})
        line = location.get("line", "?")

        print(f"[{i}] [{severity}] {title}")
        print(f"    Line: {line}")
        print(f"    Confidence: {confidence}%")

        if "cwe" in finding:
            print(f"    CWE: {finding['cwe']}")

        description = finding.get("description", "")
        if description:
            # Truncate long descriptions
            if len(description) > 150:
                description = description[:147] + "..."
            print(f"    {description}")

        print()


async def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Run single-agent analysis on a file",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python single_agent.py --file app.py --agent exploit
  python single_agent.py --file auth.py --agent break
  python single_agent.py --file api.py --agent chaos
        """,
    )
    parser.add_argument(
        "--file",
        "-f",
        type=Path,
        required=True,
        help="Path to the file to analyze",
    )
    parser.add_argument(
        "--agent",
        "-a",
        choices=["exploit", "break", "chaos"],
        default="exploit",
        help="Agent to use (default: exploit)",
    )

    args = parser.parse_args()

    if not args.file.exists():
        print(f"Error: File not found: {args.file}")
        return

    print(f"Analyzing {args.file} with {args.agent} agent...")

    result = await analyze_file(args.file, args.agent)
    findings = result.get("findings", [])

    print_findings(findings, args.agent)
    print(f"Total: {len(findings)} findings")


if __name__ == "__main__":
    asyncio.run(main())
