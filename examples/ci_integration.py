#!/usr/bin/env python3
"""CI/CD Integration example: Integrate security analysis into your pipeline.

This example shows how to:
1. Analyze changed files in a PR
2. Filter findings by severity
3. Generate reports in various formats
4. Exit with appropriate status codes for CI
"""

import asyncio
import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

from adversarial_debate import (
    AgentContext,
    AnthropicProvider,
    Arbiter,
    BeadStore,
    BreakAgent,
    ChaosAgent,
    CryptoAgent,
    ExploitAgent,
)


def get_changed_files(base_branch: str = "main") -> list[Path]:
    """Get list of changed Python files compared to base branch.

    Args:
        base_branch: The branch to compare against.

    Returns:
        List of paths to changed Python files.
    """
    try:
        result = subprocess.run(
            ["git", "diff", "--name-only", base_branch, "--", "*.py"],
            capture_output=True,
            text=True,
            check=True,
        )
        files = [Path(f) for f in result.stdout.strip().split("\n") if f]
        return [f for f in files if f.exists()]
    except subprocess.CalledProcessError:
        return []


async def analyze_files(
    files: list[Path],
    fail_on: str = "high",
) -> tuple[list[dict], bool]:
    """Analyze files and determine if CI should fail.

    Args:
        files: List of files to analyze.
        fail_on: Minimum severity to fail on ('critical', 'high', 'medium', 'low').

    Returns:
        Tuple of (findings list, should_fail boolean).
    """
    if not files:
        return [], False

    # Initialize components
    provider = AnthropicProvider()
    store = BeadStore(":memory:")

    # Create agents
    exploit_agent = ExploitAgent(provider, store)
    break_agent = BreakAgent(provider, store)
    chaos_agent = ChaosAgent(provider, store)
    crypto_agent = CryptoAgent(provider, store)
    arbiter = Arbiter(provider, store)

    all_findings = []

    for file_path in files:
        print(f"Analyzing: {file_path}")

        code = file_path.read_text()
        timestamp = datetime.now(UTC).isoformat()

        context = AgentContext(
            run_id=f"ci-{file_path.name}",
            timestamp_iso=timestamp,
            policy={},
            thread_id="ci-thread",
            task_id=f"analyze-{file_path.name}",
            inputs={
                "code": code,
                "file_path": str(file_path),
                "language": "python",
                "exposure": "public",
            },
        )

        # Run all agents in parallel
        results = await asyncio.gather(
            exploit_agent.run(context),
            break_agent.run(context),
            chaos_agent.run(context),
            crypto_agent.run(context),
        )

        # Consolidate findings
        arbiter_context = AgentContext(
            run_id=f"ci-{file_path.name}",
            timestamp_iso=timestamp,
            policy={},
            thread_id="ci-thread",
            task_id=f"arbiter-{file_path.name}",
            inputs={
                "findings": {
                    "exploit": results[0].result,
                    "break": results[1].result,
                    "chaos": results[2].result,
                    "crypto": results[3].result,
                }
            },
        )

        final_result = await arbiter.run(arbiter_context)
        findings = final_result.result.get("findings", [])

        # Add file path to each finding
        for finding in findings:
            finding["file"] = str(file_path)

        all_findings.extend(findings)

    # Determine if we should fail
    severity_levels = ["critical", "high", "medium", "low", "info"]
    fail_threshold = severity_levels.index(fail_on) if fail_on in severity_levels else 1

    should_fail = any(
        severity_levels.index(f.get("severity", "info")) <= fail_threshold for f in all_findings
    )

    return all_findings, should_fail


def generate_markdown_report(findings: list[dict]) -> str:
    """Generate a markdown report for PR comments."""
    if not findings:
        return "## Security Analysis\n\nNo security issues found."

    lines = [
        "## Security Analysis Results",
        "",
        f"Found **{len(findings)}** potential issues:",
        "",
    ]

    # Group by severity
    by_severity = {}
    for finding in findings:
        severity = finding.get("severity", "unknown")
        if severity not in by_severity:
            by_severity[severity] = []
        by_severity[severity].append(finding)

    severity_order = ["critical", "high", "medium", "low", "info"]
    severity_icons = {
        "critical": "🔴",
        "high": "🟠",
        "medium": "🟡",
        "low": "🔵",
        "info": "⚪",
    }

    for severity in severity_order:
        if severity in by_severity:
            icon = severity_icons.get(severity, "⚪")
            lines.append(f"### {icon} {severity.upper()} ({len(by_severity[severity])})")
            lines.append("")

            for finding in by_severity[severity]:
                title = finding.get("title", "Untitled")
                file = finding.get("file", "unknown")
                line = finding.get("location", {}).get("line", "?")
                confidence = finding.get("confidence", 0)

                lines.append(f"- **{title}**")
                lines.append(f"  - File: `{file}:{line}`")
                lines.append(f"  - Confidence: {confidence}%")

                if "cwe" in finding:
                    lines.append(f"  - CWE: {finding['cwe']}")

                lines.append("")

    return "\n".join(lines)


