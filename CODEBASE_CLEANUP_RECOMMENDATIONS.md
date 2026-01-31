# Codebase Cleanup Recommendations (adversarial-debate)
Date: 2026-01-30
Scope: all **git-tracked** files (`git ls-files`, 120 files).
Goal: identify redundancy, dead/placeholder code, and files likely unnecessary. This is a recommendations-only document (no deletions performed).

## Quick Signals
- TODO/FIXME/etc markers: 0 file(s)
- `NotImplementedError`: 0 file(s)
- Debug breakpoints (`pdb`/`breakpoint()`): 0 file(s)

## Recommended Deletes
- `.bevel/VERSION`
- `.bevel/shareable/.bevelignore`
- `.bevel/shareable/allowedFileExtensions.json`
- `.bevel/shareable/config.json`
- `tests/__init__.py`
- `tests/benchmarks/__init__.py`
- `tests/integration/__init__.py`
- `tests/property/__init__.py`
- `tests/unit/__init__.py`
- `tests/unit/test_agents/__init__.py`
- `tests/unit/test_providers/__init__.py`

## Recommended Modifies
- `scripts/demo.sh`
- `src/adversarial_debate/cli.py`
- `src/adversarial_debate/sandbox/__init__.py`
- `tests/unit/test_providers/test_azure.py`
- `tests/unit/test_providers/test_openai.py`

## Per-file Review

### `.bevel/VERSION` — **DELETE**
- Reasons:
  - Bevel-specific tooling config; not referenced by runtime/CI/tests.
  - Reduces repo surface area and avoids confusing contributors who don’t use Bevel.
  - If you actively use Bevel, keep `.bevel/` and document the workflow instead.

### `.bevel/shareable/.bevelignore` — **DELETE**
- Reasons:
  - Bevel-specific tooling config; not referenced by runtime/CI/tests.
  - Reduces repo surface area and avoids confusing contributors who don’t use Bevel.
  - If you actively use Bevel, keep `.bevel/` and document the workflow instead.

### `.bevel/shareable/allowedFileExtensions.json` — **DELETE**
- Summary: JSON file
- Reasons:
  - Bevel-specific tooling config; not referenced by runtime/CI/tests.
  - Reduces repo surface area and avoids confusing contributors who don’t use Bevel.
  - If you actively use Bevel, keep `.bevel/` and document the workflow instead.

### `.bevel/shareable/config.json` — **DELETE**
- Summary: JSON file
- Reasons:
  - Bevel-specific tooling config; not referenced by runtime/CI/tests.
  - Reduces repo surface area and avoids confusing contributors who don’t use Bevel.
  - If you actively use Bevel, keep `.bevel/` and document the workflow instead.

### `.dockerignore` — **KEEP**
- Why keep:
  - Repository hygiene / security tooling configuration.

### `.env.example` — **KEEP**
- Why keep:
  - Keeps the repo functional and documented.

### `.github/CODEOWNERS` — **KEEP**
- Why keep:
  - GitHub metadata (CI, templates, CODEOWNERS, etc.).

### `.github/ISSUE_TEMPLATE/bug_report.yml` — **KEEP**
- Why keep:
  - GitHub metadata (CI, templates, CODEOWNERS, etc.).

### `.github/ISSUE_TEMPLATE/config.yml` — **KEEP**
- Why keep:
  - GitHub metadata (CI, templates, CODEOWNERS, etc.).

### `.github/ISSUE_TEMPLATE/feature_request.yml` — **KEEP**
- Why keep:
  - GitHub metadata (CI, templates, CODEOWNERS, etc.).

### `.github/ISSUE_TEMPLATE/question.yml` — **KEEP**
- Why keep:
  - GitHub metadata (CI, templates, CODEOWNERS, etc.).

### `.github/PULL_REQUEST_TEMPLATE.md` — **KEEP**
- Summary: Description
- Why keep:
  - GitHub metadata (CI, templates, CODEOWNERS, etc.).

### `.github/workflows/ci.yml` — **KEEP**
- Why keep:
  - GitHub metadata (CI, templates, CODEOWNERS, etc.).

### `.github/workflows/release.yml` — **KEEP**
- Why keep:
  - GitHub metadata (CI, templates, CODEOWNERS, etc.).

### `.gitignore` — **KEEP**
- Why keep:
  - Repository hygiene / security tooling configuration.

