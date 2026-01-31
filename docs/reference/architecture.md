# Architecture Deep Dive

Technical architecture documentation for contributors and advanced users.

## System Overview

Adversarial Debate is a multi-agent AI security testing framework built on three core principles:

1. **Multi-agent adversarial analysis** — Multiple specialised agents attack code from different angles
2. **Event sourcing with beads** — Complete audit trail of all agent actions
3. **Structured coordination** — Orchestrated attack planning with cross-examination

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           Adversarial Debate                            │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─────────────┐    ┌─────────────────────────────────────────────┐    │
│  │   CLI /     │───▶│              Pipeline Executor              │    │
│  │  Python API │    │                                             │    │
│  └─────────────┘    │  ┌───────────────────────────────────────┐  │    │
│                     │  │         ChaosOrchestrator             │  │    │
│                     │  │         (Attack Planning)             │  │    │
│                     │  └─────────────────┬─────────────────────┘  │    │
│                     │                    │                        │    │
│                     │    ┌───────────────┼───────────────┐        │    │
│                     │    ▼               ▼               ▼        │    │
│                     │  ┌─────┐       ┌─────┐        ┌─────┐       │    │
│                     │  │Explt│       │Break│        │Chaos│       │    │
│                     │  │Agent│       │Agent│        │Agent│       │    │
│                     │  └──┬──┘       └──┬──┘        └──┬──┘       │    │
│                     │     │             │              │          │    │
│                     │     └─────────────┼──────────────┘          │    │
│                     │                   ▼                         │    │
│                     │  ┌───────────────────────────────────────┐  │    │
│                     │  │      CrossExaminationAgent            │  │    │
│                     │  └─────────────────┬─────────────────────┘  │    │
│                     │                    ▼                        │    │
│                     │  ┌───────────────────────────────────────┐  │    │
│                     │  │            Arbiter                    │  │    │
│                     │  │        (Final Verdict)                │  │    │
│                     │  └───────────────────────────────────────┘  │    │
│                     └─────────────────────────────────────────────┘    │
│                                        │                               │
│  ┌─────────────┐    ┌─────────────┐   │   ┌─────────────┐             │
│  │ BeadStore   │◀───│  Providers  │◀──┴──▶│  Formatters │             │
│  │ (Ledger)    │    │ (LLM APIs)  │       │  (Output)   │             │
│  └─────────────┘    └─────────────┘       └─────────────┘             │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

## Module Structure

```
src/adversarial_debate/
├── __init__.py          # Public API exports
├── cli.py               # CLI entry point
├── cli_commands.py      # Command implementations
├── cli_output.py        # Output formatting
├── cli_provider.py      # Provider setup
├── config.py            # Configuration management
├── exceptions.py        # Exception hierarchy
├── logging.py           # Logging setup
├── completions.py       # LLM completion utilities
├── watch.py             # File watching (continuous mode)
│
├── agents/              # Agent implementations
│   ├── __init__.py
│   ├── base.py          # Agent base class
│   ├── exploit_agent.py # Security vulnerabilities
│   ├── break_agent.py   # Logic bugs
│   ├── chaos_agent.py   # Resilience testing
│   ├── crypto_agent.py  # Cryptographic weaknesses
│   ├── chaos_orchestrator.py  # Attack coordination
│   ├── cross_examiner.py      # Finding validation
│   └── arbiter.py       # Final verdict
│
├── providers/           # LLM provider implementations
│   ├── __init__.py
│   ├── base.py          # Provider interface
│   ├── anthropic.py     # Anthropic Claude
│   ├── openai.py        # OpenAI GPT
│   ├── azure.py         # Azure OpenAI
│   ├── ollama.py        # Local Ollama
│   └── mock.py          # Testing mock
│
├── store/               # Event sourcing
│   ├── __init__.py
│   └── beads.py         # Bead store implementation
│
├── formatters/          # Output formatters
│   ├── __init__.py
│   ├── base.py          # Formatter interface
│   ├── json.py          # JSON output
│   ├── sarif.py         # SARIF format
│   ├── html.py          # HTML reports
│   └── markdown.py      # Markdown output
│
├── sandbox/             # Secure execution
│   ├── __init__.py
│   └── executor.py      # Docker sandbox
│
├── cache/               # Response caching
│   ├── __init__.py
│   ├── manager.py       # Cache manager
│   ├── file_cache.py    # File-based cache
│   └── hash.py          # Content hashing
│
├── knowledge/           # Security knowledge base
│   ├── __init__.py
│   ├── cwe_patterns.py  # CWE pattern definitions
│   └── dangerous_sinks.py  # Dangerous function lists
│
├── attack_plan.py       # Attack plan types
├── verdict.py           # Verdict types
├── baseline.py          # Baseline comparison
└── results.py           # Results bundle
```

