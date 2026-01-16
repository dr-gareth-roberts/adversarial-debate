.PHONY: demo lint format typecheck test

# Deterministic demo (no API key required)
demo:
	LLM_PROVIDER=mock ADVERSARIAL_BEAD_LEDGER=output/ledger.jsonl python3 -m adversarial_debate.cli run examples/mini-app/ --output output

lint:
	uv run ruff check src/

format:
	uv run ruff format src/

typecheck:
	uv run mypy src/adversarial_debate --ignore-missing-imports

test:
	uv run pytest tests/ -v
