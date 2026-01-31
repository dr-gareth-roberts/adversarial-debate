# Troubleshooting

Common issues and their solutions.

## Installation Issues

### `pip install` fails with dependency errors

**Symptom:**
```
ERROR: Could not find a version that satisfies the requirement ...
```

**Solution:**
1. Ensure Python 3.11+ is installed:
   ```bash
   python --version
   ```
2. Try using `uv` for faster, more reliable installation:
   ```bash
   pip install uv
   uv pip install adversarial-debate
   ```

### ImportError after installation

**Symptom:**
```python
ImportError: No module named 'adversarial_debate'
```

**Solution:**
1. Check the package is installed:
   ```bash
   pip show adversarial-debate
   ```
2. Ensure you're using the correct Python:
   ```bash
   which python
   pip list | grep adversarial
   ```
3. If using a virtual environment, ensure it's activated.

---

## API Key Issues

### "ANTHROPIC_API_KEY not set"

**Symptom:**
```
Error: ANTHROPIC_API_KEY environment variable is not set
```

**Solution:**
1. Set the API key:
   ```bash
   export ANTHROPIC_API_KEY="sk-ant-..."
   ```
2. Or add to your shell profile (`~/.bashrc`, `~/.zshrc`):
   ```bash
   echo 'export ANTHROPIC_API_KEY="sk-ant-..."' >> ~/.zshrc
   source ~/.zshrc
   ```
3. Or use a `.env` file in your project:
   ```
   ANTHROPIC_API_KEY=sk-ant-...
   ```

### "Invalid API key"

**Symptom:**
```
Error: Invalid API key provided
```

