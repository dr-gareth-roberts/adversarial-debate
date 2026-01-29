"""SARIF (Static Analysis Results Interchange Format) output formatter.

SARIF is a standard format for static analysis tools, supported by:
- GitHub Code Scanning
- Azure DevOps
- VS Code SARIF Viewer
- Many other security tools

Specification: https://sarifweb.azurewebsites.net/
"""

import json
from datetime import UTC, datetime
from typing import Any
from urllib.parse import quote

from .base import Formatter, FormatterConfig, OutputFormat

# Mapping from our severity levels to SARIF levels
SEVERITY_TO_SARIF_LEVEL = {
    "CRITICAL": "error",
    "HIGH": "error",
    "MEDIUM": "warning",
    "LOW": "note",
    "INFO": "note",
    "UNKNOWN": "none",
}

# Mapping from our severity to SARIF security-severity score
SEVERITY_TO_SCORE = {
    "CRITICAL": 9.0,
    "HIGH": 7.0,
    "MEDIUM": 5.0,
    "LOW": 3.0,
    "INFO": 1.0,
}


class SARIFFormatter(Formatter):
    """SARIF 2.1.0 output formatter.

    Produces SARIF output compatible with GitHub Code Scanning
    and other SARIF-consuming tools.
    """

    SARIF_VERSION = "2.1.0"
    SARIF_SCHEMA = "https://raw.githubusercontent.com/oasis-tcs/sarif-spec/master/Schemata/sarif-schema-2.1.0.json"

    def __init__(self, config: FormatterConfig | None = None):
        super().__init__(config)

    @property
    def format_type(self) -> OutputFormat:
        return OutputFormat.SARIF

    @property
    def file_extension(self) -> str:
        return ".sarif"

    @property
    def content_type(self) -> str:
        return "application/sarif+json"

    def format(self, data: dict[str, Any]) -> str:
        """Format data as SARIF.

        Args:
            data: Analysis results containing findings

        Returns:
            SARIF JSON string
        """
        sarif = self._build_sarif(data)
        indent = 2 if self.config.pretty else None
        return json.dumps(sarif, indent=indent, default=str, ensure_ascii=False)

    def _build_sarif(self, data: dict[str, Any]) -> dict[str, Any]:
        """Build the SARIF document structure."""
        findings = data.get("findings", [])
        verdict = data.get("verdict", {})

        # Build rules from unique finding types
        rules = self._build_rules(findings)
        rule_index = {rule["id"]: i for i, rule in enumerate(rules)}

        # Build results
        results = [self._finding_to_result(finding, rule_index) for finding in findings]

        # Build the run
        run: dict[str, Any] = {
            "tool": {
                "driver": {
                    "name": self.config.tool_name,
                    "version": self.config.tool_version,
                    "informationUri": "https://github.com/dr-gareth-roberts/adversarial-debate",
                    "rules": rules,
                }
            },
            "results": results,
            "invocations": [
                {
                    "executionSuccessful": True,
                    "endTimeUtc": datetime.now(UTC).isoformat(),
                }
            ],
        }

        # Add verdict as run properties if available
        if verdict:
            run["properties"] = {
                "verdict": verdict.get("summary", {}),
            }

        return {
            "$schema": self.SARIF_SCHEMA,
            "version": self.SARIF_VERSION,
            "runs": [run],
        }

    def _build_rules(self, findings: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Build SARIF rules from findings."""
        rules_map: dict[str, dict[str, Any]] = {}

        for finding in findings:
            rule_id = self._get_rule_id(finding)
            if rule_id in rules_map:
                continue

            severity = finding.get("severity", "MEDIUM")
            category = finding.get("category", finding.get("finding_type", "security"))

            rule: dict[str, Any] = {
                "id": rule_id,
                "name": finding.get("title", rule_id),
                "shortDescription": {
                    "text": finding.get("title", "Security Finding"),
                },
                "fullDescription": {
                    "text": finding.get("description", finding.get("title", "Security Finding")),
                },
                "defaultConfiguration": {
                    "level": SEVERITY_TO_SARIF_LEVEL.get(severity, "warning"),
                },
                "properties": {
                    "tags": [category, "security"],
                    "security-severity": str(SEVERITY_TO_SCORE.get(severity, 5.0)),
                },
            }

            # Add help URL if available
            if finding.get("cwe"):
                rule["helpUri"] = f"https://cwe.mitre.org/data/definitions/{finding['cwe']}.html"

            rules_map[rule_id] = rule

        return list(rules_map.values())

    def _get_rule_id(self, finding: dict[str, Any]) -> str:
        """Generate a rule ID from a finding."""
        # Use CWE if available
        if finding.get("cwe"):
            return f"CWE-{finding['cwe']}"

        # Use finding type or category
        finding_type = finding.get("finding_type", finding.get("category", "security"))
        title = finding.get("title", "finding")

        # Create a stable ID from type and title
        safe_title = quote(title.lower().replace(" ", "-")[:50], safe="-")
        return f"AD-{finding_type}-{safe_title}"

    def _finding_to_result(
        self, finding: dict[str, Any], rule_index: dict[str, int]
    ) -> dict[str, Any]:
        """Convert a finding to a SARIF result."""
        rule_id = self._get_rule_id(finding)
        severity = finding.get("severity", "MEDIUM")

        result: dict[str, Any] = {
            "ruleId": rule_id,
            "ruleIndex": rule_index.get(rule_id, 0),
            "level": SEVERITY_TO_SARIF_LEVEL.get(severity, "warning"),
            "message": {
                "text": self._build_message(finding),
            },
        }

        # Add locations
        locations = self._build_locations(finding)
        if locations:
            result["locations"] = locations

        # Add code flows if available
        if finding.get("attack_steps") or finding.get("reproduction_steps"):
            result["codeFlows"] = self._build_code_flows(finding)

        # Add fingerprint for deduplication
        fingerprint = finding.get("fingerprint", finding.get("id"))
        if fingerprint:
            result["fingerprints"] = {"primary": str(fingerprint)}

        # Add properties for extra metadata
        properties: dict[str, Any] = {}
        if finding.get("confidence"):
            properties["confidence"] = finding["confidence"]
        if finding.get("agent"):
            properties["agent"] = finding["agent"]
        if finding.get("remediation"):
            properties["remediation"] = finding["remediation"]
        if finding.get("exploitation_difficulty"):
            properties["exploitationDifficulty"] = finding["exploitation_difficulty"]

        if properties:
            result["properties"] = properties

        return result

    def _build_message(self, finding: dict[str, Any]) -> str:
        """Build the result message from a finding."""
        parts = []

        # Title/summary
        title = finding.get("title", "Security Finding")
        parts.append(title)

        # Description
        description = finding.get("description")
        if description and description != title:
            parts.append(description)

        # Impact
        impact = finding.get("impact")
        if impact:
            parts.append(f"Impact: {impact}")

        # Remediation hint
        remediation = finding.get("remediation")
        if remediation:
            parts.append(f"Remediation: {remediation}")

        return "\n\n".join(parts)

    def _build_locations(self, finding: dict[str, Any]) -> list[dict[str, Any]]:
        """Build SARIF locations from a finding."""
        locations = []

        # Primary location
        file_path = finding.get("file_path", finding.get("file"))
        line = finding.get("line", finding.get("line_number", 1))

        if file_path:
            location: dict[str, Any] = {
                "physicalLocation": {
                    "artifactLocation": {
                        "uri": file_path,
                        "uriBaseId": "%SRCROOT%",
                    },
                    "region": {
                        "startLine": max(1, int(line)),
                    },
                },
            }

            # Add end line if available
            end_line = finding.get("end_line")
            if end_line:
                location["physicalLocation"]["region"]["endLine"] = int(end_line)

            # Add column if available
            column = finding.get("column")
            if column:
                location["physicalLocation"]["region"]["startColumn"] = int(column)

            # Add code snippet if available
            snippet = finding.get("code_snippet", finding.get("vulnerable_code"))
            if snippet:
                location["physicalLocation"]["region"]["snippet"] = {"text": snippet}

            locations.append(location)

        # Additional affected locations
        for affected in finding.get("affected_locations", []):
            if isinstance(affected, dict):
                loc: dict[str, Any] = {
                    "physicalLocation": {
                        "artifactLocation": {
                            "uri": affected.get("file", "unknown"),
                            "uriBaseId": "%SRCROOT%",
                        },
                        "region": {
                            "startLine": max(1, int(affected.get("line", 1))),
                        },
                    },
                }
                locations.append(loc)

        return locations

    def _build_code_flows(self, finding: dict[str, Any]) -> list[dict[str, Any]]:
        """Build SARIF code flows from attack/reproduction steps."""
        steps = finding.get("attack_steps") or finding.get("reproduction_steps") or []
        if not steps:
            return []

        thread_flow_locations = []
        for i, step in enumerate(steps):
            if isinstance(step, str):
                location: dict[str, Any] = {
                    "location": {
                        "message": {"text": step},
                    },
                    "nestingLevel": 0,
                    "executionOrder": i + 1,
                }
            else:
                location = {
                    "location": {
                        "message": {"text": step.get("description", str(step))},
                    },
                    "nestingLevel": step.get("level", 0),
                    "executionOrder": i + 1,
                }
                if step.get("file"):
                    location["location"]["physicalLocation"] = {
                        "artifactLocation": {"uri": step["file"]},
                        "region": {"startLine": step.get("line", 1)},
                    }

            thread_flow_locations.append(location)

        return [{"threadFlows": [{"locations": thread_flow_locations}]}]
