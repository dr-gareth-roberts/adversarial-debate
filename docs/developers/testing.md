# Testing Guide

Comprehensive guide to testing agents, providers, and extensions in Adversarial Debate.

## Test Structure

The test suite is organised by type:

```
tests/
├── conftest.py              # Shared fixtures
├── unit/                    # Fast, isolated tests
│   ├── test_agents/         # Agent tests
│   ├── test_providers/      # Provider tests
│   ├── test_config.py       # Configuration tests
│   ├── test_store.py        # Bead store tests
│   └── ...
├── integration/             # Tests with external dependencies
│   └── test_cli.py          # CLI integration tests
├── property/                # Property-based tests
│   ├── test_cache_properties.py
│   └── test_sandbox_security.py
└── benchmarks/              # Performance tests
    └── test_performance.py
```

## Running Tests

### Basic Commands

```bash
# Run all tests
uv run pytest

# Run with verbose output
uv run pytest -v

# Run specific test file
uv run pytest tests/unit/test_store.py

# Run specific test class or function
uv run pytest tests/unit/test_store.py::TestBeadStore::test_append

# Run with coverage
uv run pytest --cov=adversarial_debate --cov-report=html
```

### Test Categories

```bash
# Run only unit tests (fast)
uv run pytest tests/unit/

# Run only integration tests
uv run pytest tests/integration/

# Run property-based tests
uv run pytest tests/property/

# Run benchmarks
uv run pytest tests/benchmarks/ -v
```

### Markers

```bash
# Skip slow tests
uv run pytest -m "not slow"

# Run only tests marked as needing Docker
uv run pytest -m docker

# Run tests requiring API keys
uv run pytest -m integration
```

## Writing Tests

### Using Fixtures

The `conftest.py` provides common fixtures:

```python
import pytest
from adversarial_debate.agents import AgentContext

def test_my_agent(
    mock_provider,       # MockLLMProvider instance
    bead_store,          # Temporary BeadStore
    sample_context,      # Pre-configured AgentContext
    sample_findings,     # Sample finding data
    temp_dir,            # Temporary directory Path
    test_config,         # Test Config instance
):
    # Use fixtures in your test
    pass
```

### Testing Agents

#### Basic Agent Test

```python
import pytest
from adversarial_debate.agents import ExploitAgent

class TestExploitAgent:
    """Tests for ExploitAgent."""

    @pytest.fixture
    def agent(self, mock_provider, test_config):
        """Create agent with mock provider."""
        return ExploitAgent(
            provider=mock_provider,
            config=test_config,
        )

    def test_analyse_sql_injection(
        self,
        agent,
        sample_context,
    ):
        """Test detection of SQL injection."""
        context = sample_context
        context.inputs["code"] = '''
def get_user(user_id: str):
    query = f"SELECT * FROM users WHERE id = '{user_id}'"
    return db.execute(query)
'''

        result = agent.analyse(context)

        assert result.confidence > 0.8
        assert any(
            "sql" in f.get("title", "").lower()
            for f in result.result.get("findings", [])
        )
```

#### Testing with Mock Responses

```python
from tests.conftest import MockLLMProvider
import json

def test_agent_parses_response(test_config):
    """Test agent handles provider response correctly."""
    # Configure mock with specific response
    mock_response = json.dumps({
        "findings": [
            {
                "id": "TEST-001",
                "title": "Test Finding",
                "severity": "HIGH",
                "confidence": 0.9,
            }
        ],
        "confidence": 0.85,
    })

    provider = MockLLMProvider(responses=[mock_response])
    agent = ExploitAgent(provider=provider, config=test_config)

    context = AgentContext(
        thread_id="test",
        task_id="test",
        inputs={"code": "print('hello')"},
    )

    result = agent.analyse(context)

    assert result.result["findings"][0]["title"] == "Test Finding"
    assert provider.call_count == 1
```

#### Testing Error Handling

