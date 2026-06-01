# Changelog

All notable changes to the **Adversarial Debate** framework will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.2.0] - 2026-06-02

### Added
- Comprehensive API documentation
- Real-world usage examples
- Docker support for containerized deployment
- Pre-commit hooks for code quality
- GitHub issue and PR templates
- Security policy and vulnerability reporting process
- Opt-in incremental caching for the `run` pipeline (`run --cache`): reuses
  per-agent results when the target code is unchanged and self-invalidates on
  any change. Off by default (a cache hit skips the agent's bead-ledger
  entries). Configurable via `cache_dir` / `ADVERSARIAL_CACHE_DIR`
- Test coverage for previously untested modules: all output formatters
  (JSON/SARIF/HTML/Markdown), results normalisation, shell completions, file
  watching, the cache manager, structured logging, the Anthropic provider, and
  the CLI command layer — raising overall coverage from 51% to 82%
- `CryptoAgent` is now exported from the top-level `adversarial_debate` package
- `examples/quickstart.py`: a minimal, zero-setup example that runs with the
  mock provider out of the box
- Integration tests that run every shipped example end-to-end, plus a guard
  that every concrete agent is exported from the package root

### Changed
- Enhanced README with badges and better examples
- Raised the CI coverage gate from 45% to 80%
- Upgraded dependencies to clear known CVEs (aiohttp, idna, requests, urllib3,
  pip, pytest)
- Examples now honour `LLM_PROVIDER` so they run with no API key
  (`LLM_PROVIDER=mock`) and use a real temporary bead ledger
- Documentation accuracy pass: corrected CLI-reference flag/default drift
  (`--baseline-file`, `--completions`, watch/orchestrate defaults, exit codes,
  removed non-existent `--format`/`cache --older-than`), removed configuration
  keys and environment variables that were never read, and fixed the documented
  exception hierarchy and `AgentType` values

### Fixed
- Watch mode no longer runs a synchronous analysis callback twice per change
  (it was invoked once to probe the result type and again via a worker thread)
- Shipped examples now run to completion (a missing `CryptoAgent` export broke
  `ci_integration.py`; `BeadStore(":memory:")` was treated as a literal file
  path, and examples ignored the configured provider)

### Removed
- Stale internal audit notes (`CODEBASE_AUDIT.md`,
  `CODEBASE_CLEANUP_RECOMMENDATIONS.md`)

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
  - Risk-based prioritisation
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
  - Human-readable console output with colours
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