### `.pre-commit-config.yaml` — **KEEP**
- Summary: Pre-commit hooks for Adversarial Debate
- Why keep:
  - Repository hygiene / security tooling configuration.

### `.secrets.baseline` — **KEEP**
- Why keep:
  - Repository hygiene / security tooling configuration.

### `CHANGELOG.md` — **KEEP**
- Summary: Changelog
- Why keep:
  - Standard project metadata/documentation.

### `CODEBASE_AUDIT.md` — **KEEP**
- Summary: Codebase Audit (adversarial-debate)
- Why keep:
  - Keeps the repo functional and documented.

### `CODE_OF_CONDUCT.md` — **KEEP**
- Summary: Contributor Covenant Code of Conduct
- Why keep:
  - Standard project metadata/documentation.

### `CONTRIBUTING.md` — **KEEP**
- Summary: Contributing to adversarial-debate
- Why keep:
  - Standard project metadata/documentation.

### `Dockerfile` — **KEEP**
- Why keep:
  - Containerization / local dev & execution tooling.

### `LICENSE` — **KEEP**
- Why keep:
  - Standard project metadata/documentation.

### `Makefile` — **KEEP**
- Why keep:
  - Developer convenience wrappers.

### `README.md` — **KEEP**
- Summary: 🔴 Adversarial Debate
- Why keep:
  - Standard project metadata/documentation.

### `SECURITY.md` — **KEEP**
- Summary: Security Policy
- Why keep:
  - Standard project metadata/documentation.

### `action.yml` — **KEEP**
- Why keep:
  - GitHub Action definition for using this tool in CI.

### `docker-compose.sandbox.yml` — **KEEP**
- Summary: Adversarial Debate - Sandboxed Execution Configuration
- Why keep:
  - Containerization / local dev & execution tooling.

### `docker-compose.yml` — **KEEP**
- Summary: Adversarial Debate - Docker Compose Configuration
- Why keep:
  - Containerization / local dev & execution tooling.

### `docs/agents.md` — **KEEP**
- Summary: Agent System Documentation
- Why keep:
  - Project documentation.

### `docs/api.md` — **KEEP**
- Summary: API Reference
- Why keep:
  - Project documentation.

### `docs/architecture.md` — **KEEP**
- Summary: Architecture Deep Dive
- Why keep:
  - Project documentation.

### `docs/data-structures.md` — **KEEP**
- Summary: Data Structures Reference
- Why keep:
  - Project documentation.

### `docs/demo.md` — **KEEP**
- Summary: Demo Walkthrough (No API Key)
- Why keep:
  - Project documentation.

### `docs/pipeline.md` — **KEEP**
- Summary: Pipeline Execution Guide
- Why keep:
  - Project documentation.

### `examples/README.md` — **KEEP**
- Summary: Examples
- Why keep:
  - Example usage / demos.

### `examples/basic_analysis.py` — **KEEP**
- Summary: Basic example: Analyse code with all agents. | Functions: main
- Why keep:
  - Example usage / demos.

### `examples/ci_integration.py` — **KEEP**
- Summary: CI/CD Integration example: Integrate security analysis into your pipeline. | Functions: get_changed_files, analyze_files, generate_markdown_report, generate_sarif_report, main
- Why keep:
  - Example usage / demos.

### `examples/mini-app/README.md` — **KEEP**
- Summary: Mini App (Intentional Vulnerabilities)
- Why keep:
  - Example usage / demos.

### `examples/mini-app/app.py` — **KEEP**
- Summary: Intentionally vulnerable mini app for demos. | Functions: get_user, run_report, fetch_profile, load_session
- Why keep:
  - Example usage / demos.

### `examples/sandbox_execution.py` — **KEEP**
- Summary: Sandbox execution examples: run untrusted code safely. | Functions: basic_execution, execution_with_inputs, timeout_handling, sql_injection_test, error_handling, network_isolation, memory_limit_handling, main
- Why keep:
  - Example usage / demos.

### `examples/single_agent.py` — **KEEP**
- Summary: Single agent example: Run targeted analysis with one agent. | Functions: analyze_file, print_findings, main
- Why keep:
  - Example usage / demos.

### `examples/vulnerable_samples/command_injection.py` — **KEEP**
- Summary: Command Injection Vulnerabilities - INTENTIONALLY VULNERABLE. | Functions: ping_host_system, get_file_info_popen, run_command_shell_true, execute_script_popen, calculate_expression, run_user_code, read_log_file, run_with_env, grep_logs_format, backup_file_chained…
- Why keep:
  - Example usage / demos.

