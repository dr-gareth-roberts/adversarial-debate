.PHONY: demo lint format typecheck test import-cycles

# Deterministic demo (no API key required)
demo:
	./scripts/demo.sh output

lint:
	uv run --extra dev ruff check src tests

format:
	uv run --extra dev ruff format src tests

typecheck:
	uv run --extra dev python -m mypy src

test:
	uv run --extra dev python -m pytest tests/ -v

import-cycles:
	uv run python scripts/check_import_cycles.py
