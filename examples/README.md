# Examples

This directory contains examples demonstrating how to use Adversarial Debate.

## Quick Start Examples

| Example | Description |
|---------|-------------|
| [basic_analysis.py](basic_analysis.py) | Simple code analysis with all agents |
| [single_agent.py](single_agent.py) | Using a single agent for targeted analysis |
| [sandbox_execution.py](sandbox_execution.py) | Safe code execution in sandbox |

## Integration Examples

| Example | Description |
|---------|-------------|
| [ci_integration.py](ci_integration.py) | CI/CD pipeline integration |
| [workflows/security-analysis.yml](workflows/security-analysis.yml) | Example GitHub Actions workflow using the tool |
| [mini-app/](mini-app/) | Intentionally vulnerable mini app for deterministic demos |

## Running Examples

1. Install dependencies:
   ```bash
   uv sync --extra dev
   ```

2. (Optional) Set your API key:
   ```bash
   export ANTHROPIC_API_KEY=your-key-here
   ```

3. Run an example:
   ```bash
   uv run python examples/basic_analysis.py
   ```

## Sample Vulnerable Code

The `vulnerable_samples/` directory contains intentionally vulnerable code for testing:

- `sql_injection.py` - SQL injection vulnerabilities
- `command_injection.py` - Command injection vulnerabilities

For a more complete deterministic demo target, see `mini-app/`.

**Warning:** These samples contain intentional vulnerabilities for educational purposes.
Do not use this code in production.
