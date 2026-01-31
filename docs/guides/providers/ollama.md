# Ollama Provider

Ollama runs large language models locally on your machine. Use it for air-gapped environments, privacy-sensitive analysis, or to avoid API costs.

## Quick Setup

```bash
# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Pull a model
ollama pull llama3.1

# Configure Adversarial Debate
export LLM_PROVIDER=ollama
export OLLAMA_BASE_URL=http://localhost:11434
export LLM_MODEL=llama3.1
```

## When to Use Ollama

**Best for:**
- Air-gapped or offline environments
- Sensitive code that cannot leave your network
- Cost reduction (no per-token charges)
- Experimentation with different models

**Consider alternatives when:**
- You need highest-quality security analysis
- Hardware is limited
- Fast response times are critical

## Installation

### macOS

```bash
brew install ollama
```

### Linux

```bash
curl -fsSL https://ollama.com/install.sh | sh
```

### Windows

Download from [ollama.com/download](https://ollama.com/download).

### Docker

```bash
docker run -d -v ollama:/root/.ollama -p 11434:11434 --name ollama ollama/ollama
```

## Pulling Models

Download models before using them:

```bash
# Recommended for security analysis
ollama pull llama3.1:70b  # Best quality (requires ~40GB RAM)
ollama pull llama3.1       # Good balance (requires ~8GB RAM)
ollama pull codellama      # Code-focused

# Smaller models for limited hardware
ollama pull llama3.2       # Smaller model
ollama pull phi3           # Very small, fast
```

## Hardware Requirements

| Model | RAM Required | GPU Memory | Notes |
|-------|--------------|------------|-------|
| llama3.1:70b | 40GB+ | 48GB+ | Best quality |
| llama3.1 (8B) | 8GB | 8GB | Good balance |
| codellama | 8GB | 8GB | Code-focused |
| phi3 | 4GB | 4GB | Fast, limited quality |

**GPU acceleration:** Ollama automatically uses GPU if available. For best performance, use NVIDIA with CUDA or Apple Silicon.

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `LLM_PROVIDER` | — | Set to `ollama` |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama server URL |
| `LLM_MODEL` | `llama3.1` | Model to use |
| `LLM_TIMEOUT` | `300` | Timeout (local models are slower) |

### Configuration File

```json
{
  "provider": {
    "provider": "ollama",
    "base_url": "http://localhost:11434",
    "model": "llama3.1",
    "timeout_seconds": 300,
    "temperature": 0.7,
    "extra": {
      "num_ctx": 8192,
      "num_gpu": 1
    }
  }
}
```

## Recommended Models

### For Security Analysis

| Model | Quality | Speed | RAM |
|-------|---------|-------|-----|
| `llama3.1:70b` | Excellent | Slow | 40GB+ |
| `llama3.1` | Good | Medium | 8GB |
| `codellama:34b` | Very Good | Slow | 20GB+ |

### For Development/Testing

| Model | Quality | Speed | RAM |
|-------|---------|-------|-----|
| `llama3.2` | Moderate | Fast | 4GB |
| `phi3` | Basic | Very Fast | 4GB |

## Running Ollama as a Service

### Linux (systemd)

```bash
# Ollama installs as a service automatically
sudo systemctl enable ollama
sudo systemctl start ollama
```

### macOS (launchd)

```bash
# Starts automatically after installation
# Or run manually:
ollama serve
```

### Docker Compose

```yaml
version: '3'
services:
  ollama:
    image: ollama/ollama
    ports:
      - "11434:11434"
    volumes:
      - ollama:/root/.ollama
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]

volumes:
  ollama:
```

## Remote Ollama Server

Run Ollama on a powerful server and connect remotely:

### On the Server

```bash
# Allow remote connections
OLLAMA_HOST=0.0.0.0:11434 ollama serve
```

### On the Client

```bash
export OLLAMA_BASE_URL=http://your-server:11434
export LLM_PROVIDER=ollama
adversarial-debate run src/
```

**Security:** Use SSH tunnelling or VPN for remote access. Ollama has no authentication by default.

## Performance Tuning

### GPU Optimisation

```json
{
  "provider": {
    "provider": "ollama",
    "extra": {
      "num_gpu": 1,
      "main_gpu": 0
    }
  }
}
```

### Context Length

Increase context for larger files:

```json
{
  "provider": {
    "extra": {
      "num_ctx": 16384
    }
  }
}
```

### Parallel Requests

Ollama handles one request at a time by default. For parallel analysis:

```bash
# Run multiple Ollama instances on different ports
OLLAMA_HOST=0.0.0.0:11434 ollama serve &
OLLAMA_HOST=0.0.0.0:11435 ollama serve &
```

## Troubleshooting

### "Connection refused"

Check Ollama is running:

```bash
ollama list
curl http://localhost:11434/api/tags
```

Start if needed:

```bash
ollama serve
```

### "Model not found"

Pull the model first:

```bash
ollama pull llama3.1
ollama list  # Verify it's downloaded
```

### Slow Responses

Options:
1. Use a smaller model
2. Increase timeout: `LLM_TIMEOUT=600`
3. Use GPU acceleration
4. Reduce `--parallel` to avoid resource contention

### Out of Memory

Options:
1. Use a smaller model
2. Close other applications
3. Reduce context length in config
4. Add swap space (temporary fix)

## Quality Comparison

Local models typically produce less accurate results than cloud providers:

| Aspect | Ollama (llama3.1) | Anthropic (Claude) |
|--------|-------------------|-------------------|
| SQL injection detection | Good | Excellent |
| Complex logic bugs | Moderate | Excellent |
| False positive rate | Higher | Lower |
| Context understanding | Good | Excellent |

**Recommendation:** Use Ollama for development/testing, cloud providers for production security analysis.

## See Also

- [Provider Index](index.md) — Compare all providers
- [Mock Provider](mock.md) — For testing without any LLM
- [Configuration Guide](../configuration.md) — All options
