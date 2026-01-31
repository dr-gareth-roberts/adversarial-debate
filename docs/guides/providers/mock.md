# Mock Provider

The mock provider produces deterministic results without requiring an API key or LLM. Use it for testing, demos, and CI smoke tests.

## Quick Setup

```bash
export LLM_PROVIDER=mock
adversarial-debate run examples/mini-app/
```

No API key, no internet connection, no LLM required.

## When to Use the Mock Provider

**Best for:**
- Getting started and exploring the tool
- CI/CD smoke tests
- Demos and presentations
- Testing integration code
- Offline development

**Not suitable for:**
- Actual security analysis of real code
- Production security scanning
- Accurate vulnerability detection

## How It Works

The mock provider returns pre-defined, deterministic responses:

1. **ExploitAgent** returns fixed SQL injection and command injection findings
2. **BreakAgent** returns fixed boundary condition and race condition findings
3. **ChaosAgent** returns fixed resilience experiment designs
4. **CryptoAgent** returns fixed cryptographic weakness findings
5. **Arbiter** returns a fixed BLOCK verdict

Results are based on the target path, so the same input produces the same output every time.

## Example Output

```bash
$ LLM_PROVIDER=mock adversarial-debate analyze exploit examples/mini-app/app.py

============================================================
ExploitAgent Analysis Results
============================================================
Confidence: 82%

Findings: 2
  [HIGH] SQL injection in user lookup
  [HIGH] Command injection via report runner
```

## Configuration

The mock provider has minimal configuration:

```json
{
  "provider": {
    "provider": "mock"
  }
}
```

### Customising Mock Responses

For testing specific scenarios, you can create custom mock responses by extending the provider:

```python
from adversarial_debate.providers.mock import MockProvider

class CustomMockProvider(MockProvider):
    def _get_mock_findings(self) -> list[dict]:
        return [
            {
                "finding_id": "CUSTOM-001",
                "title": "Custom test finding",
                "severity": "CRITICAL",
                # ...
            }
        ]
```

## CI/CD Usage

The mock provider is ideal for CI smoke tests:

```yaml
# .github/workflows/ci.yml
jobs:
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
```

This verifies:
- The tool installs correctly
- CLI commands work
- Output files are generated
- No runtime errors

## Demo Script

The repository includes a demo script using the mock provider:

```bash
./scripts/demo.sh
# or
make demo
```

This runs a full analysis and displays formatted results.

## Comparison with Real Providers

| Aspect | Mock | Real Provider |
|--------|------|---------------|
| API key | Not needed | Required |
| Internet | Not needed | Required |
| Speed | Instant | Seconds to minutes |
| Accuracy | Deterministic/fake | Actual analysis |
| Cost | Free | Per-token charges |
| Results | Same every time | Varies by code |

## Transitioning to Real Analysis

Once you're ready to analyse real code:

```bash
# Development with mock
LLM_PROVIDER=mock adversarial-debate run src/

# Real analysis with Anthropic
export ANTHROPIC_API_KEY=sk-ant-...
adversarial-debate run src/
```

See [Anthropic Setup](anthropic.md) or other provider guides for configuration.

## See Also

- [Provider Index](index.md) — Compare all providers
- [Quickstart](../../getting-started/quickstart.md) — Getting started with mock
- [CI/CD Integration](../../integration/ci-cd.md) — Using mock in CI
