"""Comprehensive tests for SandboxExecutor Docker execution paths."""

import asyncio
import json
import os
import signal
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from adversarial_debate.sandbox import (
    ExecutionResult,
    SandboxConfig,
    SandboxExecutor,
    SandboxSecurityError,
)


class TestSandboxExecutorDocker:
    """Tests for SandboxExecutor Docker execution paths."""

    @pytest.fixture
    def docker_config(self):
        """Create a Docker-enabled sandbox config."""
        return SandboxConfig(
            use_docker=True,
            use_subprocess=False,
            timeout_seconds=10,
            memory_limit="256m",
            cpu_limit=0.5,
            docker_image="python:3.11-slim",
        )

    @pytest.fixture
    def executor(self, docker_config):
        """Create a SandboxExecutor with Docker config."""
        return SandboxExecutor(docker_config)

    @pytest.mark.asyncio
    async def test_docker_execution_success(self, executor):
        """Test successful Docker execution."""
        code = "print('Hello from Docker')"
        
        # Mock Docker availability
        with patch.object(executor, 'is_docker_available', return_value=True):
            # Mock subprocess execution
            mock_proc = AsyncMock()
            mock_proc.stdout = AsyncMock()
            mock_proc.stderr = AsyncMock()
            mock_proc.wait = AsyncMock(return_value=0)
            mock_proc.returncode = 0
            
            # Mock stream reading
            async def mock_read_stdout(limit):
                return b"Hello from Docker\n", False
            
            async def mock_read_stderr(limit):
                return b"", False
            
            with patch('asyncio.create_subprocess_exec', return_value=mock_proc):
                with patch('adversarial_debate.sandbox.executor._read_stream_limited') as mock_read:
                    mock_read.side_effect = [mock_read_stdout(1024), mock_read_stderr(1024)]
                    
                    result = await executor.execute_python(code, inputs={})
                    
                    assert result.success is True
                    assert "Hello from Docker" in result.output
                    assert result.exit_code == 0
                    assert result.timed_out is False

    @pytest.mark.asyncio
    async def test_docker_execution_with_inputs(self, executor):
        """Test Docker execution with input variables."""
        code = "print(f'Result: {x + y}')"
        inputs = {"x": 10, "y": 20}
        
        with patch.object(executor, 'is_docker_available', return_value=True):
            mock_proc = AsyncMock()
            mock_proc.stdout = AsyncMock()
            mock_proc.stderr = AsyncMock()
            mock_proc.wait = AsyncMock(return_value=0)
            mock_proc.returncode = 0
            
            async def mock_read_stdout(limit):
                return b"Result: 30\n", False
            
            async def mock_read_stderr(limit):
                return b"", False
            
            with patch('asyncio.create_subprocess_exec', return_value=mock_proc):
                with patch('adversarial_debate.sandbox.executor._read_stream_limited') as mock_read:
                    mock_read.side_effect = [mock_read_stdout(1024), mock_read_stderr(1024)]
                    
                    result = await executor.execute_python(code, inputs=inputs)
                    
                    assert result.success is True
                    assert "Result: 30" in result.output

    @pytest.mark.asyncio
    async def test_docker_execution_timeout(self, executor):
        """Test Docker execution timeout handling."""
        code = "import time; time.sleep(100)"
        
        with patch.object(executor, 'is_docker_available', return_value=True):
            mock_proc = AsyncMock()
            mock_proc.stdout = AsyncMock()
            mock_proc.stderr = AsyncMock()
            
            # Simulate timeout
            async def mock_wait_timeout():
                raise asyncio.TimeoutError()
            
            mock_proc.wait = mock_wait_timeout
            mock_proc.send_signal = MagicMock()
            
            async def mock_read_stdout(limit):
                return b"", False
            
            async def mock_read_stderr(limit):
                return b"", False
            
            with patch('asyncio.create_subprocess_exec', return_value=mock_proc):
                with patch('adversarial_debate.sandbox.executor._read_stream_limited') as mock_read:
                    mock_read.side_effect = [mock_read_stdout(1024), mock_read_stderr(1024)]
                    
                    result = await executor.execute_python(code, timeout=1, inputs={})
                    
                    assert result.timed_out is True
                    assert result.success is False
                    assert result.exit_code == -1
                    # Verify SIGKILL was sent
                    mock_proc.send_signal.assert_called_once_with(signal.SIGKILL)

    @pytest.mark.asyncio
    async def test_docker_execution_error(self, executor):
        """Test Docker execution with error output."""
        code = "raise ValueError('Test error')"
        
        with patch.object(executor, 'is_docker_available', return_value=True):
            mock_proc = AsyncMock()
            mock_proc.stdout = AsyncMock()
            mock_proc.stderr = AsyncMock()
            mock_proc.wait = AsyncMock(return_value=1)
            mock_proc.returncode = 1
            
            async def mock_read_stdout(limit):
                return b"", False
            
            async def mock_read_stderr(limit):
                return b"Traceback (most recent call last):\n  File \"/code/script.py\", line 1, in <module>\n    raise ValueError('Test error')\nValueError: Test error\n", False
            
            with patch('asyncio.create_subprocess_exec', return_value=mock_proc):
                with patch('adversarial_debate.sandbox.executor._read_stream_limited') as mock_read:
                    mock_read.side_effect = [mock_read_stdout(1024), mock_read_stderr(1024)]
                    
                    result = await executor.execute_python(code, inputs={})
                    
                    assert result.success is False
                    assert result.exit_code == 1
                    assert "ValueError" in result.error
                    assert "Test error" in result.error

    @pytest.mark.asyncio
    async def test_docker_command_construction(self, executor):
        """Test that Docker command is constructed correctly."""
        code = "print('test')"
        
        with patch.object(executor, 'is_docker_available', return_value=True):
            mock_proc = AsyncMock()
            mock_proc.stdout = AsyncMock()
            mock_proc.stderr = AsyncMock()
            mock_proc.wait = AsyncMock(return_value=0)
            mock_proc.returncode = 0
            
            async def mock_read_stdout(limit):
                return b"test\n", False
            
            async def mock_read_stderr(limit):
                return b"", False
            
            with patch('asyncio.create_subprocess_exec') as mock_exec:
                mock_exec.return_value = mock_proc
                with patch('adversarial_debate.sandbox.executor._read_stream_limited') as mock_read:
                    mock_read.side_effect = [mock_read_stdout(1024), mock_read_stderr(1024)]
                    
                    await executor.execute_python(code, inputs={})
                    
                    # Verify command structure
                    call_args = mock_exec.call_args[0]
                    assert call_args[0] == "docker"
                    assert call_args[1] == "run"
                    assert "--rm" in call_args
                    assert "--memory=256m" in call_args
                    assert "--cpus=0.5" in call_args
                    assert "--network=none" in call_args
                    assert "--read-only" in call_args
                    assert "--security-opt=no-new-privileges" in call_args
                    assert "python:3.11-slim" in call_args
                    assert "python" in call_args
                    assert "/code/script.py" in call_args

    @pytest.mark.asyncio
    async def test_docker_temp_file_creation(self, executor):
        """Test that temporary file is created and cleaned up."""
        code = "print('test')"
        
        with patch.object(executor, 'is_docker_available', return_value=True):
            mock_proc = AsyncMock()
            mock_proc.stdout = AsyncMock()
            mock_proc.stderr = AsyncMock()
            mock_proc.wait = AsyncMock(return_value=0)
            mock_proc.returncode = 0
            
            async def mock_read_stdout(limit):
                return b"test\n", False
            
            async def mock_read_stderr(limit):
                return b"", False
            
            temp_files_created = []
            
            def track_temp_file(*args, **kwargs):
                # Track the temp file path from volume mount
                for arg in args:
                    if isinstance(arg, str) and arg.startswith("-v"):
                        continue
                    if isinstance(arg, str) and ":/code/script.py:ro" in arg:
                        temp_path = arg.split(":")[0]
                        temp_files_created.append(temp_path)
                return mock_proc
            
            with patch('asyncio.create_subprocess_exec', side_effect=track_temp_file):
                with patch('adversarial_debate.sandbox.executor._read_stream_limited') as mock_read:
                    mock_read.side_effect = [mock_read_stdout(1024), mock_read_stderr(1024)]
                    
                    await executor.execute_python(code, inputs={})
                    
                    # Verify temp file was created (and should be cleaned up)
                    # The file should not exist after execution
                    for temp_file in temp_files_created:
                        assert not os.path.exists(temp_file)

    @pytest.mark.asyncio
    async def test_docker_network_enabled(self, docker_config):
        """Test Docker execution with network enabled."""
        docker_config.network_enabled = True
        executor = SandboxExecutor(docker_config)
        
        code = "print('test')"
        
        with patch.object(executor, 'is_docker_available', return_value=True):
            mock_proc = AsyncMock()
            mock_proc.stdout = AsyncMock()
            mock_proc.stderr = AsyncMock()
            mock_proc.wait = AsyncMock(return_value=0)
            mock_proc.returncode = 0
            
            async def mock_read_stdout(limit):
                return b"test\n", False
            
            async def mock_read_stderr(limit):
                return b"", False
            
            with patch('asyncio.create_subprocess_exec') as mock_exec:
                mock_exec.return_value = mock_proc
                with patch('adversarial_debate.sandbox.executor._read_stream_limited') as mock_read:
                    mock_read.side_effect = [mock_read_stdout(1024), mock_read_stderr(1024)]
                    
                    await executor.execute_python(code, inputs={})
                    
                    # Verify --network=none is NOT in command
                    call_args = mock_exec.call_args[0]
                    assert "--network=none" not in call_args

    @pytest.mark.asyncio
    async def test_docker_read_write_mode(self, docker_config):
        """Test Docker execution with read-write mode."""
        docker_config.read_only = False
        executor = SandboxExecutor(docker_config)
        
        code = "print('test')"
        
        with patch.object(executor, 'is_docker_available', return_value=True):
            mock_proc = AsyncMock()
            mock_proc.stdout = AsyncMock()
            mock_proc.stderr = AsyncMock()
            mock_proc.wait = AsyncMock(return_value=0)
            mock_proc.returncode = 0
            
            async def mock_read_stdout(limit):
                return b"test\n", False
            
            async def mock_read_stderr(limit):
                return b"", False
            
            with patch('asyncio.create_subprocess_exec') as mock_exec:
                mock_exec.return_value = mock_proc
                with patch('adversarial_debate.sandbox.executor._read_stream_limited') as mock_read:
                    mock_read.side_effect = [mock_read_stdout(1024), mock_read_stderr(1024)]
                    
                    await executor.execute_python(code, inputs={})
                    
                    # Verify --read-only is NOT in command
                    call_args = mock_exec.call_args[0]
                    assert "--read-only" not in call_args

    @pytest.mark.asyncio
    async def test_docker_not_available_fallback(self, executor):
        """Test fallback when Docker is not available."""
        code = "print('test')"
        
        with patch.object(executor, 'is_docker_available', return_value=False):
            # Should fall back to subprocess if enabled
            executor.config.use_subprocess = True
            
            result = await executor.execute_python(code, inputs={})
            
            # Should succeed via subprocess
            assert result.success is True

    @pytest.mark.asyncio
    async def test_docker_not_available_no_fallback(self, executor):
        """Test error when Docker is not available and no fallback."""
        code = "print('test')"
        executor.config.use_subprocess = False
        
        with patch.object(executor, 'is_docker_available', return_value=False):
            result = await executor.execute_python(code, inputs={})
            
            assert result.success is False
            assert "No execution backend available" in result.error

    @pytest.mark.asyncio
    async def test_docker_security_validation_failure(self, executor):
        """Test that security validation prevents execution."""
        # Code too large
        code = "x" * (2 * 1024 * 1024)  # 2MB
        
        with patch.object(executor, 'is_docker_available', return_value=True):
            result = await executor.execute_python(code, inputs={})
            
            assert result.success is False
            assert "Security validation failed" in result.error

    @pytest.mark.asyncio
    async def test_docker_output_truncation(self, executor):
        """Test that large output is truncated."""
        code = "print('x' * 10000)"
        
        with patch.object(executor, 'is_docker_available', return_value=True):
            mock_proc = AsyncMock()
            mock_proc.stdout = AsyncMock()
            mock_proc.stderr = AsyncMock()
            mock_proc.wait = AsyncMock(return_value=0)
            mock_proc.returncode = 0
            
            async def mock_read_stdout(limit):
                # Simulate truncation
                return b"x" * 1000, True
            
            async def mock_read_stderr(limit):
                return b"", False
            
            with patch('asyncio.create_subprocess_exec', return_value=mock_proc):
                with patch('adversarial_debate.sandbox.executor._read_stream_limited') as mock_read:
                    mock_read.side_effect = [mock_read_stdout(1024), mock_read_stderr(1024)]
                    
                    result = await executor.execute_python(code, inputs={})
                    
                    assert result.success is True
                    assert "[stdout truncated]" in result.output


