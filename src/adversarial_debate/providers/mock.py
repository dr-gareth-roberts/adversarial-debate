"""Deterministic mock provider for demos and tests."""

from __future__ import annotations

import json
import re
from typing import Any

from .base import LLMProvider, LLMResponse, Message, ModelTier, ProviderConfig


class MockProvider(LLMProvider):
    """Deterministic provider that returns canned JSON outputs."""

    def __init__(self, config: ProviderConfig | None = None):
        config = config or ProviderConfig(
            model="mock-1",
            temperature=0.0,
            max_tokens=2048,
            timeout=1.0,
        )
        super().__init__(config)

    @property
    def name(self) -> str:
        return "mock"

    def _default_model(self) -> str:
        return "mock-1"

    def get_model_for_tier(self, tier: ModelTier) -> str:
        return f"mock-{tier.value}"

    async def complete(
        self,
        messages: list[Message],
        *,
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        json_mode: bool = False,
    ) -> LLMResponse:
        del model, temperature, max_tokens, json_mode

        agent = self._detect_agent(messages)
        file_path = self._extract_file_path(messages)

        if agent == "exploit":
            payload = self._exploit_payload(file_path)
        elif agent == "break":
            payload = self._break_payload(file_path)
        elif agent == "crypto":
            payload = self._crypto_payload(file_path)
        elif agent == "chaos":
            payload = self._chaos_payload(file_path)
        elif agent == "orchestrator":
            payload = self._orchestrator_payload(file_path)
        elif agent == "arbiter":
            payload = self._arbiter_payload()
        else:
            payload = {"message": "mock provider could not infer agent"}

        content = json.dumps(payload, indent=2)
        return LLMResponse(
            content=content,
            model=self._default_model(),
            usage={"input_tokens": 0, "output_tokens": 0},
            finish_reason="stop",
            raw_response={"mock": True, "agent": agent},
        )

    def _detect_agent(self, messages: list[Message]) -> str:
        system = "".join(m.content for m in messages if m.role == "system")
        if "senior penetration tester" in system:
            return "exploit"
        if "senior QA engineer" in system:
            return "break"
        if "senior cryptography engineer" in system:
            return "crypto"
        if "chaos engineer designing experiments" in system:
            return "chaos"
        if "red team coordinator" in system:
            return "orchestrator"
        if "You are the Arbiter" in system:
            return "arbiter"
        return "unknown"

    def _extract_file_path(self, messages: list[Message]) -> str:
        user_text = "\n".join(m.content for m in messages if m.role == "user")
        patterns = [
            r"\*\*File:\*\* `([^`]+)`",
            r"`([^`]+\.py)`",
            r"\*\*([^*]+\.py):\*\*",
        ]
        for pattern in patterns:
            match = re.search(pattern, user_text)
            if match:
                return match.group(1)
        return "unknown"

    def _exploit_payload(self, file_path: str) -> dict[str, Any]:
        return {
            "target": {
                "file_path": file_path,
                "function_name": "get_user",
                "exposure": "public",
            },
            "findings": [
                {
                    "id": "EXPLOIT-001",
                    "title": "SQL injection in user lookup",
                    "severity": "HIGH",
                    "owasp_category": "A03:2021-Injection",
                    "cwe_id": "CWE-89",
                    "confidence": 0.85,
                    "description": "User input is concatenated into a SQL query.",
                    "vulnerable_code": {
                        "file": file_path,
                        "line_start": 12,
                        "line_end": 15,
                        "snippet": 'query = f"SELECT id, email FROM users WHERE id = {user_id}"',
                    },
                    "exploit": {
                        "description": "Injects SQL to bypass filtering and dump user rows.",
                        "payload": "1 OR 1=1",
                        "curl_command": "curl 'http://localhost/api/users?id=1%20OR%201=1'",
                        "prerequisites": ["Public endpoint"],
                        "impact": "Unauthorized access to user data.",
                    },
                    "remediation": {
                        "immediate": "Use parameterized queries.",
                        "code_fix": (
                            'cursor.execute("SELECT id, email FROM users WHERE id = ?", (user_id,))'
                        ),
                        "defense_in_depth": ["Add input validation", "Use least-privilege DB user"],
                    },
                },
                {
                    "id": "EXPLOIT-002",
                    "title": "Command injection via report runner",
                    "severity": "HIGH",
                    "owasp_category": "A03:2021-Injection",
                    "cwe_id": "CWE-78",
                    "confidence": 0.8,
                    "description": "Shell execution uses unsanitized input.",
                    "vulnerable_code": {
                        "file": file_path,
                        "line_start": 24,
                        "line_end": 26,
                        "snippet": "subprocess.check_output(command, shell=True)",
                    },
                    "exploit": {
                        "description": "Chain commands with shell metacharacters.",
                        "payload": "report.sh; cat /etc/passwd",
                        "curl_command": "curl -X POST /run?command=report.sh%3Bcat%20/etc/passwd",
                        "prerequisites": ["Execute report endpoint"],
                        "impact": "Arbitrary command execution on host.",
                    },
                    "remediation": {
                        "immediate": "Avoid shell=True and pass args as a list.",
                        "code_fix": 'subprocess.check_output(["report.sh", user_id])',
                        "defense_in_depth": ["Allowlist commands", "Run under a restricted user"],
                    },
                },
            ],
            "attack_surface_analysis": {
                "user_inputs": ["query parameters", "POST body"],
                "external_calls": ["database", "shell"],
                "sensitive_data": ["user emails"],
            },
            "confidence": 0.82,
            "assumptions": ["Endpoints are exposed without additional WAF rules"],
            "unknowns": ["No auth or rate limiting context provided"],
        }

    def _crypto_payload(self, file_path: str) -> dict[str, Any]:
        return {
            "target": {
                "file_path": file_path,
                "function_name": "verify_token",
                "exposure": "public",
            },
            "findings": [
                {
                    "id": "CRYPTO-001",
                    "title": "Predictable randomness used for secrets",
                    "severity": "HIGH",
                    "cwe_id": "CWE-330",
                    "confidence": 0.8,
                    "description": "Non-cryptographic PRNG is used for security-sensitive tokens.",
                    "evidence": {
                        "file": file_path,
                        "line_start": 10,
                        "line_end": 12,
                        "snippet": "token = random.random()",
                    },
                    "attack": {
                        "description": (
                            "Attacker can predict tokens with enough samples/state leakage."
                        ),
                        "prerequisites": ["Attacker can obtain multiple tokens"],
                        "impact": "Session/token forgery and account takeover.",
                    },
                    "remediation": {
                        "immediate": "Use secrets.token_urlsafe() or secrets.randbelow().",
                        "code_fix": "token = secrets.token_urlsafe(32)",
                        "defense_in_depth": ["Rotate tokens", "Add token expiry"],
                    },
                }
            ],
            "confidence": 0.82,
            "assumptions": ["Tokens are security-sensitive"],
            "unknowns": ["No surrounding authentication context provided"],
        }

    def _break_payload(self, file_path: str) -> dict[str, Any]:
        return {
            "target": {
                "file_path": file_path,
                "function_name": "load_session",
                "code_analyzed": "Session deserialization flow",
            },
            "findings": [
                {
                    "id": "BREAK-001",
                    "title": "Unbounded session payload causes memory pressure",
                    "severity": "MEDIUM",
                    "category": "resource",
                    "confidence": 0.7,
                    "description": "Session payload size is not validated before processing.",
                    "attack_vector": "Send a very large session blob to trigger memory growth.",
                    "proof_of_concept": {
                        "description": "Allocates a huge payload to force memory use.",
                        "code": "load_session(b'A' * 10_000_000)",
                        "expected_behavior": "Reject oversized payloads.",
                        "vulnerable_behavior": (
                            "Process allocates large buffer and slows or crashes."
                        ),
                    },
                    "impact": "Possible slowdown or crash under load.",
                    "remediation": {
                        "immediate": "Enforce a max payload size.",
                        "proper": "Stream and validate session data before decoding.",
                        "code_example": "if len(raw) > MAX_SESSION_BYTES: raise ValueError",
                    },
                    "line_numbers": [34, 35, 36],
                }
            ],
            "attack_vectors_tried": [
                "oversized payload",
                "malformed bytes",
            ],
            "code_quality_observations": [
                "Input validation is minimal around session parsing",
            ],
            "confidence": 0.72,
            "assumptions": ["Session data is user-controlled"],
            "unknowns": ["No upstream size limits observed"],
        }

    def _chaos_payload(self, file_path: str) -> dict[str, Any]:
        return {
            "target": {
                "file_path": file_path,
                "function_name": "fetch_profile",
                "code_analyzed": "Outbound HTTP fetch",
            },
            "dependencies_detected": [
                {
                    "name": "External HTTP service",
                    "type": "api",
                    "evidence": ["requests.get(url, timeout=3)"],
                    "criticality": "important",
                }
            ],
            "resilience_analysis": {
                "has_timeouts": True,
                "has_retries": False,
                "has_circuit_breaker": False,
                "has_fallbacks": False,
                "has_health_checks": False,
                "overall_resilience_score": 45,
            },
            "experiments": [
                {
                    "id": "CHAOS-001",
                    "title": "Simulate upstream timeout",
                    "category": "dependency_failure",
                    "target_dependency": "External HTTP service",
                    "failure_mode": "timeout",
                    "severity_if_vulnerable": "MEDIUM",
                    "experiment": {
                        "description": "Inject 5s latency to upstream calls.",
                        "method": "toxiproxy latency=5000ms",
                        "duration_seconds": 60,
                        "safe_to_automate": True,
                        "requires_isolation": True,
                        "rollback": "remove toxiproxy latency rule",
                    },
                    "hypothesis": {
                        "expected_resilient_behavior": "Request fails fast with a clear error.",
                        "predicted_actual_behavior": "User request times out without fallback.",
                        "prediction_confidence": 0.6,
                    },
                    "evidence": {
                        "code_location": f"{file_path}:28",
                        "problematic_code": "requests.get(url, timeout=3)",
                        "missing_patterns": ["retry/backoff", "fallback response"],
                    },
                    "remediation": {
                        "immediate": "Add a fallback response for timeouts.",
                        "proper": "Implement retries with backoff and circuit breaker.",
                        "code_example": "try: ... except Timeout: return cached_profile",
                    },
                }
            ],
            "confidence": 0.7,
            "assumptions": ["Upstream failures are possible in production"],
            "unknowns": ["No circuit breaker configured"],
        }

    def _orchestrator_payload(self, file_path: str) -> dict[str, Any]:
        return {
            "attack_surface_analysis": {
                "files": [
                    {
                        "file_path": file_path,
                        "risk_score": 85,
                        "risk_factors": [
                            "user input reaches SQL and shell",
                            "external HTTP requests",
                        ],
                        "recommended_agents": [
                            "ExploitAgent",
                            "BreakAgent",
                            "ChaosAgent",
                        ],
                        "attack_vectors": [
                            "SQL injection",
                            "command injection",
                            "timeout handling",
                        ],
                        "exposure": "public",
                        "data_sensitivity": "high",
                    }
                ],
                "total_risk_score": 85,
                "highest_risk_file": file_path,
                "primary_concerns": [
                    "SQL injection in user lookup",
                    "command execution without validation",
                ],
                "recommended_focus_areas": [
                    "database access",
                    "input validation",
                    "external calls",
                ],
            },
            "risk_level": "HIGH",
            "risk_factors": [
                "public exposure",
                "direct database access",
                "shell execution",
            ],
            "attacks": [
                {
                    "id": "ATK-001",
                    "agent": "ExploitAgent",
                    "target_file": file_path,
                    "target_function": "get_user",
                    "priority": 1,
                    "attack_vectors": [
                        {
                            "name": "SQL Injection",
                            "description": "Probe query construction for injection.",
                            "category": "injection",
                            "payload_hints": ["1 OR 1=1", "' OR '1'='1"],
                            "expected_behavior": "Query uses parameters",
                            "success_indicators": ["returns all rows", "SQL error"],
                        }
                    ],
                    "time_budget_seconds": 60,
                    "rationale": "User input is interpolated into SQL.",
                    "depends_on": [],
                    "can_parallel_with": ["ATK-002", "ATK-003"],
                    "hints": ["Look for f-strings building SQL"],
                },
                {
                    "id": "ATK-002",
                    "agent": "BreakAgent",
                    "target_file": file_path,
                    "target_function": "load_session",
                    "priority": 3,
                    "attack_vectors": [
                        {
                            "name": "Payload Size",
                            "description": "Send oversized payloads.",
                            "category": "resource",
                            "payload_hints": ["10MB blob"],
                            "expected_behavior": "Reject oversized payloads",
                            "success_indicators": ["memory spike", "timeout"],
                        }
                    ],
                    "time_budget_seconds": 45,
                    "rationale": "Session data is decoded without limits.",
                    "depends_on": [],
                    "can_parallel_with": ["ATK-001", "ATK-003"],
                    "hints": ["Check session deserialization"],
                },
                {
                    "id": "ATK-003",
                    "agent": "ChaosAgent",
                    "target_file": file_path,
                    "target_function": "fetch_profile",
                    "priority": 3,
                    "attack_vectors": [
                        {
                            "name": "Upstream Timeout",
                            "description": "Simulate slow upstream API.",
                            "category": "dependency_failure",
                            "payload_hints": ["5s latency"],
                            "expected_behavior": "Fail fast with fallback",
                            "success_indicators": ["request timeout", "no fallback"],
                        }
                    ],
                    "time_budget_seconds": 45,
                    "rationale": "Outbound requests lack retries or fallback.",
                    "depends_on": [],
                    "can_parallel_with": ["ATK-001", "ATK-002"],
                    "hints": ["Check requests.get timeout behavior"],
                },
            ],
            "parallel_groups": [
                {
                    "group_id": "PG-001",
                    "attack_ids": ["ATK-001", "ATK-002", "ATK-003"],
                    "estimated_duration_seconds": 120,
                }
            ],
            "execution_order": ["ATK-001", "ATK-002", "ATK-003"],
            "skipped": [],
            "recommendations": [
                "Prioritize injection points",
                "Validate input paths and payload sizes",
            ],
            "confidence": 0.74,
            "assumptions": ["Target code is user-facing"],
            "unknowns": ["Auth and WAF configuration not provided"],
        }

    def _arbiter_payload(self) -> dict[str, Any]:
        return {
            "decision": "WARN",
            "decision_rationale": (
                "Issues are plausible with meaningful impact, but mitigations may exist."
            ),
            "blocking_issues": [],
            "warnings": [
                {
                    "original_id": "EXPLOIT-001",
                    "original_agent": "ExploitAgent",
                    "original_title": "SQL injection in user lookup",
                    "original_severity": "HIGH",
                    "validation_status": "LIKELY",
                    "validated_severity": "HIGH",
                    "adjusted_severity_reason": "No evidence of auth gates in context",
                    "exploitation_difficulty": "EASY",
                    "exploitation_prerequisites": ["Access to endpoint"],
                    "real_world_exploitability": 0.7,
                    "impact_description": "Unauthorized reads from the user table.",
                    "affected_components": ["user_service", "database"],
                    "data_at_risk": ["user emails"],
                    "remediation_effort": "HOURS",
                    "suggested_fix": "Parameterize SQL queries.",
                    "fix_code_example": (
                        'cursor.execute("SELECT id, email FROM users WHERE id = ?", (user_id,))'
                    ),
                    "workaround": "Apply WAF rule as temporary mitigation.",
                    "confidence": 0.78,
                }
            ],
            "passed_findings": [],
            "false_positives": [],
            "remediation_tasks": [
                {
                    "finding_id": "EXPLOIT-001",
                    "title": "Fix SQL injection in user lookup",
                    "description": "Replace string concatenation with parameterized queries.",
                    "priority": "HIGH",
                    "estimated_effort": "HOURS",
                    "fix_guidance": "Use parameterized queries and validate inputs.",
                    "acceptance_criteria": [
                        "No string interpolation in SQL",
                        "Input is validated",
                    ],
                }
            ],
            "summary": "1 warning, no blockers. Fix input handling in database queries.",
            "key_concerns": ["Injection paths", "Shell execution"],
            "recommendations": ["Add input validation", "Introduce retry/backoff for HTTP"],
            "confidence": 0.78,
            "assumptions": ["Public exposure"],
            "limitations": ["Runtime auth controls not provided"],
        }