### `examples/vulnerable_samples/sql_injection.py` — **KEEP**
- Summary: SQL Injection Vulnerabilities - INTENTIONALLY VULNERABLE. | Functions: get_user_by_id_concat, get_user_by_name_fstring, search_users_format, get_user_by_email_percent, search_products_like, get_users_sorted, get_users_by_ids, get_data_from_table, get_user_by_id_secure, search_users_secure…
- Why keep:
  - Example usage / demos.

### `examples/workflows/security-analysis.yml` — **KEEP**
- Summary: Example workflow for using adversarial-debate in your repository.
- Why keep:
  - Example usage / demos.

### `pyproject.toml` — **KEEP**
- Summary: TOML config
- Why keep:
  - Build/dependency configuration for the project.

### `schemas/config.schema.json` — **KEEP**
- Summary: JSON file
- Why keep:
  - Schema used for config validation/documentation.

### `scripts/check_import_cycles.py` — **KEEP**
- Summary: Detect internal import cycles in the adversarial_debate package. | Classes: Module | Functions: _repo_root, _src_root, _pkg_root, _module_name_for, _resolve_relative_import, _iter_modules, _build_graph, _strongly_connected_components, main
- Why keep:
  - Developer tooling / CI helper script.

### `scripts/demo.sh` — **MODIFY**
- Summary: !/usr/bin/env bash
- Why modify:
  - Overlaps with `Makefile` target `demo` (same underlying command).
- Recommended changes:
  - Pick a single canonical demo entry point (Makefile target or shell script) and have the other delegate to it.
  - Ensure README/docs reference only the canonical entry point to prevent drift.

### `src/adversarial_debate/__init__.py` — **KEEP**
- Summary: Adversarial Debate - AI Red Team Security Testing Framework.
- Why keep:
  - Core library/runtime code.

### `src/adversarial_debate/agents/__init__.py` — **KEEP**
- Summary: Adversarial agents for security analysis.
- Why keep:
  - Core library/runtime code.

### `src/adversarial_debate/agents/arbiter.py` — **KEEP**
- Summary: Arbiter - Judges red team findings and renders verdicts. | Classes: Arbiter
- Why keep:
  - Core library/runtime code.

### `src/adversarial_debate/agents/base.py` — **KEEP**
- Summary: Base agent class for adversarial debate agents. | Classes: AgentContext, AgentOutput, Agent
- Why keep:
  - Core library/runtime code.

### `src/adversarial_debate/agents/break_agent.py` — **KEEP**
- Summary: BreakAgent - Adversarial agent that finds logic errors and edge cases. | Classes: BreakAgent
- Why keep:
  - Core library/runtime code.

### `src/adversarial_debate/agents/chaos_agent.py` — **KEEP**
- Summary: ChaosAgent - Adversarial agent for resilience testing through chaos engineering. | Classes: ChaosAgent
- Why keep:
  - Core library/runtime code.

### `src/adversarial_debate/agents/chaos_orchestrator.py` — **KEEP**
- Summary: ChaosOrchestrator - Coordinates red team agents for adversarial testing. | Classes: ChaosOrchestrator
- Why keep:
  - Core library/runtime code.

### `src/adversarial_debate/agents/cross_examiner.py` — **KEEP**
- Summary: CrossExaminationAgent - makes agents argue over findings. | Classes: CrossExaminationAgent | Functions: _has_concrete_repro, _enforce_repro_dismissal
- Why keep:
  - Core library/runtime code.

### `src/adversarial_debate/agents/exploit_agent.py` — **KEEP**
- Summary: ExploitAgent - Security-focused adversarial agent for finding vulnerabilities. | Classes: ExploitAgent
- Why keep:
  - Core library/runtime code.

### `src/adversarial_debate/attack_plan.py` — **KEEP**
- Summary: Attack plan types for ChaosOrchestrator coordination. | Classes: AgentType, AttackPriority, RiskLevel, AttackVector, Attack, ParallelGroup, SkipReason, FileRiskProfile, AttackSurface, AttackPlan
- Why keep:
  - Core library/runtime code.

### `src/adversarial_debate/baseline.py` — **KEEP**
- Summary: Baseline/regression utilities. | Classes: BaselineDiff | Functions: severity_gte, compute_fingerprint, index_by_fingerprint, diff_bundles
- Why keep:
  - Core library/runtime code.