```python
def test_agent_handles_invalid_json(test_config):
    """Test agent handles malformed provider response."""
    provider = MockLLMProvider(responses=["not valid json"])
    agent = ExploitAgent(provider=provider, config=test_config)

    context = AgentContext(
        thread_id="test",
        task_id="test",
        inputs={"code": "x = 1"},
    )

    result = agent.analyse(context)

    # Agent should handle gracefully
    assert result.confidence < 0.5
    assert len(result.errors) > 0
```

### Testing Providers

#### Mock Provider Tests

```python
import pytest
from adversarial_debate.providers import LLMResponse, Message

class TestMockProvider:
    """Tests for the MockLLMProvider."""

    @pytest.mark.asyncio
    async def test_complete_returns_response(self, mock_provider):
        """Test basic completion."""
        messages = [
            Message(role="user", content="Hello"),
        ]

        response = await mock_provider.complete(messages)

        assert isinstance(response, LLMResponse)
        assert response.content is not None

    @pytest.mark.asyncio
    async def test_tracks_calls(self, mock_provider):
        """Test call tracking."""
        messages = [Message(role="user", content="Test")]

        await mock_provider.complete(messages)
        await mock_provider.complete(messages)

        assert mock_provider.call_count == 2
        assert len(mock_provider.calls) == 2
```

#### Custom Provider Tests

```python
import pytest
from adversarial_debate.providers import LLMProvider, LLMResponse, Message

class TestCustomProvider:
    """Tests for custom provider implementation."""

    @pytest.fixture
    def provider(self):
        """Create custom provider."""
        from my_providers import CustomProvider
        return CustomProvider(api_key="test-key")

    @pytest.mark.asyncio
    async def test_complete_format(self, provider):
        """Test response format."""
        messages = [Message(role="user", content="Test")]

        response = await provider.complete(messages)

        assert isinstance(response, LLMResponse)
        assert response.model is not None
        assert "input_tokens" in response.usage

    @pytest.mark.asyncio
    async def test_handles_timeout(self, provider):
        """Test timeout handling."""
        from adversarial_debate.exceptions import ProviderError

        messages = [Message(role="user", content="Test")]

        with pytest.raises(ProviderError):
            await provider.complete(
                messages,
                timeout=0.001,  # Very short timeout
            )
```

### Testing Formatters

```python
import pytest
from adversarial_debate.formatters import CSVFormatter

class TestCSVFormatter:
    """Tests for CSV formatter."""

    @pytest.fixture
    def sample_bundle(self):
        """Create sample results bundle."""
        return {
            "metadata": {"run_id": "test-001"},
            "summary": {"verdict": "WARN", "total_findings": 1},
            "findings": [
                {
                    "finding_id": "EXP-001",
                    "title": "SQL Injection",
                    "severity": "CRITICAL",
                    "agent": "ExploitAgent",
                    "location": {"file": "app.py", "line": 42},
                    "owasp_category": "A03:2021",
                    "confidence": 0.95,
                    "remediation": "Use parameterised queries",
                }
            ],
        }

    def test_csv_output(self, sample_bundle):
        """Test CSV generation."""
        formatter = CSVFormatter()
        output = formatter.format(sample_bundle)

        assert "Finding ID" in output  # Header
        assert "EXP-001" in output
        assert "SQL Injection" in output
        assert "CRITICAL" in output

    def test_file_extension(self):
        """Test file extension property."""
        formatter = CSVFormatter()
        assert formatter.file_extension == ".csv"

    def test_handles_empty_findings(self):
        """Test with no findings."""
        formatter = CSVFormatter()
        bundle = {
            "metadata": {},
            "summary": {},
            "findings": [],
        }

        output = formatter.format(bundle)

        # Should still have header
        assert "Finding ID" in output
```

### Testing the Bead Store

