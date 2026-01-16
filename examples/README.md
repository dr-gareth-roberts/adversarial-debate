# Examples

This directory contains examples demonstrating how to use Adversarial Debate.

## Quick Start Examples

| Example | Description |
|---------|-------------|
| [basic_analysis.py](basic_analysis.py) | Simple code analysis with all agents |
| [single_agent.py](single_agent.py) | Using a single agent for targeted analysis |
| [custom_agent.py](custom_agent.py) | Creating a custom agent |
| [sandbox_execution.py](sandbox_execution.py) | Safe code execution in sandbox |

## Integration Examples

| Example | Description |
|---------|-------------|
| [ci_integration.py](ci_integration.py) | CI/CD pipeline integration |
| [batch_analysis.py](batch_analysis.py) | Analyzing multiple files |
| [webhook_handler.py](webhook_handler.py) | GitHub webhook for PR analysis |

## Advanced Examples

| Example | Description |
|---------|-------------|
| [custom_provider.py](custom_provider.py) | Implementing a custom LLM provider |
| [streaming_results.py](streaming_results.py) | Streaming analysis results |
| [bead_queries.py](bead_queries.py) | Querying the bead store |

## Running Examples

1. Install the package:
   ```bash
   pip install adversarial-debate
   ```

2. Set your API key:
   ```bash
   export ANTHROPIC_API_KEY=your-key-here
   ```

3. Run an example:
   ```bash
   python examples/basic_analysis.py
   ```

## Sample Vulnerable Code

The `vulnerable_samples/` directory contains intentionally vulnerable code for testing:

- `sql_injection.py` - SQL injection vulnerabilities
- `command_injection.py` - Command injection vulnerabilities
- `auth_bypass.py` - Authentication bypass issues
- `race_condition.py` - Race condition bugs
- `resource_exhaustion.py` - Resource exhaustion issues

**Warning:** These samples contain intentional vulnerabilities for educational purposes.
Do not use this code in production.