### `src/adversarial_debate/cache/__init__.py` — **KEEP**
- Summary: Incremental analysis cache for adversarial-debate.
- Why keep:
  - Core library/runtime code.

### `src/adversarial_debate/cache/file_cache.py` — **KEEP**
- Summary: File-based cache storage for analysis results. | Classes: CacheEntry, FileCache
- Why keep:
  - Core library/runtime code.

### `src/adversarial_debate/cache/hash.py` — **KEEP**
- Summary: Content hashing utilities for cache invalidation. | Functions: normalize_code, hash_content, hash_file, hash_file_content, hash_files, hash_analysis_inputs
- Why keep:
  - Core library/runtime code.

### `src/adversarial_debate/cache/manager.py` — **KEEP**
- Summary: Cache manager for incremental analysis. | Classes: CacheManager
- Why keep:
  - Core library/runtime code.

### `src/adversarial_debate/cli.py` — **MODIFY**
- Summary: Command-line interface for adversarial-debate. | Functions: create_parser, load_config, print_json, print_error, _get_provider_from_config, cmd_analyze, cmd_orchestrate, cmd_verdict, cmd_run, cmd_watch…
- Why modify:
  - Large single module (~1202 lines); command handling/UI/utilities are tightly coupled.
- Recommended changes:
  - Split into smaller modules (e.g. `src/adversarial_debate/cli/commands/*.py`, `src/adversarial_debate/cli/output.py`, `src/adversarial_debate/cli/args.py`) and keep `adversarial_debate.cli:main` stable.
  - After splitting, run `ruff`, `mypy`, and `pytest` to confirm no behaviour drift.

### `src/adversarial_debate/completions.py` — **KEEP**
- Summary: Shell completion scripts for adversarial-debate CLI. | Functions: get_completion_script, print_completion_script, get_install_instructions
- Why keep:
  - Core library/runtime code.

### `src/adversarial_debate/config.py` — **KEEP**
- Summary: Configuration management for adversarial-debate. | Classes: ProviderConfig, LoggingConfig, Config | Functions: _parse_sandbox_config, get_config, set_config
- Why keep:
  - Core library/runtime code.

### `src/adversarial_debate/exceptions.py` — **KEEP**
- Summary: Exception hierarchy for adversarial-debate. | Classes: AdversarialDebateError, AgentError, AgentExecutionError, AgentParseError, AgentTimeoutError, ProviderError, ProviderRateLimitError, ProviderConnectionError, ProviderAuthenticationError, SandboxError…
- Why keep:
  - Core library/runtime code.

### `src/adversarial_debate/formatters/__init__.py` — **KEEP**
- Summary: Output formatters for adversarial-debate results. | Functions: get_formatter
- Why keep:
  - Core library/runtime code.

### `src/adversarial_debate/formatters/base.py` — **KEEP**
- Summary: Base formatter abstraction. | Classes: OutputFormat, FormatterConfig, Formatter
- Why keep:
  - Core library/runtime code.

### `src/adversarial_debate/formatters/html.py` — **KEEP**
- Summary: HTML output formatter for human-readable reports. | Classes: HTMLFormatter
- Why keep:
  - Core library/runtime code.

### `src/adversarial_debate/formatters/json.py` — **KEEP**
- Summary: JSON output formatter. | Classes: JSONFormatter
- Why keep:
  - Core library/runtime code.

### `src/adversarial_debate/formatters/markdown.py` — **KEEP**
- Summary: Markdown output formatter for documentation-friendly output. | Classes: MarkdownFormatter
- Why keep:
  - Core library/runtime code.

### `src/adversarial_debate/formatters/sarif.py` — **KEEP**
- Summary: SARIF (Static Analysis Results Interchange Format) output formatter. | Classes: SARIFFormatter
- Why keep:
  - Core library/runtime code.

### `src/adversarial_debate/logging.py` — **KEEP**
- Summary: Structured logging for adversarial-debate. | Classes: StructuredFormatter, HumanReadableFormatter, AgentLoggerAdapter | Functions: setup_logging, get_logger, get_agent_logger
- Why keep:
  - Core library/runtime code.

### `src/adversarial_debate/providers/__init__.py` — **KEEP**
- Summary: LLM provider abstraction for multi-provider support. | Classes: _ProviderFactory | Functions: _get_openai_provider, _get_azure_provider, _get_ollama_provider, get_provider, list_providers
- Why keep:
  - Core library/runtime code.

