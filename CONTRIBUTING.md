# Contributing to adversarial-debate

Thank you for your interest in contributing to adversarial-debate! This document provides guidelines and information for contributors.

## Development Setup

### Prerequisites

- Python 3.11 or 3.12
- [uv](https://docs.astral.sh/uv/) package manager

### Getting Started

1. Clone the repository:
   ```bash
   git clone https://github.com/your-username/adversarial-debate.git
   cd adversarial-debate
   ```

2. Install dependencies:
   ```bash
   uv sync --dev
   ```

3. Verify your setup:
   ```bash
   uv run pytest tests/ -v
   uv run adversarial-debate --help
   ```

## Development Workflow

### Running Tests

```bash
# Run all tests
uv run pytest tests/ -v

# Run with coverage
uv run pytest tests/ --cov=adversarial_debate --cov-report=html

# Run specific test file
uv run pytest tests/unit/test_verdict.py -v
```

### Code Quality

We use several tools to maintain code quality:

```bash
# Linting
uv run ruff check src/

# Auto-fix linting issues
uv run ruff check src/ --fix

# Formatting
uv run ruff format src/

# Type checking
uv run mypy src/adversarial_debate --ignore-missing-imports
```

### Pre-commit Checks

Before committing, ensure:

1. All tests pass: `uv run pytest tests/`
2. Linting passes: `uv run ruff check src/`
3. Formatting is correct: `uv run ruff format --check src/`
4. Types check: `uv run mypy src/adversarial_debate --ignore-missing-imports`

## Code Style

### General Guidelines

- Follow PEP 8 style guidelines
- Use type hints for all function signatures
- Write docstrings for all public functions and classes
- Keep functions focused and single-purpose
- Prefer explicit over implicit

### Docstring Format

Use Google-style docstrings:

```python
def analyze_code(code: str, focus_areas: list[str] | None = None) -> AnalysisResult:
    """Analyze code for security vulnerabilities.

    Args:
        code: The source code to analyze.
        focus_areas: Optional list of specific areas to focus on.

    Returns:
        AnalysisResult containing findings and confidence score.

    Raises:
        AnalysisError: If the code cannot be parsed.
    """
```

### Import Organization

Imports should be organized in this order:
1. Standard library imports
2. Third-party imports
3. Local application imports

Use `ruff` to automatically sort imports.

## Architecture

### Agent Design

Agents follow a consistent pattern:

1. **Stateless execution**: Agents receive context, process, and return results
2. **Bead emission**: All actions produce beads for coordination and audit
3. **Structured output**: JSON-parseable results with confidence scores

### Adding a New Agent

1. Create a new file in `src/adversarial_debate/agents/`
2. Extend the `Agent` base class
3. Implement required methods: `name`, `bead_type`, `_build_prompt`, `_parse_response`
4. Add to `__init__.py` exports
5. Add tests in `tests/unit/test_agents/`

Example:

```python
from adversarial_debate.agents.base import Agent, AgentContext, AgentOutput
from adversarial_debate.store import BeadType

class MyAgent(Agent):
    @property
    def name(self) -> str:
        return "MyAgent"

    @property
    def bead_type(self) -> BeadType:
        return BeadType.ANALYSIS

    def _build_prompt(self, context: AgentContext) -> list[Message]:
        # Build prompt messages
        ...

    def _parse_response(self, response: str, context: AgentContext) -> AgentOutput:
        # Parse LLM response into structured output
        ...
```

## Testing

### Test Organization

- `tests/unit/`: Unit tests for individual components
- `tests/integration/`: Integration tests for CLI and workflows

### Writing Tests

- Test one thing per test function
- Use descriptive test names
- Include edge cases and error conditions
- Mock external dependencies (LLM providers, file system)

### Test Fixtures

Common fixtures are defined in `tests/conftest.py`:

- `test_config`: Test configuration
- `mock_provider`: Mock LLM provider
- `bead_store`: In-memory bead store
- `sample_context`: Sample agent context

## Pull Request Process

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Make your changes with tests
4. Ensure all checks pass
5. Submit a pull request with a clear description

### PR Guidelines

- Keep PRs focused on a single change
- Include tests for new functionality
- Update documentation as needed
- Reference any related issues

## Reporting Issues

When reporting bugs, please include:

- Python version
- Operating system
- Steps to reproduce
- Expected vs actual behavior
- Error messages and stack traces

## Questions?

Feel free to open an issue for questions or discussions about the project.
