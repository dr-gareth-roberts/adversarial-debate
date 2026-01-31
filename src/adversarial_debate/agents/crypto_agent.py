import json
from typing import Any

from ..knowledge import CWE_PATTERNS, DANGEROUS_SINKS
from ..providers import Message, ModelTier
from ..store import BeadType
from .base import Agent, AgentContext, AgentOutput

CRYPTO_AGENT_SYSTEM_PROMPT = """You are a senior cryptography engineer and security auditor.
Your job is to find exploitable crypto and auth-adjacent weaknesses, not theoretical risks.

You MUST respond with valid JSON only.

Output schema:
{
  "target": {
    "file_path": "path/to/file.py",
    "function_name": "function_being_analyzed",
    "exposure": "public"
  },
  "findings": [
    {
      "id": "CRYPTO-001",
      "title": "Weak hashing for passwords",
      "severity": "HIGH",
      "cwe_id": "CWE-327",
      "confidence": 0.8,
      "description": "...",
      "evidence": {
        "file": "path/to/file.py",
        "line_start": 10,
        "line_end": 12,
        "snippet": "hashlib.md5(password).hexdigest()"
      },
      "attack": {
        "description": "How it can be abused",
        "prerequisites": ["..."],
        "impact": "..."
      },
      "remediation": {
        "immediate": "Quick fix",
        "code_fix": "Suggested code",
        "defense_in_depth": ["..."
        ]
      }
    }
  ],
  "confidence": 0.8,
  "assumptions": [],
  "unknowns": []
}

Rules:
1. Prefer concrete issues: weak algorithms, hardcoded keys/secrets, predictable randomness,
   unsafe comparisons.
2. Include evidence snippet.
3. Provide actionable remediation.
"""