### `src/adversarial_debate/providers/anthropic.py` — **KEEP**
- Summary: Anthropic Claude provider implementation. | Classes: AnthropicProvider
- Why keep:
  - Core library/runtime code.

### `src/adversarial_debate/providers/azure.py` — **KEEP**
- Summary: Azure OpenAI provider implementation. | Classes: AzureOpenAIProvider
- Why keep:
  - Core library/runtime code.

### `src/adversarial_debate/providers/base.py` — **KEEP**
- Summary: Base LLM provider abstraction. | Classes: ModelTier, Message, ProviderConfig, LLMResponse, StreamChunk, LLMProvider
- Why keep:
  - Core library/runtime code.

### `src/adversarial_debate/providers/mock.py` — **KEEP**
- Summary: Deterministic mock provider for demos and tests. | Classes: MockProvider
- Why keep:
  - Core library/runtime code.

### `src/adversarial_debate/providers/ollama.py` — **KEEP**
- Summary: Ollama provider implementation for local LLM models. | Classes: OllamaProvider
- Why keep:
  - Core library/runtime code.

### `src/adversarial_debate/providers/openai.py` — **KEEP**
- Summary: OpenAI GPT provider implementation. | Classes: OpenAIProvider
- Why keep:
  - Core library/runtime code.

### `src/adversarial_debate/py.typed` — **KEEP**
- Summary: PEP 561 typing marker
- Why keep:
  - Core library/runtime code.

### `src/adversarial_debate/results.py` — **KEEP**
- Summary: Utilities for producing a canonical results bundle. | Classes: BundleInputs | Functions: _parse_cwe_id, _parse_location, normalize_exploit_findings, normalize_break_findings, normalize_chaos_experiments, normalize_verdict_for_reporting, build_results_bundle, _infer_single_file_target
- Why keep:
  - Core library/runtime code.

### `src/adversarial_debate/sandbox/__init__.py` — **MODIFY**
- Summary: Sandbox executor for safely running adversarial proofs-of-concept. | Classes: SandboxConfig, ExecutionResult, SandboxExecutor | Functions: _parse_size_bytes, _read_stream_limited, _decode_and_mark, validate_identifier, validate_code_size, validate_inputs, validate_path_for_mount, validate_test_params, generate_secure_temp_name, validate_sandbox_config
- Why modify:
  - Implementation lives in `__init__.py` and is very large (~1772 lines); harder to maintain and review.
- Recommended changes:
  - Move implementation into dedicated modules (e.g. `src/adversarial_debate/sandbox/executor.py`, `validation.py`, `types.py`) and keep `src/adversarial_debate/sandbox/__init__.py` for re-exports.
  - After splitting, run `ruff`, `mypy`, and `pytest` to confirm no behaviour drift.

### `src/adversarial_debate/store/__init__.py` — **KEEP**
- Summary: Bead store for event-sourced coordination.
- Why keep:
  - Core library/runtime code.

### `src/adversarial_debate/store/beads.py` — **KEEP**
- Summary: Bead store implementation - append-only JSONL ledger for coordination. | Classes: BeadType, ArtefactType, Artefact, Bead, BeadStore
- Why keep:
  - Core library/runtime code.

### `src/adversarial_debate/verdict.py` — **KEEP**
- Summary: Verdict types for Arbiter decision making. | Classes: VerdictDecision, ExploitationDifficulty, RemediationEffort, FindingValidation, ValidatedFinding, RejectedFinding, RemediationTask, ArbiterVerdict
- Why keep:
  - Core library/runtime code.

### `src/adversarial_debate/watch.py` — **KEEP**
- Summary: File watching functionality for continuous analysis. | Classes: WatchEvent, WatchConfig, FileWatcher, WatchRunner
- Why keep:
  - Core library/runtime code.

### `tests/__init__.py` — **DELETE**
- Summary: Test suite for adversarial-debate.
- Reasons:
  - Docstring-only `__init__.py` files are unnecessary for pytest discovery.
  - Removing them reduces accidental “tests as an importable package” coupling.

### `tests/benchmarks/__init__.py` — **DELETE**
- Summary: Performance benchmarks for adversarial-debate.
- Reasons:
  - Docstring-only `__init__.py` files are unnecessary for pytest discovery.
  - Removing them reduces accidental “tests as an importable package” coupling.

