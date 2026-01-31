# Extending Formatters

Create custom output formatters for specialised reporting needs.

## Overview

Formatters transform the results bundle into various output formats. Creating a custom formatter allows you to:
- Generate reports for specific tools or platforms
- Create custom visualisations
- Integrate with internal systems
- Export to specialised formats

## The Formatter Interface

All formatters implement a simple interface:

```python
from abc import ABC, abstractmethod
from typing import Any


class Formatter(ABC):
    @abstractmethod
    def format(self, bundle: dict[str, Any]) -> str:
        """Transform the results bundle into a formatted string."""
        ...

    @property
    def file_extension(self) -> str:
        """Suggested file extension for output."""
        return ".txt"
```

## The Results Bundle

Formatters receive the canonical bundle structure:

```python
bundle = {
    "metadata": {
        "run_id": "run-20240115-143022",
        "target": "src/",
        "provider": "anthropic",
        "started_at": "2024-01-15T14:30:22Z",
        "finished_at": "2024-01-15T14:32:45Z",
        "files_analyzed": ["src/api/users.py"],
        "version": "0.1.0",
    },
    "summary": {
        "verdict": "BLOCK",
        "total_findings": 5,
        "by_severity": {
            "CRITICAL": 1,
            "HIGH": 2,
            "MEDIUM": 1,
            "LOW": 1,
        },
        "should_block": True,
    },
    "findings": [...],
    "verdict": {...},
    "attack_plan": {...},
}
```

## Creating a Custom Formatter

Let's create a formatter that outputs findings in CSV format.

### Step 1: Implement the Formatter

```python
# src/adversarial_debate/formatters/csv_formatter.py

import csv
import io
from typing import Any

from adversarial_debate.formatters.base import Formatter


class CSVFormatter(Formatter):
    """Exports findings as CSV for spreadsheet analysis."""

    @property
    def file_extension(self) -> str:
        return ".csv"

    def format(self, bundle: dict[str, Any]) -> str:
        output = io.StringIO()
        writer = csv.writer(output)

        # Write header
        writer.writerow([
            "Finding ID",
            "Title",
            "Severity",
            "Agent",
            "File",
            "Line",
            "Category",
            "Confidence",
            "Remediation",
        ])

        # Write findings
        for finding in bundle.get("findings", []):
            location = finding.get("location", {})
            writer.writerow([
                finding.get("finding_id", ""),
                finding.get("title", ""),
                finding.get("severity", ""),
                finding.get("agent", ""),
                location.get("file", ""),
                location.get("line", ""),
                finding.get("owasp_category", finding.get("category", "")),
                finding.get("confidence", ""),
                finding.get("remediation", "")[:200],  # Truncate
            ])

        return output.getvalue()
```

### Step 2: Create a JUnit XML Formatter

For CI/CD test results integration:

```python
# src/adversarial_debate/formatters/junit.py

from typing import Any
from xml.etree import ElementTree as ET

from adversarial_debate.formatters.base import Formatter


class JUnitFormatter(Formatter):
    """Exports findings as JUnit XML for CI integration."""

    @property
    def file_extension(self) -> str:
        return ".xml"

    def format(self, bundle: dict[str, Any]) -> str:
        findings = bundle.get("findings", [])
        metadata = bundle.get("metadata", {})

        # Create test suite
        testsuite = ET.Element("testsuite")
        testsuite.set("name", "Security Analysis")
        testsuite.set("tests", str(len(findings)))

        # Count failures
        failures = sum(
            1 for f in findings
            if f.get("severity") in ["CRITICAL", "HIGH"]
        )
        testsuite.set("failures", str(failures))
        testsuite.set("time", self._calculate_duration(metadata))

        # Add test cases
        for finding in findings:
            testcase = ET.SubElement(testsuite, "testcase")
            testcase.set("name", finding.get("title", "Unknown"))
            testcase.set("classname", finding.get("agent", "Unknown"))

            location = finding.get("location", {})
            testcase.set("file", location.get("file", ""))

            # Mark as failure if high severity
            severity = finding.get("severity", "MEDIUM")
            if severity in ["CRITICAL", "HIGH"]:
                failure = ET.SubElement(testcase, "failure")
                failure.set("message", finding.get("title", ""))
                failure.set("type", severity)
                failure.text = self._format_failure_details(finding)

        # Serialise
        return ET.tostring(testsuite, encoding="unicode", xml_declaration=True)

    def _calculate_duration(self, metadata: dict) -> str:
        # Calculate duration from timestamps if available
        return "0"

    def _format_failure_details(self, finding: dict) -> str:
        parts = [
            f"Severity: {finding.get('severity')}",
            f"Description: {finding.get('description', '')}",
            f"Location: {finding.get('location', {})}",
            f"Remediation: {finding.get('remediation', '')}",
        ]
        return "\n".join(parts)
```