class TestSandboxExecutorExploit:
    """Tests for SandboxExecutor exploit execution."""

    @pytest.fixture
    def executor(self):
        """Create a SandboxExecutor."""
        config = SandboxConfig(use_docker=False, use_subprocess=True, timeout_seconds=5)
        return SandboxExecutor(config)

    @pytest.mark.asyncio
    async def test_execute_exploit_success(self, executor):
        """Test successful exploit execution."""
        target_code = """
def vulnerable_function(user_input):
    return eval(user_input)
"""
        exploit_code = """
result = vulnerable_function("1 + 1")
print(f"Result: {result}")
"""
        
        result = await executor.execute_exploit(target_code, exploit_code)
        
        assert result.success is True
        assert "EXPLOIT_SUCCESS" in result.output
        assert "Result: 2" in result.output

    @pytest.mark.asyncio
    async def test_execute_exploit_failure(self, executor):
        """Test failed exploit execution."""
        target_code = """
def safe_function(user_input):
    return int(user_input)
"""
        exploit_code = """
result = safe_function("not a number")
"""
        
        result = await executor.execute_exploit(target_code, exploit_code)
        
        assert "EXPLOIT_FAILED" in result.output

    @pytest.mark.asyncio
    async def test_verify_finding_confirmed(self, executor):
        """Test finding verification when exploit succeeds."""
        target_code = """
def vulnerable_function(user_input):
    return eval(user_input)
"""
        poc_code = """
result = vulnerable_function("__import__('os').system('echo VULNERABLE')")
"""
        
        verified, explanation = await executor.verify_finding(
            target_code, poc_code, "Should execute arbitrary code"
        )
        
        assert verified is True
        assert "Vulnerability confirmed" in explanation

    @pytest.mark.asyncio
    async def test_verify_finding_timeout(self, executor):
        """Test finding verification when exploit times out."""
        target_code = """
def slow_function():
    import time
    time.sleep(100)
"""
        poc_code = """
slow_function()
"""
        
        verified, explanation = await executor.verify_finding(
            target_code, poc_code, "Should timeout"
        )
        
        assert verified is False
        assert "timed out" in explanation.lower()


