"""CrossExaminationAgent - makes agents argue over findings.

This agent takes the combined findings (typically from ExploitAgent and BreakAgent)
and forces an adversarial cross-examination:
  - strongest objections per finding
  - required evidence / reproduction steps
  - confidence/severity adjustments

The goal is fewer false positives and more actionable, battle-tested findings.
"""

from __future__ import annotations

import json
from typing import Any

from ..baseline import compute_fingerprint
from ..providers import Message, ModelTier
from ..store import BeadType
from .base import Agent, AgentContext, AgentOutput

CROSS_EXAMINER_ROUND1_SYSTEM_PROMPT = """You are the CrossExaminationAgent.

ROUND 1: ATTACK (Cross-examination)

You simulate a ferocious attack phase between TWO adversarial specialists:

1) ExploitAgent (security attacker): ruthless about exploitability, insists on a plausible exploit
   path.
2) BreakAgent (logic breaker): ruthless about edge cases, insists on concrete reproduction.

Your job is NOT to be polite. Your job is to attack weak claims and list missing evidence.

Debate rules:
- Assume findings are wrong until defended with evidence.
- Demand specificity: exact file path, line, and minimal repro or payload.
- Identify what evidence is missing (payload, repro steps, snippet, line, etc).

Output format:
Return valid JSON ONLY with this exact schema:

{
  "challenges": [
    {
      "fingerprint": "string",
      "attacks": ["strongest objections / counterarguments"],
      "missing_evidence": ["what evidence is missing (payload/repro/line/snippet/etc)"],
      "minimum_required_repro": ["the minimal payload or reproduction steps required"]
    }
  ],
  "confidence": 0.8,
  "assumptions": ["assumptions made"],
  "unknowns": ["things that couldn't be determined"]
}

Constraints:
- Do not invent file paths/lines; if unknown, set null.
- Do not add new findings; only refine or dismiss existing ones.
"""


CROSS_EXAMINER_ROUND2_SYSTEM_PROMPT = """You are the CrossExaminationAgent.

ROUND 2: FORCED REBUTTAL (Defense) + FINAL JUDGMENT

You must produce final, battle-tested findings by forcing each claim through:
  - Attack: strongest objections (from Round 1)
  - Defense: rebuttal grounded in evidence
  - Judgment: UPHOLD, DOWNGRADE, or DISMISS

Hard rule (automatic dismissal):
- If a finding does NOT include a concrete exploitation payload or concrete reproduction steps,
  you MUST set resolution=DISMISS.

Preserve IDs/fingerprints when possible for baseline stability.

Output format:
Return valid JSON ONLY with this exact schema:

{
  "findings": [
    {
      "id": null,
      "fingerprint": "string",
      "finding_type": "exploit",
      "agent": "ExploitAgent",
      "title": "string",
      "severity": "MEDIUM",
      "confidence": 0.7,
      "file_path": null,
      "line": null,
      "description": null,
      "impact": null,
      "remediation": null,
      "reproduction_steps": ["step 1", "step 2"],
      "debate": {
        "attacks": ["strongest objections / counterarguments"],
        "defenses": ["defenses grounded in evidence"],
        "resolution": "DOWNGRADE",
        "confidence_delta": -0.2
      },
      "raw": {}
    }
  ],
  "summary": {
    "upheld": 0,
    "downgraded": 1,
    "dismissed": 0
  },
  "confidence": 0.8,
  "assumptions": ["assumptions made"],
  "unknowns": ["things that couldn't be determined"]
}

Constraints:
- Do not invent file paths/lines; if unknown, set null.
- Do not add new findings; only refine or dismiss existing ones.
"""


def _has_concrete_repro(finding: dict[str, Any]) -> bool:
    """True if finding has concrete payload/reproduction steps."""
    steps = finding.get("reproduction_steps")
    if isinstance(steps, list) and any(isinstance(s, str) and s.strip() for s in steps):
        return True

    raw = finding.get("raw") or {}
    if isinstance(raw, dict):
        exploit = raw.get("exploit")
        if isinstance(exploit, dict):
            for key in ("payload", "curl_command"):
                value = exploit.get(key)
                if isinstance(value, str) and value.strip():
                    return True

        poc = raw.get("proof_of_concept")
        if isinstance(poc, dict):
            code = poc.get("code")
            if isinstance(code, str) and code.strip():
                return True

    return False


