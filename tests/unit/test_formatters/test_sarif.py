"""Tests for the SARIF 2.1.0 formatter.

These assert structural validity against the parts of the SARIF 2.1.0 spec
that downstream consumers (GitHub Code Scanning in particular) rely on,
without pulling in a network-fetched JSON schema.
"""

from __future__ import annotations

import json
from typing import Any

from adversarial_debate.formatters.sarif import SARIFFormatter


def _parse(data: dict[str, Any]) -> dict[str, Any]:
    return json.loads(SARIFFormatter().format(data))


def test_top_level_structure(sample_bundle: dict[str, Any]) -> None:
    sarif = _parse(sample_bundle)
    assert sarif["version"] == "2.1.0"
    assert sarif["$schema"].endswith("sarif-schema-2.1.0.json")
    assert isinstance(sarif["runs"], list)
    assert len(sarif["runs"]) == 1


def test_driver_metadata_uses_config(sample_bundle: dict[str, Any]) -> None:
    driver = _parse(sample_bundle)["runs"][0]["tool"]["driver"]
    assert driver["name"] == "adversarial-debate"
    assert driver["version"] == "0.1.0"
    assert driver["informationUri"].startswith("https://")


def test_one_result_per_finding(sample_bundle: dict[str, Any]) -> None:
    results = _parse(sample_bundle)["runs"][0]["results"]
    assert len(results) == len(sample_bundle["findings"])


def test_result_rule_index_points_at_correct_rule(sample_bundle: dict[str, Any]) -> None:
    run = _parse(sample_bundle)["runs"][0]
    rules = run["tool"]["driver"]["rules"]
    for result in run["results"]:
        idx = result["ruleIndex"]
        assert 0 <= idx < len(rules)
        assert rules[idx]["id"] == result["ruleId"]


def test_cwe_finding_gets_cwe_rule_id_and_help_uri(sample_bundle: dict[str, Any]) -> None:
    run = _parse(sample_bundle)["runs"][0]
    cwe_rules = [r for r in run["tool"]["driver"]["rules"] if r["id"] == "CWE-89"]
    assert len(cwe_rules) == 1
    assert cwe_rules[0]["helpUri"] == "https://cwe.mitre.org/data/definitions/89.html"


def test_severity_maps_to_sarif_level(sample_bundle: dict[str, Any]) -> None:
    results = _parse(sample_bundle)["runs"][0]["results"]
    by_rule = {r["ruleId"]: r for r in results}
    # CRITICAL -> error
    assert by_rule["CWE-89"]["level"] == "error"
    # MEDIUM (the break finding, no CWE) -> warning
    medium = next(r for r in results if r["ruleId"] != "CWE-89")
    assert medium["level"] == "warning"


def test_security_severity_score_present(sample_bundle: dict[str, Any]) -> None:
    rules = _parse(sample_bundle)["runs"][0]["tool"]["driver"]["rules"]
    cwe_rule = next(r for r in rules if r["id"] == "CWE-89")
    assert cwe_rule["properties"]["security-severity"] == "9.0"


def test_location_region_is_one_based(sample_bundle: dict[str, Any]) -> None:
    results = _parse(sample_bundle)["runs"][0]["results"]
    region = results[0]["locations"][0]["physicalLocation"]["region"]
    assert region["startLine"] >= 1


def test_zero_line_is_clamped_to_one() -> None:
    data = {"findings": [{"title": "x", "severity": "LOW", "file_path": "a.py", "line": 0}]}
    region = _parse(data)["runs"][0]["results"][0]["locations"][0]["physicalLocation"]["region"]
    assert region["startLine"] == 1


def test_code_flows_built_from_reproduction_steps(sample_bundle: dict[str, Any]) -> None:
    results = _parse(sample_bundle)["runs"][0]["results"]
    exploit = next(r for r in results if r["ruleId"] == "CWE-89")
    flows = exploit["codeFlows"]
    locations = flows[0]["threadFlows"][0]["locations"]
    assert [loc["location"]["message"]["text"] for loc in locations] == [
        "Send id=1 OR 1=1",
        "Observe every row returned",
    ]
    assert [loc["executionOrder"] for loc in locations] == [1, 2]


def test_fingerprint_is_emitted(sample_bundle: dict[str, Any]) -> None:
    results = _parse(sample_bundle)["runs"][0]["results"]
    exploit = next(r for r in results if r["ruleId"] == "CWE-89")
    assert exploit["fingerprints"]["primary"] == "fp-exploit-001"


def test_empty_findings_produce_valid_empty_run() -> None:
    sarif = _parse({"findings": []})
    run = sarif["runs"][0]
    assert run["results"] == []
    assert run["tool"]["driver"]["rules"] == []


def test_invocation_marked_successful(sample_bundle: dict[str, Any]) -> None:
    invocation = _parse(sample_bundle)["runs"][0]["invocations"][0]
    assert invocation["executionSuccessful"] is True
    assert "endTimeUtc" in invocation


def test_duplicate_cwe_findings_share_a_single_rule() -> None:
    data = {
        "findings": [
            {"title": "A", "severity": "HIGH", "cwe": 89, "file_path": "a.py", "line": 1},
            {"title": "B", "severity": "HIGH", "cwe": 89, "file_path": "b.py", "line": 2},
        ]
    }
    rules = _parse(data)["runs"][0]["tool"]["driver"]["rules"]
    assert [r["id"] for r in rules] == ["CWE-89"]