```python
import pytest
from adversarial_debate.store.beads import BeadStore, Bead, BeadType
from adversarial_debate.exceptions import BeadValidationError, DuplicateBeadError

class TestBeadStore:
    """Tests for BeadStore."""

    def test_append_and_retrieve(self, bead_store, sample_bead):
        """Test basic append and retrieval."""
        bead_store.append(sample_bead)

        retrieved = bead_store.get_by_id(sample_bead.bead_id)

        assert retrieved is not None
        assert retrieved.bead_id == sample_bead.bead_id
        assert retrieved.payload == sample_bead.payload

    def test_idempotent_append(self, bead_store, sample_bead):
        """Test idempotent append prevents duplicates."""
        bead_store.append_idempotent(sample_bead)

        with pytest.raises(DuplicateBeadError):
            bead_store.append_idempotent(sample_bead)

    def test_query_by_type(self, bead_store, sample_bead):
        """Test querying by bead type."""
        bead_store.append(sample_bead)

        results = bead_store.query(
            bead_type=BeadType.EXPLOIT_ANALYSIS,
        )

        assert len(results) == 1
        assert results[0].bead_id == sample_bead.bead_id

    def test_validation_rejects_invalid(self):
        """Test validation catches invalid beads."""
        with pytest.raises(BeadValidationError):
            Bead(
                bead_id="x",  # Too short
                parent_bead_id="root",
                thread_id="test",
                task_id="test",
                timestamp_iso="2024-01-01T00:00:00Z",
                agent="Test",
                bead_type=BeadType.PROPOSAL,
                payload={},
                artefacts=[],
                idempotency_key="test",
                confidence=0.5,
            )
```

## Property-Based Testing

Use Hypothesis for property-based tests:

```python
import pytest
from hypothesis import given, strategies as st
from adversarial_debate.store.beads import Bead, BeadType, BeadStore

class TestBeadProperties:
    """Property-based tests for beads."""

    @given(
        confidence=st.floats(min_value=0.0, max_value=1.0),
        payload_data=st.dictionaries(
            keys=st.text(min_size=1, max_size=10),
            values=st.text(max_size=100),
            max_size=5,
        ),
    )
    def test_bead_roundtrip(self, confidence, payload_data, temp_dir):
        """Test bead serialisation roundtrip."""
        store = BeadStore(temp_dir / "ledger.jsonl")

        bead = Bead(
            bead_id=BeadStore.generate_bead_id(),
            parent_bead_id="root",
            thread_id="test-thread",
            task_id="test-task",
            timestamp_iso=BeadStore.now_iso(),
            agent="TestAgent",
            bead_type=BeadType.PROPOSAL,
            payload=payload_data,
            artefacts=[],
            idempotency_key=f"test-{BeadStore.generate_bead_id()}",
            confidence=confidence,
        )

        store.append(bead)
        retrieved = store.get_by_id(bead.bead_id)

        assert retrieved is not None
        assert retrieved.confidence == bead.confidence
        assert retrieved.payload == bead.payload

    @given(
        text=st.text(min_size=3, max_size=100),
    )
    def test_search_finds_content(self, text, temp_dir):
        """Test search finds content in beads."""
        store = BeadStore(temp_dir / "ledger.jsonl")

        bead = Bead(
            bead_id=BeadStore.generate_bead_id(),
            parent_bead_id="root",
            thread_id="test-thread",
            task_id="test-task",
            timestamp_iso=BeadStore.now_iso(),
            agent="TestAgent",
            bead_type=BeadType.PROPOSAL,
            payload={"searchable": text},
            artefacts=[],
            idempotency_key=f"test-{BeadStore.generate_bead_id()}",
            confidence=0.5,
        )

        store.append(bead)
        results = store.search(text)

        assert len(results) >= 1
```

## Integration Tests

### CLI Integration

```python
import pytest
from click.testing import CliRunner
from adversarial_debate.cli import main

class TestCLIIntegration:
    """Integration tests for CLI."""

    @pytest.fixture
    def runner(self):
        """Create CLI test runner."""
        return CliRunner()

    def test_version(self, runner):
        """Test --version flag."""
        result = runner.invoke(main, ["--version"])
        assert result.exit_code == 0
        assert "adversarial-debate" in result.output

    def test_run_with_mock(self, runner, temp_dir):
        """Test run command with mock provider."""
        # Create test file
        test_file = temp_dir / "test.py"
        test_file.write_text("x = 1")

        result = runner.invoke(main, [
            "run",
            str(test_file),
            "--provider", "mock",
            "--output", str(temp_dir / "output"),
        ])

        assert result.exit_code == 0

    def test_analyse_single_file(self, runner, temp_dir):
        """Test analyse command."""
        test_file = temp_dir / "vulnerable.py"
        test_file.write_text('''
def get_user(id):
    query = f"SELECT * FROM users WHERE id = '{id}'"
    return db.execute(query)
''')

        result = runner.invoke(main, [
            "analyse",
            str(test_file),
            "--provider", "mock",
            "--agent", "exploit",
        ])

        assert result.exit_code == 0
```