## Core Components

### 1. Agent System

The agent system follows a stateless processor pattern:

```
                    ┌─────────────────────────┐
                    │      AgentContext       │
                    │  (inputs, policy, beads)│
                    └───────────┬─────────────┘
                                │
                                ▼
┌───────────────────────────────────────────────────────┐
│                      Agent.run()                       │
│                                                        │
│  1. _build_prompt(context) → list[Message]            │
│  2. provider.complete(messages) → LLMResponse         │
│  3. _parse_response(response) → AgentOutput           │
│  4. bead_store.append(beads)                          │
│                                                        │
└───────────────────────────────────────────────────────┘
                                │
                                ▼
                    ┌─────────────────────────┐
                    │      AgentOutput        │
                    │  (result, beads, conf)  │
                    └─────────────────────────┘
```

**Key design decisions:**

- **Stateless agents** — All state passed via `AgentContext`, enabling parallelisation
- **Structured output** — Agents return typed `AgentOutput` with consistent schema
- **Bead emission** — All significant actions recorded for audit
- **Abstract interface** — Easy to add new agent types

### 2. Provider Abstraction

The provider layer abstracts LLM API differences:

```python
class LLMProvider(ABC):
    @property
    @abstractmethod
    def name(self) -> str: ...

    @abstractmethod
    async def complete(
        self,
        messages: list[Message],
        **kwargs,
    ) -> LLMResponse: ...

    @abstractmethod
    def get_model_for_tier(self, tier: ModelTier) -> str: ...
```

**Model tier routing:**

| Tier | Purpose | Example Models |
|------|---------|----------------|
| `HOSTED_SMALL` | Fast, cheap | Haiku, GPT-4o-mini |
| `HOSTED_LARGE` | Powerful | Sonnet, GPT-4o |
| `LOCAL` | Self-hosted | Ollama models |

### 3. Event Sourcing (Beads)

The bead system provides an append-only audit trail:

```
┌──────────────────────────────────────────────────────────────┐
│                        BeadStore                             │
│                                                              │
│  beads/ledger.jsonl                                          │
│  ┌────────────────────────────────────────────────────────┐  │
│  │ {"bead_id":"B-001","bead_type":"attack_plan",...}     │  │
│  │ {"bead_id":"B-002","bead_type":"exploit_analysis",... │  │
│  │ {"bead_id":"B-003","bead_type":"break_analysis",...   │  │
│  │ {"bead_id":"B-004","bead_type":"arbiter_verdict",...  │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                              │
│  Operations:                                                 │
│  • append(bead)           - Add bead to ledger              │
│  • append_idempotent()    - Prevent duplicates              │
│  • query(thread_id, ...)  - Filter beads                    │
│  • get_by_id(bead_id)     - Retrieve specific bead          │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

**Thread safety:** File locking (`fcntl.LOCK_EX`) enables concurrent writes.

### 4. Pipeline Execution

The pipeline orchestrates agent execution:

```
Phase 1: Orchestration
┌─────────────────────────────────────────────────────────────┐
│ ChaosOrchestrator                                           │
│ • Analyse attack surface                                    │
│ • Create attack plan                                        │
│ • Assign work to agents                                     │
│ • Define execution order                                    │
└────────────────────────────┬────────────────────────────────┘
                             │
                             ▼
Phase 2: Analysis (parallel)
┌─────────────────────────────────────────────────────────────┐
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐     │
│  │ExploitAgent │    │ BreakAgent  │    │ ChaosAgent  │     │
│  │             │    │             │    │             │     │
│  │• SQL inject │    │• Boundaries │    │• Timeouts   │     │
│  │• XSS        │    │• Race conds │    │• Failures   │     │
│  │• Auth       │    │• State bugs │    │• Resilience │     │
│  └─────────────┘    └─────────────┘    └─────────────┘     │
│                                                             │
│        Optional: CryptoAgent for crypto-specific code       │
└────────────────────────────┬────────────────────────────────┘
                             │
                             ▼
Phase 3: Cross-Examination
┌─────────────────────────────────────────────────────────────┐
│ CrossExaminationAgent                                       │
│ • Challenge each finding                                    │
│ • Identify false positives                                  │
│ • Adjust confidence levels                                  │
└────────────────────────────┬────────────────────────────────┘
                             │
                             ▼
Phase 4: Verdict
┌─────────────────────────────────────────────────────────────┐
│ Arbiter                                                     │
│ • Review all findings                                       │
│ • Apply severity calibration                                │
│ • Render BLOCK/WARN/PASS verdict                           │
│ • Create remediation tasks                                  │
└─────────────────────────────────────────────────────────────┘
```

### 5. Formatter System

Formatters transform the results bundle into various outputs:

```python
class Formatter(ABC):
    @abstractmethod
    def format(self, bundle: dict[str, Any]) -> str: ...

    @property
    def file_extension(self) -> str:
        return ".txt"
