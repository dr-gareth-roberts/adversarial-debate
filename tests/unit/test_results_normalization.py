"""Unit tests for the individual results normalisation helpers.

These complement ``test_results_bundle.py`` (which covers the happy-path
``build_results_bundle``) by exercising each normaliser and the small parsing
utilities directly, including the crypto/chaos paths and edge cases.
"""

from __future__ import annotations

from adversarial_debate.results import (
    BundleInputs,
    _infer_single_file_target,
    _parse_cwe_id,
    _parse_location,
    build_results_bundle,
    normalize_break_findings,
    normalize_chaos_experiments,
    normalize_crypto_findings,
    normalize_exploit_findings,
    normalize_verdict_for_reporting,
)


class TestParseCweId:
    def test_none_returns_none(self) -> None:
        assert _parse_cwe_id(None) is None

    def test_int_passthrough(self) -> None:
        assert _parse_cwe_id(89) == 89

    def test_cwe_prefixed_string(self) -> None:
        assert _parse_cwe_id("CWE-79") == 79

    def test_lowercase_prefix(self) -> None:
        assert _parse_cwe_id("cwe-22") == 22

    def test_bare_digit_string(self) -> None:
        assert _parse_cwe_id("352") == 352

    def test_unparseable_returns_none(self) -> None:
        assert _parse_cwe_id("not-a-cwe") is None
        assert _parse_cwe_id(3.14) is None


class TestParseLocation:
    def test_file_and_line(self) -> None:
        assert _parse_location("src/app.py:42") == ("src/app.py", 42)

    def test_file_only(self) -> None:
        assert _parse_location("src/app.py") == ("src/app.py", None)

    def test_non_string(self) -> None:
        assert _parse_location(None) == (None, None)

    def test_trailing_colon_non_numeric(self) -> None:
        assert _parse_location("src/app.py:notaline") == ("src/app.py:notaline", None)


class TestNormalizeExploit:
    def test_maps_nested_fields(self) -> None:
        out = normalize_exploit_findings(
            [
                {
                    "id": "E1",
                    "title": "SQLi",
                    "severity": "HIGH",
                    "cwe_id": "CWE-89",
                    "owasp_category": "A03",
                    "confidence": 0.8,
                    "vulnerable_code": {"file": "a.py", "line_start": 5, "snippet": "x"},
                    "exploit": {
                        "impact": "data loss",
                        "description": "step1",
                        "payload": "p",
                        "curl_command": "curl",
                    },
                    "remediation": {"immediate": "fix it"},
                }
            ]
        )
        assert len(out) == 1
        f = out[0]
        assert f["agent"] == "ExploitAgent"
        assert f["finding_type"] == "exploit"
        assert f["cwe"] == 89
        assert f["category"] == "A03"
        assert f["file_path"] == "a.py"
        assert f["line"] == 5
        assert f["impact"] == "data loss"
        assert f["remediation"] == "fix it"
        assert f["reproduction_steps"] == ["step1", "p", "curl"]
        assert f["fingerprint"]

    def test_defaults_when_minimal(self) -> None:
        out = normalize_exploit_findings([{"id": "E2"}])
        assert out[0]["severity"] == "MEDIUM"
        assert out[0]["reproduction_steps"] == []


class TestNormalizeCrypto:
    def test_maps_evidence_and_attack(self) -> None:
        out = normalize_crypto_findings(
            [
                {
                    "id": "C1",
                    "title": "Weak hash",
                    "severity": "HIGH",
                    "cwe_id": "327",
                    "evidence": {"file": "c.py", "line_start": 3, "snippet": "md5"},
                    "attack": {
                        "impact": "collision",
                        "description": "do attack",
                        "prerequisites": ["network", "time"],
                    },
                    "remediation": {"code_fix": "use sha256"},
                }
            ]
        )
        f = out[0]
        assert f["agent"] == "CryptoAgent"
        assert f["category"] == "crypto"
        assert f["cwe"] == 327
        assert f["file_path"] == "c.py"
        assert f["remediation"] == "use sha256"
        assert f["reproduction_steps"] == ["do attack", "network", "time"]

    def test_non_dict_evidence_is_tolerated(self) -> None:
        out = normalize_crypto_findings([{"id": "C2", "evidence": "oops"}])
        assert out[0]["file_path"] is None


