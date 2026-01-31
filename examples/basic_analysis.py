#!/usr/bin/env python3
"""Basic example: Analyze code with all agents.

This example demonstrates how to:
1. Set up the framework
2. Run all three agents (Exploit, Break, Chaos)
3. Consolidate findings with the Arbiter
4. Display results
"""

import asyncio
from datetime import UTC, datetime

from adversarial_debate import (
    AgentContext,
    AnthropicProvider,
    Arbiter,
    BeadStore,
    BreakAgent,
    ChaosAgent,
    ExploitAgent,
)

# Sample vulnerable code to analyze
VULNERABLE_CODE = '''
import sqlite3
import os
import pickle


def get_user(user_id: str) -> dict:
    """Get user by ID - VULNERABLE TO SQL INJECTION."""
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    # BAD: String interpolation in SQL query
    query = f"SELECT * FROM users WHERE id = '{user_id}'"
    cursor.execute(query)
    return cursor.fetchone()


def run_command(cmd: str) -> str:
    """Run a shell command - VULNERABLE TO COMMAND INJECTION."""
    # BAD: User input passed directly to shell
    return os.popen(cmd).read()


def load_data(data: bytes) -> object:
    """Load pickled data - VULNERABLE TO INSECURE DESERIALIZATION."""
    # BAD: Unpickling untrusted data
    return pickle.loads(data)


def authenticate(username: str, password: str) -> bool:
    """Authenticate user - VULNERABLE TO TIMING ATTACK."""
    stored_password = get_stored_password(username)
    # BAD: Character-by-character comparison leaks timing info
    if len(password) != len(stored_password):
        return False
    for i in range(len(password)):
        if password[i] != stored_password[i]:
            return False
    return True


def get_stored_password(username: str) -> str:
    """Placeholder for getting stored password."""
    return "secret123"  # BAD: Hardcoded password
'''


async def main() -> None:
    """Run analysis on vulnerable code."""
    print("=" * 60)
    print("Adversarial Debate - Basic Analysis Example")
    print("=" * 60)
    print()

    # Initialize components
    print("[1/5] Initializing framework...")
    provider = AnthropicProvider()
    store = BeadStore(":memory:")  # In-memory store for example

    # Create agents
    exploit_agent = ExploitAgent(provider, store)
    break_agent = BreakAgent(provider, store)
    chaos_agent = ChaosAgent(provider, store)
    arbiter = Arbiter(provider, store)

    # Build analysis context
    timestamp = datetime.now(UTC).isoformat()
    context = AgentContext(
        run_id="example-001",
        timestamp_iso=timestamp,
        policy={},
        thread_id="thread-001",
        task_id="task-001",
        inputs={
            "code": VULNERABLE_CODE,
            "file_path": "vulnerable_app.py",
            "language": "python",
            "exposure": "public",
        },
    )

    # Run ExploitAgent
    print("[2/5] Running ExploitAgent (OWASP Top 10)...")
    exploit_result = await exploit_agent.run(context)
    print(f"      Found {len(exploit_result.result.get('findings', []))} potential vulnerabilities")

    # Run BreakAgent
    print("[3/5] Running BreakAgent (Logic bugs)...")
    break_result = await break_agent.run(context)
    print(f"      Found {len(break_result.result.get('findings', []))} potential logic bugs")

    # Run ChaosAgent
    print("[4/5] Running ChaosAgent (Resilience)...")
    chaos_result = await chaos_agent.run(context)
    print(f"      Found {len(chaos_result.result.get('findings', []))} resilience issues")

    # Consolidate with Arbiter
    print("[5/5] Running Arbiter (Consolidation)...")
    arbiter_context = AgentContext(
        run_id="example-001",
        timestamp_iso=timestamp,
        policy={},
        thread_id="thread-001",
        task_id="arbiter-001",
        inputs={
            "findings": {
                "exploit": exploit_result.result,
                "break": break_result.result,
                "chaos": chaos_result.result,
            }
        },
    )
    final_result = await arbiter.run(arbiter_context)

    # Display results
    print()
    print("=" * 60)
    print("CONSOLIDATED FINDINGS")
    print("=" * 60)
    print()

    findings = final_result.result.get("findings", [])
    if not findings:
        print("No findings to report.")
        return

    # Sort by severity
    severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}
    findings.sort(key=lambda f: severity_order.get(f.get("severity", "info"), 4))

    for i, finding in enumerate(findings, 1):
        severity = finding.get("severity", "unknown").upper()
        title = finding.get("title", "Untitled")
        confidence = finding.get("confidence", 0)
        cwe = finding.get("cwe", "N/A")
        description = finding.get("description", "No description")
        remediation = finding.get("remediation", "No remediation provided")

        print(f"[{i}] [{severity}] {title}")
        print(f"    Confidence: {confidence}%")
        print(f"    CWE: {cwe}")
        print(f"    Description: {description[:100]}...")
        print(f"    Remediation: {remediation[:100]}...")
        print()

    print("=" * 60)
    print(f"Total findings: {len(findings)}")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