def _enforce_repro_dismissal(
    findings: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    """Force-dismiss (and drop) any finding without concrete repro/payload."""
    upheld = downgraded = dismissed = 0
    kept: list[dict[str, Any]] = []

    for f in findings:
        if not isinstance(f, dict):
            continue

        if not f.get("fingerprint"):
            f["fingerprint"] = compute_fingerprint(f)

        raw_debate = f.get("debate")
        debate: dict[str, Any] = raw_debate if isinstance(raw_debate, dict) else {}
        resolution = str(debate.get("resolution", "")).upper()

        if not _has_concrete_repro(f):
            debate = dict(debate)
            raw_attacks = debate.get("attacks")
            attacks = [str(a) for a in raw_attacks] if isinstance(raw_attacks, list) else []
            attacks.append("Missing concrete reproduction steps/payload; auto-dismissed by policy.")
            debate["attacks"] = attacks
            debate["resolution"] = "DISMISS"
            debate["confidence_delta"] = float(debate.get("confidence_delta", -0.5) or -0.5)
            f["debate"] = debate
            f["confidence"] = 0.0
            dismissed += 1
            continue

        if resolution == "DISMISS":
            dismissed += 1
            continue
        if resolution == "DOWNGRADE":
            downgraded += 1
        else:
            upheld += 1

        kept.append(f)

    return kept, {"upheld": upheld, "downgraded": downgraded, "dismissed": dismissed}


class CrossExaminationAgent(Agent):
    @property
    def name(self) -> str:
        return "CrossExaminationAgent"

    @property
    def bead_type(self) -> BeadType:
        return BeadType.CROSS_EXAMINATION

    @property
    def model_tier(self) -> ModelTier:
        return ModelTier.HOSTED_LARGE

    def _build_prompt(self, context: AgentContext) -> list[Message]:
        # Not used: run() is overridden to do two rounds.
        return self._build_round2_prompt(context, challenges={})

    def _build_round1_prompt(self, context: AgentContext) -> list[Message]:
        findings = context.inputs.get("findings", [])
        code_excerpt = context.inputs.get("code_excerpt", "")
        max_findings = int(context.inputs.get("max_findings", 40))

        trimmed = findings[:max_findings] if isinstance(findings, list) else []

        user_parts = [
            "## Findings To Cross-Examine (Round 1: Attack)",
            "```json",
            json.dumps(trimmed, indent=2, default=str)[:20000],
            "```",
        ]

        if code_excerpt:
            user_parts.extend(
                [
                    "",
                    "## Code Excerpt (for evidence checks)",
                    "```",
                    code_excerpt[:20000],
                    "```",
                ]
            )

        user_parts.extend(
            [
                "",
                "Round 1: ATTACK. Return only JSON.",
            ]
        )

        return [
            Message(role="system", content=CROSS_EXAMINER_ROUND1_SYSTEM_PROMPT),
            Message(role="user", content="\n".join(user_parts)),
        ]

    def _build_round2_prompt(
        self,
        context: AgentContext,
        *,
        challenges: dict[str, Any],
    ) -> list[Message]:
        findings = context.inputs.get("findings", [])
        code_excerpt = context.inputs.get("code_excerpt", "")
        max_findings = int(context.inputs.get("max_findings", 40))

        trimmed = findings[:max_findings] if isinstance(findings, list) else []

        user_parts = [
            "## Findings To Cross-Examine (Original)",
            "```json",
            json.dumps(trimmed, indent=2, default=str)[:20000],
            "```",
            "",
            "## Round 1 Challenges",
            "```json",
            json.dumps(challenges, indent=2, default=str)[:20000],
            "```",
        ]

        if code_excerpt:
            user_parts.extend(
                [
                    "",
                    "## Code Excerpt (for evidence checks)",
                    "```",
                    code_excerpt[:20000],
                    "```",
                ]
            )

        user_parts.extend(
            [
                "",
                "Round 2: FORCED REBUTTAL + FINAL JUDGMENT. Return only JSON.",
            ]
        )

        return [
            Message(role="system", content=CROSS_EXAMINER_ROUND2_SYSTEM_PROMPT),
            Message(role="user", content="\n".join(user_parts)),
        ]

    async def run(self, context: AgentContext) -> AgentOutput:
        """Two rounds: attack, then forced rebuttal/judgment.

        Enforces a hard policy to dismiss findings without concrete repro/payload.
        """
        model = self.provider.get_model_for_tier(self.model_tier)

        # Round 1
        round1_messages = self._build_round1_prompt(context)
        round1_response = await self.provider.complete(round1_messages, model=model, json_mode=True)
        try:
            challenges = self._parse_json_response(round1_response.content)
        except json.JSONDecodeError:
            challenges = {"challenges": [], "error": "failed_to_parse_round1"}

        # Round 2
        round2_messages = self._build_round2_prompt(context, challenges=challenges)
        round2_response = await self.provider.complete(round2_messages, model=model, json_mode=True)
        output = self._parse_response(round2_response.content, context)

        # Hard enforcement
        findings = output.result.get("findings", [])
        if isinstance(findings, list):
            filtered, counts = _enforce_repro_dismissal(findings)
            output.result["findings"] = filtered
            output.result["summary"] = counts

            if output.beads_out:
                output.beads_out[0].payload["findings_out"] = len(filtered)
                output.beads_out[0].payload["upheld"] = counts["upheld"]
                output.beads_out[0].payload["downgraded"] = counts["downgraded"]
                output.beads_out[0].payload["dismissed"] = counts["dismissed"]

        return output

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
        summary = data.get("summary", {})

        bead = self._create_bead(
            context,
            payload={
                "findings_in": len(context.inputs.get("findings", []) or []),
                "findings_out": len(findings or []),
                "upheld": summary.get("upheld", 0),
                "downgraded": summary.get("downgraded", 0),
                "dismissed": summary.get("dismissed", 0),
            },
            confidence=data.get("confidence", 0.8),
            assumptions=data.get("assumptions", []),
            unknowns=data.get("unknowns", []),
        )

        return AgentOutput(
            agent_name=self.name,
            result={
                "findings": findings,
                "summary": summary,
            },
            beads_out=[bead],
            confidence=data.get("confidence", 0.8),
            assumptions=data.get("assumptions", []),
            unknowns=data.get("unknowns", []),
        )