class TestNormalizeBreak:
    def test_uses_line_numbers_and_poc(self) -> None:
        out = normalize_break_findings(
            [
                {
                    "id": "B1",
                    "title": "Off by one",
                    "severity": "LOW",
                    "line_numbers": [7, 8],
                    "attack_vector": "boundary",
                    "proof_of_concept": {
                        "code": "poc()",
                        "description": "desc",
                        "expected_behavior": "ok",
                        "vulnerable_behavior": "crash",
                    },
                    "remediation": {"proper": "guard"},
                }
            ],
            target_file_path="fallback.py",
        )
        f = out[0]
        assert f["agent"] == "BreakAgent"
        assert f["line"] == 7
        assert f["code_snippet"] == "poc()"
        assert f["file_path"] == "fallback.py"
        assert f["remediation"] == "guard"
        assert f["reproduction_steps"] == ["boundary", "desc", "ok", "crash"]


class TestNormalizeChaos:
    def test_parses_code_location_and_hypothesis(self) -> None:
        out = normalize_chaos_experiments(
            [
                {
                    "id": "X1",
                    "title": "Timeout storm",
                    "severity_if_vulnerable": "HIGH",
                    "category": "resilience",
                    "evidence": {
                        "code_location": "svc.py:99",
                        "problematic_code": "sleep(1)",
                    },
                    "experiment": {
                        "description": "inject latency",
                        "method": "delay",
                        "rollback": "remove delay",
                    },
                    "hypothesis": {
                        "prediction_confidence": 0.6,
                        "predicted_actual_behavior": "cascading failure",
                    },
                    "remediation": {"immediate": "add timeout"},
                }
            ]
        )
        f = out[0]
        assert f["agent"] == "ChaosAgent"
        assert f["finding_type"] == "chaos_experiment"
        assert f["severity"] == "HIGH"
        assert f["file_path"] == "svc.py"
        assert f["line"] == 99
        assert f["confidence"] == 0.6
        assert f["impact"] == "cascading failure"
        assert f["reproduction_steps"] == ["delay", "remove delay"]


class TestVerdictNormalisation:
    def test_report_promoted_into_summary(self) -> None:
        out = normalize_verdict_for_reporting({"report": "all good", "decision": "PASS"})
        assert out["summary"]["report"] == "all good"

    def test_existing_summary_report_preserved(self) -> None:
        out = normalize_verdict_for_reporting({"report": "outer", "summary": {"report": "inner"}})
        assert out["summary"]["report"] == "inner"


class TestBuildBundleIntegration:
    def _inputs(self, files: list[str]) -> BundleInputs:
        return BundleInputs(
            run_id="r",
            target=".",
            provider="mock",
            started_at_iso="2026-01-01T00:00:00+00:00",
            finished_at_iso="2026-01-01T00:00:05+00:00",
            files_analyzed=files,
        )

    def test_combines_all_agent_outputs(self) -> None:
        bundle = build_results_bundle(
            inputs=self._inputs(["a.py"]),
            exploit_result={"findings": [{"id": "E", "severity": "CRITICAL"}]},
            break_result={"findings": [{"id": "B", "severity": "LOW"}]},
            chaos_result={"experiments": [{"id": "X", "severity_if_vulnerable": "MEDIUM"}]},
            crypto_result={"findings": [{"id": "C", "severity": "HIGH"}]},
            arbiter_result={"decision": "BLOCK", "report": "blocked"},
        )
        assert bundle["metadata"]["finding_counts"]["total"] == 4
        by_sev = bundle["metadata"]["finding_counts"]["by_severity"]
        assert by_sev == {"CRITICAL": 1, "LOW": 1, "MEDIUM": 1, "HIGH": 1}
        assert bundle["verdict"]["summary"]["report"] == "blocked"

    def test_no_results_yields_empty_bundle(self) -> None:
        bundle = build_results_bundle(inputs=self._inputs([]))
        assert bundle["findings"] == []
        assert bundle["verdict"] == {}
        assert bundle["metadata"]["finding_counts"]["total"] == 0


class TestInferSingleFileTarget:
    def test_single_file(self) -> None:
        assert _infer_single_file_target(["only.py"]) == "only.py"

    def test_multiple_files(self) -> None:
        assert _infer_single_file_target(["a.py", "b.py"]) is None

    def test_empty(self) -> None:
        assert _infer_single_file_target([]) is None
