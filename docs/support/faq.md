# Frequently Asked Questions

Common questions about Adversarial Debate.

## General

### What is Adversarial Debate?

Adversarial Debate is a multi-agent AI security testing framework. It uses multiple specialised AI agents to attack your code from different angles—security vulnerabilities, logic bugs, resilience issues—then consolidates findings with confidence scoring.

### How is it different from other security scanners?

| Aspect | Traditional Scanners | Adversarial Debate |
|--------|---------------------|-------------------|
| Approach | Pattern matching | LLM-powered reasoning |
| Findings | Fixed rules | Contextual analysis |
| False positives | Common | Cross-examination reduces them |
| Exploits | Theoretical | Working payloads generated |
| Coverage | Pre-defined | Adaptive to code patterns |

### What languages are supported?

Primary support is for Python. Partial support exists for:
- JavaScript/TypeScript
- Java
- Go
- Ruby
- PHP

The agents can analyse any text-based code, but detection patterns are optimised for Python.

### Do I need an API key?

Yes, you need an API key for at least one LLM provider:
- **Anthropic** (default) — [console.anthropic.com](https://console.anthropic.com)
- **OpenAI** — [platform.openai.com](https://platform.openai.com)
- **Azure OpenAI** — Azure subscription required

For testing without an API key, use the mock provider:
```bash
adversarial-debate run src/ --provider mock
```

### How much does it cost to run?

Costs depend on your code size and provider:

| Provider | Approximate Cost per 1000 LOC |
|----------|-------------------------------|
| Anthropic Claude Haiku | $0.01 - $0.05 |
| Anthropic Claude Sonnet | $0.10 - $0.50 |
| OpenAI GPT-4o-mini | $0.02 - $0.10 |
| OpenAI GPT-4o | $0.20 - $1.00 |
| Ollama (local) | Free (compute costs) |

Use caching to reduce costs significantly:
```bash
adversarial-debate run src/ --cache
```

---

## Security & Privacy

### Is my code sent to third parties?

Yes, your code is sent to the LLM provider you configure (Anthropic, OpenAI, Azure, or Ollama). Review your provider's data handling policies:
- [Anthropic Privacy Policy](https://www.anthropic.com/privacy)
- [OpenAI Privacy Policy](https://openai.com/policies/privacy-policy)
- [Azure Data Privacy](https://azure.microsoft.com/privacy)

For sensitive code, consider:
- Using Ollama for local analysis
- Self-hosting an LLM
- Azure OpenAI with private endpoints

### Is sandbox execution secure?

The Docker sandbox provides strong isolation:
- Network disabled
- Filesystem read-only
- Resource limits enforced
- Non-root user
- Restricted syscalls

However, no sandbox is 100% secure. For maximum security:
- Use dedicated CI runners
- Don't run untrusted code locally
- Review generated payloads before execution

### Can the AI-generated payloads harm my system?

Payloads are executed only in the sandbox environment with strict isolation. Without the sandbox (`--no-sandbox`), payloads are NOT executed—they're only suggested.

---

## Usage

### How do I analyse only changed files?

```bash
# Compare against baseline
adversarial-debate run src/ --baseline previous-bundle.json

# Or use git diff
git diff --name-only HEAD~1 | xargs adversarial-debate run
```

### How do I reduce false positives?

1. **Use cross-examination** (enabled by default):
   ```bash
   adversarial-debate run src/  # Includes cross-examination
   ```

2. **Adjust thresholds**:
   ```bash
   adversarial-debate run src/ --min-confidence 0.8
   ```

3. **Use suppression files**:
   ```json
   {
     "suppressions": [
       {"pattern": "Missing CSRF.*admin", "reason": "Different auth mechanism"}
     ]
   }
   ```

### How do I only fail on critical issues?

```bash
adversarial-debate run src/ --fail-threshold CRITICAL
```

Or in CI:
```yaml
- run: adversarial-debate run src/ --fail-threshold HIGH
  continue-on-error: false
```

### Can I customise which agents run?

```bash
# Run specific agents
adversarial-debate run src/ --agents exploit,break

# Skip certain agents
adversarial-debate run src/ --skip-agents chaos
```

### How do I analyse a specific function?

```bash
adversarial-debate analyze src/api/users.py::get_user
```

---

## Findings & Verdicts

### What do the severity levels mean?

| Severity | Meaning | Examples |
|----------|---------|----------|
| CRITICAL | Immediate exploit risk | RCE, auth bypass, full data access |
| HIGH | Significant security issue | SQL injection, privilege escalation |
| MEDIUM | Moderate risk | XSS, limited data exposure |
| LOW | Minor issue | Information disclosure, edge cases |

### What do the verdicts mean?

| Verdict | Action | Typical Findings |
|---------|--------|------------------|
| BLOCK | Must fix before shipping | CRITICAL or HIGH severity confirmed issues |
| WARN | Should fix, track in backlog | MEDIUM issues or uncertain HIGH issues |
| PASS | No actionable issues | No findings or all false positives |

### Why are some findings rejected?

Findings are rejected during cross-examination if:
- They're **false positives** (code doesn't actually have the vulnerability)
- They're **not exploitable** (mitigations exist)
- They're **out of scope** (external dependencies, test code)
- They're **duplicates** of other findings

### How is confidence calculated?

Confidence (0.0-1.0) reflects:
- Evidence strength (code snippets, working exploits)
- Agent agreement (multiple agents finding same issue)
- Cross-examination validation
- Context certainty (known frameworks, patterns)

---

## Integration

### Does it work with monorepos?

Yes. Specify paths to analyse:
```bash
adversarial-debate run packages/api packages/auth
```

Or use configuration:
```toml
[analysis]
targets = ["packages/api", "packages/auth"]
exclude = ["packages/legacy"]
```

### Can I use it in a Docker container?

Yes:
```dockerfile
FROM python:3.11-slim

RUN pip install adversarial-debate

# For sandbox (Docker-in-Docker)
RUN apt-get update && apt-get install -y docker.io

ENTRYPOINT ["adversarial-debate"]
```

### Does it support custom LLM endpoints?

Yes, for OpenAI-compatible APIs:
```bash
export OPENAI_API_BASE="https://your-llm-endpoint.com/v1"
export OPENAI_API_KEY="your-key"
adversarial-debate run src/ --provider openai
```

### Can I export findings to Jira/Linear/etc?

Use the JSON output and integrate with your tools:
```bash
adversarial-debate run src/ --format json -o findings.json
# Then process findings.json with your integration script
```

Or use the Python API:
```python
from adversarial_debate import run_analysis

results = run_analysis("src/")
for finding in results["findings"]:
    create_jira_ticket(finding)
```

---

## Performance

### How can I speed up analysis?

1. **Use caching**:
   ```bash
   adversarial-debate run src/ --cache
   ```

2. **Limit scope**:
   ```bash
   adversarial-debate run src/api/  # Critical paths only
   ```

3. **Quick mode**:
   ```bash
   adversarial-debate run src/ --quick
   ```

4. **Parallel execution**:
   ```bash
   adversarial-debate run src/ --max-parallel 4
   ```

### Why does analysis take so long?

Analysis time depends on:
- **Code size** — More files = longer analysis
- **Provider latency** — API response times
- **Model choice** — Larger models are slower
- **Agent count** — More agents = more analysis

For faster results, use smaller models and limit scope.

### Does caching affect result quality?

No. The cache uses content-addressable storage—identical code gets identical cached responses. Results are only served from cache when the code, prompt, and model are exactly the same.

---

## Extending

### Can I add custom agents?

Yes. Create a class extending `Agent`:
```python
from adversarial_debate.agents.base import Agent

class MyAgent(Agent):
    @property
    def name(self) -> str:
        return "MyAgent"

    # ... implement abstract methods
```

See [Extending Agents](../developers/extending-agents.md).

### Can I use a custom LLM?

Yes. Create a provider implementing `LLMProvider`:
```python
from adversarial_debate.providers import LLMProvider

class MyProvider(LLMProvider):
    async def complete(self, messages, **kwargs):
        # ... call your LLM
```

See [Extending Providers](../developers/extending-providers.md).

### Can I add custom output formats?

Yes. Create a formatter implementing `Formatter`:
```python
from adversarial_debate.formatters.base import Formatter

class MyFormatter(Formatter):
    def format(self, bundle: dict) -> str:
        # ... format output
```

See [Extending Formatters](../developers/extending-formatters.md).

---

## Troubleshooting

### Why am I getting rate limit errors?

You've exceeded your provider's API rate limits. Solutions:
1. Wait and retry
2. Enable caching
3. Reduce parallelism
4. Upgrade your API tier

### Why are findings empty for vulnerable code?

1. Check the provider is working (try `--provider mock`)
2. Verify the code is being read (`--debug`)
3. The LLM may have missed the vulnerability (retry or use a larger model)
4. The vulnerability may require specific context

### Where can I get help?

1. Check [Troubleshooting](troubleshooting.md)
2. Search [GitHub Issues](https://github.com/dr-gareth-roberts/adversarial-debate/issues)
3. Open a new issue with debug output

## See Also

- [Troubleshooting](troubleshooting.md) — Common issues
- [Glossary](glossary.md) — Term definitions
- [CLI Reference](../guides/cli-reference.md) — Command options
