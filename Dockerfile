# Adversarial Debate - Docker Image
#
# Build:
#   docker build -t adversarial-debate .
#
# Build with all providers:
#   docker build --build-arg INSTALL_ALL_PROVIDERS=true -t adversarial-debate:full .
#
# Run with Anthropic:
#   docker run -e ANTHROPIC_API_KEY=your-key -e ADVERSARIAL_OUTPUT_DIR=/output -v $(pwd)/output:/output adversarial-debate analyze exploit /code
#
# Run with OpenAI:
#   docker run -e OPENAI_API_KEY=your-key -e LLM_PROVIDER=openai -e ADVERSARIAL_OUTPUT_DIR=/output -v $(pwd)/output:/output adversarial-debate analyze exploit /code
#
# Run with Ollama (requires Ollama running):
#   docker run --network host -e LLM_PROVIDER=ollama -e ADVERSARIAL_OUTPUT_DIR=/output -v $(pwd)/output:/output adversarial-debate analyze exploit /code
#
# Mount code for analysis:
#   docker run -v $(pwd):/code -v $(pwd)/output:/output -e ANTHROPIC_API_KEY=your-key -e ADVERSARIAL_OUTPUT_DIR=/output adversarial-debate analyze exploit /code

# =============================================================================
# Stage 1: Build stage
# =============================================================================
FROM python:3.11-slim AS builder

# Build arguments for optional providers
ARG INSTALL_ALL_PROVIDERS=false
ARG INSTALL_OPENAI=false
ARG INSTALL_DEV=false

# Set build-time variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy dependency files
WORKDIR /app
COPY pyproject.toml README.md ./
COPY src/ src/

# Install the package with optional providers
RUN pip install --upgrade pip && \
    EXTRAS="" && \
    if [ "$INSTALL_DEV" = "true" ]; then \
        EXTRAS="dev"; \
    fi && \
    if [ "$INSTALL_ALL_PROVIDERS" = "true" ]; then \
        if [ -n "$EXTRAS" ]; then \
            EXTRAS="$EXTRAS,all-providers"; \
        else \
            EXTRAS="all-providers"; \
        fi; \
    elif [ "$INSTALL_OPENAI" = "true" ]; then \
        if [ -n "$EXTRAS" ]; then \
            EXTRAS="$EXTRAS,openai"; \
        else \
            EXTRAS="openai"; \
        fi; \
    fi && \
    if [ -n "$EXTRAS" ]; then \
        pip install ".[${EXTRAS}]"; \
    else \
        pip install .; \
    fi

# =============================================================================
# Stage 2: Runtime stage
# =============================================================================
FROM python:3.11-slim AS runtime

# Security labels
LABEL org.opencontainers.image.title="Adversarial Debate" \
      org.opencontainers.image.description="AI Red Team Security Testing Framework" \
      org.opencontainers.image.version="0.1.0" \
      org.opencontainers.image.source="https://github.com/dr-gareth-roberts/adversarial-debate" \
      org.opencontainers.image.licenses="MIT"

# Set runtime environment
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONFAULTHANDLER=1 \
    PATH="/opt/venv/bin:$PATH"

# Create non-root user for security
RUN groupadd --gid 1000 adversarial && \
    useradd --uid 1000 --gid adversarial --shell /bin/bash --create-home adversarial

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv

# Create directories for code mounting and output
RUN mkdir -p /code /output && \
    chown -R adversarial:adversarial /code /output

# Switch to non-root user
USER adversarial

# Set working directory
WORKDIR /code

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD adversarial-debate --version || exit 1

# Default entrypoint
ENTRYPOINT ["adversarial-debate"]

# Default command (show help)
CMD ["--help"]