def generate_sarif_report(findings: list[dict]) -> dict:
    """Generate SARIF format report for GitHub Security tab."""
    rules = []
    results = []

    for i, finding in enumerate(findings):
        rule_id = f"adversarial-debate-{i}"
        severity = finding.get("severity", "warning")

        # Map severity to SARIF level
        level_map = {
            "critical": "error",
            "high": "error",
            "medium": "warning",
            "low": "note",
            "info": "note",
        }

        rules.append(
            {
                "id": rule_id,
                "name": finding.get("title", "Security Issue"),
                "shortDescription": {"text": finding.get("title", "")},
                "fullDescription": {"text": finding.get("description", "")},
                "help": {"text": finding.get("remediation", "")},
                "properties": {
                    "severity": severity,
                    "confidence": finding.get("confidence", 0),
                },
            }
        )

        location = finding.get("location", {})
        results.append(
            {
                "ruleId": rule_id,
                "level": level_map.get(severity, "warning"),
                "message": {"text": finding.get("description", "Security issue found")},
                "locations": [
                    {
                        "physicalLocation": {
                            "artifactLocation": {
                                "uri": finding.get("file", "unknown"),
                            },
                            "region": {
                                "startLine": location.get("line", 1),
                            },
                        },
                    }
                ],
            }
        )

    return {
        "$schema": "https://raw.githubusercontent.com/oasis-tcs/sarif-spec/master/Schemata/sarif-schema-2.1.0.json",
        "version": "2.1.0",
        "runs": [
            {
                "tool": {
                    "driver": {
                        "name": "Adversarial Debate",
                        "version": "0.1.0",
                        "informationUri": "https://github.com/dr-gareth-roberts/adverserial-debate",
                        "rules": rules,
                    },
                },
                "results": results,
            },
        ],
    }


async def main() -> int:
    """Run CI analysis and return exit code."""
    import argparse

    parser = argparse.ArgumentParser(description="Security analysis for CI/CD")
    parser.add_argument(
        "--base-branch",
        default="main",
        help="Base branch to compare against",
    )
    parser.add_argument(
        "--fail-on",
        choices=["critical", "high", "medium", "low"],
        default="high",
        help="Minimum severity to fail CI on",
    )
    parser.add_argument(
        "--format",
        choices=["text", "markdown", "json", "sarif"],
        default="text",
        help="Output format",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Output file (default: stdout)",
    )
    parser.add_argument(
        "--files",
        nargs="*",
        type=Path,
        help="Specific files to analyze (overrides git diff)",
    )

    args = parser.parse_args()

    # Get files to analyze
    if args.files:
        files = [f for f in args.files if f.exists()]
    else:
        files = get_changed_files(args.base_branch)

    if not files:
        print("No Python files to analyze.")
        return 0

    print(f"Analyzing {len(files)} file(s)...")

    # Run analysis
    findings, should_fail = await analyze_files(files, args.fail_on)

    # Generate output
    if args.format == "markdown":
        output = generate_markdown_report(findings)
    elif args.format == "json":
        output = json.dumps(findings, indent=2)
    elif args.format == "sarif":
        output = json.dumps(generate_sarif_report(findings), indent=2)
    else:
        # Text format
        output = f"Found {len(findings)} issues\n"
        for f in findings:
            output += (
                f"[{f.get('severity', 'unknown').upper()}] {f.get('title', 'Untitled')} "
                f"in {f.get('file', 'unknown')}\n"
            )

    # Write output
    if args.output:
        args.output.write_text(output)
        print(f"Report written to: {args.output}")
    else:
        print(output)

    # Return exit code
    if should_fail:
        print(f"\nCI FAILED: Found issues with severity >= {args.fail_on}")
        return 1

    print("\nCI PASSED: No blocking issues found")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
