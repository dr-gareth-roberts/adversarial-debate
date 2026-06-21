"""Comprehensive tests for Ollama provider complete() method and related functionality."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
import pytest

from adversarial_debate.providers.base import Message, ModelTier, ProviderConfig
from adversarial_debate.providers.ollama import OllamaProvider


class TestOllamaComplete:
    """Tests for OllamaProvider.complete() method."""

    @pytest.fixture
    def provider(self):
        """Create an OllamaProvider instance."""
        return OllamaProvider()

    @pytest.fixture
    def mock_response(self):
        """Create a mock aiohttp response."""
        response = AsyncMock()
        response.status = 200
        response.json = AsyncMock()
        response.raise_for_status = MagicMock()
        return response

    @pytest.mark.asyncio
    async def test_complete_basic_call(self, provider, mock_response):
        """Test basic complete() call with minimal parameters."""
        messages = [Message(role="user", content="Hello")]
        
        mock_response.json.return_value = {
            "message": {"content": "Hi there!"},
            "model": "llama3.1:8b",
            "prompt_eval_count": 10,
            "eval_count": 5,
            "done_reason": "stop",
        }

        with patch.object(provider, '_get_session') as mock_session:
            mock_session_obj = AsyncMock()
            mock_session_obj.post = MagicMock(return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_response)))
            mock_session.return_value = mock_session_obj

            result = await provider.complete(messages)

            assert result.content == "Hi there!"
            assert result.model == "llama3.1:8b"
            assert result.usage["input_tokens"] == 10
            assert result.usage["output_tokens"] == 5
            assert result.finish_reason == "stop"

    @pytest.mark.asyncio
    async def test_complete_with_custom_model(self, provider, mock_response):
        """Test complete() with custom model parameter."""
        messages = [Message(role="user", content="Test")]
        
        mock_response.json.return_value = {
            "message": {"content": "Response"},
            "model": "custom-model",
            "prompt_eval_count": 5,
            "eval_count": 3,
        }

        with patch.object(provider, '_get_session') as mock_session:
            mock_session_obj = AsyncMock()
            mock_session_obj.post = MagicMock(return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_response)))
            mock_session.return_value = mock_session_obj

            result = await provider.complete(messages, model="custom-model")

            assert result.model == "custom-model"

    @pytest.mark.asyncio
    async def test_complete_with_temperature(self, provider, mock_response):
        """Test complete() with temperature parameter."""
        messages = [Message(role="user", content="Test")]
        
        mock_response.json.return_value = {
            "message": {"content": "Response"},
            "model": "llama3.1:8b",
        }

        with patch.object(provider, '_get_session') as mock_session:
            mock_session_obj = AsyncMock()
            mock_post = MagicMock(return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_response)))
            mock_session_obj.post = mock_post
            mock_session.return_value = mock_session_obj

            await provider.complete(messages, temperature=0.7)

            # Verify temperature was passed in request body
            call_args = mock_post.call_args
            request_body = call_args[1]['json']
            assert request_body['options']['temperature'] == 0.7

    @pytest.mark.asyncio
    async def test_complete_with_max_tokens(self, provider, mock_response):
        """Test complete() with max_tokens parameter."""
        messages = [Message(role="user", content="Test")]
        
        mock_response.json.return_value = {
            "message": {"content": "Response"},
            "model": "llama3.1:8b",
        }

        with patch.object(provider, '_get_session') as mock_session:
            mock_session_obj = AsyncMock()
            mock_post = MagicMock(return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_response)))
            mock_session_obj.post = mock_post
            mock_session.return_value = mock_session_obj

            await provider.complete(messages, max_tokens=100)

            # Verify max_tokens was passed as num_predict
            call_args = mock_post.call_args
            request_body = call_args[1]['json']
            assert request_body['options']['num_predict'] == 100

    @pytest.mark.asyncio
    async def test_complete_with_json_mode(self, provider, mock_response):
        """Test complete() with json_mode enabled."""
        messages = [Message(role="user", content="Test")]
        
        mock_response.json.return_value = {
            "message": {"content": '{"result": "success"}'},
            "model": "llama3.1:8b",
        }

        with patch.object(provider, '_get_session') as mock_session:
            mock_session_obj = AsyncMock()
            mock_post = MagicMock(return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_response)))
            mock_session_obj.post = mock_post
            mock_session.return_value = mock_session_obj

            await provider.complete(messages, json_mode=True)

            # Verify format=json was added to request
            call_args = mock_post.call_args
            request_body = call_args[1]['json']
            assert request_body['format'] == "json"

    @pytest.mark.asyncio
    async def test_complete_message_conversion(self, provider, mock_response):
        """Test that messages are correctly converted to Ollama format."""
        messages = [
            Message(role="system", content="You are helpful"),
            Message(role="user", content="Hello"),
            Message(role="assistant", content="Hi!"),
            Message(role="user", content="How are you?"),
        ]
        
        mock_response.json.return_value = {
            "message": {"content": "I'm good!"},
            "model": "llama3.1:8b",
        }

        with patch.object(provider, '_get_session') as mock_session:
            mock_session_obj = AsyncMock()
            mock_post = MagicMock(return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_response)))
            mock_session_obj.post = mock_post
            mock_session.return_value = mock_session_obj

            await provider.complete(messages)

            # Verify message format
            call_args = mock_post.call_args
            request_body = call_args[1]['json']
            assert len(request_body['messages']) == 4
            assert request_body['messages'][0] == {"role": "system", "content": "You are helpful"}
            assert request_body['messages'][1] == {"role": "user", "content": "Hello"}

    @pytest.mark.asyncio
    async def test_complete_empty_response(self, provider, mock_response):
        """Test complete() with empty response content."""
        messages = [Message(role="user", content="Test")]
        
        mock_response.json.return_value = {
            "message": {"content": ""},
            "model": "llama3.1:8b",
        }

        with patch.object(provider, '_get_session') as mock_session:
            mock_session_obj = AsyncMock()
            mock_session_obj.post = MagicMock(return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_response)))
            mock_session.return_value = mock_session_obj

            result = await provider.complete(messages)

            assert result.content == ""

    @pytest.mark.asyncio
    async def test_complete_missing_message_field(self, provider, mock_response):
        """Test complete() when response is missing message field."""
        messages = [Message(role="user", content="Test")]
        
        mock_response.json.return_value = {
            "model": "llama3.1:8b",
        }

        with patch.object(provider, '_get_session') as mock_session:
            mock_session_obj = AsyncMock()
            mock_session_obj.post = MagicMock(return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_response)))
            mock_session.return_value = mock_session_obj

            result = await provider.complete(messages)

            assert result.content == ""

    @pytest.mark.asyncio
    async def test_complete_http_error(self, provider):
        """Test complete() when HTTP error occurs."""
        messages = [Message(role="user", content="Test")]
        
        error_response = AsyncMock()
        error_response.raise_for_status = MagicMock(side_effect=aiohttp.ClientResponseError(
            request_info=MagicMock(),
            history=(),
            status=404,
            message="Not Found"
        ))

        with patch.object(provider, '_get_session') as mock_session:
            mock_session_obj = AsyncMock()
            mock_session_obj.post = MagicMock(return_value=AsyncMock(__aenter__=AsyncMock(return_value=error_response)))
            mock_session.return_value = mock_session_obj

            with pytest.raises(aiohttp.ClientResponseError):
                await provider.complete(messages)

    @pytest.mark.asyncio
    async def test_complete_connection_error(self, provider):
        """Test complete() when connection error occurs."""
        messages = [Message(role="user", content="Test")]

        with patch.object(provider, '_get_session') as mock_session:
            mock_session_obj = AsyncMock()
            mock_session_obj.post = MagicMock(side_effect=aiohttp.ClientConnectionError("Connection failed"))
            mock_session.return_value = mock_session_obj

            with pytest.raises(aiohttp.ClientConnectionError):
                await provider.complete(messages)

    @pytest.mark.asyncio
    async def test_complete_url_construction(self, provider, mock_response):
        """Test that complete() constructs correct URL."""
        messages = [Message(role="user", content="Test")]
        
        mock_response.json.return_value = {
            "message": {"content": "Response"},
            "model": "llama3.1:8b",
        }

        with patch.object(provider, '_get_session') as mock_session:
            mock_session_obj = AsyncMock()
            mock_post = MagicMock(return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_response)))
            mock_session_obj.post = mock_post
            mock_session.return_value = mock_session_obj

            await provider.complete(messages)

            # Verify URL
            call_args = mock_post.call_args
            assert call_args[0][0] == "http://localhost:11434/api/chat"

    @pytest.mark.asyncio
    async def test_complete_stream_false(self, provider, mock_response):
        """Test that complete() sets stream=False in request."""
        messages = [Message(role="user", content="Test")]
        
        mock_response.json.return_value = {
            "message": {"content": "Response"},
            "model": "llama3.1:8b",
        }

        with patch.object(provider, '_get_session') as mock_session:
            mock_session_obj = AsyncMock()
            mock_post = MagicMock(return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_response)))
            mock_session_obj.post = mock_post
            mock_session.return_value = mock_session_obj

            await provider.complete(messages)

            # Verify stream=False
            call_args = mock_post.call_args
            request_body = call_args[1]['json']
            assert request_body['stream'] is False


class TestOllamaListModels:
    """Tests for OllamaProvider.list_models() method."""

    @pytest.fixture
    def provider(self):
        """Create an OllamaProvider instance."""
        return OllamaProvider()

    @pytest.mark.asyncio
    async def test_list_models_success(self, provider):
        """Test successful list_models() call."""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.raise_for_status = MagicMock()
        mock_response.json = AsyncMock(return_value={
            "models": [
                {"name": "llama3.1:8b", "size": 4000000000},
                {"name": "llama3.2:3b", "size": 2000000000},
            ]
        })

        with patch.object(provider, '_get_session') as mock_session:
            mock_session_obj = AsyncMock()
            mock_session_obj.get = MagicMock(return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_response)))
            mock_session.return_value = mock_session_obj

            models = await provider.list_models()

            assert len(models) == 2
            assert models[0]["name"] == "llama3.1:8b"
            assert models[1]["name"] == "llama3.2:3b"

    @pytest.mark.asyncio
    async def test_list_models_empty(self, provider):
        """Test list_models() with no models available."""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.raise_for_status = MagicMock()
        mock_response.json = AsyncMock(return_value={"models": []})

        with patch.object(provider, '_get_session') as mock_session:
            mock_session_obj = AsyncMock()
            mock_session_obj.get = MagicMock(return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_response)))
            mock_session.return_value = mock_session_obj

            models = await provider.list_models()

            assert models == []

    @pytest.mark.asyncio
    async def test_list_models_invalid_response(self, provider):
        """Test list_models() with invalid response format."""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.raise_for_status = MagicMock()
        mock_response.json = AsyncMock(return_value={"models": "not a list"})

        with patch.object(provider, '_get_session') as mock_session:
            mock_session_obj = AsyncMock()
            mock_session_obj.get = MagicMock(return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_response)))
            mock_session.return_value = mock_session_obj

            models = await provider.list_models()

            assert models == []

    @pytest.mark.asyncio
    async def test_list_models_filters_non_dict(self, provider):
        """Test list_models() filters out non-dict entries."""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.raise_for_status = MagicMock()
        mock_response.json = AsyncMock(return_value={
            "models": [
                {"name": "llama3.1:8b"},
                "invalid",
                {"name": "llama3.2:3b"},
                123,
            ]
        })

        with patch.object(provider, '_get_session') as mock_session:
            mock_session_obj = AsyncMock()
            mock_session_obj.get = MagicMock(return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_response)))
            mock_session.return_value = mock_session_obj

            models = await provider.list_models()

            assert len(models) == 2
            assert all(isinstance(m, dict) for m in models)


class TestOllamaPullModel:
    """Tests for OllamaProvider.pull_model() method."""

    @pytest.fixture
    def provider(self):
        """Create an OllamaProvider instance."""
        return OllamaProvider()

    @pytest.mark.asyncio
    async def test_pull_model_success(self, provider):
        """Test successful pull_model() call."""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.raise_for_status = MagicMock()

        with patch.object(provider, '_get_session') as mock_session:
            mock_session_obj = AsyncMock()
            mock_post = MagicMock(return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_response)))
            mock_session_obj.post = mock_post
            mock_session.return_value = mock_session_obj

            await provider.pull_model("llama3.1:8b")

            # Verify request
            call_args = mock_post.call_args
            assert call_args[0][0] == "http://localhost:11434/api/pull"
            request_body = call_args[1]['json']
            assert request_body['name'] == "llama3.1:8b"
            assert request_body['stream'] is False

    @pytest.mark.asyncio
    async def test_pull_model_http_error(self, provider):
        """Test pull_model() when HTTP error occurs."""
        error_response = AsyncMock()
        error_response.raise_for_status = MagicMock(side_effect=aiohttp.ClientResponseError(
            request_info=MagicMock(),
            history=(),
            status=404,
            message="Model not found"
        ))

        with patch.object(provider, '_get_session') as mock_session:
            mock_session_obj = AsyncMock()
            mock_session_obj.post = MagicMock(return_value=AsyncMock(__aenter__=AsyncMock(return_value=error_response)))
            mock_session.return_value = mock_session_obj

            with pytest.raises(aiohttp.ClientResponseError):
                await provider.pull_model("nonexistent-model")


class TestOllamaIsAvailable:
    """Tests for OllamaProvider.is_available() method."""

    @pytest.fixture
    def provider(self):
        """Create an OllamaProvider instance."""
        return OllamaProvider()

    @pytest.mark.asyncio
    async def test_is_available_true(self, provider):
        """Test is_available() when server is available."""
        mock_response = AsyncMock()
        mock_response.status = 200

        with patch.object(provider, '_get_session') as mock_session:
            mock_session_obj = AsyncMock()
            mock_session_obj.get = MagicMock(return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_response)))
            mock_session.return_value = mock_session_obj

            result = await provider.is_available()

            assert result is True

    @pytest.mark.asyncio
    async def test_is_available_false_status(self, provider):
        """Test is_available() when server returns non-200 status."""
        mock_response = AsyncMock()
        mock_response.status = 500

        with patch.object(provider, '_get_session') as mock_session:
            mock_session_obj = AsyncMock()
            mock_session_obj.get = MagicMock(return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_response)))
            mock_session.return_value = mock_session_obj

            result = await provider.is_available()

            assert result is False

    @pytest.mark.asyncio
    async def test_is_available_connection_error(self, provider):
        """Test is_available() when connection error occurs."""
        with patch.object(provider, '_get_session') as mock_session:
            mock_session_obj = AsyncMock()
            mock_session_obj.get = MagicMock(side_effect=aiohttp.ClientConnectionError("Connection failed"))
            mock_session.return_value = mock_session_obj

            result = await provider.is_available()

            assert result is False

    @pytest.mark.asyncio
    async def test_is_available_os_error(self, provider):
        """Test is_available() when OS error occurs."""
        with patch.object(provider, '_get_session') as mock_session:
            mock_session_obj = AsyncMock()
            mock_session_obj.get = MagicMock(side_effect=OSError("Network error"))
            mock_session.return_value = mock_session_obj

            result = await provider.is_available()

            assert result is False