```

**Available formatters:**

| Formatter | Output | Use Case |
|-----------|--------|----------|
| `JSONFormatter` | `.json` | Programmatic access |
| `SARIFFormatter` | `.sarif` | IDE integration |
| `HTMLFormatter` | `.html` | Visual reports |
| `MarkdownFormatter` | `.md` | Documentation |

### 6. Sandbox Execution

The sandbox provides secure execution of generated payloads:

```
┌─────────────────────────────────────────────────────────────┐
│                     SandboxExecutor                         │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │                  Docker Container                    │   │
│  │                                                      │   │
│  │  • Network: disabled                                 │   │
│  │  • Filesystem: read-only                            │   │
│  │  • Resources: limited (memory, CPU, time)           │   │
│  │  • User: non-root                                   │   │
│  │  • Syscalls: restricted (seccomp)                   │   │
│  │                                                      │   │
│  │  ┌──────────────────────────────────────────────┐   │   │
│  │  │  Payload Execution                           │   │   │
│  │  │  • Validate payload                          │   │   │
│  │  │  • Execute in isolation                      │   │   │
│  │  │  • Capture output                            │   │   │
│  │  │  • Enforce timeout                           │   │   │
│  │  └──────────────────────────────────────────────┘   │   │
│  │                                                      │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  Result: ExecutionResult(exit_code, stdout, stderr, ...)   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## Data Flow

### Complete Analysis Flow

```
Input                    Processing                      Output
─────                    ──────────                      ──────

src/api/          ┌─────────────────────┐
users.py    ───▶  │  File Discovery     │
                  │  (glob patterns)    │
                  └─────────┬───────────┘
                            │
                            ▼
                  ┌─────────────────────┐
                  │  ChaosOrchestrator  │
                  │                     │
                  │  • Risk assessment  │
                  │  • Attack planning  │
                  │  • Agent assignment │
                  └─────────┬───────────┘
                            │
              ┌─────────────┼─────────────┐
              ▼             ▼             ▼
        ┌───────────┐ ┌───────────┐ ┌───────────┐
        │Exploit    │ │Break      │ │Chaos      │
        │Agent      │ │Agent      │ │Agent      │
        └─────┬─────┘ └─────┬─────┘ └─────┬─────┘
              │             │             │
              │    Findings │             │
              └─────────────┼─────────────┘
                            ▼
                  ┌─────────────────────┐
                  │ CrossExamination    │
                  │                     │
                  │ • Validate findings │
                  │ • Reject false +    │
                  └─────────┬───────────┘
                            │
                            ▼
                  ┌─────────────────────┐
                  │      Arbiter        │
                  │                     │───▶  bundle.json
                  │ • Render verdict    │───▶  report.sarif
                  │ • Create tasks      │───▶  report.html
                  └─────────────────────┘
```

### Bead Chain

```
                    ATTACK_PLAN (root)
                         │
        ┌────────────────┼────────────────┐
        │                │                │
        ▼                ▼                ▼
   EXPLOIT_ANALYSIS BREAK_ANALYSIS  CHAOS_ANALYSIS
        │                │                │
        ▼                ▼                ▼
   CROSS_EXAMINATION CROSS_EXAMINATION CROSS_EXAMINATION
        │                │                │
        └────────────────┼────────────────┘
                         │
                         ▼
                  ARBITER_VERDICT
```

## Configuration System

### Configuration Hierarchy

```
Priority (high → low):
1. CLI arguments (--provider, --model, etc.)
2. Environment variables (ADVERSARIAL_PROVIDER, etc.)
3. Project config (.adversarial-debate.toml)
4. User config (~/.config/adversarial-debate/config.toml)
5. Default values
```

### Configuration Schema

```python
@dataclass
class Config:
    provider: ProviderConfig
    logging: LoggingConfig
    sandbox: SandboxConfig
    debug: bool = False
    dry_run: bool = False

@dataclass
class ProviderConfig:
    provider: str = "anthropic"
    api_key: str = ""
    model: str = ""
    timeout_seconds: int = 120
    max_retries: int = 3
    temperature: float = 0.7
    max_tokens: int = 4096

@dataclass
class SandboxConfig:
    use_docker: bool = True
    timeout_seconds: int = 30
    memory_limit_mb: int = 256
    network_disabled: bool = True
```

## Caching System

The cache system reduces API costs and improves performance:

