# Installation

This guide covers all methods of installing Adversarial Debate and verifying your setup.

## Requirements

| Requirement | Version | Notes |
|-------------|---------|-------|
| Python | 3.11+ | Required |
| Docker | Any recent | Required for hardened sandbox; optional otherwise |
| API Key | — | Required for real analysis; not needed for mock provider |

## Installation Methods

### Using uv (Recommended)

[uv](https://github.com/astral-sh/uv) is a fast Python package manager. It's the recommended way to install Adversarial Debate.

```bash
# Install uv if you haven't already
curl -LsSf https://astral.sh/uv/install.sh | sh

# Add to your project
uv add adversarial-debate

# Or install globally
uv tool install adversarial-debate
```

### Using pip

```bash
pip install adversarial-debate
```

### From Source

For development or to get the latest unreleased changes:

```bash
git clone https://github.com/dr-gareth-roberts/adversarial-debate.git
cd adversarial-debate

# Install with development dependencies
uv sync --extra dev

# Or with pip
pip install -e ".[dev]"
```

### With Optional Providers

The default installation includes the Anthropic provider. To use other providers:

```bash
# OpenAI support
uv add "adversarial-debate[openai]"

# All providers
uv add "adversarial-debate[all-providers]"
```

## Verification

After installation, verify everything is working:

```bash
# Check the CLI is available
adversarial-debate --version

# Run a quick test with the mock provider
LLM_PROVIDER=mock adversarial-debate analyze exploit examples/mini-app/app.py
```

You should see output showing findings from the mock provider.

## Docker Setup

Docker is required for the hardened sandbox that safely executes code during analysis. Without Docker, the framework falls back to a subprocess-based sandbox with reduced isolation.

### Installing Docker

**macOS:**
```bash
brew install --cask docker
# Then open Docker.app to complete setup
```

**Linux (Ubuntu/Debian):**
```bash
sudo apt-get update
sudo apt-get install docker.io
sudo systemctl start docker
sudo usermod -aG docker $USER
# Log out and back in for group membership to take effect
```

**Windows:**
- Install [Docker Desktop for Windows](https://docs.docker.com/desktop/install/windows-install/)
- Enable WSL 2 backend for best performance

### Verifying Docker

```bash
# Check Docker is running
docker info

# Pull the Python image used by the sandbox
docker pull python:3.11-slim
```

## Setting Up Your Provider

The framework needs an LLM provider to analyse code. The default is Anthropic.

### Anthropic (Default)

```bash
export ANTHROPIC_API_KEY=your-key-here
```

Get your API key from [console.anthropic.com](https://console.anthropic.com/).

### Mock Provider (No API Key)

For testing and demos, use the mock provider:

```bash
export LLM_PROVIDER=mock
```

### Other Providers

See [Provider Setup](../guides/providers/index.md) for:
- [OpenAI](../guides/providers/openai.md)
- [Azure OpenAI](../guides/providers/azure.md)
- [Ollama (Local)](../guides/providers/ollama.md)

## Configuration File (Optional)

Instead of environment variables, you can use a configuration file:

```bash
# Copy the example configuration
cp .env.example .env

# Edit with your settings
nano .env
```

See [Configuration Guide](../guides/configuration.md) for all options.

## Troubleshooting Installation

### "Command not found: adversarial-debate"

Ensure the package is installed and the binary is in your PATH:

```bash
# Check if installed
pip show adversarial-debate

# Find where it's installed
which adversarial-debate

# If using uv tool install, ensure ~/.local/bin is in PATH
export PATH="$HOME/.local/bin:$PATH"
```

### "No module named 'adversarial_debate'"

You may have multiple Python installations. Ensure you're using the correct one:

```bash
# Check which Python pip is using
pip --version

# Install for a specific Python version
python3.11 -m pip install adversarial-debate
```

### Docker Permission Denied

On Linux, you may need to add your user to the docker group:

```bash
sudo usermod -aG docker $USER
# Log out and back in
```

Or run with sudo (not recommended for regular use):

```bash
sudo adversarial-debate run src/
```

### SSL Certificate Errors

If you see SSL errors when connecting to providers, ensure your system certificates are up to date:

```bash
# macOS
brew install ca-certificates

# Ubuntu/Debian
sudo apt-get update && sudo apt-get install ca-certificates
```

## Next Steps

- **[Your First Analysis](first-analysis.md)** — Step-by-step tutorial
- **[Configuration Guide](../guides/configuration.md)** — Customise the framework
- **[CLI Reference](../guides/cli-reference.md)** — Explore all commands