### Step 3: Create a Jira Import Formatter

For importing issues into Jira:

```python
# src/adversarial_debate/formatters/jira.py

import json
from typing import Any

from adversarial_debate.formatters.base import Formatter


class JiraFormatter(Formatter):
    """Exports findings as Jira-importable JSON."""

    SEVERITY_TO_PRIORITY = {
        "CRITICAL": "Highest",
        "HIGH": "High",
        "MEDIUM": "Medium",
        "LOW": "Low",
        "INFO": "Lowest",
    }

    @property
    def file_extension(self) -> str:
        return ".json"

    def format(self, bundle: dict[str, Any]) -> str:
        issues = []

        for finding in bundle.get("findings", []):
            severity = finding.get("severity", "MEDIUM")
            location = finding.get("location", {})

            issue = {
                "fields": {
                    "project": {"key": "SEC"},  # Configure as needed
                    "issuetype": {"name": "Bug"},
                    "priority": {"name": self.SEVERITY_TO_PRIORITY.get(severity, "Medium")},
                    "summary": finding.get("title", "Security Finding"),
                    "description": self._format_description(finding),
                    "labels": [
                        "security",
                        "automated",
                        finding.get("agent", "").lower(),
                    ],
                    "components": [{"name": "Security"}],
                    "customfield_10001": finding.get("owasp_category", ""),  # Custom field
                }
            }
            issues.append(issue)

        return json.dumps({"issues": issues}, indent=2)

    def _format_description(self, finding: dict) -> str:
        location = finding.get("location", {})
        parts = [
            f"*Severity:* {finding.get('severity')}",
            f"*Agent:* {finding.get('agent')}",
            "",
            "*Description:*",
            finding.get("description", ""),
            "",
            "*Location:*",
            f"File: {location.get('file', 'Unknown')}",
            f"Line: {location.get('line', 'Unknown')}",
            "",
            "*Remediation:*",
            finding.get("remediation", ""),
        ]

        if poc := finding.get("proof_of_concept"):
            parts.extend(["", "*Proof of Concept:*", f"{{code}}{poc}{{code}}"])

        return "\n".join(parts)
```

### Step 4: Register Formatters

```python
# src/adversarial_debate/formatters/__init__.py

from .base import Formatter
from .json import JSONFormatter
from .sarif import SARIFFormatter
from .html import HTMLFormatter
from .markdown import MarkdownFormatter
from .csv_formatter import CSVFormatter
from .junit import JUnitFormatter
from .jira import JiraFormatter

FORMATTERS = {
    "json": JSONFormatter,
    "sarif": SARIFFormatter,
    "html": HTMLFormatter,
    "markdown": MarkdownFormatter,
    "csv": CSVFormatter,
    "junit": JUnitFormatter,
    "jira": JiraFormatter,
}


def get_formatter(name: str) -> Formatter:
    if name not in FORMATTERS:
        raise ValueError(f"Unknown formatter: {name}")
    return FORMATTERS[name]()
```

### Step 5: Add CLI Support

```python
# In cli_commands.py

FORMAT_CHOICES = ["json", "sarif", "html", "markdown", "csv", "junit", "jira"]

parser.add_argument(
    "--format",
    choices=FORMAT_CHOICES,
    default="json",
    help="Output format",
)
```

## Testing Formatters

