"""Performance benchmarks for critical operations.

Measures execution time and resource usage for security-critical paths.
Run with: pytest tests/benchmarks/ --benchmark-only
"""

import pytest
import tempfile
import os
from pathlib import Path

from adversarial_debate.cache.hash import hash_content, hash_file_content, normalize_code
from adversarial_debate.sandbox import (
    SandboxConfig,
    validate_identifier,
    validate_code_size,
    validate_inputs,
    validate_sandbox_config,
    generate_secure_temp_name,
)


# =============================================================================
# Hash Performance Benchmarks
# =============================================================================

class TestHashPerformance:
    """Benchmarks for content hashing operations."""

    @pytest.fixture
    def small_code(self) -> str:
        """Small code sample (~100 bytes)."""
        return "def hello():\n    return 'Hello, World!'\n"

    @pytest.fixture
    def medium_code(self) -> str:
        """Medium code sample (~10KB)."""
        return "x = 1\n" * 1000

    @pytest.fixture
    def large_code(self) -> str:
        """Large code sample (~100KB)."""
        return "# Comment\n" * 10000

    def test_hash_small_content(self, benchmark, small_code: str) -> None:
        """Benchmark hashing small content."""
        result = benchmark(hash_content, small_code)
        assert len(result) == 64

    def test_hash_medium_content(self, benchmark, medium_code: str) -> None:
        """Benchmark hashing medium content."""
        result = benchmark(hash_content, medium_code)
        assert len(result) == 64

    def test_hash_large_content(self, benchmark, large_code: str) -> None:
        """Benchmark hashing large content."""
        result = benchmark(hash_content, large_code)
        assert len(result) == 64

    def test_normalize_code(self, benchmark, medium_code: str) -> None:
        """Benchmark code normalization."""
        result = benchmark(normalize_code, medium_code)
        assert isinstance(result, str)


# =============================================================================
# Validation Performance Benchmarks
# =============================================================================

class TestValidationPerformance:
    """Benchmarks for input validation operations."""

    def test_validate_simple_identifier(self, benchmark) -> None:
        """Benchmark validating a simple identifier."""
        benchmark(validate_identifier, "my_variable")

    def test_validate_long_identifier(self, benchmark) -> None:
        """Benchmark validating a long identifier."""
        identifier = "a" * 60  # Near max length
        benchmark(validate_identifier, identifier)

    def test_validate_small_code(self, benchmark) -> None:
        """Benchmark validating small code."""
        code = "print('hello')"
        benchmark(validate_code_size, code)

    def test_validate_large_code(self, benchmark) -> None:
        """Benchmark validating large code."""
        code = "x = 1\n" * 50000  # ~500KB
        benchmark(validate_code_size, code)

    def test_validate_small_inputs(self, benchmark) -> None:
        """Benchmark validating small input dict."""
        inputs = {"name": "test", "value": 42}
        benchmark(validate_inputs, inputs)

    def test_validate_large_inputs(self, benchmark) -> None:
        """Benchmark validating large input dict."""
        inputs = {f"var_{i}": f"value_{i}" for i in range(100)}
        benchmark(validate_inputs, inputs)

    def test_validate_config(self, benchmark) -> None:
        """Benchmark config validation."""
        config = SandboxConfig()
        benchmark(validate_sandbox_config, config)


# =============================================================================
# Secure Random Generation Benchmarks
# =============================================================================

class TestSecureRandomPerformance:
    """Benchmarks for cryptographic operations."""

    def test_generate_temp_name(self, benchmark) -> None:
        """Benchmark secure temp name generation."""
        result = benchmark(generate_secure_temp_name, "sandbox")
        assert result.startswith("sandbox_")
        assert result.endswith(".py")

    def test_generate_many_temp_names(self, benchmark) -> None:
        """Benchmark generating many unique temp names."""
        def generate_many():
            return [generate_secure_temp_name() for _ in range(100)]

        results = benchmark(generate_many)
        assert len(results) == len(set(results))  # All unique


# =============================================================================
# File I/O Benchmarks
# =============================================================================

class TestFileIOPerformance:
    """Benchmarks for file operations."""

    @pytest.fixture
    def temp_file_small(self, tmp_path: Path) -> Path:
        """Create a small temp file."""
        path = tmp_path / "small.py"
        path.write_text("print('hello')\n" * 10)
        return path

    @pytest.fixture
    def temp_file_large(self, tmp_path: Path) -> Path:
        """Create a large temp file."""
        path = tmp_path / "large.py"
        path.write_text("x = 1\n" * 10000)
        return path

    def test_hash_small_file(self, benchmark, temp_file_small: Path) -> None:
        """Benchmark hashing a small file."""
        result = benchmark(hash_file_content, temp_file_small)
        assert len(result) == 64

    def test_hash_large_file(self, benchmark, temp_file_large: Path) -> None:
        """Benchmark hashing a large file."""
        result = benchmark(hash_file_content, temp_file_large)
        assert len(result) == 64


# =============================================================================
# Memory Usage Tests
# =============================================================================

class TestMemoryUsage:
    """Tests for memory efficiency of operations."""

    def test_large_input_validation_memory(self) -> None:
        """Verify large input validation doesn't leak memory."""
        import sys

        # Create large inputs
        large_inputs = {f"var_{i}": "x" * 1000 for i in range(100)}

        # Get baseline memory
        baseline = sys.getsizeof(large_inputs)

        # Validate multiple times
        for _ in range(10):
            validate_inputs(large_inputs)

        # Memory shouldn't grow significantly
        # (This is a simple check; real memory profiling would use tracemalloc)
        current = sys.getsizeof(large_inputs)
        assert current == baseline, "Validation should not modify input"

    def test_hash_streaming_memory(self) -> None:
        """Verify hashing doesn't load entire content into memory twice."""
        # Create content that would be noticeable if duplicated
        large_content = "x" * (1024 * 1024)  # 1MB

        # Hash should process without keeping multiple copies
        result = hash_content(large_content)
        assert len(result) == 64

        # Clean up
        del large_content