### API Integration

```python
import pytest

class TestAPIIntegration:
    """Integration tests requiring real API access."""

    @pytest.fixture
    def api_key(self):
        """Get API key from environment."""
        import os
        key = os.environ.get("ANTHROPIC_API_KEY")
        if not key:
            pytest.skip("ANTHROPIC_API_KEY not set")
        return key

    @pytest.mark.integration
    @pytest.mark.slow
    def test_real_analysis(self, api_key, temp_dir):
        """Test with real API (slow, requires key)."""
        from adversarial_debate import run_analysis

        test_file = temp_dir / "test.py"
        test_file.write_text("print('hello')")

        result = run_analysis(
            target=str(test_file),
            provider="anthropic",
            api_key=api_key,
        )

        assert result is not None
        assert "verdict" in result
```

## Async Tests

For testing async code:

```python
import pytest

class TestAsyncOperations:
    """Tests for async functionality."""

    @pytest.mark.asyncio
    async def test_async_provider(self, mock_provider):
        """Test async provider completion."""
        from adversarial_debate.providers import Message

        messages = [Message(role="user", content="Test")]
        response = await mock_provider.complete(messages)

        assert response.content is not None

    @pytest.mark.asyncio
    async def test_concurrent_agents(self, mock_provider, test_config):
        """Test concurrent agent execution."""
        import asyncio
        from adversarial_debate.agents import ExploitAgent, BreakAgent

        exploit = ExploitAgent(provider=mock_provider, config=test_config)
        break_agent = BreakAgent(provider=mock_provider, config=test_config)

        context = AgentContext(
            thread_id="test",
            task_id="test",
            inputs={"code": "x = 1"},
        )

        # Run concurrently
        results = await asyncio.gather(
            asyncio.to_thread(exploit.analyse, context),
            asyncio.to_thread(break_agent.analyse, context),
        )

        assert len(results) == 2
```

## Mocking External Services

### Mocking Docker

```python
import pytest
from unittest.mock import patch, MagicMock

class TestSandbox:
    """Tests for sandbox execution."""

    @patch("docker.from_env")
    def test_docker_execution(self, mock_docker):
        """Test Docker sandbox without real Docker."""
        from adversarial_debate.sandbox import DockerSandbox

        # Configure mock
        mock_client = MagicMock()
        mock_docker.return_value = mock_client
        mock_container = MagicMock()
        mock_container.wait.return_value = {"StatusCode": 0}
        mock_container.logs.return_value = b"output"
        mock_client.containers.run.return_value = mock_container

        sandbox = DockerSandbox()
        result = sandbox.execute("print('hello')")

        assert result["exit_code"] == 0
        mock_client.containers.run.assert_called_once()
```

### Mocking HTTP Requests

```python
import pytest
from unittest.mock import patch, AsyncMock

class TestProviderHTTP:
    """Tests for provider HTTP calls."""

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient.post")
    async def test_api_call(self, mock_post):
        """Test API call without network."""
        from adversarial_debate.providers.anthropic import AnthropicProvider

        mock_response = AsyncMock()
        mock_response.json.return_value = {
            "content": [{"type": "text", "text": "response"}],
            "model": "claude-sonnet-4-20250514",
            "usage": {"input_tokens": 10, "output_tokens": 20},
        }
        mock_post.return_value = mock_response

        provider = AnthropicProvider(api_key="test-key")
        result = await provider.complete([
            Message(role="user", content="Test"),
        ])

        assert result.content == "response"
```