class CryptoAgent(Agent):
    @property
    def name(self) -> str:
        return "CryptoAgent"

    @property
    def bead_type(self) -> BeadType:
        return BeadType.CRYPTO_ANALYSIS

    @property
    def model_tier(self) -> ModelTier:
        return ModelTier.HOSTED_LARGE

    def _build_prompt(self, context: AgentContext) -> list[Message]:
        target_code = context.inputs.get("code", "")
        file_path = context.inputs.get("file_path", "unknown")
        function_name = context.inputs.get("function_name", "")
        language = context.inputs.get("language", "python")
        exposure = context.inputs.get("exposure", "internal")

        attack_hints = context.inputs.get("attack_hints", [])
        focus_areas = context.inputs.get("focus_areas", [])
        hints = context.inputs.get("hints", [])
        payload_hints = context.inputs.get("payload_hints", [])
        success_indicators = context.inputs.get("success_indicators", [])

        user_parts: list[str] = [
            "## Target Code",
            "",
            f"**File:** `{file_path}`",
        ]
        if function_name:
            user_parts.append(f"**Function/Class:** `{function_name}`")

        user_parts.extend(
            [
                f"**Language:** {language}",
                f"**Exposure:** {exposure}",
                "",
                f"```{language}",
                target_code,
                "```",
                "",
            ]
        )

        user_parts.append("## Reference Knowledge")
        user_parts.append("")
        user_parts.append("**Common crypto CWEs:**")
        for key in ("CWE-327", "CWE-798"):
            item = CWE_PATTERNS.get(key, {})
            name = item.get("name") if isinstance(item, dict) else None
            if name:
                user_parts.append(f"- {key}: {name}")
            else:
                user_parts.append(f"- {key}")
        user_parts.append("")

        sinks = DANGEROUS_SINKS.get("python", [])
        if sinks:
            user_parts.append("**Dangerous sinks (context):**")
            for s in sinks[:25]:
                user_parts.append(f"- {s}")
            user_parts.append("")

        if any([attack_hints, focus_areas, hints, payload_hints, success_indicators]):
            user_parts.append("## Attack Plan Hints")
            user_parts.append("")

            if attack_hints:
                user_parts.append("**Attack hints:**")
                for h in attack_hints[:30]:
                    user_parts.append(f"- {h}")
                user_parts.append("")

            if focus_areas:
                user_parts.append("**Focus areas:**")
                for area in focus_areas[:30]:
                    user_parts.append(f"- {area}")
                user_parts.append("")

            if payload_hints:
                user_parts.append("**Payload hints:**")
                for ph in payload_hints[:30]:
                    user_parts.append(f"- {ph}")
                user_parts.append("")

            if success_indicators:
                user_parts.append("**Success indicators:**")
                for si in success_indicators[:30]:
                    user_parts.append(f"- {si}")
                user_parts.append("")

            if hints:
                user_parts.append("**Code hints:**")
                for h in hints[:30]:
                    user_parts.append(f"- {h}")
                user_parts.append("")

        user_parts.extend(
            [
                "## Your Mission",
                "",
                "Find exploitable cryptography and auth-adjacent weaknesses.",
                "",
                "Focus on:",
                "- Weak algorithms (MD5/SHA1/DES/RC4/ECB)",
                "- Hardcoded keys/IVs/salts/secrets",
                "- Predictable randomness (random vs secrets)",
                "- Timing issues in comparisons",
                "- JWT misuse (alg=none, weak secret, missing issuer/audience)",
                "",
                "Respond with valid JSON matching the schema in your instructions.",
            ]
        )

        return [
            Message(role="system", content=CRYPTO_AGENT_SYSTEM_PROMPT),
            Message(role="user", content="\n".join(user_parts)),
        ]

    def _parse_response(self, response: str, context: AgentContext) -> AgentOutput:
        try:
            data = self._parse_json_response(response)
        except json.JSONDecodeError as e:
            return AgentOutput(
                agent_name=self.name,
                result={"findings": [], "error": f"Failed to parse response: {e}"},
                beads_out=[],
                confidence=0.0,
                errors=[f"Failed to parse response as JSON: {e}"],
            )

        findings = data.get("findings", [])
        target = data.get("target", {})

        normalized_findings: list[dict[str, Any]] = []
        for i, finding in enumerate(findings):
            normalized = self._normalize_finding(finding, i, context)
            if normalized:
                normalized_findings.append(normalized)

        payload = {
            "target": target,
            "findings_count": len(normalized_findings),
            "findings_by_severity": self._count_by_severity(normalized_findings),
            "has_critical": any(f.get("severity") == "CRITICAL" for f in normalized_findings),
            "has_high": any(f.get("severity") == "HIGH" for f in normalized_findings),
        }

        bead = self._create_bead(
            context,
            payload=payload,
            artefacts=[],
            confidence=data.get("confidence", 0.8),
            assumptions=data.get("assumptions", []),
            unknowns=data.get("unknowns", []),
        )

        return AgentOutput(
            agent_name=self.name,
            result={
                "target": target,
                "findings": normalized_findings,
                "summary": {
                    "total_findings": len(normalized_findings),
                    "by_severity": self._count_by_severity(normalized_findings),
                },
            },
            beads_out=[bead],
            confidence=data.get("confidence", 0.8),
            assumptions=data.get("assumptions", []),
            unknowns=data.get("unknowns", []),
        )

    def _normalize_finding(
        self,
        finding: dict[str, Any],
        index: int,
        context: AgentContext,
    ) -> dict[str, Any] | None:
        if not finding.get("title"):
            return None

        evidence = finding.get("evidence") or {}
        if not isinstance(evidence, dict) or not evidence.get("snippet"):
            return None

        fid = finding.get("id") or f"CRYPTO-{index + 1:03d}"

        normalized = dict(finding)
        normalized["id"] = fid

        target = normalized.get("target")
        if not isinstance(target, dict):
            normalized["target"] = {
                "file_path": context.inputs.get("file_path", "unknown"),
                "function_name": context.inputs.get("function_name", ""),
                "exposure": context.inputs.get("exposure", "internal"),
            }

        severity = str(normalized.get("severity", "MEDIUM")).upper()
        if severity not in {"CRITICAL", "HIGH", "MEDIUM", "LOW"}:
            normalized["severity"] = "MEDIUM"

        return normalized

    def _count_by_severity(self, findings: list[dict[str, Any]]) -> dict[str, int]:
        counts: dict[str, int] = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
        for f in findings:
            sev = str(f.get("severity", "MEDIUM")).upper()
            counts[sev] = counts.get(sev, 0) + 1
        return counts
