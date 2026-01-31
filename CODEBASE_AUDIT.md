# Codebase Audit (adversarial-debate)

Date: 2026-01-29

Scope: all **git-tracked** files (`git ls-files`, 119 files). I ran `ruff`, `mypy`, and `pytest` and aligned docs/examples/CI/Action/Compose to the canonical `src/` APIs.

## Current Status (post-fixes)

- `ruff check src tests`: ✅
- `ruff format --check src tests`: ✅
- `mypy src` (strict via `pyproject.toml`): ✅
- `pytest`: ✅ (`293 passed, 1 skipped`, `294 collected` on macOS)

## High-Impact Issues Found (and Fixed)

1. **API drift** across `src/`, `tests/`, `docs/`, `examples/`, GitHub Action, and Docker Compose.
   - Standardized on `src/` as canonical.
   - Updated docs/examples/tests/action/compose to match the current sandbox/result/provider APIs.
2. **Config + schema mismatch**
   - `adversarial_debate.config.Config` delegates sandbox config to `adversarial_debate.sandbox.SandboxConfig`.
   - `schemas/config.schema.json` updated to reflect the real config structure (with a small legacy-keys section).
3. **CLI provider config not wired**
   - CLI now constructs a runtime `providers.base.ProviderConfig` from `Config.provider` and passes it to `get_provider(...)`.
4. **CI/Dev ergonomics drift**
   - Fixed `uv` usage (`uv sync --extra dev`), added `--frozen` in CI, and ensured ruff/mypy run against `src` + `tests`.
5. **Repo hygiene / secret scanning**
   - Removed tracked `.bevel/do_not_share/*` artefacts.
   - Added `.secrets.baseline` for `detect-secrets`.
   - Moved the “example workflow” out of `.github/workflows/` so forks/PRs don’t fail due to missing secrets.
6. **Docker + Compose drift**
   - `Dockerfile` now supports `INSTALL_DEV` to build a test image with pytest/ruff/mypy.
   - `docker-compose.yml` test service overrides entrypoint correctly.

## Follow-ups (completed)

- **Sandbox behaviour in containers**
  - Documented the “Docker backend is host-oriented” story; containerized runs typically fall back to the subprocess backend unless Docker daemon access is explicitly provided.
- **Permissions hardening**
  - Best-effort restrictive perms for bead ledger + cache outputs (dirs `0700`, files `0600`).
- **Docs deep pass**
  - Updated `docs/architecture.md` and `docs/pipeline.md` to match current CLI behaviour and output paths.
- **Import-cycle guard**
  - Added `scripts/check_import_cycles.py` and a CI step to catch future regressions.
- **Prompt JSON examples**
  - Updated agent system prompts to show valid JSON examples (no pseudo-values like `0-100` / `true/false`); constraints are now listed as plain text.
- **Exception unification**
  - Unified `SandboxSecurityError` to the canonical type in `adversarial_debate.exceptions`.

## Reproduce the Checks

```bash
uv sync --extra dev
uv run ruff check src tests
uv run ruff format --check src tests
uv run mypy src
uv run python scripts/check_import_cycles.py
uv run pytest tests -q
```