### `tests/benchmarks/test_performance.py` — **KEEP**
- Summary: Performance benchmarks for critical operations. | Classes: TestHashPerformance, TestValidationPerformance, TestSecureRandomPerformance, TestFileIOPerformance, TestMemoryUsage
- Why keep:
  - Test coverage / regression protection.

### `tests/conftest.py` — **KEEP**
- Summary: Pytest configuration and fixtures for adversarial-debate tests. | Classes: MockLLMProvider | Functions: clean_environment, temp_dir, test_config, mock_provider, mock_provider_factory, bead_store, sample_bead, sample_context, sample_findings, exploit_agent_response…
- Why keep:
  - Test coverage / regression protection.

### `tests/integration/__init__.py` — **DELETE**
- Summary: Integration tests for adversarial-debate.
- Reasons:
  - Docstring-only `__init__.py` files are unnecessary for pytest discovery.
  - Removing them reduces accidental “tests as an importable package” coupling.

### `tests/integration/test_cli.py` — **KEEP**
- Summary: Integration tests for CLI. | Classes: TestCLIHelp, TestCLIAnalyze, TestCLIOrchestrate, TestCLIVerdict, TestCLIRun, TestCLIOutput | Functions: sample_code_file
- Why keep:
  - Test coverage / regression protection.

### `tests/property/__init__.py` — **DELETE**
- Summary: Property-based tests for adversarial-debate.
- Reasons:
  - Docstring-only `__init__.py` files are unnecessary for pytest discovery.
  - Removing them reduces accidental “tests as an importable package” coupling.

### `tests/property/test_cache_properties.py` — **KEEP**
- Summary: Property-based tests for cache integrity. | Functions: test_hash_is_deterministic, test_different_content_different_hash, test_hash_format, test_normalization_is_idempotent, test_normalized_code_has_consistent_hash, test_trailing_whitespace_normalized, test_single_char_change_different_hash, test_empty_content_has_hash, test_binary_content_handling
- Why keep:
  - Test coverage / regression protection.

### `tests/property/test_sandbox_security.py` — **KEEP**
- Summary: Property-based tests for sandbox security. | Functions: test_identifier_validation_rejects_non_identifiers, test_identifier_validation_blocks_dangerous_builtins, test_identifier_validation_rejects_long_names, test_valid_identifiers_pass, test_large_code_rejected, test_small_code_accepted, test_valid_inputs_accepted, test_inputs_with_invalid_keys_rejected, test_secure_temp_names_unique, test_secure_temp_names_format…
- Why keep:
  - Test coverage / regression protection.

### `tests/unit/__init__.py` — **DELETE**
- Summary: Unit tests for adversarial-debate.
- Reasons:
  - Docstring-only `__init__.py` files are unnecessary for pytest discovery.
  - Removing them reduces accidental “tests as an importable package” coupling.

### `tests/unit/test_agents/__init__.py` — **DELETE**
- Summary: Unit tests for agents.
- Reasons:
  - Docstring-only `__init__.py` files are unnecessary for pytest discovery.
  - Removing them reduces accidental “tests as an importable package” coupling.

### `tests/unit/test_agents/test_base.py` — **KEEP**
- Summary: Unit tests for base agent functionality. | Classes: TestAgentContext, TestAgentOutput
- Why keep:
  - Test coverage / regression protection.

### `tests/unit/test_agents/test_validation.py` — **KEEP**
- Summary: Validation tests for agent normalisation requirements. | Functions: _make_context, test_exploit_agent_requires_payload, test_break_agent_requires_poc_code, test_chaos_agent_requires_rollback, test_arbiter_flags_unknown_or_missing_ids
- Why keep:
  - Test coverage / regression protection.

### `tests/unit/test_attack_plan.py` — **KEEP**
- Summary: Unit tests for attack plan types. | Classes: TestAgentType, TestAttackPriority, TestRiskLevel, TestAttackVector, TestAttack, TestParallelGroup, TestFileRiskProfile, TestAttackSurface, TestAttackPlan
- Why keep:
  - Test coverage / regression protection.

### `tests/unit/test_baseline.py` — **KEEP**
- Summary: Unit tests for baseline diffing. | Functions: test_diff_bundles_new_and_fixed
- Why keep:
  - Test coverage / regression protection.

### `tests/unit/test_cli.py` — **KEEP**
- Summary: Unit tests for CLI module. | Classes: TestCreateParser, TestLoadConfig, TestPrintFunctions, TestAnalyzeCommand, TestOrchestrateCommand, TestVerdictCommand
- Why keep:
  - Test coverage / regression protection.