```python
# tests/unit/test_formatters/test_csv_formatter.py

import pytest
from adversarial_debate.formatters import CSVFormatter


@pytest.fixture
def sample_bundle():
    return {
        "metadata": {"run_id": "test-001"},
        "summary": {"verdict": "WARN", "total_findings": 1},
        "findings": [
            {
                "finding_id": "EXP-001",
                "title": "SQL Injection",
                "severity": "CRITICAL",
                "agent": "ExploitAgent",
                "location": {"file": "app.py", "line": 42},
                "owasp_category": "A03:2021",
                "confidence": 0.95,
                "remediation": "Use parameterised queries",
            }
        ],
    }


def test_csv_output(sample_bundle):
    formatter = CSVFormatter()
    output = formatter.format(sample_bundle)

    assert "Finding ID" in output  # Header
    assert "EXP-001" in output
    assert "SQL Injection" in output
    assert "CRITICAL" in output
    assert "app.py" in output
    assert "42" in output


def test_file_extension():
    formatter = CSVFormatter()
    assert formatter.file_extension == ".csv"
```

## Advanced Patterns

### Template-Based Formatters

For complex HTML or text templates:

```python
from jinja2 import Environment, PackageLoader


class TemplateFormatter(Formatter):
    def __init__(self):
        self.env = Environment(
            loader=PackageLoader("adversarial_debate", "templates")
        )

    def format(self, bundle: dict[str, Any]) -> str:
        template = self.env.get_template("report.html.j2")
        return template.render(bundle=bundle)
```

### Configurable Formatters

Support custom configuration:

```python
class ConfigurableFormatter(Formatter):
    def __init__(
        self,
        include_remediation: bool = True,
        max_findings: int | None = None,
        severity_filter: list[str] | None = None,
    ):
        self.include_remediation = include_remediation
        self.max_findings = max_findings
        self.severity_filter = severity_filter

    def format(self, bundle: dict[str, Any]) -> str:
        findings = bundle.get("findings", [])

        # Apply filters
        if self.severity_filter:
            findings = [
                f for f in findings
                if f.get("severity") in self.severity_filter
            ]

        if self.max_findings:
            findings = findings[:self.max_findings]

        # Format...
```

### Async Formatters

For formatters that need to fetch additional data:

```python
class AsyncFormatter(Formatter):
    async def format_async(self, bundle: dict[str, Any]) -> str:
        # Fetch additional data
        enriched = await self._enrich_findings(bundle)
        return self._render(enriched)

    def format(self, bundle: dict[str, Any]) -> str:
        # Sync wrapper
        import asyncio
        return asyncio.run(self.format_async(bundle))
```

## Best Practices

### 1. Handle Missing Data

```python
def format(self, bundle: dict[str, Any]) -> str:
    findings = bundle.get("findings", [])
    metadata = bundle.get("metadata", {})

    # Use .get() with defaults
    run_id = metadata.get("run_id", "unknown")
    verdict = bundle.get("summary", {}).get("verdict", "UNKNOWN")
```

### 2. Escape Output

```python
import html

def _escape_html(self, text: str) -> str:
    return html.escape(text)

def _format_finding(self, finding: dict) -> str:
    return f"<p>{self._escape_html(finding.get('title', ''))}</p>"
```

### 3. Support Streaming

For large reports:

```python
def format_stream(self, bundle: dict[str, Any]):
    """Yield formatted chunks."""
    yield self._format_header(bundle)
    for finding in bundle.get("findings", []):
        yield self._format_finding(finding)
    yield self._format_footer(bundle)
```

### 4. Validate Output

```python
def format(self, bundle: dict[str, Any]) -> str:
    output = self._generate_output(bundle)

    # Validate
    if self.file_extension == ".json":
        json.loads(output)  # Validate JSON
    elif self.file_extension == ".xml":
        ET.fromstring(output)  # Validate XML

    return output
```

## See Also

- [Output Formats](../guides/output-formats.md) — Built-in formatters
- [Python API Guide](python-api.md) — Using formatters
- [CI/CD Integration](../integration/ci-cd.md) — Using outputs in pipelines