**Solution:**
1. Verify the key at [console.anthropic.com](https://console.anthropic.com)
2. Check for trailing whitespace in the key
3. Ensure the key hasn't been revoked
4. Regenerate the key if needed

### Rate limit errors

**Symptom:**
```
Error: Rate limit exceeded. Please retry after X seconds.
```

**Solution:**
1. Wait for the rate limit to reset
2. Use caching to reduce API calls:
   ```bash
   adversarial-debate run src/ --cache
   ```
3. Reduce parallelism:
   ```bash
   adversarial-debate run src/ --max-parallel 1
   ```
4. Consider upgrading your API tier

---

## Provider Issues

### OpenAI provider not working

**Symptom:**
```
Error: OpenAI provider requires openai package
```

**Solution:**
```bash
pip install adversarial-debate[openai]
```

### Azure OpenAI authentication failure

**Symptom:**
```
Error: Azure authentication failed
```

**Solution:**
1. Verify all required environment variables:
   ```bash
   echo $AZURE_OPENAI_API_KEY
   echo $AZURE_OPENAI_ENDPOINT
   echo $AZURE_OPENAI_DEPLOYMENT
   ```
2. Check the endpoint format (should not include `/openai/...`)
3. Verify the deployment name matches exactly

### Ollama connection refused

**Symptom:**
```
Error: Connection refused to localhost:11434
```

**Solution:**
1. Ensure Ollama is running:
   ```bash
   ollama serve
   ```
2. Check if a model is available:
   ```bash
   ollama list
   ```
3. Pull a model if needed:
   ```bash
   ollama pull llama3
   ```
4. For remote Ollama, set the base URL:
   ```bash
   export OLLAMA_BASE_URL="http://your-server:11434"
   ```

---

## Docker/Sandbox Issues

### "Docker not found"

**Symptom:**
```
Error: Docker is required for sandbox execution
```

**Solution:**
1. Install Docker:
   - **macOS:** `brew install --cask docker`
   - **Linux:** Follow [Docker installation guide](https://docs.docker.com/engine/install/)
2. Start Docker Desktop or the Docker daemon
3. Verify Docker works:
   ```bash
   docker run hello-world
   ```

### Docker permission denied

**Symptom:**
```
Error: permission denied while trying to connect to the Docker daemon
```

**Solution (Linux):**
```bash
sudo usermod -aG docker $USER
newgrp docker
```

Then log out and back in.

### Sandbox timeout

**Symptom:**
```
Error: Sandbox execution timed out after 30 seconds
```

**Solution:**
1. Increase the timeout:
   ```bash
   adversarial-debate run src/ --sandbox-timeout 60
   ```
2. Disable sandbox if not needed:
   ```bash
   adversarial-debate run src/ --no-sandbox
   ```

---

## Analysis Issues

### "No files to analyse"

**Symptom:**
```
Warning: No files matched the target pattern
```

**Solution:**
1. Check the target path exists:
   ```bash
   ls src/
   ```
2. Use explicit file patterns:
   ```bash
   adversarial-debate run "src/**/*.py"
   ```
3. Check `.gitignore` isn't excluding files

### Analysis takes too long

**Symptom:** Analysis runs for hours without completing.

**Solution:**
1. Limit the scope:
   ```bash
   adversarial-debate run src/api/  # Specific directory
   ```
2. Use quick mode:
   ```bash
   adversarial-debate run src/ --quick
   ```
3. Limit file count:
   ```bash
   adversarial-debate run src/ --max-files 10
   ```
4. Use caching:
   ```bash
   adversarial-debate run src/ --cache
   ```

### Empty or minimal findings

**Symptom:** Analysis completes but finds nothing in obviously vulnerable code.

**Solution:**
1. Check the provider is working:
   ```bash
   adversarial-debate run examples/vulnerable.py --provider mock
   ```
2. Verify code is being read correctly:
   ```bash
   adversarial-debate analyse src/file.py --debug
   ```
3. Check file isn't too large (may be truncated)
4. Try with a more capable model:
   ```bash
   adversarial-debate run src/ --model claude-sonnet-4-20250514
   ```

### JSON parse errors

**Symptom:**
```
Error: Failed to parse response as JSON
```

**Solution:**
1. This usually means the LLM produced malformed output
2. Retry the analysis (responses can vary)
3. Try a different model (larger models are more reliable)
4. Report persistent issues as bugs

---

## Output Issues

### Can't open HTML report

**Symptom:** HTML file appears corrupted or blank.

**Solution:**
1. Check the file was generated:
   ```bash
   ls -la output/run-*/report.html
   ```
2. Open in a different browser
3. Check file permissions:
   ```bash
   chmod 644 output/run-*/report.html
   ```

### SARIF not recognised by IDE

**Symptom:** VS Code doesn't show SARIF results.

**Solution:**
1. Install SARIF Viewer extension
2. Check SARIF file is valid:
   ```bash
   python -m json.tool output/run-*/report.sarif
   ```
3. Ensure file paths in SARIF match your workspace

### Bundle file is too large

**Symptom:** `bundle.json` is several MB.

**Solution:**
1. Limit findings:
   ```bash
   adversarial-debate run src/ --max-findings 100
   ```
2. Archive old runs:
   ```bash
   gzip output/run-*/bundle.json
   ```

---

## CI/CD Issues

### GitHub Action fails with timeout

**Symptom:**
```
Error: Job timed out after 360 minutes
```

**Solution:**
1. Limit analysis scope:
   ```yaml
   - run: adversarial-debate run src/ --quick --max-files 20
   ```
2. Use caching:
   ```yaml
   - uses: actions/cache@v3
     with:
       path: ~/.cache/adversarial-debate
       key: adversarial-${{ hashFiles('src/**/*.py') }}
   ```

### Secret not available in workflow

**Symptom:**
```
Error: ANTHROPIC_API_KEY is empty
```

**Solution:**
1. Add secret to repository settings
2. Reference correctly in workflow:
   ```yaml
   env:
     ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
   ```
3. For forks, secrets aren't available by default (security feature)

### Pre-commit hook slows down commits

**Symptom:** Commits take minutes due to analysis.

**Solution:**
1. Use quick mode in pre-commit:
   ```yaml
   - repo: local
     hooks:
       - id: adversarial-debate
         args: ["--quick", "--fail-threshold", "CRITICAL"]
   ```
2. Only run on changed files:
   ```yaml
   args: ["--changed-only"]
   ```
3. Move full analysis to CI instead of pre-commit

---

## Performance Issues

### High memory usage

**Symptom:** Process uses several GB of RAM.

**Solution:**
1. Limit parallel execution:
   ```bash
   adversarial-debate run src/ --max-parallel 1
   ```
2. Process files in batches
3. Increase swap space if needed

### Slow on large codebases

**Symptom:** Analysis of 1000+ files is very slow.

**Solution:**
1. Use incremental analysis:
   ```bash
   adversarial-debate run src/ --changed-only
   ```
2. Analyse critical paths only:
   ```bash
   adversarial-debate run src/api/ src/auth/
   ```
3. Use baseline tracking to skip unchanged code

---

## Debugging

### Enable debug logging

```bash
adversarial-debate run src/ --debug
```

Or set environment variable:
```bash
export ADVERSARIAL_DEBUG=1
```

### View raw LLM responses

```bash
adversarial-debate run src/ --debug --show-prompts
```

### Check bead store

```bash
# View recent beads
tail -5 beads/ledger.jsonl | jq .

# Count beads by type
jq -s 'group_by(.bead_type) | map({type: .[0].bead_type, count: length})' \
  beads/ledger.jsonl
```

### Validate configuration

```bash
adversarial-debate config show
adversarial-debate config validate
```

---

## Getting Help

If you're still stuck:

1. **Search existing issues:**
   [GitHub Issues](https://github.com/dr-gareth-roberts/adverserial-debate/issues)

2. **Check the FAQ:**
   [FAQ](faq.md)

3. **Open a new issue with:**
   - Error message and full traceback
   - Command that caused the error
   - Python version (`python --version`)
   - Package version (`pip show adversarial-debate`)
   - Operating system
   - Debug output (`--debug`)

## See Also

- [FAQ](faq.md) — Frequently asked questions
- [Configuration](../guides/configuration.md) — Configuration options
- [CLI Reference](../guides/cli-reference.md) — Command reference