### `tests/unit/test_config.py` — **KEEP**
- Summary: Unit tests for configuration module. | Classes: TestProviderConfig, TestLoggingConfig, TestSandboxConfig, TestConfig, TestGlobalConfig
- Why keep:
  - Test coverage / regression protection.

### `tests/unit/test_cross_examination_agent.py` — **KEEP**
- Summary: Unit tests for CrossExaminationAgent wiring. | Functions: test_cross_examination_agent_metadata, test_cross_exam_auto_dismisses_missing_repro
- Why keep:
  - Test coverage / regression protection.

### `tests/unit/test_exceptions.py` — **KEEP**
- Summary: Unit tests for exception hierarchy. | Classes: TestAdversarialDebateError, TestAgentErrors, TestProviderErrors, TestSandboxErrors, TestStoreErrors, TestConfigErrors, TestExceptionHierarchy
- Why keep:
  - Test coverage / regression protection.

### `tests/unit/test_mock_provider.py` — **KEEP**
- Summary: Tests for MockProvider. | Functions: test_get_provider_mock, test_mock_provider_returns_json
- Why keep:
  - Test coverage / regression protection.

### `tests/unit/test_providers/__init__.py` — **DELETE**
- Summary: Tests for LLM providers.
- Reasons:
  - Docstring-only `__init__.py` files are unnecessary for pytest discovery.
  - Removing them reduces accidental “tests as an importable package” coupling.

### `tests/unit/test_providers/test_azure.py` — **MODIFY**
- Summary: Tests for Azure OpenAI provider. | Classes: TestAzureOpenAIProvider
- Why modify:
  - Contains a bare `except ImportError: pass` that can hide regressions.
- Recommended changes:
  - Replace `try/except ImportError: pass` with an explicit assertion (or `pytest.xfail`) so unexpected import failures are visible.
  - Optionally refactor provider modules/tests to guarantee deterministic behaviour when optional dependencies are missing.

### `tests/unit/test_providers/test_base.py` — **KEEP**
- Summary: Tests for base provider classes. | Classes: TestMessage, TestProviderConfig, TestLLMResponse, TestStreamChunk, TestModelTier
- Why keep:
  - Test coverage / regression protection.

### `tests/unit/test_providers/test_factory.py` — **KEEP**
- Summary: Tests for provider factory functions. | Classes: TestGetProvider, TestListProviders
- Why keep:
  - Test coverage / regression protection.

### `tests/unit/test_providers/test_ollama.py` — **KEEP**
- Summary: Tests for Ollama provider. | Classes: TestOllamaProvider
- Why keep:
  - Test coverage / regression protection.

### `tests/unit/test_providers/test_openai.py` — **MODIFY**
- Summary: Tests for OpenAI provider. | Classes: TestOpenAIProvider
- Why modify:
  - Contains a bare `except ImportError: pass` that can hide regressions.
- Recommended changes:
  - Replace `try/except ImportError: pass` with an explicit assertion (or `pytest.xfail`) so unexpected import failures are visible.
  - Optionally refactor provider modules/tests to guarantee deterministic behaviour when optional dependencies are missing.

### `tests/unit/test_results_bundle.py` — **KEEP**
- Summary: Unit tests for results bundle normalisation. | Functions: test_build_results_bundle_normalizes_findings
- Why keep:
  - Test coverage / regression protection.

### `tests/unit/test_sandbox.py` — **KEEP**
- Summary: Unit tests for the sandbox execution module. | Classes: TestSandboxConfig, TestInputValidation, TestSandboxExecutor, TestSandboxResourceLimits
- Why keep:
  - Test coverage / regression protection.

### `tests/unit/test_store.py` — **KEEP**
- Summary: Unit tests for the bead store module. | Classes: TestBead, TestBeadStore, TestBeadIdGeneration
- Why keep:
  - Test coverage / regression protection.

### `tests/unit/test_verdict.py` — **KEEP**
- Summary: Unit tests for verdict types. | Classes: TestVerdictDecision, TestExploitationDifficulty, TestRemediationEffort, TestValidatedFinding, TestRejectedFinding, TestRemediationTask, TestArbiterVerdict
- Why keep:
  - Test coverage / regression protection.

### `uv.lock` — **KEEP**
- Summary: Lockfile
- Why keep:
  - Build/dependency configuration for the project.
