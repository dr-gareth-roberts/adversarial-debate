"""Utilities for producing a canonical results bundle.

The CLI and GitHub Action should rely on a stable JSON "bundle" schema:
  - metadata: run context (target, run_id, timestamps, etc.)
  - findings: normalized findings across agents
  - verdict: arbiter output (if generated)

Formatters (SARIF/Markdown/HTML/JSON) consume this bundle directly.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from .baseline import compute_fingerprint


def _parse_cwe_id(value: Any) -> int | None:
    if value is None:
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        match = re.search(r"\bCWE-(\d+)\b", value, re.IGNORECASE)
        if match:
            return int(match.group(1))
        if value.isdigit():
            return int(value)
    return None


def _parse_location(value: Any) -> tuple[str | None, int | None]:
    """Parse 'file.py:123' or return (None, None) if unknown."""
    if not isinstance(value, str):
        return (None, None)
    if ":" not in value:
        return (value, None)
    file_path, _, line_s = value.rpartition(":")
    try:
        return (file_path or None, int(line_s))
    except ValueError:
        return (value, None)


def normalize_exploit_findings(findings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for f in findings:
        vulnerable = f.get("vulnerable_code") or {}
        file_path = vulnerable.get("file") or f.get("file_path")
        line = vulnerable.get("line_start")
        snippet = vulnerable.get("snippet")

        remediation = f.get("remediation") or {}
        exploit = f.get("exploit") or {}

        finding = (
            {
                "id": f.get("id"),
                "finding_type": "exploit",
                "agent": "ExploitAgent",
                "title": f.get("title"),
                "severity": f.get("severity", "MEDIUM"),
                "description": f.get("description"),
                "category": f.get("owasp_category"),
                "cwe": _parse_cwe_id(f.get("cwe_id")),
                "confidence": f.get("confidence"),
                "file_path": file_path,
                "line": line,
                "code_snippet": snippet,
                "impact": exploit.get("impact"),
                "remediation": remediation.get("immediate") or remediation.get("code_fix"),
                "reproduction_steps": [
                    step
                    for step in [
                        exploit.get("description"),
                        exploit.get("payload"),
                        exploit.get("curl_command"),
                    ]
                    if step
                ],
                "raw": f,
            }
        )
        finding["fingerprint"] = compute_fingerprint(finding)
        normalized.append(finding)
    return normalized


def normalize_break_findings(
    findings: list[dict[str, Any]],
    *,
    target_file_path: str | None = None,
) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for f in findings:
        line_numbers = f.get("line_numbers") or []
        line = line_numbers[0] if isinstance(line_numbers, list) and line_numbers else None

        remediation = f.get("remediation") or {}
        poc = f.get("proof_of_concept") or {}
        code_snippet = f.get("code_snippet") or poc.get("code")

        finding = (
            {
                "id": f.get("id"),
                "finding_type": "break",
                "agent": "BreakAgent",
                "title": f.get("title"),
                "severity": f.get("severity", "MEDIUM"),
                "description": f.get("description"),
                "category": f.get("category"),
                "confidence": f.get("confidence"),
                "file_path": f.get("file_path") or target_file_path,
                "line": f.get("line") or line,
                "code_snippet": code_snippet,
                "impact": f.get("impact"),
                "remediation": remediation.get("immediate") or remediation.get("proper"),
                "reproduction_steps": [
                    step
                    for step in [
                        f.get("attack_vector"),
                        poc.get("description"),
                        poc.get("expected_behavior"),
                        poc.get("vulnerable_behavior"),
                    ]
                    if step
                ],
                "raw": f,
            }
        )
        finding["fingerprint"] = compute_fingerprint(finding)
        normalized.append(finding)
    return normalized


def normalize_chaos_experiments(experiments: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for e in experiments:
        evidence = e.get("evidence") or {}
        file_path, line = _parse_location(evidence.get("code_location"))

        remediation = e.get("remediation") or {}
        experiment = e.get("experiment") or {}
        hypothesis = e.get("hypothesis") or {}

        finding = (
            {
                "id": e.get("id"),
                "finding_type": "chaos_experiment",
                "agent": "ChaosAgent",
                "title": e.get("title"),
                "severity": e.get("severity_if_vulnerable", "MEDIUM"),
                "description": experiment.get("description") or e.get("failure_mode"),
                "category": e.get("category"),
                "confidence": hypothesis.get("prediction_confidence"),
                "file_path": file_path,
                "line": line,
                "code_snippet": evidence.get("problematic_code"),
                "impact": hypothesis.get("predicted_actual_behavior"),
                "remediation": remediation.get("immediate") or remediation.get("proper"),
                "reproduction_steps": [
                    step
                    for step in [
                        experiment.get("method"),
                        experiment.get("rollback"),
                    ]
                    if step
                ],
                "raw": e,
            }
        )
        finding["fingerprint"] = compute_fingerprint(finding)
        normalized.append(finding)
    return normalized


def normalize_verdict_for_reporting(verdict_result: dict[str, Any]) -> dict[str, Any]:
    """Make arbiter output consistent for formatters and CI parsing."""
    verdict: dict[str, Any] = dict(verdict_result)

    summary = dict(verdict.get("summary") or {})
    report = verdict.get("report")
    if report and "report" not in summary:
        summary["report"] = report
    verdict["summary"] = summary
    return verdict


@dataclass(frozen=True)
class BundleInputs:
    run_id: str
    target: str
    provider: str
    started_at_iso: str
    finished_at_iso: str
    files_analyzed: list[str]
    time_budget_seconds: int | None = None
    config_path: str | None = None


def build_results_bundle(
    *,
    inputs: BundleInputs,
    exploit_result: dict[str, Any] | None = None,
    break_result: dict[str, Any] | None = None,
    chaos_result: dict[str, Any] | None = None,
    arbiter_result: dict[str, Any] | None = None,
) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []

    if exploit_result:
        findings.extend(normalize_exploit_findings(exploit_result.get("findings", [])))
    if break_result:
        findings.extend(
            normalize_break_findings(
                break_result.get("findings", []),
                target_file_path=_infer_single_file_target(inputs.files_analyzed),
            )
        )
    if chaos_result:
        findings.extend(normalize_chaos_experiments(chaos_result.get("experiments", [])))

    verdict = normalize_verdict_for_reporting(arbiter_result) if arbiter_result else {}

    severity_counts: dict[str, int] = {}
    for f in findings:
        sev = str(f.get("severity", "UNKNOWN")).upper()
        severity_counts[sev] = severity_counts.get(sev, 0) + 1

    metadata = {
        "run_id": inputs.run_id,
        "target": inputs.target,
        "provider": inputs.provider,
        "started_at": inputs.started_at_iso,
        "finished_at": inputs.finished_at_iso,
        "files_analyzed": inputs.files_analyzed,
        "time_budget_seconds": inputs.time_budget_seconds,
        "config_path": inputs.config_path,
        "finding_counts": {
            "total": len(findings),
            "by_severity": severity_counts,
        },
        "generated_at": datetime.now(UTC).isoformat(),
    }

    return {
        "metadata": metadata,
        "findings": findings,
        "verdict": verdict,
    }


def _infer_single_file_target(files: list[str]) -> str | None:
    if len(files) == 1:
        return files[0]
    return None