## Test Fixtures Reference

### Available Fixtures

| Fixture | Description |
|---------|-------------|
| `clean_environment` | Restores environment after test (autouse) |
| `temp_dir` | Temporary directory as Path |
| `test_config` | Pre-configured Config object |
| `mock_provider` | MockLLMProvider instance |
| `mock_provider_factory` | MockLLMProvider class |
| `bead_store` | BeadStore with temp ledger |
| `sample_bead` | Pre-configured Bead |
| `sample_context` | AgentContext with test data |
| `sample_findings` | List of finding dicts |
| `exploit_agent_response` | JSON for ExploitAgent |
| `arbiter_response` | JSON for Arbiter |
| `orchestrator_response` | JSON for ChaosOrchestrator |

### Creating Custom Fixtures

```python
# In conftest.py or test file
import pytest

@pytest.fixture
def my_custom_fixture(mock_provider, test_config):
    """Create custom test fixture."""
    from adversarial_debate.agents import ExploitAgent

    return ExploitAgent(
        provider=mock_provider,
        config=test_config,
    )

@pytest.fixture
def vulnerable_code():
    """Sample vulnerable code for testing."""
    return '''
import sqlite3

def get_user(user_id: str) -> dict:
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    cursor.execute(f"SELECT * FROM users WHERE id = '{user_id}'")
    return cursor.fetchone()

def run_command(cmd: str) -> str:
    import os
    return os.system(cmd)
'''
```

## Best Practices

### 1. Test One Thing

```python
# Good - focused test
def test_detects_sql_injection(agent, context):
    context.inputs["code"] = "query = f\"SELECT * FROM x WHERE id = '{id}'\""
    result = agent.analyse(context)
    assert any("sql" in f["title"].lower() for f in result.result["findings"])

# Bad - testing multiple things
def test_agent_works(agent, context):
    result = agent.analyse(context)
    assert result.confidence > 0
    assert len(result.result["findings"]) > 0
    assert result.errors == []
    assert result.agent_name == "ExploitAgent"
```

### 2. Use Descriptive Names

```python
# Good
def test_raises_validation_error_when_confidence_exceeds_one():
    ...

# Bad
def test_error():
    ...
```

### 3. Arrange-Act-Assert

```python
def test_query_returns_matching_beads(bead_store):
    # Arrange
    bead = Bead(
        bead_id="B-001",
        bead_type=BeadType.EXPLOIT_ANALYSIS,
        # ...
    )
    bead_store.append(bead)

    # Act
    results = bead_store.query(bead_type=BeadType.EXPLOIT_ANALYSIS)

    # Assert
    assert len(results) == 1
    assert results[0].bead_id == "B-001"
```

### 4. Isolate Tests

```python
# Good - each test is independent
def test_first(bead_store):
    bead_store.append(bead1)
    assert bead_store.count() == 1

def test_second(bead_store):  # Gets fresh store
    bead_store.append(bead2)
    assert bead_store.count() == 1

# Bad - tests depend on each other
class TestSharedState:
    store = BeadStore()  # Shared across tests!

    def test_first(self):
        self.store.append(bead1)

    def test_second(self):  # Depends on test_first!
        assert self.store.count() == 1
```

### 5. Test Edge Cases

```python
class TestEdgeCases:
    def test_empty_input(self, agent):
        context = AgentContext(thread_id="t", task_id="t", inputs={})
        result = agent.analyse(context)
        assert result is not None

    def test_very_large_input(self, agent):
        context = AgentContext(
            thread_id="t",
            task_id="t",
            inputs={"code": "x = 1\n" * 10000},
        )
        result = agent.analyse(context)
        assert result is not None

    def test_unicode_input(self, agent):
        context = AgentContext(
            thread_id="t",
            task_id="t",
            inputs={"code": "# 中文注释\nprint('héllo')"},
        )
        result = agent.analyse(context)
        assert result is not None
```

## See Also

- [Extending Agents](extending-agents.md) — Creating testable agents
- [Extending Providers](extending-providers.md) — Testing providers
- [Architecture](../reference/architecture.md) — System design
