# CI/CD Integration

Integrate Adversarial Debate into your continuous integration and deployment pipelines for automated security analysis.

## Overview

The framework supports multiple integration patterns:

| Pattern | Use Case | Speed | Coverage |
|---------|----------|-------|----------|
| [Pull Request Analysis](#pull-request-analysis) | PR security gates | Medium | Changed files |
| [Scheduled Scans](#scheduled-scans) | Regular full scans | Slow | Full codebase |
| [Pre-commit Hooks](#pre-commit-hooks) | Developer feedback | Fast | Staged files |
| [Smoke Tests](#smoke-tests) | CI verification | Instant | Mock provider |

## GitHub Actions

### Pull Request Analysis

Analyse code changes on every pull request:

```yaml
# .github/workflows/security.yml
name: Security Analysis

on:
  pull_request:
    branches: [main]
    paths:
      - '**.py'

jobs:
  security:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install adversarial-debate
        run: pip install adversarial-debate

      - name: Run security analysis
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
          LLM_PROVIDER: anthropic
        run: |
          adversarial-debate run src/ \
            --format sarif \
            --report-file results.sarif \
            --fail-on block

      - name: Upload SARIF results
        uses: github/codeql-action/upload-sarif@v3
        if: always()
        with:
          sarif_file: results.sarif

      - name: Comment on PR
        if: failure()
        uses: actions/github-script@v7
        with:
          script: |
            github.rest.issues.createComment({
              issue_number: context.issue.number,
              owner: context.repo.owner,
              repo: context.repo.repo,
              body: '⚠️ Security analysis found blocking issues. Please review the findings in the Security tab.'
            })
```

### Scheduled Full Scans

Run comprehensive scans on a schedule:

```yaml
# .github/workflows/security-scan.yml
name: Scheduled Security Scan

on:
  schedule:
    - cron: '0 2 * * 1'  # Every Monday at 2 AM
  workflow_dispatch:  # Allow manual triggers

jobs:
  full-scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install adversarial-debate
        run: pip install adversarial-debate

      - name: Run full security scan
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
        run: |
          adversarial-debate run src/ \
            --output security-report/ \
            --format html \
            --report-file security-report/report.html \
            --time-budget 1800

      - name: Upload report
        uses: actions/upload-artifact@v4
        with:
          name: security-report
          path: security-report/

      - name: Create issue on failures
        if: failure()
        uses: actions/github-script@v7
        with:
          script: |
            github.rest.issues.create({
              owner: context.repo.owner,
              repo: context.repo.repo,
              title: 'Security Scan: Issues Found',
              body: 'The scheduled security scan found issues. See the workflow run for details.',
              labels: ['security', 'automated']
            })
```

### Using Baseline Comparison

Track regressions between scans:

```yaml
- name: Download previous baseline
  uses: actions/download-artifact@v4
  continue-on-error: true
  with:
    name: security-baseline
    path: baseline/

- name: Run security analysis with baseline
  run: |
    if [ -f baseline/bundle.json ]; then
      adversarial-debate run src/ \
        --baseline baseline/bundle.json \
        --fail-on block
    else
      adversarial-debate run src/ --fail-on block
    fi

- name: Upload new baseline
  uses: actions/upload-artifact@v4
  with:
    name: security-baseline
    path: output/*/bundle.json
```

## GitLab CI

### Basic Configuration

```yaml
# .gitlab-ci.yml
security-analysis:
  image: python:3.11
  stage: test
  script:
    - pip install adversarial-debate
    - adversarial-debate run src/ --format sarif --report-file results.sarif --fail-on block
  artifacts:
    reports:
      sast: results.sarif
    paths:
      - results.sarif
  rules:
    - if: $CI_PIPELINE_SOURCE == "merge_request_event"
```

### With Docker

```yaml
security-analysis:
  image: python:3.11
  stage: test
  services:
    - docker:dind
  variables:
    DOCKER_HOST: tcp://docker:2375
    ADVERSARIAL_SANDBOX_DOCKER: "true"
  script:
    - pip install adversarial-debate
    - adversarial-debate run src/ --fail-on block
```

## Jenkins

### Jenkinsfile

```groovy
pipeline {
    agent any

    environment {
        ANTHROPIC_API_KEY = credentials('anthropic-api-key')
    }

    stages {
        stage('Security Analysis') {
            steps {
                sh '''
                    pip install adversarial-debate
                    adversarial-debate run src/ \
                        --format sarif \
                        --report-file results.sarif \
                        --fail-on block
                '''
            }
            post {
                always {
                    recordIssues(
                        tools: [sarif(pattern: 'results.sarif')]
                    )
                }
            }
        }
    }
}
```

## Pre-commit Hooks

### Installation

```bash
pip install pre-commit
```

### Configuration

```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: adversarial-debate
        name: Security Analysis (Manual)
        entry: bash -lc 'adversarial-debate run . --files "$@" --skip-verdict --fail-on never --format markdown --report-file .security-check.md'
        language: system
        types: [python]
        stages: [manual]  # Only run when explicitly invoked
```

### Running

```bash
# Run on staged files
pre-commit run adversarial-debate --hook-stage manual

# Run on all files
pre-commit run adversarial-debate --hook-stage manual --all-files
```

### Automatic Analysis (Use with Caution)

For automatic analysis on every commit (slower):

```yaml
- repo: local
  hooks:
    - id: adversarial-debate-auto
      name: Quick Security Check
      entry: bash -lc 'LLM_PROVIDER=mock adversarial-debate analyze exploit "$@" || true'
      language: system
      types: [python]
      stages: [commit]
```

## Smoke Tests

Use the mock provider for fast CI verification:

```yaml
smoke-test:
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v4

    - name: Install
      run: pip install adversarial-debate

    - name: Smoke test
      env:
        LLM_PROVIDER: mock
      run: |
        adversarial-debate run examples/mini-app/ --output output
        test -f output/run-*/verdict.json
        echo "Smoke test passed"
```

This verifies the tool works without consuming API credits.

## Fail Conditions

Control when the pipeline fails:

| Option | Behaviour |
|--------|-----------|
| `--fail-on block` | Fail on BLOCK verdict (default) |
| `--fail-on warn` | Fail on BLOCK or WARN verdict |
| `--fail-on never` | Never fail (always exit 0) |

### Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success (PASS verdict) |
| 1 | Error (configuration, runtime) |
| 2 | Blocked (BLOCK verdict) |
| 3 | Warning (WARN verdict with `--fail-on warn`) |

## Secrets Management

### GitHub Actions

```yaml
env:
  ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
```

Add the secret in: Settings → Secrets and variables → Actions

### GitLab CI

```yaml
variables:
  ANTHROPIC_API_KEY: $ANTHROPIC_API_KEY  # Set in CI/CD settings
```

Add the variable in: Settings → CI/CD → Variables (masked)

### Jenkins

```groovy
environment {
    ANTHROPIC_API_KEY = credentials('anthropic-api-key')
}
```

Add the credential in: Manage Jenkins → Credentials

## Cost Management

API calls cost money. Strategies to manage costs:

### Limit Scope

```yaml
# Only analyse changed files
- name: Get changed files
  id: changed-files
  run: |
    echo "files=$(git diff --name-only origin/main...HEAD | grep '\.py$' | tr '\n' ' ')" >> $GITHUB_OUTPUT

- name: Run analysis
  if: steps.changed-files.outputs.files != ''
  run: |
    adversarial-debate run . --files ${{ steps.changed-files.outputs.files }}
```

### Use Time Budgets

```yaml
# Limit analysis time
run: adversarial-debate run src/ --time-budget 300  # 5 minutes max
```

### Skip Stages

```yaml
# Skip verdict for faster runs
run: adversarial-debate run src/ --skip-verdict --skip-debate
```

### Caching

```yaml
- name: Cache analysis results
  uses: actions/cache@v4
  with:
    path: .adversarial-cache
    key: security-${{ hashFiles('src/**/*.py') }}
```

## Best Practices

### 1. Start with Mock Provider

Test your CI configuration with the mock provider before using real API keys.

### 2. Use Baseline Comparison

Store baselines as artefacts to track regressions and avoid re-analysing known issues.

### 3. Set Reasonable Time Budgets

Prevent runaway costs with `--time-budget`.

### 4. Upload SARIF to GitHub

Enable Code Scanning alerts for better visibility.

### 5. Fail Fast on Critical Issues

Use `--fail-on block` to prevent merging security issues.

### 6. Review False Positives

Maintain a baseline to suppress known false positives.

## See Also

- [Baseline Tracking](baseline-tracking.md) — Managing baselines
- [Output Formats](../guides/output-formats.md) — SARIF and other formats
- [Configuration Guide](../guides/configuration.md) — All options
