.PHONY: demo lint format typecheck test import-cycles

# Deterministic demo (no API key required)
demo:
	LLM_PROVIDER=mock ADVERSARIAL_BEAD_LEDGER=output/ledger.jsonl uv run adversarial-debate run examples/mini-app/ --output output

lint:
	uv run --extra dev ruff check src tests

format:
	uv run --extra dev ruff format src tests

typecheck:
	uv run --extra dev mypy src

test:
	uv run --extra dev pytest tests/ -v

import-cycles:
	uv run python scripts/check_import_cycles.py
