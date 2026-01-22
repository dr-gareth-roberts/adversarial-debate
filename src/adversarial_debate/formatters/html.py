"""HTML output formatter for human-readable reports."""

from datetime import UTC, datetime
from html import escape
from typing import Any

from .base import Formatter, FormatterConfig, OutputFormat


# Severity colors for visual distinction
SEVERITY_COLORS = {
    "CRITICAL": "#d32f2f",
    "HIGH": "#f57c00",
    "MEDIUM": "#fbc02d",
    "LOW": "#388e3c",
    "INFO": "#1976d2",
}

# Verdict decision colors
VERDICT_COLORS = {
    "BLOCK": "#d32f2f",
    "WARN": "#f57c00",
    "PASS": "#388e3c",
}


class HTMLFormatter(Formatter):
    """HTML output formatter.

    Produces a self-contained HTML report suitable for viewing
    in a browser or embedding in documentation.
    """

    def __init__(self, config: FormatterConfig | None = None):
        super().__init__(config)

    @property
    def format_type(self) -> OutputFormat:
        return OutputFormat.HTML

    @property
    def file_extension(self) -> str:
        return ".html"

    @property
    def content_type(self) -> str:
        return "text/html"

    def format(self, data: dict[str, Any]) -> str:
        """Format data as HTML.

        Args:
            data: Analysis results

        Returns:
            HTML string
        """
        findings = data.get("findings", [])
        verdict = data.get("verdict", {})
        metadata = data.get("metadata", {})

        html_parts = [
            self._html_header(),
            self._html_summary(findings, verdict, metadata),
        ]

        if verdict:
            html_parts.append(self._html_verdict(verdict))

        if findings:
            html_parts.append(self._html_findings(findings))

        html_parts.append(self._html_footer())

        return "\n".join(html_parts)

    def _html_header(self) -> str:
        """Generate HTML header with embedded styles."""
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Security Analysis Report - {self.config.tool_name}</title>
    <style>
        :root {{
            --bg-primary: #1a1a2e;
            --bg-secondary: #16213e;
            --text-primary: #eee;
            --text-secondary: #aaa;
            --border-color: #333;
            --accent: #0f3460;
        }}
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: var(--bg-primary);
            color: var(--text-primary);
            line-height: 1.6;
            padding: 2rem;
        }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        header {{
            text-align: center;
            padding: 2rem;
            border-bottom: 1px solid var(--border-color);
            margin-bottom: 2rem;
        }}
        h1 {{ font-size: 2rem; margin-bottom: 0.5rem; }}
        h2 {{ font-size: 1.5rem; margin: 1.5rem 0 1rem; border-bottom: 1px solid var(--border-color); padding-bottom: 0.5rem; }}
        h3 {{ font-size: 1.2rem; margin: 1rem 0 0.5rem; }}
        .meta {{ color: var(--text-secondary); font-size: 0.9rem; }}
        .summary {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 1rem;
            margin: 1.5rem 0;
        }}
        .stat {{
            background: var(--bg-secondary);
            padding: 1rem;
            border-radius: 8px;
            text-align: center;
        }}
        .stat-value {{ font-size: 2rem; font-weight: bold; }}
        .stat-label {{ color: var(--text-secondary); font-size: 0.85rem; }}
        .verdict {{
            padding: 1.5rem;
            border-radius: 8px;
            margin: 1.5rem 0;
            text-align: center;
        }}
        .verdict-decision {{ font-size: 2rem; font-weight: bold; }}
        .finding {{
            background: var(--bg-secondary);
            border-radius: 8px;
            padding: 1.5rem;
            margin: 1rem 0;
            border-left: 4px solid var(--accent);
        }}
        .finding-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 1rem;
        }}
        .severity {{
            padding: 0.25rem 0.75rem;
            border-radius: 4px;
            font-size: 0.8rem;
            font-weight: bold;
            color: white;
        }}
        .finding-meta {{ color: var(--text-secondary); font-size: 0.85rem; }}
        .finding-description {{ margin: 1rem 0; }}
        .code-snippet {{
            background: #0d1117;
            padding: 1rem;
            border-radius: 4px;
            font-family: 'Monaco', 'Menlo', monospace;
            font-size: 0.9rem;
            overflow-x: auto;
            white-space: pre-wrap;
            word-break: break-word;
        }}
        .remediation {{
            background: rgba(56, 142, 60, 0.1);
            border-left: 3px solid #388e3c;
            padding: 1rem;
            margin-top: 1rem;
            border-radius: 0 4px 4px 0;
        }}
        .tags {{ display: flex; gap: 0.5rem; flex-wrap: wrap; margin-top: 0.5rem; }}
        .tag {{
            background: var(--accent);
            padding: 0.2rem 0.5rem;
            border-radius: 4px;
            font-size: 0.75rem;
        }}
        footer {{
            text-align: center;
            padding: 2rem;
            color: var(--text-secondary);
            border-top: 1px solid var(--border-color);
            margin-top: 2rem;
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🛡️ Security Analysis Report</h1>
            <p class="meta">Generated by {escape(self.config.tool_name)} v{escape(self.config.tool_version)}</p>
            <p class="meta">{datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S UTC')}</p>
        </header>
"""

    def _html_summary(
        self, findings: list[dict[str, Any]], verdict: dict[str, Any], metadata: dict[str, Any]
    ) -> str:
        """Generate summary section."""
        # Count by severity
        severity_counts: dict[str, int] = {}
        for finding in findings:
            sev = finding.get("severity", "UNKNOWN")
            severity_counts[sev] = severity_counts.get(sev, 0) + 1

        summary_html = '<section id="summary"><h2>Summary</h2><div class="summary">'

        # Total findings
        summary_html += f"""
            <div class="stat">
                <div class="stat-value">{len(findings)}</div>
                <div class="stat-label">Total Findings</div>
            </div>
        """

        # By severity
        for sev in ["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"]:
            count = severity_counts.get(sev, 0)
            if count > 0:
                color = SEVERITY_COLORS.get(sev, "#666")
                summary_html += f"""
                    <div class="stat">
                        <div class="stat-value" style="color: {color}">{count}</div>
                        <div class="stat-label">{sev}</div>
                    </div>
                """

        summary_html += "</div></section>"
        return summary_html

    def _html_verdict(self, verdict: dict[str, Any]) -> str:
        """Generate verdict section."""
        summary = verdict.get("summary", verdict)
        decision = summary.get("decision", "UNKNOWN")
        color = VERDICT_COLORS.get(decision, "#666")

        verdict_html = f"""
        <section id="verdict">
            <h2>Verdict</h2>
            <div class="verdict" style="background: {color}20; border: 2px solid {color}">
                <div class="verdict-decision" style="color: {color}">{escape(decision)}</div>
        """

        if summary.get("blocking_issues"):
            verdict_html += f'<p>Blocking Issues: {summary["blocking_issues"]}</p>'
        if summary.get("warnings"):
            verdict_html += f'<p>Warnings: {summary["warnings"]}</p>'
        if summary.get("report"):
            verdict_html += f'<p style="text-align: left; margin-top: 1rem;">{escape(str(summary["report"]))}</p>'

        verdict_html += "</div></section>"
        return verdict_html

    def _html_findings(self, findings: list[dict[str, Any]]) -> str:
        """Generate findings section."""
        # Sort by severity
        severity_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3, "INFO": 4}
        sorted_findings = sorted(
            findings,
            key=lambda f: severity_order.get(f.get("severity", "MEDIUM"), 5)
        )

        findings_html = '<section id="findings"><h2>Findings</h2>'

        for i, finding in enumerate(sorted_findings, 1):
            findings_html += self._html_finding(finding, i)

        findings_html += "</section>"
        return findings_html

    def _html_finding(self, finding: dict[str, Any], index: int) -> str:
        """Generate HTML for a single finding."""
        severity = finding.get("severity", "MEDIUM")
        color = SEVERITY_COLORS.get(severity, "#666")
        title = escape(finding.get("title", f"Finding #{index}"))
        description = escape(finding.get("description", ""))

        html = f"""
        <div class="finding" style="border-left-color: {color}">
            <div class="finding-header">
                <h3>{title}</h3>
                <span class="severity" style="background: {color}">{severity}</span>
            </div>
            <div class="finding-meta">
        """

        # Add metadata
        if finding.get("file_path"):
            html += f'<span>📄 {escape(str(finding["file_path"]))}'
            if finding.get("line"):
                html += f':{finding["line"]}'
            html += "</span> "

        if finding.get("agent"):
            html += f'<span>🤖 {escape(str(finding["agent"]))}</span> '

        if finding.get("confidence"):
            html += f'<span>🎯 {finding["confidence"]:.0%} confidence</span>'

        html += "</div>"

        # Description
        if description:
            html += f'<div class="finding-description">{description}</div>'

        # Code snippet
        code = finding.get("code_snippet") or finding.get("vulnerable_code")
        if code:
            html += f'<div class="code-snippet">{escape(str(code))}</div>'

        # Remediation
        remediation = finding.get("remediation")
        if remediation:
            html += f'<div class="remediation"><strong>💡 Remediation:</strong> {escape(str(remediation))}</div>'

        # Tags
        tags = []
        if finding.get("cwe"):
            tags.append(f"CWE-{finding['cwe']}")
        if finding.get("category"):
            tags.append(finding["category"])
        if finding.get("finding_type"):
            tags.append(finding["finding_type"])

        if tags:
            html += '<div class="tags">'
            for tag in tags:
                html += f'<span class="tag">{escape(str(tag))}</span>'
            html += "</div>"

        html += "</div>"
        return html

    def _html_footer(self) -> str:
        """Generate HTML footer."""
        return f"""
        <footer>
            <p>Generated by <strong>{escape(self.config.tool_name)}</strong> v{escape(self.config.tool_version)}</p>
            <p>AI Red Team Security Testing Framework</p>
        </footer>
    </div>
</body>
</html>
"""
