# Changelog

All notable changes to the **Adversarial Debate** framework will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Comprehensive API documentation
- Real-world usage examples
- Docker support for containerized deployment
- Pre-commit hooks for code quality
- GitHub issue and PR templates
- Security policy and vulnerability reporting process

### Changed
- Enhanced README with badges and better examples

## [0.1.0] - 2025-01-17

### Added

#### Core Framework
- **Agent Architecture**: Modular agent system with base classes for easy extension
  - `AgentContext`: Structured input for agents with code and configuration
  - `AgentOutput`: Standardized output format with findings and metadata
  - Async execution support throughout the framework

#### Security Agents
- **ExploitAgent**: OWASP Top 10 vulnerability scanner
  - A01:2021 - Broken Access Control detection
  - A02:2021 - Cryptographic Failures identification
  - A03:2021 - Injection vulnerability discovery (SQL, Command, XSS)
  - A05:2021 - Security Misconfiguration detection
  - A08:2021 - Software and Data Integrity Failures
  - A10:2021 - Server-Side Request Forgery (SSRF)

- **BreakAgent**: Logic bug and edge case finder
  - Boundary condition analysis
  - State machine corruption detection
  - Concurrency and race condition identification
  - Error handling pathway analysis
  - Type confusion vulnerability detection

- **ChaosAgent**: Resilience and failure mode tester
  - Resource exhaustion scenarios
  - Network failure simulation
  - Cascading failure detection
  - Recovery mechanism analysis

#### Orchestration
- **ChaosOrchestrator**: Attack strategy coordinator
  - Risk-based prioritization
  - Multi-agent attack planning
  - Parallel execution support
  - Context-aware strategy selection

- **Arbiter**: Findings consolidation engine
  - Cross-agent deduplication
  - Confidence scoring
  - Severity adjustment
  - Remediation roadmap generation

#### Infrastructure
- **LLM Provider Abstraction**
  - Anthropic Claude integration (claude-3-5-sonnet, claude-3-5-haiku)
  - Extensible provider interface for future integrations
  - Token usage tracking and cost estimation
  - Streaming response support

- **Sandbox Execution Environment**
  - Docker-based isolation with resource limits
  - Subprocess fallback with setrlimit restrictions
  - Comprehensive input validation
  - Security exploit testing methods (SQL injection, command injection, SSRF, etc.)
  - Atomic file operations with secure permissions

- **Bead Store**: Event-sourced findings ledger
  - Append-only JSONL storage for audit trails
  - SQLite-backed full-text search (FTS5)
  - Idempotent bead creation
  - Query interface for findings retrieval

- **Configuration System**
  - Type-safe Pydantic configuration
  - Environment variable support
  - YAML/JSON configuration files
  - Comprehensive validation with helpful error messages

- **Logging System**
  - Structured JSON logging for machine processing
  - Human-readable console output with colors
  - Configurable log levels and destinations
  - Agent context tracking

- **CLI Interface**
  - `adversarial-debate analyze` - Run full analysis
  - `adversarial-debate exploit` - Run only ExploitAgent
  - `adversarial-debate break` - Run only BreakAgent
  - `adversarial-debate chaos` - Run only ChaosAgent
  - JSON and human-readable output formats

#### Development
- Comprehensive exception hierarchy for error handling
- Full type hints with mypy strict mode support
- pytest test suite with fixtures and mocks
- GitHub Actions CI/CD pipeline
- Ruff linting and formatting
- Bandit security scanning

### Security
- Sandbox hardening against code execution attacks
- Input size limits to prevent DoS
- Secure temporary file handling
- API key protection in configuration exports

---

## Version History Summary

| Version | Date | Highlights |
|---------|------|------------|
| 0.1.0 | 2025-01-17 | Initial release with full agent suite |

---

[Unreleased]: https://github.com/dr-gareth-roberts/adversarial-debate/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/dr-gareth-roberts/adversarial-debate/releases/tag/v0.1.0
