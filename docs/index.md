# Adversarial Debate Documentation

Welcome to the Adversarial Debate documentation. This guide covers everything from getting started to extending the framework.

## What is Adversarial Debate?

Adversarial Debate is a multi-agent AI security testing framework. It deploys specialised AI agents that attack your code from different angles—security vulnerabilities, logic bugs, resilience issues, and cryptographic weaknesses—then consolidates findings with confidence scoring and actionable remediation guidance.

Think of it as having a team of expert security researchers reviewing your code, each with different specialisations, working in parallel.

---

## Documentation Overview

### Getting Started

New to Adversarial Debate? Start here.

| Guide | Description |
|-------|-------------|
| [Quickstart](getting-started/quickstart.md) | Get your first scan running in 5 minutes |
| [Installation](getting-started/installation.md) | All installation methods and verification |
| [Your First Analysis](getting-started/first-analysis.md) | Step-by-step tutorial with real code |

### User Guides

Learn how to use the tool effectively.

| Guide | Description |
|-------|-------------|
| [CLI Reference](guides/cli-reference.md) | Complete command-line reference |
| [Configuration](guides/configuration.md) | Environment variables, config files, customization |
| [Provider Setup](guides/providers/index.md) | Configure Anthropic, OpenAI, Azure, Ollama, or Mock |
| [Output Formats](guides/output-formats.md) | JSON, SARIF, HTML, Markdown output options |
| [Interpreting Results](guides/interpreting-results.md) | Understanding findings, severity, and remediation |

### Integration

Integrate Adversarial Debate into your workflow.

| Guide | Description |
|-------|-------------|
| [CI/CD Integration](integration/ci-cd.md) | GitHub Actions, GitLab CI, Jenkins, pre-commit |
| [Baseline Tracking](integration/baseline-tracking.md) | Track regressions across runs |

### Concepts

Understand how the system works.

| Guide | Description |
|-------|-------------|
| [How It Works](concepts/how-it-works.md) | High-level system overview |
| [Security Model](concepts/security-model.md) | Threat model, sandbox architecture, trust boundaries |
| [Attack Coverage](concepts/attack-coverage.md) | What vulnerabilities each agent detects |

### Developer Guides

Build with and extend the framework.

| Guide | Description |
|-------|-------------|
| [Python API](developers/python-api.md) | Programmatic usage with full examples |
| [Extending Agents](developers/extending-agents.md) | Add custom agents to the framework |
| [Extending Providers](developers/extending-providers.md) | Add new LLM providers |
| [Extending Formatters](developers/extending-formatters.md) | Add new output formatters |
| [Event Sourcing](developers/event-sourcing.md) | The Bead audit trail system |
| [Testing Guide](developers/testing.md) | Testing agents and providers |

### Reference

Detailed technical reference.

| Guide | Description |
|-------|-------------|
| [Agent Reference](reference/agents.md) | Detailed agent behavior documentation |
| [Data Structures](reference/data-structures.md) | Types, enums, and schemas |
| [Architecture](reference/architecture.md) | System internals for contributors |

### Support

Get help and answers.

| Guide | Description |
|-------|-------------|
| [Troubleshooting](support/troubleshooting.md) | Common errors and solutions |
| [FAQ](support/faq.md) | Frequently asked questions |
| [Glossary](support/glossary.md) | Key terms defined |

---

## Quick Links

- [GitHub Repository](https://github.com/dr-gareth-roberts/adverserial-debate)
- [PyPI Package](https://pypi.org/project/adversarial-debate/)
- [Report a Bug](https://github.com/dr-gareth-roberts/adverserial-debate/issues/new?template=bug_report.yml)
- [Request a Feature](https://github.com/dr-gareth-roberts/adverserial-debate/issues/new?template=feature_request.yml)
- [Contributing Guide](../CONTRIBUTING.md)

---

## System Requirements

- **Python**: 3.11 or higher
- **Docker**: Required for hardened sandbox execution (optional for basic analysis)
- **API Key**: Anthropic API key (default provider) or configure alternative providers
- **OS**: Linux, macOS, Windows (WSL recommended for Windows)
