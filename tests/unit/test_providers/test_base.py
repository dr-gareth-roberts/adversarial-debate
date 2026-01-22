"""Tests for base provider classes."""

import pytest

from adversarial_debate.providers.base import (
    LLMResponse,
    Message,
    ModelTier,
    ProviderConfig,
    StreamChunk,
)


class TestMessage:
    """Tests for Message dataclass."""

    def test_create_message(self):
        """Test creating a message."""
        msg = Message(role="user", content="Hello")
        assert msg.role == "user"
        assert msg.content == "Hello"

    def test_message_roles(self):
        """Test different message roles."""
        for role in ["system", "user", "assistant"]:
            msg = Message(role=role, content="test")
            assert msg.role == role


class TestProviderConfig:
    """Tests for ProviderConfig dataclass."""

    def test_default_config(self):
        """Test default configuration values."""
        config = ProviderConfig()
        assert config.api_key is None
        assert config.base_url is None
        assert config.model is None
        assert config.temperature == 0.7
        assert config.max_tokens == 4096
        assert config.timeout == 120.0
        assert config.extra == {}

    def test_custom_config(self):
        """Test custom configuration values."""
        config = ProviderConfig(
            api_key="test-key",
            base_url="https://api.example.com",
            model="test-model",
            temperature=0.5,
            max_tokens=2048,
            timeout=60.0,
            extra={"custom": "value"},
        )
        assert config.api_key == "test-key"
        assert config.base_url == "https://api.example.com"
        assert config.model == "test-model"
        assert config.temperature == 0.5
        assert config.max_tokens == 2048
        assert config.timeout == 60.0
        assert config.extra == {"custom": "value"}


class TestLLMResponse:
    """Tests for LLMResponse dataclass."""

    def test_create_response(self):
        """Test creating an LLM response."""
        response = LLMResponse(
            content="Hello, world!",
            model="test-model",
            usage={"input_tokens": 10, "output_tokens": 5},
            finish_reason="stop",
        )
        assert response.content == "Hello, world!"
        assert response.model == "test-model"
        assert response.usage["input_tokens"] == 10
        assert response.usage["output_tokens"] == 5
        assert response.finish_reason == "stop"

    def test_response_defaults(self):
        """Test response default values."""
        response = LLMResponse(
            content="test",
            model="model",
            usage={"input_tokens": 0, "output_tokens": 0},
        )
        assert response.finish_reason is None
        assert response.raw_response is None


class TestStreamChunk:
    """Tests for StreamChunk dataclass."""

    def test_create_chunk(self):
        """Test creating a stream chunk."""
        chunk = StreamChunk(content="Hello")
        assert chunk.content == "Hello"
        assert chunk.is_final is False
        assert chunk.finish_reason is None
        assert chunk.usage is None

    def test_final_chunk(self):
        """Test creating a final stream chunk."""
        chunk = StreamChunk(
            content="",
            is_final=True,
            finish_reason="stop",
            usage={"input_tokens": 10, "output_tokens": 20},
        )
        assert chunk.is_final is True
        assert chunk.finish_reason == "stop"
        assert chunk.usage is not None


class TestModelTier:
    """Tests for ModelTier enum."""

    def test_tier_values(self):
        """Test model tier values."""
        assert ModelTier.LOCAL_SMALL.value == "local_small"
        assert ModelTier.HOSTED_SMALL.value == "hosted_small"
        assert ModelTier.HOSTED_LARGE.value == "hosted_large"

    def test_tier_is_string(self):
        """Test that ModelTier can be used as string."""
        assert str(ModelTier.LOCAL_SMALL) == "local_small"
        assert ModelTier.HOSTED_LARGE == "hosted_large"
