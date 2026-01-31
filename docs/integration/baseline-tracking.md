# Baseline Tracking

Track security findings over time, detect regressions, and manage known issues.

## Overview

Baseline tracking allows you to:
- Detect **new issues** introduced by code changes
- Identify **regressions** when fixed issues reappear
- Suppress **known issues** you've accepted or are tracking
- Track **trends** in security posture over time

## How It Works

```
Previous Run             Current Run              Comparison
┌─────────────┐         ┌─────────────┐         ┌─────────────────────┐
│ bundle.json │    +    │ New Results │    =    │ New/Fixed/Unchanged │
│ (baseline)  │         │             │         │ Issues              │
└─────────────┘         └─────────────┘         └─────────────────────┘
```

The framework compares current findings against a baseline to categorise:
- **New findings** — Not in baseline (potential regressions)
- **Fixed findings** — In baseline but not current (resolved issues)
- **Unchanged findings** — In both (ongoing issues)

## Creating a Baseline

Run an analysis and save the bundle:

```bash
# Run full analysis
adversarial-debate run src/ --output baseline-run/

# The bundle.json is your baseline
ls baseline-run/run-*/bundle.json
```

For CI, store the baseline as an artefact:

```yaml
- name: Upload baseline
  uses: actions/upload-artifact@v4
  with:
    name: security-baseline
    path: baseline-run/run-*/bundle.json
```

## Using a Baseline

Compare against a baseline:

```bash
adversarial-debate run src/ --baseline previous-bundle.json
```

Output shows the comparison:

```
============================================================
COMPARISON AGAINST BASELINE
============================================================

NEW ISSUES (2):
  [HIGH] SQL injection in new endpoint (EXP-003)
  [MEDIUM] Missing rate limiting (EXP-004)

FIXED ISSUES (1):
  [HIGH] Hardcoded credentials (EXP-001)

UNCHANGED ISSUES (3):
  [CRITICAL] SQL injection in user lookup (EXP-001)
  [MEDIUM] Missing CSRF token (EXP-002)
  [LOW] Verbose error messages (BRK-001)
```

## Fail on New Issues Only

Configure the pipeline to only fail on new issues:

```bash
adversarial-debate run src/ \
  --baseline previous-bundle.json \
  --fail-on-new-only
```

This allows:
- New critical/high issues → Fail
- Existing issues (in baseline) → Pass
- Fixed issues → Pass

## CI/CD Integration

### GitHub Actions

```yaml
jobs:
  security:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Download previous baseline
        uses: actions/download-artifact@v4
        continue-on-error: true
        with:
          name: security-baseline
          path: baseline/

      - name: Run security analysis
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
        run: |
          if [ -f baseline/bundle.json ]; then
            adversarial-debate run src/ \
              --baseline baseline/bundle.json \
              --fail-on-new-only \
              --output current-run/
          else
            adversarial-debate run src/ --output current-run/
          fi

      - name: Upload new baseline
        uses: actions/upload-artifact@v4
        if: github.ref == 'refs/heads/main'
        with:
          name: security-baseline
          path: current-run/run-*/bundle.json
          retention-days: 90
```

### Branch-Specific Baselines

Use different baselines for different branches:

```yaml
- name: Download baseline
  uses: actions/download-artifact@v4
  continue-on-error: true
  with:
    name: security-baseline-${{ github.base_ref }}
    path: baseline/
```

## Managing Known Issues

### Accepting Findings

For findings you've reviewed and accepted:

1. Create a suppression file:

```json
// .adversarial-suppress.json
{
  "suppressions": [
    {
      "finding_id": "EXP-001",
      "reason": "Accepted risk: internal admin endpoint only",
      "expires": "2024-06-01"
    },
    {
      "pattern": "Missing CSRF.*admin",
      "reason": "Admin endpoints use different auth mechanism"
    }
  ]
}
```

2. Use it in analysis:

```bash
adversarial-debate run src/ --suppress .adversarial-suppress.json
```

### Suppression File Format

```json
{
  "suppressions": [
    {
      "finding_id": "EXP-001",      // Exact finding ID match
      "reason": "Accepted risk",    // Documentation
      "expires": "2024-06-01"       // Optional expiry
    },
    {
      "pattern": "SQL injection",   // Regex pattern on title
      "file_pattern": "tests/*",    // Regex pattern on file path
      "reason": "Test code only"
    }
  ]
}
```

## Tracking Trends

### Generating Reports

Track security posture over time:

```bash
# Store historical data
adversarial-debate run src/ --output security-history/$(date +%Y-%m-%d)/
```

### Metrics Dashboard

Extract metrics from bundle files:

```python
import json
from pathlib import Path
from collections import Counter

def extract_metrics(bundle_path: Path) -> dict:
    bundle = json.loads(bundle_path.read_text())
    return {
        "date": bundle["metadata"]["finished_at"][:10],
        "verdict": bundle["summary"]["verdict"],
        "total_findings": bundle["summary"]["total_findings"],
        "by_severity": bundle["summary"]["by_severity"],
    }

# Collect metrics from all runs
history = Path("security-history")
metrics = [extract_metrics(p) for p in history.glob("*/bundle.json")]

# Analyse trends
print(f"Runs: {len(metrics)}")
print(f"Verdicts: {Counter(m['verdict'] for m in metrics)}")
```

## Baseline Schema

The baseline uses the same format as `bundle.json`:

```json
{
  "metadata": {
    "run_id": "run-20240115-143022",
    "target": "src/",
    "finished_at": "2024-01-15T14:32:45Z"
  },
  "summary": {
    "verdict": "WARN",
    "total_findings": 5
  },
  "findings": [
    {
      "finding_id": "EXP-001",
      "title": "SQL injection",
      "location": {"file": "src/api/users.py", "line": 42},
      "fingerprint": "sha256:abc123..."  // For stable matching
    }
  ]
}
```

## Finding Matching

Findings are matched between baseline and current run using:

1. **Fingerprint** — Hash of code location and finding type
2. **Finding ID** — If fingerprints don't match
3. **Location + Title** — Fallback matching

This handles:
- Code moves (same fingerprint, different line)
- Renamed files (similar fingerprint)
- Refactored code (may create new finding)

## Best Practices

### 1. Update Baseline on Main

Only update the baseline when merging to main:

```yaml
if: github.ref == 'refs/heads/main'
```

### 2. Set Baseline Retention

Don't keep baselines forever:

```yaml
retention-days: 90
```

### 3. Document Suppressions

Always include a reason for suppressions:

```json
{
  "finding_id": "EXP-001",
  "reason": "Tracked in JIRA-1234, fix scheduled for Q2"
}
```

### 4. Review Regularly

Periodically review:
- Accepted suppressions
- Fixed issues that could regress
- Trends in finding counts

### 5. Separate Baselines by Environment

Different baselines for:
- Development branches
- Staging
- Production

## Troubleshooting

### "All findings appear as new"

Check:
- Baseline file path is correct
- Baseline format is valid JSON
- Files haven't been significantly refactored

### "Fixed issues keep reappearing"

The code may have similar but not identical vulnerabilities. Check:
- Line numbers
- Function names
- The actual vulnerability details

### "Baseline is too large"

Archive old baselines and only keep recent ones:

```bash
# Keep only last 30 days
find security-history -mtime +30 -delete
```

## See Also

- [CI/CD Integration](ci-cd.md) — Pipeline setup
- [Output Formats](../guides/output-formats.md) — Bundle format details
- [Interpreting Results](../guides/interpreting-results.md) — Understanding findings