```
┌─────────────────────────────────────────────────────────────┐
│                      Cache Manager                          │
│                                                             │
│  Cache Key = hash(prompt + model + temperature + ...)       │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │                  File Cache                          │   │
│  │                                                      │   │
│  │  ~/.cache/adversarial-debate/                       │   │
│  │  ├── ab/                                            │   │
│  │  │   └── cd1234...json                              │   │
│  │  ├── cd/                                            │   │
│  │  │   └── ef5678...json                              │   │
│  │  └── ...                                            │   │
│  │                                                      │   │
│  │  Features:                                           │   │
│  │  • Content-addressed (hash-based keys)              │   │
│  │  • TTL expiration (default: 7 days)                 │   │
│  │  • Size limits with LRU eviction                    │   │
│  │                                                      │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## Exception Hierarchy

```
AdversarialDebateError
├── AgentError
│   ├── AgentExecutionError
│   ├── AgentParseError
│   └── AgentTimeoutError
│
├── ProviderError
│   ├── ProviderRateLimitError
│   └── ProviderConnectionError
│
├── SandboxError
│   ├── SandboxExecutionError
│   └── SandboxTimeoutError
│
├── StoreError
│   └── BeadValidationError
│
└── ConfigError
    └── ConfigValidationError
```

## Extension Points

### Adding a New Agent

1. **Create agent class** in `agents/`
2. **Implement abstract methods:**
   - `name` — Agent identifier
   - `bead_type` — Type of bead to emit
   - `_build_prompt()` — Construct LLM prompt
   - `_parse_response()` — Parse LLM response
3. **Register in `agents/__init__.py`**

### Adding a New Provider

1. **Create provider class** in `providers/`
2. **Implement `LLMProvider` interface:**
   - `name` — Provider identifier
   - `complete()` — Send completion request
   - `get_model_for_tier()` — Model routing
3. **Register in `providers/__init__.py`**
4. **Add to factory in `get_provider()`**

### Adding a New Formatter

1. **Create formatter class** in `formatters/`
2. **Implement `Formatter` interface:**
   - `format()` — Transform bundle to string
   - `file_extension` — Output file extension
3. **Register in `formatters/__init__.py`**
4. **Add to CLI choices**

## Concurrency Model

```
┌─────────────────────────────────────────────────────────────┐
│                    Async Execution                          │
│                                                             │
│  Main Thread                                                │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  async def run_pipeline():                          │   │
│  │      plan = await orchestrator.run(context)         │   │
│  │                                                      │   │
│  │      # Parallel agent execution                     │   │
│  │      results = await asyncio.gather(                │   │
│  │          exploit_agent.run(ctx1),                   │   │
│  │          break_agent.run(ctx2),                     │   │
│  │          chaos_agent.run(ctx3),                     │   │
│  │      )                                              │   │
│  │                                                      │   │
│  │      verdict = await arbiter.run(all_findings)      │   │
│  │                                                      │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  Thread Pool (for sync operations)                          │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  • File I/O                                         │   │
│  │  • Bead store operations                            │   │
│  │  • Sandbox execution                                │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## Security Considerations

### Trust Boundaries

```
┌─────────────────────────────────────────────────────────────┐
│  UNTRUSTED                                                  │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  • Target code being analysed                       │   │
│  │  • LLM-generated payloads                          │   │
│  │  • LLM responses (may hallucinate)                 │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  SEMI-TRUSTED                                               │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  • User configuration                               │   │
│  │  • Prompt templates                                 │   │
│  │  • Provider API responses                          │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  TRUSTED                                                    │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  • Core framework code                              │   │
│  │  • Sandbox isolation mechanisms                     │   │
│  │  • Bead store integrity                            │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Sandbox Isolation

The Docker sandbox enforces:

| Control | Implementation |
|---------|----------------|
| Network | `--network=none` |
| Filesystem | Read-only root, tmpfs for writes |
| Resources | `--memory`, `--cpu-quota` |
| User | `--user nobody` |
| Capabilities | `--cap-drop=all` |
| Syscalls | Seccomp profile |

## Performance Considerations

### Optimisation Strategies

1. **Parallel agent execution** — Agents without dependencies run concurrently
2. **Response caching** — Identical prompts return cached responses
3. **Incremental analysis** — Only analyse changed files
4. **Model tier routing** — Use smaller models for simple tasks
5. **Early termination** — Stop on critical blocking issues

### Bottlenecks

| Component | Bottleneck | Mitigation |
|-----------|------------|------------|
| LLM API | Rate limits, latency | Caching, retry with backoff |
| File I/O | Large codebases | Incremental analysis |
| Memory | Large responses | Streaming, truncation |
| Network | API timeouts | Timeouts, circuit breaker |

## See Also

- [Event Sourcing](../developers/event-sourcing.md) — Bead system details
- [Agent Reference](agents.md) — Agent specifications
- [Data Structures](data-structures.md) — Type definitions
- [Security Model](../concepts/security-model.md) — Security design