class TestSandboxExecutorDockerAvailability:
    """Tests for Docker availability detection."""

    @pytest.fixture
    def executor(self):
        """Create a SandboxExecutor."""
        config = SandboxConfig(use_docker=True, use_subprocess=False)
        return SandboxExecutor(config)

    def test_docker_available(self, executor):
        """Test detection when Docker is available."""
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            
            result = executor.is_docker_available()
            
            assert result is True
            mock_run.assert_called_once_with(
                ["docker", "version"],
                capture_output=True,
                timeout=5,
            )

    def test_docker_not_available(self, executor):
        """Test detection when Docker is not available."""
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(returncode=1)
            
            result = executor.is_docker_available()
            
            assert result is False

    def test_docker_timeout(self, executor):
        """Test detection when Docker command times out."""
        import subprocess
        
        with patch('subprocess.run') as mock_run:
            mock_run.side_effect = subprocess.TimeoutExpired("docker", 5)
            
            result = executor.is_docker_available()
            
            assert result is False

    def test_docker_not_found(self, executor):
        """Test detection when Docker is not installed."""
        with patch('subprocess.run') as mock_run:
            mock_run.side_effect = FileNotFoundError()
            
            result = executor.is_docker_available()
            
            assert result is False

    def test_docker_availability_cached(self, executor):
        """Test that Docker availability is cached."""
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            
            # Call twice
            result1 = executor.is_docker_available()
            result2 = executor.is_docker_available()
            
            # Should only call subprocess once
            assert mock_run.call_count == 1
            assert result1 is True
            assert result2 is True
