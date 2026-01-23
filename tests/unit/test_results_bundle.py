"""Unit tests for results bundle normalization."""

from __future__ import annotations

from adversarial_debate.results import BundleInputs, build_results_bundle


def test_build_results_bundle_normalizes_findings() -> None:
    inputs = BundleInputs(
        run_id="run-1",
        target=".",
        provider="mock",
        started_at_iso="2026-01-22T00:00:00+00:00",
        finished_at_iso="2026-01-22T00:00:01+00:00",
        files_analyzed=["a.py"],
        time_budget_seconds=60,
    )

    exploit_result = {
        "findings": [
            {
                "id": "EXPLOIT-001",
                "title": "SQL injection",
                "severity": "CRITICAL",
                "cwe_id": "CWE-89",
                "confidence": 0.9,
                "description": "User input concatenated into SQL",
                "vulnerable_code": {
                    "file": "a.py",
                    "line_start": 10,
                    "snippet": "cursor.execute('...'+user_id)",
                },
                "exploit": {"payload": "1' OR '1'='1", "impact": "Read all rows"},
                "remediation": {"immediate": "Use parameters"},
            }
        ]
    }

    bundle = build_results_bundle(inputs=inputs, exploit_result=exploit_result)
    assert bundle["metadata"]["finding_counts"]["total"] == 1
    finding = bundle["findings"][0]
    assert finding["agent"] == "ExploitAgent"
    assert finding["cwe"] == 89
    assert finding["file_path"] == "a.py"
    assert finding["line"] == 10

