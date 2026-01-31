# Output Formats

Adversarial Debate produces results in multiple formats for different use cases: JSON for programmatic access, SARIF for IDE integration, HTML for sharing, and Markdown for documentation.

## Available Formats

| Format | Use Case | File Extension |
|--------|----------|----------------|
| [JSON](#json) | Programmatic access, CI/CD | `.json` |
| [SARIF](#sarif) | IDE integration, GitHub | `.sarif` |
| [HTML](#html) | Sharing, reports | `.html` |
| [Markdown](#markdown) | Documentation, Git | `.md` |

## Specifying Output Format

```bash
# Generate SARIF report
adversarial-debate run src/ --format sarif --report-file findings.sarif

# Generate HTML report
adversarial-debate run src/ --format html --report-file report.html

# Generate Markdown report
adversarial-debate run src/ --format markdown --report-file SECURITY.md
```

The raw JSON outputs are always generated in the output directory regardless of the report format.

## JSON

JSON is the default format, providing complete structured data for programmatic access.

### Output Files

When running `adversarial-debate run`, these JSON files are created:

| File | Description |
|------|-------------|
| `attack_plan.json` | Orchestrator's attack strategy |
| `exploit_findings.json` | Security vulnerability findings |
| `break_findings.json` | Logic bug findings |
| `chaos_findings.json` | Resilience experiment findings |
| `crypto_findings.json` | Cryptographic weakness findings |
| `findings.json` | All findings combined |
| `verdict.json` | Arbiter verdict and remediation |
| `bundle.json` | Canonical results bundle |

### Bundle Format

The `bundle.json` file is the canonical representation of all results:

```json
{
  "metadata": {
    "run_id": "run-20240115-143022",
    "target": "src/",
    "provider": "anthropic",
    "started_at": "2024-01-15T14:30:22Z",
    "finished_at": "2024-01-15T14:32:45Z",
    "files_analysed": ["src/api/users.py", "src/api/auth.py"],
    "version": "0.1.0"
  },
  "summary": {
    "verdict": "BLOCK",
    "total_findings": 5,
    "by_severity": {
      "CRITICAL": 1,
      "HIGH": 2,
      "MEDIUM": 1,
      "LOW": 1
    },
    "should_block": true
  },
  "findings": [...],
  "verdict": {...},
  "attack_plan": {...}
}
```

### Using JSON in Scripts

```python
import json
from pathlib import Path

# Load the bundle
bundle = json.loads(Path("output/run-123/bundle.json").read_text())

# Check the verdict
if bundle["summary"]["should_block"]:
    print("Security issues found!")
    for finding in bundle["findings"]:
        if finding["severity"] in ["CRITICAL", "HIGH"]:
            print(f"  [{finding['severity']}] {finding['title']}")
```

## SARIF

SARIF (Static Analysis Results Interchange Format) is a standard format supported by GitHub, VS Code, and other tools.

### Generating SARIF

```bash
adversarial-debate run src/ --format sarif --report-file findings.sarif
```

### SARIF Structure

```json
{
  "$schema": "https://raw.githubusercontent.com/oasis-tcs/sarif-spec/master/Schemata/sarif-schema-2.1.0.json",
  "version": "2.1.0",
  "runs": [
    {
      "tool": {
        "driver": {
          "name": "adversarial-debate",
          "version": "0.1.0",
          "rules": [...]
        }
      },
      "results": [
        {
          "ruleId": "EXP-001",
          "level": "error",
          "message": {
            "text": "SQL injection in user lookup"
          },
          "locations": [
            {
              "physicalLocation": {
                "artifactLocation": {
                  "uri": "src/api/users.py"
                },
                "region": {
                  "startLine": 42,
                  "startColumn": 1
                }
              }
            }
          ]
        }
      ]
    }
  ]
}
```

### GitHub Integration

SARIF files can be uploaded to GitHub Code Scanning:

```yaml
# .github/workflows/security.yml
- name: Run security analysis
  run: adversarial-debate run src/ --format sarif --report-file results.sarif

- name: Upload SARIF
  uses: github/codeql-action/upload-sarif@v3
  with:
    sarif_file: results.sarif
```

Findings appear in the Security tab of your repository.

### VS Code Integration

1. Install the SARIF Viewer extension
2. Open the `.sarif` file
3. Navigate findings directly in the editor

## HTML

HTML reports are self-contained files for sharing and review.

### Generating HTML

```bash
adversarial-debate run src/ --format html --report-file report.html
```

### Features

The HTML report includes:
- Executive summary with verdict
- Severity breakdown chart
- Detailed finding cards
- Remediation guidance
- Expandable code snippets
- Print-friendly styling

### Example Usage

```bash
# Generate and open in browser
adversarial-debate run src/ --format html --report-file report.html
open report.html  # macOS
xdg-open report.html  # Linux
```

### Customisation

The HTML template can be customised by providing your own:

```json
{
  "output": {
    "html_template": "./custom-template.html"
  }
}
```

## Markdown

Markdown reports are ideal for documentation and Git repositories.

### Generating Markdown

```bash
adversarial-debate run src/ --format markdown --report-file SECURITY.md
```

### Markdown Structure

```markdown
# Security Analysis Report

**Verdict:** BLOCK
**Date:** 2024-01-15
**Target:** src/

## Summary

| Severity | Count |
|----------|-------|
| Critical | 1 |
| High | 2 |
| Medium | 1 |

## Blocking Issues

### [CRITICAL] SQL injection in user lookup

**File:** `src/api/users.py:42`
**Category:** A03:2021 Injection
**CWE:** CWE-89

#### Description

User input is directly concatenated into SQL query...

#### Remediation

Use parameterised queries:

```python
cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
```

## Warnings

...
```

### Git Integration

Generate reports for pull requests:

```bash
adversarial-debate run src/ --format markdown --report-file pr-security.md
gh pr comment 123 --body-file pr-security.md
```

## Combining Formats

You can generate multiple formats in a single run:

```bash
# Generate all formats
adversarial-debate run src/ --output results/

# JSON files are always generated
# Then generate additional formats:
adversarial-debate run src/ --format sarif --report-file results/findings.sarif
adversarial-debate run src/ --format html --report-file results/report.html
adversarial-debate run src/ --format markdown --report-file results/SECURITY.md
```

## Format Comparison

| Aspect | JSON | SARIF | HTML | Markdown |
|--------|------|-------|------|----------|
| Machine-readable | ✓ | ✓ | — | — |
| Human-readable | — | — | ✓ | ✓ |
| IDE integration | — | ✓ | — | — |
| GitHub integration | — | ✓ | — | ✓ |
| Shareable | — | — | ✓ | ✓ |
| Version control | — | — | — | ✓ |

## Custom Formatters

You can create custom formatters for specialised output needs. See [Extending Formatters](../developers/extending-formatters.md).

## See Also

- [CLI Reference](cli-reference.md) — Output options
- [CI/CD Integration](../integration/ci-cd.md) — Using outputs in pipelines
- [Interpreting Results](interpreting-results.md) — Understanding findings
